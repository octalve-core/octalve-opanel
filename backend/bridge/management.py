"""Provider-neutral management boundary. Not mounted as an HTTP route.

A future confidential Console grant must explicitly allow each operation.
Current overview-only Console v1 grants intentionally fail this boundary.
"""
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Protocol
from .views import valid_binding


class ManagementRejected(Exception):
    pass


@dataclass(frozen=True)
class ServiceScope:
    subject_id: int
    service_id: int
    binding_ref: str


class Adapter(Protocol):
    scope: ServiceScope
    capabilities: frozenset[str]

    def execute(self, operation: str, path: str, request_id: str) -> dict: ...


class NativeAdapter:
    capabilities = frozenset({'files.list', 'usage.read', 'files.mkdir'})

    def __init__(self, scope, node_id, key, transport):
        self.scope, self.node_id = scope, node_id
        self._key, self._transport = key, transport

    def execute(self, operation, path, request_id):
        request = {'version':1, 'node_id':self.node_id,
                   'service_id':self.scope.service_id,'binding_ref':self.scope.binding_ref,
                   'request_id':request_id,'expires_at':int(time.time())+30,
                   'operation':operation,'path':path}
        raw = json.dumps(request, sort_keys=True, separators=(',', ':')).encode()
        signature = hmac.new(self._key, raw, hashlib.sha256).hexdigest()
        # No retry: ambiguous mutation outcomes require reconciliation.
        return self._transport(raw, signature)


def _authorized(grant, scope, operation):
    if not valid_binding(grant, scope.subject_id, scope.service_id, scope.binding_ref):
        return False
    management = grant.get('management')
    return (isinstance(management, dict) and type(management.get('version')) is int
            and management['version'] == 1
            and isinstance(management.get('capabilities'), list)
            and all(isinstance(c, str) for c in management['capabilities'])
            and operation in management['capabilities'])


def run_operation(scope, adapter: Adapter, operation, *, entitlement, audit,
                  path='', writes_enabled=False, confirmed=False):
    """Server-supplied adapter, entitlement function and durable audit sink only.

    Callers must never bind these from browser input. No production resolver is
    configured in this batch. `confirmed` must follow a CSRF-protected user
    confirmation; a boolean received directly from an anonymous client is not
    authorization. Future HTTP routes must enforce that additional boundary.
    """
    mutation = operation == 'files.mkdir'
    if (scope != adapter.scope or operation not in adapter.capabilities
            or operation not in ('files.list','usage.read','files.mkdir')
            or (mutation and (writes_enabled is not True or confirmed is not True))):
        raise ManagementRejected('Operation is not enabled for this service.')
    if (not isinstance(path, str) or len(path) > 1024 or "\\" in path
            or any(ord(c) < 32 or ord(c) == 127 for c in path)
            or (path and any(p in ('', '.', '..') for p in path.split('/')))):
        raise ManagementRejected('Invalid operation target.')
    # This is a restricted durable audit record, not a general application log.
    # Binding and target are needed to reconcile an ambiguous remote mutation.
    event = {'request_id':secrets.token_hex(16),'service_id':scope.service_id,
             'subject_id':scope.subject_id,'operation':operation,
             'binding_ref':scope.binding_ref,'target_path':path}
    started = False
    try:
        if not _authorized(entitlement(), scope, operation):
            raise ManagementRejected('Current operation entitlement is unavailable.')
        audit({**event,'outcome':'started'})
        started = True
        result = adapter.execute(operation, path, event['request_id'])
        if not _authorized(entitlement(), scope, operation):
            raise ManagementRejected('Access changed during operation.')
        if not isinstance(result, dict):
            raise ManagementRejected('Invalid adapter result.')
        audit({**event,'outcome':'succeeded'})
        return result
    except Exception as exc:
        if started:
            try:
                audit({**event,'outcome':'unknown' if mutation else 'rejected'})
            except Exception:
                pass
        raise ManagementRejected('Operation could not be verified. Reconcile writes before retrying.') from exc


class VendorAdapter:
    capabilities = frozenset({'usage.read'})

    def __init__(self, target):
        self.scope = ServiceScope(target.subject_id, target.service_id, target.binding_ref)
        self._target = target

    def execute(self, operation, path, request_id):
        from dataclasses import asdict
        from .providers import read_usage
        if operation != 'usage.read' or path:
            raise ManagementRejected('Unsupported vendor operation.')
        return asdict(read_usage(self._target))
