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
    parsed = urlsplit(target.https_origin)
    host = (parsed.hostname or "").lower().rstrip(".")
    try:
        port = parsed.port
        ipaddress.ip_address(host)
    except ValueError as exc:
        if "does not appear to be" not in str(exc):
            # Invalid port or malformed URL are never accepted.
            if "Port could not" in str(exc) or "out of range" in str(exc):
                raise ProviderRejected("Invalid provider port.") from None
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


def read_account(target: AccountTarget, *, getter=None) -> AccountReadback:
    """One HTTPS GET after checking the current authenticated Console binding.

    This is a callable foundation, NOT an exposed HTTP API endpoint. The
    provider credential must be supplied by a later approved server-side
    OPanel vault/provisioning binding, never by a browser.
    """
    origin = _validate(target)
    try:
        entitlement = console_post("entitlement/", {
            "subject_id": target.subject_id, "service_id": target.service_id,
        })
    except ConsoleUnavailable as exc:
        raise ProviderRejected("Authoritative entitlement could not be verified.") from exc
    if not valid_binding(entitlement, target.subject_id, target.service_id, target.binding_ref):
        raise ProviderRejected("Hosting entitlement or binding is no longer valid.")
    if not isinstance(target.api_token, str) or not target.api_token:
        raise ProviderRejected("Server-only provider credential is unavailable.")
    if target.provider == "whm":
        url = origin + "/json-api/accountsummary"
        params = {"api.version": "1", "user": target.account}
        auth = "whm " + target.api_user + ":" + target.api_token
    else:
        url = origin + "/CMD_API_SHOW_USER_CONFIG"
        params = {"user": target.account}
        auth = "Basic " + base64.b64encode(
            (target.api_user + ":" + target.api_token).encode()).decode()
    try:
        get = getter or requests.get
        response = get(url, params=params, headers={
            "Accept": "application/json", "Authorization": auth,
        }, timeout=8, allow_redirects=False, verify=True, stream=True)
        # IMPORTANT: bounded even when Content-Length lies. Never read all
        # bytes from a malicious provider response before checking its size.
        length = response.headers.get("Content-Length", "")
        if response.status_code != 200 or (length and int(length) > 100000):
            raise ProviderRejected("Provider account query was rejected.")
        raw = response.raw.read(100001, decode_content=True)
        if len(raw) > 100000:
            raise ProviderRejected("Provider response exceeds the allowed size.")
        if target.provider == "whm":
            import json
            info = json.loads(raw.decode("utf-8"))
            rows = info.get("data", {}).get("acct") if isinstance(info, dict) else None
            if (not isinstance(info.get("metadata"), dict)
                    or str(info["metadata"].get("result")) != "1"
                    or not isinstance(rows, list) or len(rows) != 1):
                raise ProviderRejected("WHM did not verify the account.")
            account = rows[0]
            if not isinstance(account, dict):
                raise ProviderRejected("WHM account is malformed.")
            owner = account.get("owner")
            user = account.get("user")
            domain = account.get("domain")
            active = str(account.get("suspended", "")).lower() in ("0", "false")
        else:
            from urllib.parse import parse_qs
            fields = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
            if any(len(v) != 1 for v in fields.values()):
                raise ProviderRejected("DirectAdmin response is ambiguous.")
            item = {key: values[0] for key, values in fields.items()}
            if str(item.get("error", "0")) != "0":
                raise ProviderRejected("DirectAdmin did not verify the account.")
            owner = item.get("creator")
            user = item.get("username")
            domain = item.get("domain")
            active = (item.get("account") == "ON"
                      and item.get("suspended") == "no"
                      and item.get("usertype") == "user")
        if (user != target.account or owner != target.expected_owner
                or not isinstance(domain, str)
                or domain.rstrip(".").lower() != target.domain.rstrip(".").lower()
                or not active):
            raise ProviderRejected("Provider account ownership or status mismatch.")
        # Recheck entitlement after external I/O to close the suspension race.
        current = console_post("entitlement/", {
            "subject_id": target.subject_id, "service_id": target.service_id,
        })
        if not valid_binding(current, target.subject_id, target.service_id, target.binding_ref):
            raise ProviderRejected("Hosting authorization changed during read-back.")
        return AccountReadback(target.provider, user, domain, owner, True)
    except (ValueError, TypeError, UnicodeError, requests.RequestException,
            OSError, KeyError, ConsoleUnavailable) as exc:
        raise ProviderRejected("Provider account read-back could not be verified.") from exc
    finally:
        if "response" in locals():
            response.close()


def execute_technical_change(*_args, **_kwargs):
    """No write adapter or browser mutation route exists in this release."""
    raise ProviderRejected("Hosting modification requires separately qualified provider permissions.")
