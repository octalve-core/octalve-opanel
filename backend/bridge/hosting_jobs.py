"""Explicit operator worker coordinator. No HTTP route, daemon, or retries."""
import math
import time

from native_agent.filesystem import Refused
from .hosting_management import run_hosting_operation
from .management import ServiceScope, _authorized, ManagementRejected


def _failure_outcome(engine, job_id):
    """Native dispatch starts only after its durable `started` receipt commits.

    Only the engine's explicit absent-receipt response proves preexecution
    failure. Unavailable receipts and any ambiguous mutation remain unknown.
    A successful receipt cannot override a failed entitlement/audit boundary.
    """
    try:
        receipt = engine.receipt(job_id)
    except Refused as exc:
        return 'failed' if str(exc) == 'Unknown request.' else 'unknown'
    except Exception:
        return 'unknown'
    return 'failed' if isinstance(receipt, dict) and receipt.get('outcome') == 'rejected' else 'unknown'


def run_next(store, engine, *, entitlement, audit, now=None):
    """Trusted store/engine/resolvers only; enqueue confirmation is not a grant.

    `now` is a test/operator clock override. Without it, completion re-reads
    wall time so an operation exceeding its lease cannot report success.
    """
    job = store.claim(now=now)
    if job is None:
        return None
    scope = ServiceScope(job['subject_id'], job['service_id'], job['binding_ref'])
    result = None
    try:
        result = run_hosting_operation(
            scope, engine, job['operation'], job['data'], entitlement=entitlement,
            audit=audit, confirmed=job['confirmed'], writes_enabled=True,
            request_id=job['job_id'])
        outcome = 'succeeded'
    except Exception:
        outcome = _failure_outcome(engine, job['job_id'])
    try:
        store.finish(job['job_id'], job['lease_token'], outcome=outcome, result=result, now=now)
    except Refused:
        # Oversized/invalid results cannot convert an executed job into a
        # success. An expired lease is already durably unknown in finish().
        try:
            store.finish(job['job_id'], job['lease_token'], outcome='unknown', now=now)
        except Refused:
            pass
    return store.status(job['job_id'], subject_id=job['subject_id'])


def run_cycle(store, engine, *, entitlement, audit, enabled=False, max_jobs=10, now=None):
    """Run one explicitly enabled, bounded operator cycle; never retry terminal jobs.

    Materialize schedules once. An explicit trusted clock is forwarded to jobs;
    otherwise run_next retains its wall-clock lease checks throughout execution.
    Storage errors propagate to the operator, including after a native mutation.
    """
    if (enabled is not True or type(max_jobs) is not int or not 1 <= max_jobs <= 100
            or store.service_id != engine.service_id or store.binding_ref != engine.binding_ref):
        raise Refused('Enabled, bounded worker with matching service binding required.')
    scheduled = store.enqueue_due(time.time() if now is None else now)
    jobs, counts = [], {}
    for _ in range(max_jobs):
        status = run_next(store, engine, entitlement=entitlement, audit=audit, now=now)
        if status is None:
            break
        jobs.append({'id':status['id'], 'state':status['state']})
        counts[status['state']] = counts.get(status['state'], 0) + 1
    return {'scheduled':len(scheduled), 'processed':len(jobs), 'counts':counts, 'jobs':jobs}


def inspect_job(store, engine, job_id, *, subject_id, entitlement):
    """Inspect safe status/receipt metadata after fresh, scoped authorization.

    This is evidence for operator reconciliation, never a completion/retry API.
    Receipt results are deliberately excluded even when the engine stores them.
    """
    status = store.status(job_id, subject_id=subject_id)
    scope = ServiceScope(subject_id, store.service_id, store.binding_ref)
    if (store.service_id != engine.service_id or store.binding_ref != engine.binding_ref
            or not _authorized(entitlement(), scope, status['operation'])):
        raise ManagementRejected('Current entitlement and matching service binding required.')
    safe_status = {key:status[key] for key in
                   ('id', 'operation', 'state', 'created', 'updated', 'due', 'schedule_id')}
    receipt_status = {'state':'unavailable'}
    try:
        receipt = engine.receipt(job_id)
    except Refused as exc:
        if str(exc) == 'Unknown request.':
            receipt_status = {'state':'unobserved'}
    except Exception:
        pass
    else:
        # Current HostingEngine receipts identify request/operation, while the
        # configured journal identity binds service. No service field exists.
        try:
            valid = (isinstance(receipt, dict) and receipt.get('request_id') == job_id
                and receipt.get('operation') == status['operation']
                and receipt.get('outcome') in ('started', 'succeeded', 'unknown', 'rejected')
                and type(receipt.get('recorded_at')) in (int, float)
                and math.isfinite(receipt['recorded_at']) and receipt['recorded_at'] >= 0)
        except (ValueError, TypeError, OverflowError):
            valid = False
        if valid:
            receipt_status = {'state':'observed', **{key:receipt[key] for key in
                              ('request_id', 'operation', 'outcome', 'recorded_at')}}
    return {'job':safe_status, 'receipt':receipt_status}
