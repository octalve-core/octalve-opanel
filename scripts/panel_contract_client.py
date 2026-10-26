"""Subprocess side of the isolated cross-repository contract test."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'opanel_project.settings'
os.environ['DEBUG'] = 'true'
os.environ.pop('DATABASE_URL', None)
import django
django.setup()
from django.conf import settings
from django.test import Client, override_settings
from django.test.utils import setup_databases, teardown_databases
from bridge.client import ConsoleUnavailable
settings.DATABASES['default']['NAME'] = ':memory:'


def rpc(operation, payload):
    print(json.dumps({'operation':operation,'payload':payload}),flush=True)
    result=json.loads(sys.stdin.readline())
    return result


def console_post(endpoint,payload):
    result=rpc(endpoint,payload)
    if result['status']!=200:
        raise ConsoleUnavailable('Real Console issuer denied the request')
    return result['data']

config=setup_databases(verbosity=0,interactive=False)
try:
    with override_settings(CONSOLE_WEB_ORIGIN='https://console.example.test',
        CONSOLE_API_BASE='https://api.example.test/api',OPANEL_PUBLIC_ORIGIN='https://panel.example.test',
        OPANEL_CALLBACK_URL='https://panel.example.test/auth/callback/',
        OPANEL_CLIENT_SECRET='local-integration-test-secret-only-0123456789abcdef'):
        client=Client(enforce_csrf_checks=True)
        service=rpc('service',{})['data']['service_id']
        launch=client.get('/auth/start/',{'service_id':service})
        assert launch.status_code==302
        query=parse_qs(urlparse(launch['Location']).query)
        pending=client.session['pending']
        issued=rpc('authorize/',{'service_id':service,'state':query['state'][0],
                                 'code_challenge':query['code_challenge'][0]})
        assert issued['status']==200, issued
        grant=issued['data']
        with patch('bridge.views.console_post',side_effect=console_post):
            response=client.get('/auth/callback/',{'code':grant['code'],'state':grant['state']})
            assert response.status_code==302, response.status_code
            status=client.get('/api/session/')
            assert status.status_code==200 and status.json()['service_id']==service
            replay=rpc('exchange/',{'code':grant['code'],'code_verifier':pending['verifier'],
                                    'redirect_uri':settings.OPANEL_CALLBACK_URL})
            assert replay['status']==403
            rpc('suspend',{})
            assert client.get('/api/session/').status_code==503  # Console denies; client fails closed.
        token=client.get('/api/csrf/').json()['csrf_token']
        assert client.post('/auth/logout/',HTTP_X_CSRFTOKEN=token).status_code==302
        assert 'opanel_identity' not in client.session
    print(json.dumps({'done':True}),flush=True)
finally:
    teardown_databases(config,verbosity=0)
