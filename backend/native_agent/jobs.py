"""Private, encrypted, service-bound operator queue; no background activation.

The external 32-byte key and this directory must be inaccessible to workloads.
Expired execution leases require operator reconciliation, never automatic retry.
"""
from contextlib import contextmanager
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import time

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .engine import FIELDS, OPTIONAL, OPERATIONS, READS
from .filesystem import Refused

MAX_BYTES = 6 * 1024 * 1024
TERMINAL = frozenset({'succeeded', 'failed', 'unknown', 'cancelled'})


class InvalidCompletionResult(Refused):
    """Completion result cannot be encoded within the queue budget."""


class ExpiredJobLease(Refused):
    """Completion refused after the job was durably marked unknown."""


def _positive_id(value):
    if type(value) is not int or value < 1:
        raise Refused('Invalid subject or service.')
    return value


def _timestamp(value):
    value = time.time() if value is None else value
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 2**53:
        raise Refused('Invalid timestamp.')
    return value


def _encode(value):
    if not isinstance(value, dict):
        raise Refused('Expected an object.')
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False, ensure_ascii=False).encode()
    except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError) as exc:
        raise Refused('Invalid job data.') from exc
    if len(encoded) > MAX_BYTES:
        raise Refused('Job data exceeds budget.')
    return encoded


def _request(operation, data, confirmed):
    if (not isinstance(operation, str) or operation not in OPERATIONS
            or (operation not in READS and confirmed is not True) or type(confirmed) is not bool):
        raise Refused('Job operation is not confirmed or supported.')
    encoded = _encode(data)
    if set(data) - FIELDS[operation] or FIELDS[operation] - OPTIONAL.get(operation, set()) - set(data):
        raise Refused('Invalid operation fields.')
    return encoded


