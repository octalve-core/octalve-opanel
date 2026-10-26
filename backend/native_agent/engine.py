"""Operator-only, service-bound local engines. No network listener or implicit grants.

Private control storage must be outside customer roots, owned by the operator,
and inaccessible to hosting workloads. One confined worker identity per account.
"""
import base64
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import stat
import time
import threading
from pathlib import Path
import dns.zone
from .filesystem import AccountFiles, Refused
from .backups import capture, restore
from .dns import compile_zone, hostname
from .web import compile_site
from .certificates import inspect_certificate

OPERATIONS=frozenset({'files.list','files.read','files.write','files.mkdir','files.rename','files.remove',
                      'usage.read','backups.create','backups.restore','dns.replace','websites.configure','ssl.import'})
READS=frozenset({'files.list','files.read','usage.read'})
FIELDS={'files.list':set(),'usage.read':set(),'files.read':{'path'},'files.mkdir':{'path'},
        'files.write':{'path','content_base64','expected'},'files.rename':{'path','target','expected'},
        'files.remove':{'path','expected'},'backups.create':set(),'backups.restore':{'snapshot_id','target'},
        'dns.replace':{'zone','records','expected_serial'},'websites.configure':{'domain','aliases','document_path','expected'},
        'ssl.import':{'domains','chain_pem','key_pem'}}
OPTIONAL={'files.write':{'expected'},'files.remove':{'expected'},'websites.configure':{'expected'}}


