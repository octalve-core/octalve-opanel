"""Durable operator queue tests: real SQLite, encryption and confined mutations."""
import base64
import os
import sqlite3
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import TestCase

from native_agent.filesystem import Refused


class JobStoreTests(TestCase):
    def setUp(self):
        from native_agent.jobs import JobStore
        self.JobStore = JobStore
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name) / 'jobs'
        self.directory.mkdir(mode=0o700)
        self.key = b'k' * 32
        self.store = self.open()

    def open(self, **kwargs):
        return self.JobStore(self.directory, **{'service_id':13, 'binding_ref':'binding-13', 'key':self.key, **kwargs})

    def enqueue(self, **kwargs):
        values = dict(operation='files.mkdir', data={'path':'private-target'}, subject_id=41,
                      idempotency_key='request-1', confirmed=True, now=100)
        values.update(kwargs)
        return self.store.enqueue(**values)

    def test_encrypted_persistent_payload_result_and_scoped_metadata(self):
        job = self.enqueue(data={'path':'sensitive-body'})
        self.assertRegex(job, r'^[a-f0-9]{32}$')
        claim = self.open().claim(now=101)
        self.assertEqual(claim['data'], {'path':'sensitive-body'})
        self.assertEqual((claim['subject_id'],claim['service_id'],claim['binding_ref']), (41,13,'binding-13'))
        self.store.finish(job, claim['lease_token'], outcome='succeeded', result={'secret':'private-result'}, now=102)
        self.assertEqual(self.open().result(job,subject_id=41), {'secret':'private-result'})
        status = self.store.status(job,subject_id=41)
        self.assertEqual(status['state'], 'succeeded')
        for value in ('sensitive-body','private-result','request-1','lease_token','data','result'):
            self.assertNotIn(value, str(status))
        for file in self.directory.iterdir():
            raw=file.read_bytes()
            for secret in (b'sensitive-body',b'private-result',b'request-1',self.key): self.assertNotIn(secret,raw)
        self.assertEqual((self.directory/'jobs.sqlite3').stat().st_mode & 0o777, 0o600)
        for method in (self.store.status,self.store.result,self.store.cancel):
            with self.assertRaises(Refused): method(job,subject_id=42)

    def test_identity_key_and_private_storage_are_enforced(self):
        for kwargs in ({'service_id':14},{'binding_ref':'other'},{'key':b'x'*32},{'key':b'x'}):
            with self.assertRaises(Refused): self.open(**kwargs)
        os.chmod(self.directory,0o755)
        with self.assertRaises(Refused): self.open()
        os.chmod(self.directory,0o700)
        link=Path(self.tmp.name)/'link'; link.symlink_to(self.directory,target_is_directory=True)
        with self.assertRaises(Refused): self.JobStore(link,service_id=13,binding_ref='binding-13',key=self.key)
        db=self.directory/'jobs.sqlite3'; target=Path(self.tmp.name)/'db'; db.rename(target); db.symlink_to(target)
        with self.assertRaises(Refused): self.open()

    def test_duplicates_conflicts_confirmation_and_payload_budget(self):
        job=self.enqueue()
        self.assertEqual(self.enqueue(),job)
        self.assertNotEqual(self.enqueue(subject_id=42),job)
        for kwargs in ({'data':{'path':'changed'}},{'operation':'files.remove','data':{'path':'private-target'}},
                       {'confirmed':False},{'operation':'shell.run'},{'data':{'path':'x'*(6*1024*1024)}},
                       {'data':{'path':float('nan')}},{'data':{'extra':'x'}},{'subject_id':True},{'idempotency_key':''}):
            with self.assertRaises(Refused): self.enqueue(**kwargs)
        read=self.enqueue(operation='files.list',data={},confirmed=False,idempotency_key='read')
        self.assertEqual(self.store.status(read,subject_id=41)['state'],'queued')

    def test_claim_is_atomic_between_independent_instances(self):
        job=self.enqueue(); barrier=threading.Barrier(2)
        def claim():
            other=self.open(); barrier.wait(); return other.claim(now=101)
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims=list(pool.map(lambda _:claim(),range(2)))
        self.assertEqual([c['job_id'] for c in claims if c], [job])

    def test_expiry_never_retries_and_rejects_stale_finish(self):
        job=self.enqueue(); claim=self.store.claim(now=100,lease_seconds=10)
        with self.assertRaises(Refused): self.store.finish(job,'bad-token',outcome='succeeded',now=101)
        with self.assertRaises(Refused): self.store.finish(job,claim['lease_token'],outcome='succeeded',now=110)
        self.assertEqual(self.open().status(job,subject_id=41)['state'],'unknown')
        self.assertIsNone(self.open().claim(now=1000))
        self.assertIsNone(self.store.result(job,subject_id=41))
        for seconds in (0,301,True):
            with self.assertRaises(Refused): self.store.claim(lease_seconds=seconds,now=1000)

    def test_cancellation_and_terminal_result_controls(self):
        job=self.enqueue()
        with self.assertRaises(Refused): self.store.result(job,subject_id=41)
        self.store.cancel(job,subject_id=41)
        self.assertEqual(self.store.status(job,subject_id=41)['state'],'cancelled')
        self.assertIsNone(self.store.claim(now=100))
        other=self.enqueue(idempotency_key='other'); claim=self.store.claim(now=100)
        with self.assertRaises(Refused): self.store.cancel(other,subject_id=41)
        for values in ({'outcome':'queued'}, {'outcome':'succeeded','result':{'body':'x'*(6*1024*1024)}}):
            with self.assertRaises(Refused): self.store.finish(other,claim['lease_token'],now=101,**values)
        self.store.finish(other,claim['lease_token'],outcome='failed',now=101)
        with self.assertRaises(Refused): self.store.finish(other,claim['lease_token'],outcome='succeeded',now=102)

    def test_schedules_dedupe_races_skip_missed_slots_and_cancel_durably(self):
        schedule=self.store.add_schedule('files.mkdir',{'path':'scheduled'},subject_id=41,interval_seconds=300,starts_at=100,confirmed=True)
        self.assertEqual(self.store.enqueue_due(99),[])
        barrier=threading.Barrier(2)
        def due():
            other=self.open(); barrier.wait(); return other.enqueue_due(100)
        with ThreadPoolExecutor(max_workers=2) as pool:
            batches=list(pool.map(lambda _:due(),range(2)))
        self.assertEqual(sum(map(len,batches)),1)
        self.assertEqual(len(self.open().enqueue_due(2000)),1)
        self.assertEqual(self.open().enqueue_due(2000),[])
        self.store.cancel_schedule(schedule,subject_id=41)
        self.assertEqual(self.open().enqueue_due(10000),[])
        for kwargs in ({'interval_seconds':299},{'confirmed':False},{'operation':'bad'}, {'subject_id':False}):
            values=dict(operation='files.mkdir',data={'path':'scheduled'},subject_id=41,interval_seconds=300,starts_at=100,confirmed=True);values.update(kwargs)
            with self.assertRaises(Refused): self.store.add_schedule(**values)
        with self.assertRaises(Refused): self.store.cancel_schedule(schedule,subject_id=42)

    def test_retention_cap_is_atomic_and_duplicates_survive_capacity(self):
        first=self.enqueue()
        # Populate through the real public API, rather than changing private schema.
        for i in range(999): self.enqueue(idempotency_key=f'cap-{i}')
        self.assertEqual(self.enqueue(),first)
        with self.assertRaises(Refused): self.enqueue(idempotency_key='overflow')

    def test_full_payload_budget_accepts_exact_limit(self):
        data={'path':'x'*(6*1024*1024-11)}
        self.assertIsInstance(self.enqueue(data=data),str)

    def test_authenticated_payload_rejects_tampered_runner_fields(self):
        job=self.enqueue(operation='files.read',data={'path':'secret-file'},confirmed=False)
        with sqlite3.connect(self.directory/'jobs.sqlite3') as db:
            db.execute("UPDATE jobs SET operation='files.remove',confirmed=1 WHERE id=?",(job,))
        with self.assertRaises(Refused): self.store.claim(now=101)


    def test_status_expires_a_running_lease_without_needing_another_worker(self):
        from unittest.mock import patch
        job=self.enqueue();self.store.claim(now=100,lease_seconds=10)
        with patch('native_agent.jobs.time.time',return_value=110):
            self.assertEqual(self.open().status(job,subject_id=41)['state'],'unknown')
        self.assertIsNone(self.store.claim(now=1000))

    def test_result_expires_running_lease_to_terminal_unknown(self):
        from unittest.mock import patch
        job=self.enqueue();self.store.claim(now=100,lease_seconds=10)
        with patch('native_agent.jobs.time.time',return_value=110):
            self.assertIsNone(self.open().result(job,subject_id=41))
        self.assertEqual(self.store.status(job,subject_id=41)['state'],'unknown')

    def lock_delay(self, clock):
        """Advance the clock when BEGIN IMMEDIATE has acquired its lock."""
        from contextlib import contextmanager
        transaction = self.store._transaction
        @contextmanager
        def delayed():
            with transaction() as db:
                clock[0] = 102
                yield db
        return delayed

    def test_finish_rechecks_wall_time_after_transaction_lock_delay(self):
        from unittest.mock import patch
        job = self.enqueue()
        claim = self.store.claim(now=100, lease_seconds=1)
        clock = [100.5]
        with patch('native_agent.jobs.time.time', side_effect=lambda: clock[0]), \
                patch.object(self.store, '_transaction', self.lock_delay(clock)):
            with self.assertRaises(Refused):
                self.store.finish(job, claim['lease_token'], outcome='succeeded')
        self.assertEqual(self.store.status(job, subject_id=41)['state'], 'unknown')

    def test_claim_starts_lease_after_transaction_lock_delay(self):
        from unittest.mock import patch
        job = self.enqueue()
        clock = [100.5]
        with patch('native_agent.jobs.time.time', side_effect=lambda: clock[0]), \
                patch.object(self.store, '_transaction', self.lock_delay(clock)):
            claim = self.store.claim(lease_seconds=1)
        self.assertEqual(claim['job_id'], job)
        self.assertEqual(claim['lease_until'], 103)

    def test_explicit_clock_override_survives_transaction_lock_delay(self):
        from unittest.mock import patch
        job = self.enqueue()
        clock = [100.5]
        with patch('native_agent.jobs.time.time', side_effect=lambda: clock[0]), \
                patch.object(self.store, '_transaction', self.lock_delay(clock)):
            claim = self.store.claim(now=100, lease_seconds=1)
            self.assertEqual(claim['lease_until'], 101)
            self.store.finish(job, claim['lease_token'], outcome='succeeded', now=100.5)
        self.assertEqual(self.store.status(job, subject_id=41)['state'], 'succeeded')

    def test_invalid_unicode_payload_is_refused(self):
        with self.assertRaises(Refused):self.enqueue(data={'path':'\ud800'})


