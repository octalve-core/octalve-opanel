"""Server-only DirectAdmin/WHM read-only adapter foundation.

This adapter is independent of Octalve Console implementation: the only
cross-product dependency is the authenticated entitlement contract. All
technical modifications are deliberately disabled. Calling this module does
not create, suspend, modify, delete, or authenticate the customer's account.
No provider credential is written to sessions, responses, logs or Django DB.
"""
import base64
import ipaddress
import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import requests
from django.conf import settings
from .client import ConsoleUnavailable, console_post
from .views import valid_binding

ACCOUNT = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,31}$")
DOMAIN = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))+$")
ADAPTERS = frozenset({"directadmin", "whm"})


class ProviderRejected(Exception):
    """Do not include the vendor's raw error body or authorization header."""


@dataclass(frozen=True)
class AccountTarget:
    provider: str
    https_origin: str
    api_user: str
    api_token: str = field(repr=False)
    expected_owner: str = ""
    account: str = ""
    domain: str = ""
    subject_id: int = 0
    service_id: int = 0
    binding_ref: str = ""


@dataclass(frozen=True)
class AccountReadback:
    provider: str
    account: str
    domain: str
    owner: str
    active: bool


def _validate(target):
    if not getattr(settings, "OPANEL_VENDOR_READBACK_ENABLED", False):
        raise ProviderRejected("Technical vendor read-back is not enabled.")
    if target.provider not in ADAPTERS:
        raise ProviderRejected("No audited adapter for this provider.")
    allowed = {s.strip().lower().rstrip(".") for s in
               os.getenv("OPANEL_PROVIDER_ALLOWED_HOSTS", "").split(",") if s.strip()}
    try:
        parsed = urlsplit(target.https_origin)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        raise ProviderRejected("Provider endpoint URL or port is invalid.") from None
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ProviderRejected("IP literal provider endpoints are forbidden.")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ProviderRejected("Internal/local provider hostname is forbidden.")
    if (
        parsed.scheme != "https" or not host or host not in allowed
        or parsed.username or parsed.password or parsed.query or parsed.fragment
        or parsed.path not in ("", "/")
        or port not in ((443, 2222) if target.provider == "directadmin" else (443, 2087))
        or not ACCOUNT.fullmatch(target.api_user or "")
        or not ACCOUNT.fullmatch(target.expected_owner or "")
        or not ACCOUNT.fullmatch(target.account or "")
        or not DOMAIN.fullmatch((target.domain or "").lower())
        or type(target.service_id) is not int or target.service_id < 1
        or type(target.subject_id) is not int or target.subject_id < 1
    ):
        raise ProviderRejected("Provider identity or approved endpoint is invalid.")
    return target.https_origin.rstrip("/")


@dataclass(frozen=True)
class UsageSnapshot:
    disk_used_mb: float
    disk_limit_mb: float | None
    bandwidth_used_mb: float | None
    bandwidth_limit_mb: float | None
    source: str


def _entitled(target):
    try:
        grant = console_post("entitlement/", {"subject_id": target.subject_id, "service_id": target.service_id})
    except ConsoleUnavailable as exc:
        raise ProviderRejected("Authoritative entitlement could not be verified.") from exc
    if not valid_binding(grant, target.subject_id, target.service_id, target.binding_ref):
        raise ProviderRejected("Hosting entitlement or binding is no longer valid.")


