"""Real temporary filesystem tests; never touches a hosting server."""
import hashlib
import hmac
import json
import tempfile
import time
from pathlib import Path
from unittest import TestCase
from native_agent.worker import Worker, AgentRejected

KEY = b'synthetic-worker-key-32-bytes-long!'
BINDING = 'e60d4718-34b4-4e46-b171-04515159a7b1'

class NativeWorkerTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'account'
        self.root.mkdir()
        (self.root / 'index.html').write_text('hello')
        self.worker = Worker(self.root, Path(self.tmp.name) / 'replay.db', KEY,
                             node_id='node-1', service_id=13, binding_ref=BINDING)
        self.sequence = 0

    def request(self, operation='files.list', path='', **changes):
        self.sequence += 1
        body = {'version': 1, 'node_id': 'node-1', 'service_id': 13,
                'binding_ref': BINDING, 'request_id': f'{self.sequence:032x}',
                'expires_at': int(time.time()) + 30, 'operation': operation, 'path': path}
        body.update(changes)
        raw = json.dumps(body, separators=(',', ':'), sort_keys=True).encode()
        return raw, hmac.new(KEY, raw, hashlib.sha256).hexdigest()

    def test_real_inventory_and_usage(self):
        result = self.worker.execute(*self.request())
        self.assertEqual(result['entries'], [{'name': 'index.html', 'kind': 'file', 'size_bytes': 5}])
        result = self.worker.execute(*self.request('usage.read'))
        self.assertEqual(result['file_bytes'], 5)
        self.assertIsNone(result['bandwidth_bytes'])

    def test_traversal_absolute_and_symlink_denied(self):
        (self.root / 'escape').symlink_to(self.tmp.name, target_is_directory=True)
        for path in ('../', '/etc', 'escape', 'a/../../', 'a\\b'):
            with self.subTest(path=path), self.assertRaises(AgentRejected):
                self.worker.execute(*self.request(path=path))

    def test_scope_signature_expiry_and_unknown_operation_denied(self):
        for changes in ({'node_id':'other'}, {'service_id':14}, {'binding_ref':'other'},
                        {'expires_at':0}, {'expires_at':int(time.time())+1000},
                        {'operation':'shell'}, {'extra':'injected'}, {'service_id':True}):
            with self.subTest(changes=changes), self.assertRaises(AgentRejected):
                self.worker.execute(*self.request(**changes))
        raw, _ = self.request()
        with self.assertRaises(AgentRejected):
            self.worker.execute(raw, '0' * 64)

    def test_replay_persists_across_worker_restart(self):
        request = self.request()
        self.worker.execute(*request)
        restarted = Worker(self.root, Path(self.tmp.name) / 'replay.db', KEY,
                           node_id='node-1', service_id=13, binding_ref=BINDING)
        with self.assertRaises(AgentRejected):
            restarted.execute(*request)

    def test_directory_creation_requires_explicit_write_enablement(self):
        with self.assertRaises(AgentRejected):
            self.worker.execute(*self.request('files.mkdir', 'assets'))
        self.assertFalse((self.root / 'assets').exists())
        self.worker.allow_mkdir = True
        result = self.worker.execute(*self.request('files.mkdir', 'assets'))
        self.assertEqual(result['status'], 'created')
        self.assertTrue((self.root / 'assets').is_dir())
        with self.assertRaises(AgentRejected):
            self.worker.execute(*self.request('files.mkdir', 'assets'))

    def test_symlinks_not_counted_and_inventory_is_bounded(self):
        (self.root / 'link').symlink_to('/etc/passwd')
        self.assertEqual(self.worker.execute(*self.request('usage.read'))['file_bytes'], 5)
        self.worker.max_entries = 1
        with self.assertRaises(AgentRejected):
            self.worker.execute(*self.request())
