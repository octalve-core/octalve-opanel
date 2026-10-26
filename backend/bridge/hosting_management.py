"""Fresh entitlement boundary for configured native hosting engines, not HTTP.

A resolver must supply a trusted confined engine. No browser-supplied paths,
credentials or engine configuration may be used to construct that resolver.
"""
import secrets
from native_agent.engine import OPERATIONS, READS
from .management import _authorized, ManagementRejected


def run_hosting_operation(scope,engine,operation,data,*,entitlement,audit,confirmed=False,writes_enabled=False):
    mutation=operation not in READS
    if (scope.service_id!=engine.service_id or scope.binding_ref!=engine.binding_ref
            or operation not in OPERATIONS or operation not in engine.capabilities
            or (mutation and (confirmed is not True or writes_enabled is not True))):
        raise ManagementRejected('Hosting operation is unavailable.')
    event={'request_id':secrets.token_hex(16),'subject_id':scope.subject_id,'service_id':scope.service_id,
           'binding_ref':scope.binding_ref,'operation':operation}
    started=False
    try:
        if not _authorized(entitlement(),scope,operation): raise ManagementRejected('Current entitlement required.')
        audit({**event,'outcome':'started'}); started=True
        result=engine.execute(service_id=scope.service_id,operation=operation,data=data,request_id=event['request_id'],confirmed=confirmed)
        if not _authorized(entitlement(),scope,operation): raise ManagementRejected('Access changed during operation.')
        audit({**event,'outcome':'succeeded'})
        return {'request_id':event['request_id'],**result}
    except Exception as exc:
        if started:
            try: audit({**event,'outcome':'unknown' if mutation else 'rejected'})
            except Exception: pass
        raise ManagementRejected('Operation could not be verified; reconcile writes using the operation record.') from exc
