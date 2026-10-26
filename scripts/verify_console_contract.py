"""Run with Console's venv. Uses actual issuer/OPanel code and isolated DBs.

Transport is an in-process Django API client + subprocess RPC, not HTTPS or
browser acceptance. No provider network, payments or provisioning are invoked.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--console-root',type=Path,required=True)
parser.add_argument('--panel-python',required=True)
args=parser.parse_args()
sys.path.insert(0,str(args.console_root.resolve()/'backend'))
os.environ.update(DEBUG='true',DJANGO_SETTINGS_MODULE='octalve_backend.settings',
    DJANGO_SECRET_KEY='isolated-contract-test-only-0123456789abcdefghijkl',FRONTEND_URL='http://localhost:3001')
os.environ.pop('DATABASE_URL',None)
import django
django.setup()
from django.conf import settings
from django.test.utils import setup_databases,teardown_databases
from opanel_bridge.tests import OPanelIssuerTests, ISSUE, EXCHANGE, ENTITLEMENT
settings.DATABASES['default']['NAME'] = ':memory:'
settings.ALLOWED_HOSTS = ['testserver']
config=setup_databases(verbosity=0,interactive=False)
case=OPanelIssuerTests('test_issued_grant_is_random_hashed_single_use_and_service_bound')
case.setUpClass()
case._pre_setup()
case.setUp()
process=None
try:
    # Real Console password authentication against the synthetic customer.
    case.api.force_authenticate(user=None)
    assert case.api.login(email=case.owner.email,password='local-test-password-123')
    process=subprocess.Popen([args.panel_python,str(Path(__file__).with_name('panel_contract_client.py'))],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    done=False
    for line in process.stdout:
        event=json.loads(line)
        if event.get('done'):
            done=True; break
        op,payload=event['operation'],event['payload']
        if op=='service': result={'status':200,'data':{'service_id':case.service.pk}}
        elif op=='suspend':
            case.service.status='suspended';case.service.save(update_fields=['status'])
            result={'status':200,'data':{}}
        else:
            response=(case.api.post(ISSUE,payload,format='json') if op=='authorize/' else
                      case.confidential({'exchange/':EXCHANGE,'entitlement/':ENTITLEMENT}[op],payload))
            result={'status':response.status_code,'data':response.data}
        process.stdin.write(json.dumps(result)+'\n');process.stdin.flush()
    assert process.wait(timeout=20)==0 and done
    print('PASS: actual Console password authentication, PKCE launch, OPanel callback/session, issuer replay denial, suspension denial and CSRF logout (isolated contract transport).')
finally:
    if process and process.poll() is None:
        process.kill();process.wait()
    case._post_teardown();case.tearDownClass()
    teardown_databases(config,verbosity=0)
