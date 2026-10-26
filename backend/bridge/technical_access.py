"""Additional OPanel login; never grants access without LIVE Console entitlement."""
import hashlib
import hmac
import json
import re
from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from .models import HostingTechnicalLogin, HostingLoginThrottle

USERNAME = re.compile(r"^op[a-z0-9]{1,18}$")
WINDOW = timedelta(minutes=15)
LOCK = timedelta(minutes=15)
LIMIT = 5
DUMMY_HASH = make_password("unusable-fixture-dummy-never-a-login-password")


class TechnicalLoginRejected(ValueError):
    pass


def enabled():
    return getattr(settings, "OPANEL_TECHNICAL_LOGIN_ENABLED", False) is True


def technical_username(service_id):
    """Deterministic unique panel name, separate from DA/WHM account user."""
    if type(service_id) is not int or not 1 <= service_id < 36 ** 18:
        raise TechnicalLoginRejected("Invalid technical service identifier.")
    digits = ""
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    while service_id:
        digits = alphabet[service_id % 36] + digits
        service_id //= 36
    return "op" + digits


def _acceptable_password(password, username):
    if not isinstance(password, str) or not 14 <= len(password) <= 128:
        return False
    if any(ord(ch) < 33 or ord(ch) > 126 for ch in password):
        return False
    if (password.lower() == username.lower() or username in password.lower()
            or password.lower() in ("passwordpassword1!", "octalve123456789!", "123456789012345!")):
        return False
    return bool(re.search(r"[A-Z]", password) and re.search(r"[a-z]", password)
                and re.search(r"[0-9]", password)
                and re.search(r"[^A-Za-z0-9]", password))


def enroll(identity, password):
    """Only an already-authenticated, currently entitled SSO session may enroll.

    The caller *must* already have invoked authorize_session() and passed the
    returned verified identity. A changed binding never silently reassigns
    credentials to a new hosting service owner.
    """
    if not enabled():
        raise TechnicalLoginRejected("Separate panel login is disabled.")
    subject = identity.get("subject_id") if isinstance(identity, dict) else None
    service = identity.get("service_id") if isinstance(identity, dict) else None
    binding = identity.get("binding_ref") if isinstance(identity, dict) else None
    if not isinstance(subject, int) or type(service) is not int or subject < 1:
        raise TechnicalLoginRejected("Invalid authorized hosting session.")
    try:
        binding = UUID(str(binding))
    except (ValueError, TypeError, AttributeError):
        raise TechnicalLoginRejected("Missing verified hosting binding.") from None
    username = technical_username(service)
    if not _acceptable_password(password, username):
        raise TechnicalLoginRejected("Choose a stronger password (14+ characters, upper/lowercase, digit and symbol).")
    hashed = make_password(password)
    with transaction.atomic():
        record = HostingTechnicalLogin.objects.select_for_update().filter(service_id=service).first()
        if record is not None:
            if record.subject_id != subject or record.binding_ref != binding or record.username != username:
                raise TechnicalLoginRejected("Hosting binding changed; credential recovery requires support.")
            record.password_hash = hashed
            record.enabled = True
            record.failed_attempts = 0
            record.locked_until = None
            record.save(update_fields=["password_hash", "enabled", "failed_attempts",
                                       "locked_until", "changed_at"])
        else:
            record = HostingTechnicalLogin.objects.create(
                service_id=service, subject_id=subject, binding_ref=binding,
                username=username, password_hash=hashed, enabled=True,
            )
    return username


def _fingerprint(label, value):
    return hmac.new(str(settings.SECRET_KEY).encode("utf-8"),
                    f"{label}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()


def _gate(kind, value, *, failure, now):
    """One persistent, HMAC-keyed throttle for normalized identity or client IP."""
    key = _fingerprint(kind, value)
    with transaction.atomic():
        row, _ = HostingLoginThrottle.objects.select_for_update().get_or_create(
            fingerprint=key, defaults={"window_started": now})
        if row.locked_until and row.locked_until > now:
            return False
        if now - row.window_started >= WINDOW:
            row.window_started = now
            row.failure_count = 0
            row.locked_until = None
        if failure:
            row.failure_count += 1
            if row.failure_count >= LIMIT:
                row.locked_until = now + LOCK
            row.save(update_fields=["window_started", "failure_count", "locked_until"])
        return True


def authenticate(username, password, client_ip, *, console_post):
    """Return scoped proof only after hash check AND independent Console read-back.

    Generic error on wrong or unknown username. No separate password authority
    may override current Console suspension, ownership, account proof or expiry.
    """
    if not enabled():
        raise TechnicalLoginRejected("Separate panel login is disabled.")
    if (not isinstance(username, str) or not USERNAME.fullmatch(username)
            or not isinstance(password, str) or len(password) > 128
            or not isinstance(client_ip, str) or not 1 <= len(client_ip) <= 64):
        raise TechnicalLoginRejected("Hosting credentials are invalid.")
    now = timezone.now()
    if not _gate("ip", client_ip, failure=False, now=now) or not _gate("user", username, failure=False, now=now):
        raise TechnicalLoginRejected("Hosting login is temporarily unavailable.")
    record = HostingTechnicalLogin.objects.filter(username=username, enabled=True).first()
    safe_hash = record.password_hash if record else DUMMY_HASH
    valid = check_password(password, safe_hash)
    if not record or not valid or (record.locked_until and record.locked_until > now):
        _gate("ip", client_ip, failure=True, now=now)
        _gate("user", username, failure=True, now=now)
        raise TechnicalLoginRejected("Hosting credentials are invalid.")
    # This independently verified entitlement is the authorization authority.
    # There is no fallback to stale session, signed browser field or cached grant.
    try:
        grant = console_post("entitlement/", {
            "subject_id": record.subject_id, "service_id": record.service_id})
        from .views import valid_binding
        if not valid_binding(grant, record.subject_id, record.service_id, str(record.binding_ref)):
            raise TechnicalLoginRejected("Hosting access is unavailable.")
    except TechnicalLoginRejected:
        raise
    except Exception as exc:
        raise TechnicalLoginRejected("Hosting authorization is currently unavailable.") from exc
    _gate("user", username, failure=False, now=now)
    return {"subject_id": record.subject_id, "service_id": record.service_id,
            "binding_ref": str(record.binding_ref)}
