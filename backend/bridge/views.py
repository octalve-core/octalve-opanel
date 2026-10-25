"""Console-only customer identity; OPanel keeps an independent service-scoped session."""
import base64
import hashlib
import hmac
import math
import re
import secrets
import time
import uuid
from urllib.parse import urlencode
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect
from django.middleware.csrf import get_token
from .dashboard import dashboard_html, normalize_overview
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from .client import ConsoleUnavailable, configured, console_post

OPAQUE_CODE = re.compile(r"^[A-Za-z0-9_-]{48,128}$")
BROWSER_STATE = re.compile(r"^[A-Za-z0-9_-]{22,128}$")

SESSION_IDLE = 900
SESSION_ABSOLUTE = 7200
LAUNCH_WINDOW = 300


def clean(response):
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    return response


def denied(request, status=403):
    request.session.flush()
    return clean(HttpResponse("Secure hosting access was denied. Return to Octalve Console.", status=status))


def valid_binding(data, subject_id, service_id, binding_ref=None):
    try:
        subject = int(data["subject_id"])
        service = int(data["service_id"])
        binding = str(uuid.UUID(str(data["binding_ref"])))
        capabilities = data["capabilities"]
        return (subject == subject_id and service == service_id and
                (binding_ref is None or hmac.compare_digest(binding, binding_ref)) and
                isinstance(capabilities, list) and capabilities == ["overview"])
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


@never_cache
def health(request):
    return clean(JsonResponse({"status": "ok", "service": "opanel", "integration": "not-provisioned"}))


@never_cache
def start(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    if not configured():
        return clean(HttpResponse("OPanel Console sign-in is not configured.", status=503))
    try:
        service_id = int(request.GET.get("service_id", ""))
        if service_id < 1:
            raise ValueError
    except ValueError:
        return clean(HttpResponse("Invalid hosting service.", status=400))
    # Clear old identity and create a fresh browser-bound login transaction.
    request.session.flush()
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    request.session["pending"] = {
        "state": state, "verifier": verifier,
        "service_id": service_id, "created_at": time.time(),
    }
    request.session.set_expiry(LAUNCH_WINDOW)
    url = settings.CONSOLE_WEB_ORIGIN.rstrip("/") + (
        f"/client/services/{service_id}/authorize-opanel?"
        + urlencode({"state": state, "code_challenge": challenge})
    )
    return clean(redirect(url))


@never_cache
def callback(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    pending = request.session.get("pending")
    code = request.GET.get("code")
    state = request.GET.get("state")
    if not isinstance(pending, dict) or not isinstance(code, str) or not isinstance(state, str):
        return denied(request)
    if (not OPAQUE_CODE.fullmatch(code) or not BROWSER_STATE.fullmatch(state)
            or not isinstance(pending.get("state"), str)
            or not BROWSER_STATE.fullmatch(pending["state"])
            or not hmac.compare_digest(state, pending["state"])
            or not isinstance(pending.get("created_at"), (int, float))
            or not math.isfinite(pending["created_at"])
            or time.time() - pending["created_at"] > LAUNCH_WINDOW
            or pending["created_at"] > time.time() + 10):
        return denied(request)
    try:
        grant = console_post("exchange/", {
            "code": code,
            "code_verifier": pending["verifier"],
            "redirect_uri": settings.OPANEL_CALLBACK_URL,
        })
    except (ConsoleUnavailable, KeyError, TypeError):
        return denied(request, 503)
    service_id = pending["service_id"]
    try:
        subject_id = int(grant["subject_id"])
    except (KeyError, ValueError, TypeError):
        return denied(request)
    if subject_id < 1 or not valid_binding(grant, subject_id, service_id):
        return denied(request)
    # A code-exchange response alone does not grant technical access: read the
    # authoritative *current* entitlement separately before creating a session.
    # This also prevents mismatched subject/service/binding substitutions.
    try:
        current = console_post("entitlement/", {
            "subject_id": subject_id, "service_id": service_id,
        })
    except ConsoleUnavailable:
        return denied(request, 503)
    if not valid_binding(current, subject_id, service_id, str(uuid.UUID(grant["binding_ref"]))):
        return denied(request)
    now = time.time()
    request.session.flush()  # Discards state/verifier and old session identifier.
    request.session["opanel_identity"] = {
        "subject_id": subject_id,
        "service_id": service_id,
        "binding_ref": str(uuid.UUID(grant["binding_ref"])),
        "issued_at": now,
        "last_activity": now,
    }
    request.session.set_expiry(SESSION_IDLE)
    return clean(redirect("/"))


def authorize_session(request):
    identity = request.session.get("opanel_identity")
    now = time.time()
    if not isinstance(identity, dict):
        return None, 401
    try:
        subject_id = int(identity["subject_id"])
        service_id = int(identity["service_id"])
        issued_at = float(identity["issued_at"])
        last_activity = float(identity["last_activity"])
        binding_ref = str(uuid.UUID(str(identity["binding_ref"])))
    except (KeyError, ValueError, TypeError):
        request.session.flush()
        return None, 401
    if (not math.isfinite(issued_at) or not math.isfinite(last_activity)
            or subject_id < 1 or service_id < 1
            or now - issued_at >= SESSION_ABSOLUTE or now - last_activity >= SESSION_IDLE
            or issued_at > now + 10 or last_activity > now + 10):
        request.session.flush()
        return None, 401
    try:
        response = console_post("entitlement/", {"subject_id": subject_id, "service_id": service_id})
    except ConsoleUnavailable:
        # Fail closed; session may remain stored so customer can retry if Console recovers.
        return None, 503
    if not valid_binding(response, subject_id, service_id, binding_ref):
        request.session.flush()
        return None, 403
    identity["last_activity"] = now
    request.session["opanel_identity"] = identity
    request.session.set_expiry(min(SESSION_IDLE, max(1, int(SESSION_ABSOLUTE - (now - issued_at)))))
    return {"subject_id": subject_id, "service_id": service_id,
            "overview": normalize_overview(response.get("overview"), service_id)}, 200


@never_cache
def session_status(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    identity, status = authorize_session(request)
    if not identity:
        return clean(JsonResponse({"authenticated": False}, status=status))
    # CSRF masked token is provided to the same-origin frontend only.
    # The CSRF cookie remains HttpOnly and Django validates POST logout.
    return clean(JsonResponse({
        "authenticated": True, **identity,
        "capabilities": ["overview"],
        "csrf_token": get_token(request),
    }))


@never_cache
def home(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    identity, status = authorize_session(request)
    if not identity:
        return clean(HttpResponse(
            "OPanel access is not available. Open an active hosting service in Octalve Console.",
            status=status,
        ))
    html = dashboard_html(identity, get_token(request))
    return clean(HttpResponse(html))


@csrf_protect
@never_cache
def logout(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    request.session.flush()
    return clean(redirect("/"))
