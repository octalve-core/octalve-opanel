"""Compile typed, owned DNS zones. Does not change delegation or reload a server."""
import ipaddress
import re
import dns.zone
from .filesystem import Refused


def hostname(value):
    if (not isinstance(value,str) or len(value)>253 or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{1,62}',value)):
        raise Refused('Invalid hostname; use lowercase ASCII or punycode.')
    return value


def number(value,low,high):
    if type(value) is not int or not low<=value<=high: raise Refused('Invalid numeric record field.')
    return value


def quoted(value):
    if not isinstance(value,str) or not 1<=len(value.encode())<=1024 or any(ord(c)<32 or ord(c)>126 for c in value):
        raise Refused('Invalid record text.')
    return ' '.join('"'+value[i:i+200].replace('\\','\\\\').replace('"','\\"')+'"' for i in range(0,len(value),200))


def compile_zone(zone,records,*,serial,nameservers):
    hostname(zone); number(serial,1,4294967295)
    if not isinstance(nameservers,list) or not 1<=len(nameservers)<=4 or len(set(nameservers))!=len(nameservers): raise Refused('Nameservers required.')
    for ns in nameservers: hostname(ns)
    if not isinstance(records,list) or len(records)>500: raise Refused('Zone record budget exceeded.')
    lines=[f'$ORIGIN {zone}.','$TTL 300',f'@ 300 IN SOA {nameservers[0]}. hostmaster.{zone}. ({serial} 3600 600 1209600 300)']
    lines.extend(f'@ 300 IN NS {ns}.' for ns in nameservers)
    types={zone:{'SOA','NS'}}; ttls={(zone,'NS'):300}
    seen={(zone,'NS',ns+'.') for ns in nameservers}; aliases={}
    references=[('NS',zone,ns) for ns in nameservers]
    for record in records:
        if not isinstance(record,dict): raise Refused('Invalid record.')
        kind=record.get('type'); name=record.get('name'); value=record.get('value'); ttl=record.get('ttl')
        fields={'name','type','value','ttl'}|({'priority'} if kind=='MX' else {'priority','weight','port'} if kind=='SRV' else {'flags','tag'} if kind=='CAA' else set())
        if set(record)!=fields: raise Refused('Unsupported record fields.')
        number(ttl,60,86400)
        if not isinstance(value,str): raise Refused('Record value must be text.')
        if not isinstance(name,str): raise Refused('Invalid record name.')
        if name=='@': name=zone
        elif name.endswith('.'): name=name[:-1]
        elif name!=zone and not name.endswith('.'+zone): name=name+'.'+zone
        if len(name)>253 or not (name==zone or name.endswith('.'+zone)) or not re.fullmatch(r'(?:\*\.)?(?:[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9_])?\.)+[a-z][a-z0-9-]{1,62}',name): raise Refused('Record outside owned zone or invalid name.')
        if kind in ('A','AAAA'):
            try: address=ipaddress.ip_address(value)
            except ValueError as exc: raise Refused('Invalid address.') from exc
            if address.version!=(4 if kind=='A' else 6): raise Refused('Wrong address family.')
            data=str(address)
        elif kind in ('CNAME','NS'): data=hostname(value)+'.'
        elif kind=='MX': data=f'{number(record["priority"],0,65535)} {hostname(value)}.'
        elif kind=='SRV': data=f'{number(record["priority"],0,65535)} {number(record["weight"],0,65535)} {number(record["port"],1,65535)} {hostname(value)}.'
        elif kind=='TXT': data=quoted(value)
        elif kind=='CAA':
            if record['tag'] not in ('issue','issuewild','iodef') or record['flags'] not in (0,128) or type(record['flags']) is not int: raise Refused('Invalid CAA fields.')
            if not isinstance(value,str) or len(value)>200: raise Refused('CAA value exceeds budget.')
            data=f'{record["flags"]} {record["tag"]} {quoted(value)}'
        else: raise Refused('Unsupported DNS type.')
        current=types.setdefault(name,set())
        if (kind=='CNAME' and current) or ('CNAME' in current): raise Refused('CNAME conflicts with another record.')
        current.add(kind)
        rrset=(name,kind)
        if rrset in ttls and ttls[rrset]!=ttl: raise Refused('RRset TTLs must match.')
        ttls[rrset]=ttl
        identity=(name,kind,data)
        if identity in seen: raise Refused('Duplicate record.')
        seen.add(identity)
        if kind=='CNAME': aliases[name]=value
        if kind in ('NS','MX','SRV'): references.append((kind,name,value))
        lines.append(f'{name}. {ttl} IN {kind} {data}')
    delegations={name for name,kinds in types.items() if name!=zone and 'NS' in kinds}
    for kind,owner,target in references:
        if target in aliases: raise Refused('NS, MX and SRV targets cannot be aliases.')
        in_zone=target==zone or target.endswith('.'+zone)
        delegated=any(target==cut or target.endswith('.'+cut) for cut in delegations)
        glue=kind=='NS' and owner!=zone and (target==owner or target.endswith('.'+owner))
        if ((in_zone and not delegated) or glue) and not types.get(target,set()) & {'A','AAAA'}:
            raise Refused('In-zone reference requires address records or delegation glue.')
    for start in aliases:
        visited=set(); current=start
        while current in aliases:
            if current in visited: raise Refused('CNAME cycle.')
            visited.add(current); current=aliases[current]
    rendered='\n'.join(lines)+'\n'
    try: dns.zone.from_text(rendered,origin=zone,check_origin=True)
    except Exception as exc: raise Refused('Zone validation failed.') from exc
    return rendered
