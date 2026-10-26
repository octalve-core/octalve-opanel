"""Offline resource transitions. Never imports a live adapter or network client."""
import copy
import uuid
from .validation import Rejected, text, domain, identifier, integer, owned, file_path, dns_record

MODULES=('domains','dns','ssl','websites','files','databases','email','backups')

def empty():
    return {'mode':'simulation','revision':0,**{key:[] for key in MODULES},'activity':[]}

def selected(state,module,record_id):
    for row in state[module]:
        if row['id']==record_id: return row
    raise Rejected('This item is no longer available.')

def change(state,operation,data,confirmed):
    try: module,action=operation.split('.')
    except (ValueError,AttributeError): raise Rejected('Unsupported operation.') from None
    if module not in (*MODULES,'subdomains'): raise Rejected('Unsupported module.')
    collection='domains' if module=='subdomains' else module
    if action in ('remove','restore','rollback') and confirmed is not True:
        raise Rejected('Confirm this action before continuing.')
    if action=='update' and module in ('dns','files','databases','email'):
        row=selected(state,collection,data.get('id'))
        if module=='files' and (row['name']!=data.get('name') or row['kind']!=data.get('kind')) and any(r['name'].startswith(row['name']+'/') for r in state['files']):
            raise Rejected('Move or remove folder contents before changing its name or kind.')
        state[collection].remove(row)
        change(state,module+'.add',data,False)
        state[collection][-1]['id']=row['id']
        return
    if action=='remove':
        row=selected(state,collection,data.get('id'))
        if collection=='domains':
            if module=='subdomains' and not row.get('parent'): raise Rejected('Select a subdomain.')
            if any(r.get('parent')==row['name'] for r in state['domains']) or any(r.get('domain')==row['name'] for key in ('dns','ssl','websites','email') for r in state[key]):
                raise Rejected('Remove this domain’s dependent resources first.')
        if module=='files' and any(r['name'].startswith(row['name']+'/') for r in state['files']):
            raise Rejected('Remove the folder contents first.')
        state[collection].remove(row); return
    if action=='add':
        if len(state[collection]) >= (5 if module=='backups' else 100): raise Rejected('Workspace resource limit reached.')
        row={'id':uuid.uuid4().hex}
        if module=='domains': row.update(name=domain(data.get('name')),parent=None)
        elif module=='subdomains':
            parent=owned(state,data.get('domain')); label=text(data.get('name'),63)
            if '.' in label: raise Rejected('Enter one subdomain label.')
            row.update(name=domain(label+'.'+parent),parent=parent)
        elif module=='dns': row.update(dns_record(state,data))
        elif module=='ssl': row.update(domain=owned(state,data.get('domain')),status='simulation-pending')
        elif module=='websites': row.update(domain=owned(state,data.get('domain')),name=text(data.get('name')),releases=[],current_release=None)
        elif module=='files':
            name=file_path(data.get('name')); kind=data.get('kind')
            if kind not in ('file','directory'): raise Rejected('Choose file or directory.')
            if '/' in name and not any(r['name']==name.rsplit('/',1)[0] and r['kind']=='directory' for r in state['files']): raise Rejected('Create the parent folder first.')
            content=data.get('content','')
            if not isinstance(content,str) or len(content.encode())>4096: raise Rejected('Practice file content is limited to 4 KB.')
            row.update(name=name,kind=kind,content=content if kind=='file' else '',size_bytes=len(content.encode()) if kind=='file' else 0)
        elif module=='databases': row.update(name=identifier(data.get('name')),user=identifier(data.get('user')),engine='simulated-mysql')
        elif module=='email':
            zone=owned(state,data.get('domain')); name=identifier(data.get('name'))
            row.update(name=name+'@'+zone,domain=zone,quota_mb=integer(data.get('quota'),10,10000),delivery='simulation-only')
        elif module=='backups':
            row.update(name=text(data.get('name')),snapshot={k:copy.deepcopy(state[k]) for k in MODULES if k!='backups'},scope='simulated-resources-only')
        unique_key='domain' if module in ('ssl','websites') else 'name'
        if module!='dns' and any(r.get(unique_key)==row.get(unique_key) for r in state[collection]): raise Rejected('An item with this name already exists.')
        state[collection].append(row); return
    row=selected(state,collection,data.get('id'))
    if module=='ssl' and action in ('verify','renew'):
        row['status']='simulation-valid'; row['renewal_count']=row.get('renewal_count',0)+(action=='renew'); return
    if module=='websites' and action=='release':
        label=text(data.get('label'),64)
        if label in row['releases']: raise Rejected('Choose a unique release label.')
        if len(row['releases'])>=20: raise Rejected('Release history limit reached.')
        row['releases'].append(label); row['current_release']=label; return
    if module=='websites' and action=='rollback':
        if len(row['releases'])<2: raise Rejected('No previous release is available.')
        row['releases'].pop(); row['current_release']=row['releases'][-1]; return
    if module=='backups' and action=='restore':
        for key,value in row['snapshot'].items(): state[key]=copy.deepcopy(value)
        return
    raise Rejected('Unsupported operation.')
