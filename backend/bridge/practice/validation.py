import ipaddress
import re

class Rejected(ValueError):
    pass

def text(value, maximum=128):
    if not isinstance(value,str) or not value.strip() or len(value)>maximum or any(ord(c)<32 or ord(c)==127 for c in value):
        raise Rejected('Enter a valid value within the allowed length.')
    return value.strip()

def domain(value):
    value=text(value,253).lower().rstrip('.')
    if not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',value):
        raise Rejected('Enter a full domain name, such as example.test.')
    return value

def identifier(value):
    value=text(value,32)
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,31}',value):
        raise Rejected('Use lowercase letters, numbers and underscores, starting with a letter.')
    return value

def integer(value,minimum,maximum):
    if isinstance(value,bool) or not re.fullmatch(r'[0-9]+',str(value)) or not minimum<=int(value)<=maximum:
        raise Rejected(f'Enter a whole number between {minimum} and {maximum}.')
    return int(value)

def owned(state,name):
    name=domain(name)
    if not any(row['name']==name for row in state['domains']):
        raise Rejected('Add this domain to this workspace first.')
    return name

def file_path(value):
    value=text(value,256)
    if '\\' in value or any(p in ('','..','.') for p in value.split('/')):
        raise Rejected('Use a relative path without traversal.')
    return value

def dns_record(state,data):
    zone=owned(state,data.get('domain'))
    name=text(data.get('name'),253).lower()
    if name!='@': domain(name+'.'+zone)
    kind=data.get('type')
    value=text(data.get('value'),1024)
    ttl=integer(data.get('ttl'),60,86400)
    if kind in ('A','AAAA'):
        try: address=ipaddress.ip_address(value)
        except ValueError: raise Rejected('Enter a valid IP address.') from None
        if address.version != (4 if kind=='A' else 6): raise Rejected('Address does not match record type.')
    elif kind in ('CNAME','MX'): value=domain(value)
    elif kind!='TXT': raise Rejected('Choose a supported DNS record type.')
    if kind=='CNAME' and name=='@': raise Rejected('The zone root cannot be a CNAME.')
    for row in state['dns']:
        if row['domain']==zone and row['name']==name:
            if kind=='CNAME' or row['type']=='CNAME': raise Rejected('A CNAME cannot share this record name.')
            if row['type']==kind and row['value']==value: raise Rejected('This record already exists.')
    return {'domain':zone,'name':name,'type':kind,'value':value,'ttl':ttl,
            'priority':integer(data.get('priority',10),0,65535) if kind=='MX' else None}
