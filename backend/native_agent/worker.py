"""Native per-account operation engine; no vendor API or shell dependency.

Run only inside an independently confined, unprivileged account worker. Root,
key and replay DB are operator configuration, never request-controlled. Network
enrollment and TLS termination deliberately do not live in this module.
"""
import hashlib
import hmac
import json
import os
import re
import sqlite3
import stat
import time
from pathlib import Path


class AgentRejected(Exception):
    pass


class Worker:
    max_entries = 1000
    max_depth = 32

    def __init__(self, root, replay_db, key, *, node_id, service_id, binding_ref,
                 allow_mkdir=False):
        if not isinstance(key, bytes) or len(key) < 32:
            raise AgentRejected('Worker key is unavailable.')
        self.root = Path(root)
        self.replay_db = Path(replay_db)
        if self.replay_db.resolve().is_relative_to(self.root.resolve()):
            raise AgentRejected('Replay storage must be outside the account root.')
        self.key = key
        self.node_id, self.service_id, self.binding_ref = node_id, service_id, binding_ref
        self.allow_mkdir = allow_mkdir
        with sqlite3.connect(self.replay_db) as db:
            db.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, expires INTEGER NOT NULL)')

    def execute(self, raw, signature):
        if (not isinstance(raw, bytes) or len(raw) > 8192
                or not isinstance(signature, str) or not re.fullmatch(r'[a-f0-9]{64}', signature)
                or not hmac.compare_digest(hmac.new(self.key, raw, hashlib.sha256).hexdigest(), signature)):
            raise AgentRejected('Request authentication failed.')
        try:
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError('Duplicate field')
                    result[key] = value
                return result
            request = json.loads(raw, object_pairs_hook=unique)
            fields = {'version','node_id','service_id','binding_ref','request_id','expires_at','operation','path'}
            now = int(time.time())
            if (not isinstance(request, dict) or set(request) != fields
                    or type(request['version']) is not int or request['version'] != 1
                    or request['node_id'] != self.node_id
                    or type(request['service_id']) is not int or request['service_id'] != self.service_id
                    or request['binding_ref'] != self.binding_ref
                    or type(request['expires_at']) is not int
                    or not now < request['expires_at'] <= now + 60
                    or not isinstance(request['request_id'], str)
                    or not re.fullmatch(r'[a-f0-9]{32}', request['request_id'])
                    or request['operation'] not in ('files.list','usage.read','files.mkdir')):
                raise ValueError('Invalid scope')
            path = request['path']
            if (not isinstance(path, str) or len(path) > 1024 or '\\' in path
                    or any(ord(c) < 32 for c in path)
                    or (path and any(p in ('', '.', '..') for p in path.split('/')))):
                raise ValueError('Invalid path')
            if request['operation'] == 'usage.read' and path:
                raise ValueError('Usage is account scoped')
            if request['operation'] == 'files.mkdir' and (not self.allow_mkdir or not path):
                raise ValueError('Write disabled')
            # Consume BEFORE I/O. A timeout/error is never permission to blindly retry.
            with sqlite3.connect(self.replay_db, timeout=2) as db:
                db.execute('DELETE FROM requests WHERE expires <= ?', (now,))
                db.execute('INSERT INTO requests VALUES (?, ?)', (request['request_id'], request['expires_at']))
            components = path.split('/') if path else []
            fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                for component in components[:-1] if request['operation'] == 'files.mkdir' else components:
                    child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd)
                    fd = child
                if request['operation'] == 'files.mkdir':
                    os.mkdir(components[-1], mode=0o750, dir_fd=fd)
                    return {'status': 'created', 'request_id': request['request_id']}
                if request['operation'] == 'files.list':
                    entries = []
                    with os.scandir(fd) as iterator:
                        for entry in iterator:
                            if len(entries) >= self.max_entries:
                                raise AgentRejected('Inventory exceeds worker budget.')
                            info = entry.stat(follow_symlinks=False)
                            kind = 'directory' if stat.S_ISDIR(info.st_mode) else 'file' if stat.S_ISREG(info.st_mode) and info.st_nlink == 1 else 'restricted'
                            entries.append({'name': entry.name, 'kind': kind,
                                            'size_bytes': info.st_size if kind == 'file' else None})
                    return {'entries': sorted(entries, key=lambda e: e['name'])}
                total = self._usage(fd, [0], 0, os.fstat(fd).st_dev)
                return {'file_bytes': total, 'bandwidth_bytes': None, 'scope': 'account-files',
                        'recorded_at': int(time.time())}
            finally:
                os.close(fd)
        except (ValueError, TypeError, KeyError, OSError, sqlite3.Error, UnicodeError) as exc:
            raise AgentRejected('Native operation rejected; reconcile before retrying writes.') from exc

    def _usage(self, fd, count, depth, device):
        if depth > self.max_depth:
            raise AgentRejected('Inventory exceeds worker budget.')
        total = 0
        with os.scandir(fd) as iterator:
            for entry in iterator:
                count[0] += 1
                if count[0] > self.max_entries:
                    raise AgentRejected('Inventory exceeds worker budget.')
                info = entry.stat(follow_symlinks=False)
                if info.st_dev != device:
                    raise AgentRejected('Cross-device inventory is forbidden.')
                if stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                    total += info.st_size
                elif stat.S_ISDIR(info.st_mode):
                    child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        if os.fstat(child).st_dev != device:
                            raise AgentRejected('Cross-device inventory is forbidden.')
                        total += self._usage(child, count, depth + 1, device)
                    finally:
                        os.close(child)
        return total