class JobStore:
    def __init__(self, directory, *, service_id, binding_ref, key):
        self.service_id = _positive_id(service_id)
        if (not isinstance(binding_ref, str) or not 1 <= len(binding_ref) <= 128
                or not isinstance(key, bytes) or len(key) != 32):
            raise Refused('Invalid binding or external encryption key.')
        self.binding_ref = binding_ref
        self.directory = Path(directory).absolute()
        self.db = self.directory / 'jobs.sqlite3'
        self._key = key
        self._cipher = AESGCM(key)
        self._check_directory()
        try:
            fd = os.open(self.db, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        except OSError as exc:
            raise Refused('Unsafe queue database.') from exc
        try:
            self._check_file(os.fstat(fd))
        finally:
            os.close(fd)
        with self._transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS identity (id INTEGER PRIMARY KEY CHECK(id=1), service INTEGER, binding TEXT, marker BLOB)')
            row = db.execute('SELECT service,binding,marker FROM identity WHERE id=1').fetchone()
            if row is None:
                db.execute('INSERT INTO identity VALUES (1,?,?,?)',
                           (service_id, binding_ref, self._encrypt('identity', 'identity', b'queue-v1')))
            elif (row['service'], row['binding']) != (service_id, binding_ref):
                raise Refused('Queue belongs to another service binding.')
            elif self._decrypt('identity', 'identity', row['marker']) != b'queue-v1':
                raise Refused('Queue identity could not be verified.')
            db.execute('''CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, subject INTEGER NOT NULL, operation TEXT NOT NULL,
                confirmed INTEGER NOT NULL, payload BLOB NOT NULL, request_digest BLOB NOT NULL,
                idempotency BLOB, state TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
                due REAL NOT NULL, lease_hash BLOB, lease_until REAL, result BLOB,
                schedule_id TEXT, occurrence INTEGER,
                UNIQUE(subject,idempotency), UNIQUE(schedule_id,occurrence))''')
            db.execute('''CREATE TABLE IF NOT EXISTS schedules (
                id TEXT PRIMARY KEY, subject INTEGER NOT NULL, operation TEXT NOT NULL,
                confirmed INTEGER NOT NULL, payload BLOB NOT NULL, interval INTEGER NOT NULL,
                starts REAL NOT NULL, last_slot INTEGER NOT NULL DEFAULT -1,
                cancelled INTEGER NOT NULL DEFAULT 0)''')

    def _check_directory(self):
        try:
            info = self.directory.lstat()
            if (self.directory.resolve() != self.directory or not stat.S_ISDIR(info.st_mode)
                    or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077):
                raise Refused('Private operator-owned queue directory required.')
        except OSError as exc:
            raise Refused('Private queue directory unavailable.') from exc

    @staticmethod
    def _check_file(info):
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise Refused('Unsafe queue database or journal.')

    @contextmanager
    def _transaction(self):
        self._check_directory()
        try:
            for name in ('jobs.sqlite3', 'jobs.sqlite3-journal', 'jobs.sqlite3-wal', 'jobs.sqlite3-shm'):
                path = self.directory / name
                try:
                    self._check_file(path.lstat())
                except FileNotFoundError:
                    if name == 'jobs.sqlite3':
                        raise Refused('Queue database unavailable.')
            db = sqlite3.connect(self.db, timeout=30, isolation_level=None)
            db.row_factory = sqlite3.Row
            try:
                db.execute('PRAGMA synchronous=FULL')
                db.execute('BEGIN IMMEDIATE')
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise
            finally:
                db.close()
        except (OSError, sqlite3.Error) as exc:
            raise Refused('Queue storage unavailable.') from exc

    def _context(self, identifier, kind, runner=None):
        return json.dumps([1, self.service_id, self.binding_ref, identifier, kind, runner], separators=(',', ':')).encode()

    def _encrypt(self, identifier, kind, encoded, runner=None):
        nonce = secrets.token_bytes(12)
        return nonce + self._cipher.encrypt(nonce, encoded, self._context(identifier, kind, runner))

    def _decrypt(self, identifier, kind, encrypted, runner=None):
        try:
            return self._cipher.decrypt(encrypted[:12], encrypted[12:], self._context(identifier, kind, runner))
        except (InvalidTag, ValueError, TypeError) as exc:
            raise Refused('Queue authentication failed.') from exc

    def _digest(self, encoded):
        return hmac.new(self._key, encoded, hashlib.sha256).digest()

    def _request_digest(self, operation, encoded, confirmed):
        return self._digest(json.dumps([operation, confirmed]).encode() + b'\0' + encoded)

    def _insert(self, db, operation, encoded, subject, confirmed, now, *, idempotency=None,
                schedule=None, occurrence=None):
        if db.execute('SELECT count(*) FROM jobs').fetchone()[0] >= 1000:
            raise Refused('Queue retention maintenance required.')
        identifier = secrets.token_hex(16)
        digest = self._request_digest(operation, encoded, confirmed)
        db.execute('''INSERT INTO jobs (id,subject,operation,confirmed,payload,request_digest,
                   idempotency,state,created,updated,due,schedule_id,occurrence)
                   VALUES (?,?,?,?,?,?,?, 'queued',?,?,?,?,?)''',
                   (identifier, subject, operation, int(confirmed), self._encrypt(identifier, 'payload', encoded, [subject, operation, bool(confirmed)]),
                    digest, idempotency, now, now, now, schedule, occurrence))
        return identifier

    def enqueue(self, operation, data, *, subject_id, idempotency_key, confirmed, now=None):
        subject_id = _positive_id(subject_id)
        encoded = _request(operation, data, confirmed)
        now = _timestamp(now)
        if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 256:
            raise Refused('Invalid idempotency key.')
        token = self._digest(_encode({'subject':subject_id, 'key':idempotency_key}))
        digest = self._request_digest(operation, encoded, confirmed)
        with self._transaction() as db:
            row = db.execute('SELECT id,request_digest FROM jobs WHERE subject=? AND idempotency=?', (subject_id, token)).fetchone()
            if row:
                if not hmac.compare_digest(row['request_digest'], digest):
                    raise Refused('Idempotency key conflicts with prior request.')
                return row['id']
            return self._insert(db, operation, encoded, subject_id, confirmed, now, idempotency=token)

    @staticmethod
    def _expire(db, now):
        db.execute("UPDATE jobs SET state='unknown',updated=?,lease_hash=NULL,lease_until=NULL WHERE state='running' AND lease_until<=?", (now, now))

    def claim(self, *, lease_seconds=60, now=None):
        if type(lease_seconds) is not int or not 1 <= lease_seconds <= 300:
            raise Refused('Lease must be between 1 and 300 seconds.')
        with self._transaction() as db:
            # Lock acquisition can block; leases use time observed under lock.
            now = _timestamp(now)
            self._expire(db, now)
            row = db.execute("SELECT * FROM jobs WHERE state='queued' AND due<=? ORDER BY due,id LIMIT 1", (now,)).fetchone()
            if row is None:
                return None
            data = json.loads(self._decrypt(row['id'], 'payload', row['payload'], [row['subject'], row['operation'], bool(row['confirmed'])]))
            token = secrets.token_hex(32)
            db.execute("UPDATE jobs SET state='running',updated=?,lease_hash=?,lease_until=? WHERE id=?",
                       (now, self._digest(token.encode()), now + lease_seconds, row['id']))
            return {'job_id':row['id'], 'subject_id':row['subject'], 'service_id':self.service_id,
                    'binding_ref':self.binding_ref, 'operation':row['operation'], 'confirmed':bool(row['confirmed']),
                    'data':data, 'lease_token':token, 'lease_until':now + lease_seconds}

    def finish(self, job_id, lease_token, *, outcome, result=None, now=None):
        if outcome not in ('succeeded', 'failed', 'unknown') or not isinstance(lease_token, str):
            raise Refused('Invalid completion.')
        try:
            encoded = _encode(result) if result is not None else None
        except Refused as exc:
            raise InvalidCompletionResult(str(exc)) from exc
        accepted = False
        expired = False
        with self._transaction() as db:
            # A lease may expire while BEGIN IMMEDIATE waits for another writer.
            now = _timestamp(now)
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            expired = bool(row and row['state'] == 'running' and row['lease_until'] <= now
                           and hmac.compare_digest(row['lease_hash'], self._digest(lease_token.encode())))
            self._expire(db, now)
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if (row and row['state'] == 'running' and row['lease_until'] > now
                    and hmac.compare_digest(row['lease_hash'], self._digest(lease_token.encode()))):
                encrypted = self._encrypt(job_id, 'result', encoded) if encoded is not None else None
                db.execute('UPDATE jobs SET state=?,result=?,updated=?,lease_hash=NULL,lease_until=NULL WHERE id=?',
                           (outcome, encrypted, now, job_id))
                accepted = True
        if expired:
            raise ExpiredJobLease('Current unexpired lease required.')
        if not accepted:
            raise Refused('Current unexpired lease required.')

    @staticmethod
    def _scoped(db, job_id, subject_id):
        _positive_id(subject_id)
        row = db.execute('SELECT * FROM jobs WHERE id=? AND subject=?', (job_id, subject_id)).fetchone()
        if row is None:
            raise Refused('Job unavailable.')
        return row

    def cancel(self, job_id, *, subject_id):
        with self._transaction() as db:
            row = self._scoped(db, job_id, subject_id)
            if row['state'] != 'queued':
                raise Refused('Only queued jobs can be cancelled.')
            db.execute("UPDATE jobs SET state='cancelled',updated=? WHERE id=?", (time.time(), job_id))

    def status(self, job_id, *, subject_id):
        with self._transaction() as db:
            self._expire(db, time.time())
            row = self._scoped(db, job_id, subject_id)
            return {key:row[key] for key in ('id', 'operation', 'state', 'created', 'updated', 'due', 'schedule_id')}

    def result(self, job_id, *, subject_id):
        with self._transaction() as db:
            self._expire(db, time.time())
            row = self._scoped(db, job_id, subject_id)
            if row['state'] not in TERMINAL:
                raise Refused('Job has no terminal result.')
            return json.loads(self._decrypt(job_id, 'result', row['result'])) if row['result'] is not None else None

    def add_schedule(self, operation, data, *, subject_id, interval_seconds, starts_at, confirmed):
        subject_id = _positive_id(subject_id)
        encoded = _request(operation, data, confirmed)
        starts_at = _timestamp(starts_at)
        if type(interval_seconds) is not int or not 300 <= interval_seconds <= 2**53:
            raise Refused('Schedule interval must be at least 300 seconds.')
        identifier = secrets.token_hex(16)
        with self._transaction() as db:
            if db.execute('SELECT count(*) FROM schedules').fetchone()[0] >= 1000:
                raise Refused('Schedule retention maintenance required.')
            db.execute('INSERT INTO schedules (id,subject,operation,confirmed,payload,interval,starts) VALUES (?,?,?,?,?,?,?)',
                       (identifier, subject_id, operation, int(confirmed), self._encrypt(identifier, 'schedule', encoded, [subject_id, operation, confirmed]), interval_seconds, starts_at))
        return identifier

    def enqueue_due(self, now):
        now = _timestamp(now)
        identifiers = []
        with self._transaction() as db:
            for row in db.execute('SELECT * FROM schedules WHERE cancelled=0 AND starts<=? ORDER BY starts,id', (now,)).fetchall():
                slot = math.floor((now - row['starts']) / row['interval'])
                if slot <= row['last_slot']:
                    continue
                encoded = self._decrypt(row['id'], 'schedule', row['payload'], [row['subject'], row['operation'], bool(row['confirmed'])])
                identifiers.append(self._insert(db, row['operation'], encoded, row['subject'], bool(row['confirmed']), now,
                                                schedule=row['id'], occurrence=slot))
                db.execute('UPDATE schedules SET last_slot=? WHERE id=?', (slot, row['id']))
        return identifiers

    def cancel_schedule(self, schedule_id, *, subject_id):
        _positive_id(subject_id)
        with self._transaction() as db:
            row = db.execute('SELECT id FROM schedules WHERE id=? AND subject=?', (schedule_id, subject_id)).fetchone()
            if row is None:
                raise Refused('Schedule unavailable.')
            db.execute('UPDATE schedules SET cancelled=1 WHERE id=?', (schedule_id,))
