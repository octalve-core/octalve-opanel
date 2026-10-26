import tempfile
from pathlib import Path
from unittest import TestCase
from bridge.management import NativeAdapter, ManagementRejected, ServiceScope, run_operation
from native_agent.worker import Worker

BINDING = 'e60d4718-34b4-4e46-b171-04515159a7b1'
KEY = b'synthetic-worker-key-32-bytes-long!'

class ManagementTests(TestCase):
    def setUp(self):
        self.scope = ServiceScope(41, 13, BINDING)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name) / 'files'; root.mkdir()
        (root / 'hello.txt').write_text('hello')
        worker = Worker(root, Path(self.tmp.name)/'requests.db', KEY,
                        node_id='node-1',service_id=13,binding_ref=BINDING,allow_mkdir=True)
        self.adapter = NativeAdapter(self.scope, 'node-1', KEY, worker.execute)
        self.events = []

    def grant(self):
        return {'subject_id':41,'service_id':13,'binding_ref':BINDING,
                'capabilities':['overview'], 'management':{'version':1,
                'capabilities':['files.list','usage.read','files.mkdir']}}

    def run_op(self, operation='files.list', **kw):
        return run_operation(self.scope,self.adapter,operation,entitlement=self.grant,
                             audit=self.events.append,**kw)

    def test_real_native_inventory_through_authorized_boundary(self):
        result = self.run_op()
        self.assertEqual(result['entries'][0]['name'],'hello.txt')
        self.assertEqual([e['outcome'] for e in self.events],['started','succeeded'])
        self.assertNotIn('hello.txt',str(self.events))

    def test_overview_grant_cannot_authorize_inventory(self):
        grant = self.grant(); del grant['management']
        with self.assertRaises(ManagementRejected):
            run_operation(self.scope,self.adapter,'files.list',entitlement=lambda:grant,audit=self.events.append)

    def test_revocation_during_operation_discards_result(self):
        calls = iter([self.grant(),{}])
        with self.assertRaises(ManagementRejected):
            run_operation(self.scope,self.adapter,'files.list',entitlement=lambda:next(calls),audit=self.events.append)
        self.assertEqual(self.events[-1]['outcome'],'rejected')

    def test_write_requires_confirmation_and_explicit_gate(self):
        for enabled, confirmed in ((False,False),(True,False),(False,True)):
            with self.assertRaises(ManagementRejected):
                self.run_op('files.mkdir',path='assets',writes_enabled=enabled,confirmed=confirmed)
        self.assertEqual(self.run_op('files.mkdir',path='assets',writes_enabled=True,confirmed=True)['status'],'created')

    def test_audit_failure_denies_before_execution(self):
        def failed(_): raise OSError('audit unavailable')
        with self.assertRaises(ManagementRejected):
            run_operation(self.scope,self.adapter,'files.mkdir',path='assets',writes_enabled=True,
                          confirmed=True,entitlement=self.grant,audit=failed)
        self.assertEqual(len(self.run_op()['entries']),1)

    def test_wrong_adapter_scope_rejected(self):
        with self.assertRaises(ManagementRejected):
            run_operation(ServiceScope(42,13,BINDING),self.adapter,'files.list',
                          entitlement=self.grant,audit=self.events.append)

    def test_vendor_usage_uses_same_scoped_management_boundary(self):
        from unittest.mock import patch
        from .management import VendorAdapter
        from .providers import AccountTarget, UsageSnapshot
        target = AccountTarget('whm','https://host.example:2087','reseller','synthetic',
            expected_owner='reseller',account='account',domain='site.example',
            subject_id=41,service_id=13,binding_ref=BINDING)
        with patch('bridge.providers.read_usage',return_value=UsageSnapshot(12,100,None,None,'whm')):
            result = run_operation(self.scope,VendorAdapter(target),'usage.read',
                                   entitlement=self.grant,audit=self.events.append)
        self.assertEqual(result['disk_used_mb'],12)
        self.assertIsNone(result['bandwidth_used_mb'])

    def test_unknown_write_audit_identifies_binding_and_target(self):
        def uncertain(operation,path,request_id): raise TimeoutError('ambiguous write')
        self.adapter.execute=uncertain
        with self.assertRaises(ManagementRejected):
            self.run_op('files.mkdir',path='assets',writes_enabled=True,confirmed=True)
        self.assertEqual(self.events[-1]['outcome'],'unknown')
        self.assertEqual(self.events[0]['binding_ref'],BINDING)
        self.assertEqual(self.events[0]['target_path'],'assets')

    def test_unsafe_audit_target_is_rejected_before_start_record(self):
        with self.assertRaises(ManagementRejected):
            self.run_op('files.mkdir',path='assets\nforged event',writes_enabled=True,confirmed=True)
        self.assertEqual(self.events,[])
