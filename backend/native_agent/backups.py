"""Real bounded file snapshots, not database/mail-consistent account backups."""
import hashlib
import io
import json
import zipfile
from .filesystem import Refused, parts

MAX_ARCHIVE=36*1024*1024


def capture(files,*,service_id):
    if type(service_id) is not int or service_id<1: raise Refused('Invalid backup scope.')
    manifest={'version':1,'service_id':service_id,'entries':[]}
    buffer=io.BytesIO(); total=0
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_STORED) as archive:
        for row in files.inventory():
            row=dict(row)
            if row['kind']=='file':
                data=files.read(row['path']); total+=len(data)
                if len(data)!=row['size'] or total>files.max_total_bytes: raise Refused('Files changed or snapshot exceeds budget.')
                row['sha256']=hashlib.sha256(data).hexdigest()
                archive.writestr('data/'+row['path'],data)
            manifest['entries'].append(row)
        archive.writestr('manifest.json',json.dumps(manifest,sort_keys=True))
    return buffer.getvalue()


def validated(archive_bytes,*,service_id,expected_digest):
    if (not isinstance(archive_bytes,bytes) or len(archive_bytes)>MAX_ARCHIVE
            or hashlib.sha256(archive_bytes).hexdigest()!=expected_digest):
        raise Refused('Backup integrity check failed.')
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            infos=archive.infolist(); names=[i.filename for i in infos]
            if len(names)!=len(set(names)) or len(names)>1001: raise Refused('Invalid backup entries.')
            if any(i.flag_bits&1 or i.compress_type!=zipfile.ZIP_STORED for i in infos): raise Refused('Unsupported backup encoding.')
            info=archive.getinfo('manifest.json')
            if info.file_size>2*1024*1024: raise Refused('Manifest exceeds budget.')
            manifest=json.loads(archive.read(info))
            if (not isinstance(manifest,dict) or set(manifest)!={'version','service_id','entries'}
                    or type(manifest['version']) is not int or manifest['version']!=1
                    or type(manifest['service_id']) is not int or manifest['service_id']!=service_id
                    or not isinstance(manifest['entries'],list) or len(manifest['entries'])>1000):
                raise Refused('Wrong backup scope or format.')
            result=[]; seen=set(); expected={'manifest.json'}; total=0
            for row in manifest['entries']:
                if not isinstance(row,dict): raise Refused('Invalid manifest entry.')
                path=row['path']; segments=parts(path); kind=row['kind']; size=row['size']
                if path in seen or type(size) is not int or not 0<=size<=4*1024*1024: raise Refused('Invalid manifest entry.')
                if kind not in ('file','directory') or set(row)!=({'path','kind','size','sha256'} if kind=='file' else {'path','kind','size'}): raise Refused('Invalid manifest entry.')
                if any('/'.join(segments[:n]) not in seen for n in range(1,len(segments))): raise Refused('Missing parent directory.')
                # Directory entries must precede descendants; validated again before any write.
                if any(r['path'] in ('/'.join(segments[:n]) for n in range(1,len(segments))) and r['kind']!='directory' for r,_ in result): raise Refused('File used as parent.')
                seen.add(path)
                if kind=='directory':
                    if size!=0: raise Refused('Invalid directory size.')
                    data=None
                else:
                    name='data/'+path; expected.add(name); total+=size
                    if total>32*1024*1024 or archive.getinfo(name).file_size!=size: raise Refused('Backup exceeds budget.')
                    data=archive.read(name)
                    if hashlib.sha256(data).hexdigest()!=row['sha256']: raise Refused('Backup file checksum failed.')
                result.append((row,data))
            if set(names)!=expected: raise Refused('Unexpected backup contents.')
            return result
    except (KeyError,TypeError,ValueError,zipfile.BadZipFile,UnicodeError,RuntimeError) as exc:
        raise Refused('Backup validation failed.') from exc


def restore(files,archive_bytes,*,service_id,target,expected_digest):
    parts(target)
    rows=validated(archive_bytes,service_id=service_id,expected_digest=expected_digest)
    # Exclusive directory creation: existing content is never replaced. On I/O
    # failure leave the partially restored directory for reconciliation; never
    # report success or recursively delete a path another writer may have touched.
    for row,_ in rows: parts(target+'/'+row['path'])
    files.mkdir(target)
    for row,data in rows:
        path=target+'/'+row['path']
        if row['kind']=='directory': files.mkdir(path)
        else: files.write(path,data)
    return {'status':'restored_to_new_directory','target':target,'entries':len(rows)}