class HostingJobRunnerTests(TestCase):
    def setUp(self):
        from native_agent.jobs import JobStore
        from native_agent.engine import HostingEngine, OPERATIONS
        from bridge.hosting_jobs import run_next
        self.run_next=run_next
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'account';self.root.mkdir()
        control=Path(self.tmp.name)/'control';control.mkdir(mode=0o700)
        queue=Path(self.tmp.name)/'queue';queue.mkdir(mode=0o700)
        self.binding='e60d4718-34b4-4e46-b171-04515159a7b1'
        self.store=JobStore(queue,service_id=13,binding_ref=self.binding,key=b'k'*32)
        self.engine=HostingEngine(self.root,control,service_id=13,binding_ref=self.binding,domains=[],nameservers=[],capabilities=OPERATIONS)
        self.addCleanup(self.engine.close)
        self.grant={'subject_id':41,'service_id':13,'binding_ref':self.binding,'capabilities':['overview'],
                    'management':{'version':1,'capabilities':['files.write','files.mkdir','files.list']}}
        self.events=[]

    def enqueue(self,operation='files.write',data=None):
        return self.store.enqueue(operation,data if data is not None else {'path':'hello','content_base64':base64.b64encode(b'private body').decode()},
                                  subject_id=41,idempotency_key='once',confirmed=True,now=100)

    def run_job(self,entitlement=None,audit=None,**kwargs):
        return self.run_next(self.store,self.engine,entitlement=entitlement or (lambda:self.grant),
                             audit=self.events.append if audit is None else audit,**kwargs)

    def test_real_mutation_uses_job_receipt_and_fresh_entitlement_twice(self):
        job=self.enqueue(); checks=[]
        def entitlement(): checks.append(True);return self.grant
        status=self.run_job(entitlement=entitlement,now=100)
        self.assertEqual(status['state'],'succeeded')
        self.assertEqual(self.root.joinpath('hello').read_bytes(),b'private body')
        self.assertEqual(len(checks),2)
        self.assertEqual(self.engine.receipt(job)['outcome'],'succeeded')
        self.assertEqual([e['request_id'] for e in self.events],[job,job])
        self.assertEqual(self.store.result(job,subject_id=41)['request_id'],job)
        self.assertNotIn(base64.b64encode(b'private body').decode(),str(self.events))
        self.assertIsNone(self.run_job(now=101))

    def test_preexecution_revocation_fails_without_mutation_or_retry(self):
        job=self.enqueue()
        status=self.run_job(entitlement=lambda:{},now=100)
        self.assertEqual(status['state'],'failed')
        self.assertFalse(self.root.joinpath('hello').exists())
        with self.assertRaises(Refused): self.engine.receipt(job)
        self.assertIsNone(self.run_job(now=101))
        self.assertIsNone(self.store.result(job,subject_id=41))

    def test_postexecution_revocation_is_unknown_even_with_successful_receipt(self):
        job=self.enqueue();grants=iter([self.grant,{}])
        status=self.run_job(entitlement=lambda:next(grants),now=100)
        self.assertEqual(status['state'],'unknown')
        self.assertTrue(self.root.joinpath('hello').exists())
        self.assertEqual(self.engine.receipt(job)['outcome'],'succeeded')
        self.assertIsNone(self.store.result(job,subject_id=41))
        self.assertEqual(self.events[-1]['outcome'],'unknown')
        self.assertIsNone(self.run_job(now=101))

    def test_failed_native_mutation_is_unknown_and_never_retried(self):
        job=self.enqueue(operation='files.mkdir',data={'path':'../escape'})
        self.assertEqual(self.run_job(now=100)['state'],'unknown')
        self.assertEqual(self.engine.receipt(job)['outcome'],'unknown')
        self.assertIsNone(self.run_job(now=101))

    def test_audit_failure_before_execution_is_failed(self):
        self.enqueue()
        def reject(event): raise RuntimeError('audit unavailable')
        self.assertEqual(self.run_job(audit=reject,now=100)['state'],'failed')
        self.assertFalse(self.root.joinpath('hello').exists())

    def test_audit_failure_after_execution_never_reports_success(self):
        self.enqueue()
        def reject(event):
            if event['outcome']=='succeeded': raise RuntimeError('audit unavailable')
            self.events.append(event)
        self.assertEqual(self.run_job(audit=reject,now=100)['state'],'unknown')
        self.assertTrue(self.root.joinpath('hello').exists())

    def test_fresh_grant_must_match_exact_subject_service_binding_and_operation(self):
        for change in ({'subject_id':42},{'service_id':14},{'binding_ref':'546d4718-34b4-4e46-b171-04515159a7b1'},
                       {'management':{'version':1,'capabilities':['files.list']}}):
            job=self.store.enqueue('files.mkdir',{'path':'denied'},subject_id=41,idempotency_key=str(change),confirmed=True,now=100)
            self.assertEqual(self.run_job(entitlement=lambda:{**self.grant,**change},now=100)['state'],'failed')
            self.assertEqual(self.store.status(job,subject_id=41)['state'],'failed')
        self.assertFalse((self.root/'denied').exists())

    def test_expired_lease_after_execution_remains_unknown(self):
        from unittest.mock import patch
        job=self.enqueue()
        clock=[100]
        dispatch=self.engine._dispatch
        def slow_operation(*args):
            result=dispatch(*args)
            clock[0]=161
            return result
        self.engine._dispatch=slow_operation
        with patch('native_agent.jobs.time.time',side_effect=lambda:clock[0]):
            status=self.run_job()
        self.assertEqual(status['state'],'unknown')
        self.assertEqual(self.engine.receipt(job)['outcome'],'succeeded')
        self.assertIsNone(self.run_job(now=1000))

    def test_unavailable_or_malformed_receipt_is_unknown(self):
        self.enqueue(operation='files.mkdir',data={'path':'../escape'})
        self.engine.receipt=lambda request_id:None
        self.assertEqual(self.run_job(now=100)['state'],'unknown')


