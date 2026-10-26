import base64
import tempfile
import uuid
from pathlib import Path
from unittest import TestCase
from bridge.management import ServiceScope, ManagementRejected
from native_agent.engine import HostingEngine

class HostingBoundaryTests(TestCase):
    def test_fresh_entitlement_precedes_real_file_write(self):
        from bridge.hosting_management import run_hosting_operation
        scope=ServiceScope(41,13,'e60d4718-34b4-4e46-b171-04515159a7b1')
        grant={'subject_id':41,'service_id':13,'binding_ref':scope.binding_ref,'capabilities':['overview'], 'management':{'version':1,'capabilities':['files.write']}}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'account'; root.mkdir(); control=Path(tmp)/'control'; control.mkdir(mode=0o700)
            engine=HostingEngine(root,control,service_id=13,binding_ref=scope.binding_ref,domains=[],nameservers=[],capabilities=['files.write'])
            self.addCleanup(engine.close); events=[]
            data={'path':'hello.txt','content_base64':base64.b64encode(b'hello').decode()}
            with self.assertRaises(ManagementRejected): run_hosting_operation(scope,engine,'files.write',data,entitlement=lambda:{},audit=events.append,confirmed=True,writes_enabled=True)
            self.assertFalse((root/'hello.txt').exists())
            result=run_hosting_operation(scope,engine,'files.write',data,entitlement=lambda:grant,audit=events.append,confirmed=True,writes_enabled=True)
            self.assertEqual((root/'hello.txt').read_bytes(),b'hello')
            self.assertIn('request_id',result)
            self.assertEqual([e['outcome'] for e in events],['started','succeeded'])
            self.assertNotIn(data['content_base64'],str(events))
    def test_revocation_after_write_reports_ambiguity_and_receipt(self):
        from bridge.hosting_management import run_hosting_operation
        scope=ServiceScope(41,13,'e60d4718-34b4-4e46-b171-04515159a7b1')
        grant={'subject_id':41,'service_id':13,'binding_ref':scope.binding_ref,'capabilities':['overview'],'management':{'version':1,'capabilities':['files.mkdir']}}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'account';root.mkdir();control=Path(tmp)/'control';control.mkdir(mode=0o700)
            engine=HostingEngine(root,control,service_id=13,binding_ref=scope.binding_ref,domains=[],nameservers=[],capabilities=['files.mkdir'])
            self.addCleanup(engine.close); events=[]; grants=iter([grant,{}])
            with self.assertRaises(ManagementRejected): run_hosting_operation(scope,engine,'files.mkdir',{'path':'made'},entitlement=lambda:next(grants),audit=events.append,confirmed=True,writes_enabled=True)
            self.assertTrue((root/'made').is_dir())
            self.assertEqual(events[-1]['outcome'],'unknown')
            self.assertEqual(engine.receipt(events[-1]['request_id'])['outcome'],'succeeded')