def _get(target, endpoint, params, getter):
    origin = _validate(target)
    if not isinstance(target.api_token, str) or not target.api_token or any(c in target.api_token for c in "\r\n"):
        raise ProviderRejected("Server-only provider credential is unavailable.")
    auth = ("whm " + target.api_user + ":" + target.api_token) if target.provider == "whm" else (
        "Basic " + base64.b64encode((target.api_user + ":" + target.api_token).encode()).decode())
    response = None
    try:
        response = (getter or requests.get)(origin + endpoint, params=params, headers={
            "Accept": "application/json", "Authorization": auth,
        }, timeout=8, allow_redirects=False, verify=True, stream=True)
        length = response.headers.get("Content-Length", "")
        if response.status_code != 200 or (length and int(length) > 100000):
            raise ProviderRejected("Provider account query was rejected.")
        raw = response.raw.read(100001, decode_content=True)
        if len(raw) > 100000:
            raise ProviderRejected("Provider response exceeds the allowed size.")
        return raw.decode("utf-8")
    except (ValueError, TypeError, UnicodeError, requests.RequestException, OSError) as exc:
        raise ProviderRejected("Provider response could not be verified.") from exc
    finally:
        if response is not None:
            response.close()


def _form(raw):
    from urllib.parse import parse_qs
    fields = parse_qs(raw, keep_blank_values=True, max_num_fields=1000)
    if any(len(v) != 1 for v in fields.values()):
        raise ProviderRejected("DirectAdmin response is ambiguous.")
    item = {key: values[0] for key, values in fields.items()}
    if item.get("error", "0") != "0":
        raise ProviderRejected("DirectAdmin rejected the query.")
    return item


def _number(value, *, limit=False, whm=False):
    import math
    if limit and value == "unlimited":
        return None
    if isinstance(value, str) and whm and value.endswith("M"):
        value = value[:-1]
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ProviderRejected("Usage measurement unavailable.")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 10**12:
        raise ProviderRejected("Usage measurement invalid.")
    return number


def _read(target, getter, usage):
    _validate(target)
    _entitled(target)
    try:
        if target.provider == "whm":
            import json
            info = json.loads(_get(target, "/json-api/accountsummary",
                                   {"api.version":"1", "user":target.account}, getter))
            if not isinstance(info, dict) or not isinstance(info.get("data"), dict):
                raise ProviderRejected("WHM response malformed.")
            rows = info["data"].get("acct")
            if (not isinstance(info.get("metadata"), dict) or str(info["metadata"].get("result")) != "1"
                    or not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict)):
                raise ProviderRejected("WHM did not verify the account.")
            item = rows[0]
            owner, user, domain = item.get("owner"), item.get("user"), item.get("domain")
            active = str(item.get("suspended", "")).lower() in ("0", "false")
        else:
            item = _form(_get(target, "/CMD_API_SHOW_USER_CONFIG", {"user":target.account}, getter))
            owner, user, domain = item.get("creator"), item.get("username"), item.get("domain")
            active = item.get("account") == "ON" and item.get("suspended") == "no" and item.get("usertype") == "user"
        if (user != target.account or owner != target.expected_owner or not isinstance(domain, str)
                or domain.rstrip(".").lower() != target.domain.rstrip(".").lower() or not active):
            raise ProviderRejected("Provider account ownership or status mismatch.")
        result = AccountReadback(target.provider, user, domain, owner, True)
        if usage:
            if target.provider == "whm":
                result = UsageSnapshot(_number(item.get("diskused"), whm=True),
                    _number(item.get("disklimit"), limit=True, whm=True), None, None, "whm")
            else:
                measurements = _form(_get(target, "/CMD_API_SHOW_USER_USAGE", {"user":target.account}, getter))
                result = UsageSnapshot(_number(measurements.get("quota")), _number(item.get("quota"), limit=True),
                    _number(measurements.get("bandwidth")), _number(item.get("bandwidth"), limit=True), "directadmin")
        _entitled(target)
        return result
    except (ValueError, TypeError, KeyError, UnicodeError) as exc:
        raise ProviderRejected("Provider account read-back could not be verified.") from exc


def read_account(target: AccountTarget, *, getter=None) -> AccountReadback:
    return _read(target, getter, False)


def read_usage(target: AccountTarget, *, getter=None) -> UsageSnapshot:
    """Measured vendor MB; None means unknown/unlimited, never synthetic zero."""
    return _read(target, getter, True)


def execute_technical_change(*_args, **_kwargs):
    raise ProviderRejected("Hosting modification requires separately qualified provider permissions.")