class HostingWorkerTests(HostingJobRunnerTests):
    def cycle(self, **kwargs):
        from bridge import hosting_jobs
        self.assertTrue(callable(getattr(hosting_jobs, 'run_cycle', None)), 'run_cycle is missing')
        values = dict(entitlement=lambda: self.grant, audit=self.events.append, enabled=True, now=100)
        values.update(kwargs)
        return hosting_jobs.run_cycle(self.store, self.engine, **values)

    def inspect(self, job, **kwargs):
        from bridge import hosting_jobs
        self.assertTrue(callable(getattr(hosting_jobs, 'inspect_job', None)), 'inspect_job is missing')
        values = dict(subject_id=41, entitlement=lambda: self.grant)
        values.update(kwargs)
        return hosting_jobs.inspect_job(self.store, self.engine, job, **values)

    def test_cycle_gate_and_identity_precede_all_queue_mutations(self):
        job = self.enqueue()
        self.store.add_schedule('files.mkdir', {'path':'scheduled'}, subject_id=41,
                                interval_seconds=300, starts_at=100, confirmed=True)
        for kwargs in ({'enabled':False}, {'enabled':1}, {'max_jobs':True}, {'max_jobs':0}, {'max_jobs':101}):
            with self.assertRaises(Refused): self.cycle(**kwargs)
        self.engine.binding_ref = 'wrong'
        with self.assertRaises(Refused): self.cycle()
        self.engine.binding_ref = self.binding
        self.engine.service_id = 14
        with self.assertRaises(Refused): self.cycle()
        self.engine.service_id = 13
        self.assertEqual(self.store.status(job, subject_id=41)['state'], 'queued')
        self.assertEqual(len(self.store.enqueue_due(100)), 1)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_cycle_bound_safe_summary_and_due_schedule_execution(self):
        first = self.enqueue()
        self.store.add_schedule('files.mkdir', {'path':'scheduled'}, subject_id=41,
                                interval_seconds=300, starts_at=100, confirmed=True)
        summary = self.cycle(max_jobs=1)
        self.assertEqual(summary['scheduled'], 1)
        self.assertEqual(summary['processed'], 1)
        self.assertEqual(summary['counts'], {'succeeded':1})
        self.assertEqual(set(summary['jobs'][0]), {'id','state'})
        second = self.cycle(max_jobs=1)
        self.assertEqual(second['scheduled'], 0)
        self.assertEqual(second['processed'], 1)
        self.assertTrue((self.root/'scheduled').is_dir())
        self.assertTrue((self.root/'hello').is_file())
        self.assertIn(first, str([summary, second]))
        self.assertNotIn('private body', str(summary))
        self.assertNotIn('lease_token', str(summary))

    def test_cycle_revoked_grant_and_unknown_are_never_retried(self):
        job = self.enqueue()
        self.assertEqual(self.cycle(entitlement=lambda:{})['counts'], {'failed':1})
        self.assertFalse((self.root/'hello').exists())
        other = self.store.enqueue('files.mkdir', {'path':'../escape'}, subject_id=41,
                                   idempotency_key='uncertain', confirmed=True, now=100)
        self.assertEqual(self.cycle()['counts'], {'unknown':1})
        self.assertEqual(self.cycle()['processed'], 0)
        self.assertEqual(self.store.status(other, subject_id=41)['state'], 'unknown')
        self.assertEqual(self.store.status(job, subject_id=41)['state'], 'failed')

    def test_cycle_storage_failures_propagate(self):
        from unittest.mock import patch
        with patch.object(self.store, 'enqueue_due', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError): self.cycle()
        self.enqueue()
        with patch.object(self.store, 'finish', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError): self.cycle()

    def test_sqlite_completion_failure_stops_cycle_without_duplicate_execution(self):
        first = self.enqueue()
        second = self.store.enqueue('files.mkdir', {'path':'next'}, subject_id=41,
                                    idempotency_key='next', confirmed=True, now=101)
        dispatch = self.engine._dispatch
        executions = []
        def fail_completion(*args):
            executions.append(True)
            result = dispatch(*args)
            with sqlite3.connect(self.store.db) as db:
                db.execute("""CREATE TRIGGER deny_completion BEFORE UPDATE OF state ON jobs
                    WHEN OLD.state='running' AND NEW.state!='running'
                    BEGIN SELECT RAISE(ABORT, 'completion unavailable'); END""")
            return result
        self.engine._dispatch = fail_completion
        from unittest.mock import patch
        with patch('native_agent.jobs.time.time', return_value=101):
            with self.assertRaisesRegex(Refused, 'Queue storage unavailable') as error:
                self.cycle(now=101)
        self.assertIsInstance(error.exception.__cause__, sqlite3.Error)
        self.assertTrue((self.root/'hello').exists())
        self.assertFalse((self.root/'next').exists())
        with sqlite3.connect(self.store.db) as db:
            states = dict(db.execute('SELECT id,state FROM jobs'))
            db.execute('DROP TRIGGER deny_completion')
        self.assertEqual(states, {first:'running', second:'queued'})
        self.engine._dispatch = dispatch
        self.assertEqual(self.cycle(now=102)['counts'], {'succeeded':1})
        self.assertEqual(len(executions), 1)
        self.assertEqual(self.cycle(now=1000)['processed'], 0)
        self.assertEqual(self.store.status(first, subject_id=41)['state'], 'unknown')

    def test_unsafe_completion_storage_is_not_retried(self):
        from unittest.mock import patch
        self.enqueue()
        dispatch = self.engine._dispatch
        def unsafe_storage(*args):
            result = dispatch(*args)
            self.store.db.chmod(0o644)
            return result
        self.engine._dispatch = unsafe_storage
        with patch.object(self.store, 'finish', wraps=self.store.finish) as finish:
            with self.assertRaisesRegex(Refused, 'Unsafe queue database'):
                self.cycle()
            self.assertEqual(finish.call_count, 1)
        self.assertTrue((self.root/'hello').exists())

    def test_invalid_result_fallback_storage_failure_propagates(self):
        from unittest.mock import patch
        from bridge.hosting_management import run_hosting_operation
        self.enqueue()
        def invalid_result(*args, **kwargs):
            run_hosting_operation(*args, **kwargs)
            with sqlite3.connect(self.store.db) as db:
                db.execute("""CREATE TRIGGER deny_completion BEFORE UPDATE OF state ON jobs
                    WHEN OLD.state='running' AND NEW.state!='running'
                    BEGIN SELECT RAISE(ABORT, 'completion unavailable'); END""")
            return {'invalid': object()}
        with patch('native_agent.jobs.time.time', return_value=100), patch(
                'bridge.hosting_jobs.run_hosting_operation', side_effect=invalid_result):
            with self.assertRaisesRegex(Refused, 'Queue storage unavailable'):
                self.cycle()

    def test_invalid_and_oversized_results_become_unknown(self):
        from unittest.mock import patch
        from bridge.hosting_management import run_hosting_operation
        for index, result in enumerate(({'invalid':object()}, {'body':'x'*(6*1024*1024)})):
            job = self.store.enqueue('files.mkdir', {'path':f'invalid-{index}'}, subject_id=41,
                                     idempotency_key=f'invalid-{index}', confirmed=True, now=100)
            def invalid_result(*args, **kwargs):
                run_hosting_operation(*args, **kwargs)
                return result
            with patch('bridge.hosting_jobs.run_hosting_operation', side_effect=invalid_result):
                self.assertEqual(self.cycle()['counts'], {'unknown':1})
            self.assertTrue((self.root/f'invalid-{index}').exists())
            self.assertIsNone(self.store.result(job, subject_id=41))
        self.assertEqual(self.cycle()['processed'], 0)

    def test_inspection_denies_foreign_subject_identity_and_revocation_before_receipt(self):
        from unittest.mock import patch
        from bridge.management import ManagementRejected
        job = self.enqueue()
        with patch.object(self.engine, 'receipt', side_effect=AssertionError('receipt must not be read')) as receipt:
            with self.assertRaises(Refused): self.inspect(job, subject_id=42)
            self.engine.binding_ref = 'wrong'
            with self.assertRaises(ManagementRejected): self.inspect(job)
            self.engine.binding_ref = self.binding
            with self.assertRaises(ManagementRejected): self.inspect(job, entitlement=lambda:{})
            receipt.assert_not_called()

    def test_inspection_absent_unavailable_and_malformed_receipts(self):
        from unittest.mock import patch
        job = self.enqueue()
        self.assertEqual(self.inspect(job)['receipt'], {'state':'unobserved'})
        for receipt in (None, {}, {'request_id':job,'operation':'files.mkdir','outcome':'succeeded','recorded_at':100},
                        {'request_id':job,'operation':'files.write','outcome':'succeeded','recorded_at':'secret'}):
            with patch.object(self.engine, 'receipt', return_value=receipt):
                self.assertEqual(self.inspect(job)['receipt'], {'state':'unavailable'})
        with patch.object(self.engine, 'receipt', side_effect=OSError('private path')):
            self.assertEqual(self.inspect(job)['receipt'], {'state':'unavailable'})

    def test_inspection_safe_native_receipt_and_unknown_remains_unknown(self):
        from unittest.mock import patch
        job = self.enqueue()
        grants = iter([self.grant, {}])
        self.run_job(entitlement=lambda:next(grants), now=100)
        result = self.inspect(job)
        self.assertEqual(result['job']['state'], 'unknown')
        self.assertEqual(result['receipt']['outcome'], 'succeeded')
        self.assertEqual(set(result['receipt']), {'state','request_id','operation','outcome','recorded_at'})
        self.assertNotIn('result', result['receipt'])
        self.assertNotIn('path', str(result))
        self.assertEqual(self.store.status(job, subject_id=41)['state'], 'unknown')
        with patch.object(self.engine, 'receipt', return_value={**self.engine.receipt(job), 'outcome':'unknown'}):
            self.assertEqual(self.inspect(job)['receipt']['outcome'], 'unknown')

    def test_inspection_expires_executed_running_job_without_promoting_success(self):
        from unittest.mock import patch
        job = self.enqueue()
        claim = self.store.claim(now=100, lease_seconds=1)
        self.engine.execute(service_id=13, operation=claim['operation'], data=claim['data'],
                            request_id=job, confirmed=True)
        with patch('native_agent.jobs.time.time', return_value=102):
            self.assertEqual(self.inspect(job)['job']['state'], 'unknown')
        self.assertEqual(self.inspect(job)['receipt']['outcome'], 'succeeded')

    def test_inspection_malformed_outcome_and_extreme_timestamp_are_unavailable(self):
        from unittest.mock import patch
        job = self.enqueue()
        receipt = {'request_id':job, 'operation':'files.write', 'outcome':'succeeded',
                   'recorded_at':100, 'result':{'path':'private', 'secret':'never return'}}
        for change in ({'recorded_at':10**1000}, {'recorded_at':float('nan')},
                       {'outcome':['succeeded']}, {'request_id':'0'*32}):
            with patch.object(self.engine, 'receipt', return_value={**receipt, **change}):
                self.assertEqual(self.inspect(job)['receipt'], {'state':'unavailable'})
