"""Bounded Linux file operations inside an operator-owned, confined account root.

Caller serializes operations and enforces entitlement. This is not a sandbox:
non-cooperating writers require separate OS isolation before production use.
"""
import hashlib
import os
import re
import secrets
import stat
from contextlib import contextmanager


class Refused(ValueError):
    pass


def parts(path):
    if not isinstance(path,str) or not 1 <= len(path) <= 1024:
        raise Refused('Invalid relative path.')
    result=path.split('/')
    if len(result)>32 or any(p in ('.','..') or not re.fullmatch(r'[A-Za-z0-9_.-]{1,255}',p) for p in result):
        raise Refused('Invalid relative path.')
    return result


class AccountFiles:
    max_file_bytes=4*1024*1024
    max_total_bytes=32*1024*1024
    max_entries=1000

    def __init__(self,root):
        try:
            self.fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            self.device=os.fstat(self.fd).st_dev
        except OSError as exc: raise Refused('Account root unavailable.') from exc

    def close(self):
        if self.fd is not None: os.close(self.fd); self.fd=None

    @contextmanager
    def parent(self,path):
        names=parts(path); fd=os.dup(self.fd)
        try:
            for name in names[:-1]:
                child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
                os.close(fd); fd=child
                if os.fstat(fd).st_dev!=self.device: raise Refused('Cross-device access refused.')
            yield fd,names[-1]
        except OSError as exc: raise Refused('Filesystem operation refused.') from exc
        finally: os.close(fd)

    def _regular(self,fd):
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_dev!=self.device or info.st_size>self.max_file_bytes:
            raise Refused('File type or size is unsupported.')
        return info

    def read(self,path):
        with self.parent(path) as (parent,name):
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
            try:
                self._regular(fd); data=bytearray()
                while True:
                    chunk=os.read(fd,min(65536,self.max_file_bytes+1-len(data)))
                    if not chunk: break
                    data.extend(chunk)
                    if len(data)>self.max_file_bytes: raise Refused('File exceeds budget.')
                return bytes(data)
            finally: os.close(fd)

    def _precondition(self,path,expected):
        if not isinstance(expected,str) or not re.fullmatch('[0-9a-f]{64}',expected): raise Refused('Current file digest required.')
        if hashlib.sha256(self.read(path)).hexdigest()!=expected: raise Refused('File changed; refresh first.')

    def write(self,path,data,*,expected=None):
        if not isinstance(data,bytes) or len(data)>self.max_file_bytes: raise Refused('File exceeds budget.')
        with self.parent(path) as (parent,name):
            if expected is not None: self._precondition(path,expected)
            else:
                try: os.stat(name,dir_fd=parent,follow_symlinks=False)
                except FileNotFoundError: pass
                else: raise Refused('File exists; current digest required.')
            temp='.opanel-write-'+secrets.token_hex(16)
            fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
            try:
                with os.fdopen(fd,'wb') as output: output.write(data); output.flush(); os.fsync(output.fileno())
                if expected is None:
                    # Link is atomic no-clobber; transient staging link is removed below.
                    os.link(temp,name,src_dir_fd=parent,dst_dir_fd=parent,follow_symlinks=False)
                else:
                    self._precondition(path,expected)
                    os.replace(temp,name,src_dir_fd=parent,dst_dir_fd=parent)
                os.fsync(parent)
            finally:
                try: os.unlink(temp,dir_fd=parent)
                except FileNotFoundError: pass
        return hashlib.sha256(data).hexdigest()

    def mkdir(self,path):
        with self.parent(path) as (parent,name): os.mkdir(name,0o750,dir_fd=parent); os.fsync(parent)

    def remove(self,path,*,expected=None):
        with self.parent(path) as (parent,name):
            info=os.stat(name,dir_fd=parent,follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode): os.rmdir(name,dir_fd=parent)
            else: self._precondition(path,expected); os.unlink(name,dir_fd=parent)
            os.fsync(parent)

    def rename(self,source,target,*,expected):
        self._precondition(source,expected)
        with self.parent(source) as (src,name), self.parent(target) as (dst,new):
            # Regular files only; no replacement and no symlink traversal.
            os.link(name,new,src_dir_fd=src,dst_dir_fd=dst,follow_symlinks=False)
            os.unlink(name,dir_fd=src); os.fsync(src); os.fsync(dst)

    def inventory(self):
        rows=[]; total=0
        def walk(fd,prefix,depth):
            nonlocal total
            if depth>32: raise Refused('Tree exceeds depth budget.')
            with os.scandir(fd) as entries:
                for entry in entries:
                    path=prefix+entry.name; parts(path)
                    if len(rows)>=self.max_entries: raise Refused('Tree exceeds entry budget.')
                    info=entry.stat(follow_symlinks=False)
                    if info.st_dev!=self.device: raise Refused('Cross-device entry refused.')
                    if stat.S_ISDIR(info.st_mode):
                        rows.append({'path':path,'kind':'directory','size':0})
                        child=os.open(entry.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
                        try:
                            if os.fstat(child).st_dev!=self.device: raise Refused('Cross-device directory refused.')
                            walk(child,path+'/',depth+1)
                        finally: os.close(child)
                    elif stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size<=self.max_file_bytes:
                        total+=info.st_size
                        if total>self.max_total_bytes: raise Refused('Tree exceeds byte budget.')
                        rows.append({'path':path,'kind':'file','size':info.st_size})
                    else: raise Refused('Unsupported linked or special file.')
        try: walk(self.fd,'',0)
        except OSError as exc: raise Refused('Inventory unavailable.') from exc
        return sorted(rows,key=lambda row:row['path'])
