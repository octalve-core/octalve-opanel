"""Disposable loopback-only practice API. No external hosting credentials."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='opanel-practice-') as directory:
    env={**os.environ,'DEBUG':'true','DJANGO_SECRET_KEY':'local-practice-only-0123456789abcdefghijklmnopqrstuvwxyz',
         'DATABASE_URL':'sqlite:///'+directory+'/sessions.sqlite3','OPANEL_PRACTICE_DATABASE':directory+'/practice.sqlite3',
         'OPANEL_PRACTICE_ENABLED':'true','ALLOWED_HOSTS':'localhost,127.0.0.1',
         'OPANEL_PUBLIC_ORIGIN':'','CONSOLE_API_BASE':'','CONSOLE_WEB_ORIGIN':'',
         'OPANEL_VENDOR_READBACK_ENABLED':'false','OPANEL_TECHNICAL_LOGIN_ENABLED':'false'}
    subprocess.run([sys.executable,'manage.py','migrate','--noinput'],cwd=root/'backend',env=env,check=True,stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable,str(root/'scripts'/'practice-server.py')],cwd=root/'backend',env=env,check=True)