class HostingEngine:
    def __init__(self,root,control,*,service_id,binding_ref,domains,nameservers,capabilities=()):
        root,control=Path(root),Path(control)
        if (type(service_id) is not int or service_id<1 or not isinstance(binding_ref,str) or not 1<=len(binding_ref)<=128
                or root.is_symlink() or control.is_symlink() or not control.is_dir()
                or control.resolve().is_relative_to(root.resolve()) or root.resolve().is_relative_to(control.resolve())
                or stat.S_IMODE(control.stat().st_mode)&0o077 or control.stat().st_uid!=os.geteuid()):
            raise Refused('Private, separate operator control storage required.')
        self.service_id,self.binding_ref=service_id,binding_ref
        self.domains=frozenset(hostname(d) for d in domains)
        self.nameservers=[hostname(ns) for ns in nameservers]
        self.capabilities=frozenset(capabilities)
        if not self.capabilities<=OPERATIONS: raise Refused('Unsupported capabilities.')
        self.root=root.resolve(); self.control=control.resolve()
        self.files=AccountFiles(root); self.private=AccountFiles(control)
        self.lock_fd=None
        self._thread_lock=threading.RLock()
        try:
            self.lock_fd=os.open(control/'worker.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
            if not stat.S_ISREG(os.fstat(self.lock_fd).st_mode) or os.fstat(self.lock_fd).st_nlink!=1: raise Refused('Unsafe lock.')
            fcntl.flock(self.lock_fd,fcntl.LOCK_EX)
            for name in ('backups','dns','websites','certificates'):
                if not (control/name).exists(): self.private.mkdir(name)
                with self.private.parent(name+'/probe'): pass
            self.db=control/'operations.sqlite3'
            fd=os.open(self.db,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
            try:
                if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_nlink!=1: raise Refused('Unsafe journal.')
            finally: os.close(fd)
            with sqlite3.connect(self.db) as db:
                db.execute('CREATE TABLE IF NOT EXISTS identity (service INTEGER, binding TEXT, root TEXT)')
                row=db.execute('SELECT service,binding,root FROM identity').fetchone()
                identity=(service_id,binding_ref,str(self.root))
                if row is None: db.execute('INSERT INTO identity VALUES (?,?,?)',identity)
                elif row!=identity: raise Refused('Control storage belongs to another binding.')
                db.execute('CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, operation TEXT, digest TEXT, outcome TEXT, recorded INTEGER, result TEXT)')
        except Exception:
            self.close(); raise
        finally:
            if self.lock_fd is not None: fcntl.flock(self.lock_fd,fcntl.LOCK_UN)

    def close(self):
        self.files.close(); self.private.close()
        if self.lock_fd is not None: os.close(self.lock_fd); self.lock_fd=None

    def receipt(self,request_id):
        with sqlite3.connect(self.db) as db:
            row=db.execute('SELECT operation,outcome,recorded,result FROM operations WHERE id=?',(request_id,)).fetchone()
        if not row: raise Refused('Unknown request.')
        return {'request_id':request_id,'operation':row[0],'outcome':row[1],'recorded_at':row[2],'result':json.loads(row[3]) if row[3] else None}

    def execute(self,*,service_id,operation,data,request_id,confirmed=False):
        with self._thread_lock:
            return self._execute(service_id=service_id,operation=operation,data=data,request_id=request_id,confirmed=confirmed)

    def _execute(self,*,service_id,operation,data,request_id,confirmed=False):
        if (type(service_id) is not int or service_id!=self.service_id or operation not in self.capabilities
                or operation not in OPERATIONS or (operation not in READS and confirmed is not True)
                or not isinstance(request_id,str) or not re.fullmatch('[a-f0-9]{32}',request_id)
                or not isinstance(data,dict)):
            raise Refused('Operation is not authorized by this worker configuration.')
        if set(data)-FIELDS[operation] or FIELDS[operation]-OPTIONAL.get(operation,set())-set(data): raise Refused('Invalid operation fields.')
        try: encoded=json.dumps(data,sort_keys=True,allow_nan=False).encode()
        except (ValueError,TypeError) as exc: raise Refused('Invalid operation data.') from exc
        if len(encoded)>6*1024*1024: raise Refused('Operation payload exceeds budget.')
        fcntl.flock(self.lock_fd,fcntl.LOCK_EX)
        try:
            with sqlite3.connect(self.db) as db:
                if db.execute('SELECT count(*) FROM operations').fetchone()[0]>=10000: raise Refused('Journal retention maintenance required.')
                try: db.execute('INSERT INTO operations VALUES (?,?,?,?,?,NULL)',(request_id,operation,hashlib.sha256(encoded).hexdigest(),'started',int(time.time())))
                except sqlite3.IntegrityError as exc: raise Refused('Request already recorded; inspect its receipt before retrying.') from exc
            try:
                result=self._dispatch(operation,data,request_id)
                # Never persist private keys or file bodies in operational receipts.
                receipt={k:v for k,v in result.items() if k!='content_base64'}
                with sqlite3.connect(self.db) as db: db.execute('UPDATE operations SET outcome=?,result=? WHERE id=?',('succeeded',json.dumps(receipt),request_id))
                return result
            except Exception as exc:
                with sqlite3.connect(self.db) as db: db.execute('UPDATE operations SET outcome=? WHERE id=?',('unknown' if operation not in READS else 'rejected',request_id))
                raise Refused('Operation failed; inspect receipt and reconcile before retrying.') from exc
        finally: fcntl.flock(self.lock_fd,fcntl.LOCK_UN)

    def _dispatch(self,op,data,rid):
        path=data.get('path')
        if op=='files.list': return {'entries':self.files.inventory()}
        if op=='files.read':
            content=self.files.read(path)
            return {'content_base64':base64.b64encode(content).decode(),'sha256':hashlib.sha256(content).hexdigest(),'size':len(content)}
        if op=='files.write':
            content=base64.b64decode(data['content_base64'],validate=True)
            return {'sha256':self.files.write(path,content,expected=data.get('expected'))}
        if op=='files.mkdir': self.files.mkdir(path); return {'status':'created'}
        if op=='files.rename': self.files.rename(path,data['target'],expected=data['expected']); return {'status':'renamed'}
        if op=='files.remove': self.files.remove(path,expected=data.get('expected')); return {'status':'removed'}
        if op=='usage.read': return {'file_bytes':sum(r['size'] for r in self.files.inventory()),'bandwidth_bytes':None,'recorded_at':int(time.time()),'scope':'bounded-account-files'}
        if op=='backups.create':
            content=capture(self.files,service_id=self.service_id); digest=hashlib.sha256(content).hexdigest()
            # Snapshot size limit is larger than ordinary editable files.
            self.private.max_file_bytes=36*1024*1024
            self.private.write('backups/'+rid+'.zip',content)
            return {'snapshot_id':rid,'sha256':digest,'scope':'files-only'}
        if op=='backups.restore':
            snapshot=data['snapshot_id']
            if not isinstance(snapshot,str) or not re.fullmatch('[a-f0-9]{32}',snapshot): raise Refused('Invalid snapshot ID.')
            receipt=self.receipt(snapshot)
            if receipt['operation']!='backups.create' or receipt['outcome']!='succeeded': raise Refused('Snapshot is not verified.')
            self.private.max_file_bytes=36*1024*1024
            content=self.private.read('backups/'+snapshot+'.zip')
            return restore(self.files,content,service_id=self.service_id,target=data['target'],expected_digest=receipt['result']['sha256'])
        if op=='dns.replace':
            zone=data['zone']; hostname(zone)
            if zone not in self.domains: raise Refused('Zone ownership is not configured.')
            target='dns/'+zone+'.zone'; existing=None; serial=0
            try: existing=self.private.read(target)
            except Refused as exc:
                if not isinstance(exc.__cause__,FileNotFoundError): raise
            if existing is not None: serial=dns.zone.from_text(existing.decode(),origin=zone).get_rdataset('@','SOA')[0].serial
            if type(data['expected_serial']) is not int or data['expected_serial']!=serial: raise Refused('Zone changed; refresh first.')
            content=compile_zone(zone,data['records'],serial=serial+1,nameservers=self.nameservers).encode()
            digest=self.private.write(target,content,expected=hashlib.sha256(existing).hexdigest() if existing is not None else None)
            return {'serial':serial+1,'sha256':digest,'server_reloaded':False}
        if op=='websites.configure':
            domain=hostname(data['domain']); aliases=data['aliases']
            if not isinstance(aliases,list) or not {domain,*aliases}<=self.domains: raise Refused('Website ownership is not configured.')
            document=data['document_path']
            with self.files.parent(document+'/probe'): pass
            content=compile_site(domain,aliases=aliases,document_root=str(self.root/document)).encode()
            digest=self.private.write('websites/'+domain+'.conf',content,expected=data.get('expected'))
            return {'sha256':digest,'server_reloaded':False,'public_http_verified':False}
        if op=='ssl.import':
            domains=data['domains']
            if not isinstance(domains,list) or not set(domains)<=self.domains: raise Refused('Certificate ownership is not configured.')
            chain=data['chain_pem'].encode(); key=data['key_pem'].encode()
            report=inspect_certificate(chain,key,domains=domains)
            folder='certificates/'+rid; self.private.mkdir(folder)
            self.private.write(folder+'/chain.pem',chain); self.private.write(folder+'/key.pem',key)
            return {**report,'certificate_id':rid,'activated':False}
        raise Refused('Unsupported operation.')
