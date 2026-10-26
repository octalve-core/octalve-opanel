"""Static Nginx site configuration only; no arbitrary directives or runtime claims."""
import re
from .dns import hostname, number
from .filesystem import Refused


def config_path(path):
    if not isinstance(path,str) or not re.fullmatch(r'/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+',path) or any(p in ('.','..') for p in path.split('/')):
        raise Refused('Invalid configured absolute path.')
    return path


def compile_site(domain,*,document_root,aliases,port=8080):
    hostname(domain); config_path(document_root); number(port,1024,65535)
    if not isinstance(aliases,list) or len(aliases)>20: raise Refused('Too many aliases.')
    names=[domain]+[hostname(alias) for alias in aliases]
    if len(set(names))!=len(names): raise Refused('Duplicate website name.')
    return (f'server {{\n listen 127.0.0.1:{port};\n server_name {" ".join(names)};\n'
            f' root {document_root};\n index index.html;\n disable_symlinks on;\n autoindex off;\n'
            ' add_header X-Content-Type-Options nosniff always;\n'
            ' location ~ (^|/)\\. { deny all; }\n'
            ' location ~* \\.(php|phtml|phar|cgi|pl|py|sh)$ { return 404; }\n'
            ' location / { try_files $uri $uri/ =404; }\n}\n')
