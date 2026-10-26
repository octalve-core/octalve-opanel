"""Local-only Django server with explicit local browser origin for CSRF."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
os.environ['DJANGO_SETTINGS_MODULE']='opanel_project.settings'
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
settings.CSRF_TRUSTED_ORIGINS=['http://127.0.0.1:3300','http://localhost:3300']
call_command('runserver','127.0.0.1:8301',use_reloader=False)
