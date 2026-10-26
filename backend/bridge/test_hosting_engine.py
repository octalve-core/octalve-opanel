import base64
import tempfile
import uuid
from pathlib import Path
from unittest import TestCase
from native_agent.filesystem import Refused

class HostingEngineTests(TestCase):
    def setUp(self):
        from native_agent.engine import HostingEngine, OPERATIONS
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'account'; self.root.mkdir()
        self.control=Path(self.tmp.name)/'control'; self.control.mkdir(mode=0o700)
        self.engine=HostingEngine(self.root,self.control,service_id=13,binding_ref='binding-13',domains=['example.test','www.example.test'],nameservers=['ns1.provider.test'],capabilities=set(OPERATIONS))
        self.addCleanup(self.engine.close)
    def execute(self,operation,data=None,**kwargs):
        return self.engine.execute(service_id=13,operation=operation,data=data or {},request_id=uuid.uuid4().hex,confirmed=True,**kwargs)
    def test_real_file_backup_restore_roundtrip(self):
        self.execute('files.write',{'path':'index.html','content_base64':base64.b64encode(b'actual bytes').decode()})
        snapshot=self.execute('backups.create')
        self.execute('backups.restore',{'snapshot_id':snapshot['snapshot_id'],'target':'recovered'})
        self.assertEqual((self.root/'recovered/index.html').read_bytes(),b'actual bytes')
        self.assertEqual(self.execute('usage.read')['file_bytes'],24)
    def test_default_disabled_wrong_service_and_unconfirmed_mutations(self):
        from native_agent.engine import HostingEngine
        other=HostingEngine(self.root,self.control,service_id=13,binding_ref='binding-13',domains=['example.test'],nameservers=['ns1.provider.test'])
        try:
            with self.assertRaises(Refused): other.execute(service_id=13,operation='files.list',data={},request_id=uuid.uuid4().hex)
            with self.assertRaises(Refused): self.engine.execute(service_id=14,operation='files.list',data={},request_id=uuid.uuid4().hex)
            with self.assertRaises(Refused): self.engine.execute(service_id=13,operation='files.mkdir',data={'path':'dir'},request_id=uuid.uuid4().hex)
        finally: other.close()
    def test_durable_receipts_block_replay_and_record_failure(self):
        rid=uuid.uuid4().hex
        args=dict(service_id=13,operation='files.mkdir',data={'path':'created'},request_id=rid,confirmed=True)
        self.engine.execute(**args)
        with self.assertRaises(Refused): self.engine.execute(**args)
        self.assertEqual(self.engine.receipt(rid)['outcome'],'succeeded')
        failed=uuid.uuid4().hex
        with self.assertRaises(Refused): self.engine.execute(**{**args,'request_id':failed,'data':{'path':'../bad'}})
        self.assertEqual(self.engine.receipt(failed)['outcome'],'unknown')
        self.assertNotIn('content',str(self.engine.receipt(rid)))
    def test_zone_revision_and_scope(self):
        data={'zone':'example.test','expected_serial':0,'records':[{'name':'@','type':'A','value':'192.0.2.1','ttl':300}]}
        result=self.execute('dns.replace',data)
        self.assertEqual(result['serial'],1)
        self.assertFalse(result['server_reloaded'])
        with self.assertRaises(Refused): self.execute('dns.replace',data)
        with self.assertRaises(Refused): self.execute('dns.replace',{**data,'zone':'foreign.test'})
        self.assertIn('192.0.2.1',(self.control/'dns/example.test.zone').read_text())
    def test_control_storage_cannot_be_inside_customer_root(self):
        from native_agent.engine import HostingEngine
        control=self.root/'control'; control.mkdir(mode=0o700)
        with self.assertRaises(Refused): HostingEngine(self.root,control,service_id=13,binding_ref='binding-13',domains=[],nameservers=[])
    def test_same_worker_serializes_threads(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        entered=threading.Event(); second=threading.Event(); release=threading.Event()
        original=self.engine._dispatch
        def observed(op,data,rid):
            if data['path']=='first': entered.set(); release.wait(3)
            else: second.set()
            return original(op,data,rid)
        self.engine._dispatch=observed
        with ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(self.execute,'files.mkdir',{'path':'first'})
            self.assertTrue(entered.wait(2))
            later=pool.submit(self.execute,'files.mkdir',{'path':'second'})
            try: self.assertFalse(second.wait(.2),'Concurrent mutation entered while another holds worker lock')
            finally: release.set(); first.result(); later.result()
