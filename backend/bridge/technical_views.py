"""Separate, independently tested technical-login HTTP boundary."""
import json
import time
from django.conf import settings
from django.http import HttpResponseNotAllowed, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from . import views as core
def _limited_json(request):
    if (not request.content_type.startswith("application/json")
            or len(request.body) > 4096):
        raise ValueError("Malformed request")
    data = json.loads(request.body.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Malformed request")
    return data


@csrf_protect
@never_cache
def technical_enroll(request):
    """Only an existing valid Console SSO may establish a separate password."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    from .technical_access import enabled, enroll, TechnicalLoginRejected
    if not enabled():
        return core.clean(JsonResponse({"error": "Independent hosting login is not enabled."}, status=503))
    identity, code = core.authorize_session(request)
    if not identity:
        return core.clean(JsonResponse({"error": "Hosting authorization is required."}, status=code))
    if request.session.get("login_method", "sso") != "sso":
        return core.clean(JsonResponse({"error": "Use Console SSO to manage technical credentials."}, status=403))
    try:
        data = _limited_json(request)
        if set(data) != {"password"}:
            raise ValueError("Unexpected credential attributes")
        result = enroll({
            "subject_id": identity["subject_id"],
            "service_id": identity["service_id"],
            "binding_ref": request.session["opanel_identity"]["binding_ref"],
        }, data["password"])
    except (TechnicalLoginRejected, ValueError, KeyError, UnicodeError) as exc:
        return core.clean(JsonResponse({"error": str(exc) if isinstance(exc, TechnicalLoginRejected)
                                   else "Invalid technical password request."}, status=400))
    return core.clean(JsonResponse({"username": result, "status": "enabled"}))


@never_cache
def technical_access(request):
    """Owner only; never expose password hash, failed attempts or provider keys."""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    from .technical_access import enabled, technical_username
    from .models import HostingTechnicalLogin
    if not enabled():
        return core.clean(JsonResponse({"enabled": False}, status=503))
    identity, code = core.authorize_session(request)
    if not identity:
        return core.clean(JsonResponse({"enabled": False}, status=code))
    record = HostingTechnicalLogin.objects.filter(
        subject_id=identity["subject_id"], service_id=identity["service_id"],
        binding_ref=request.session["opanel_identity"]["binding_ref"],
        enabled=True).first()
    return core.clean(JsonResponse({
        "enabled": bool(record),
        "username": record.username if record else technical_username(identity["service_id"]),
        "enrollment_requires_console_sso": True,
    }))


@csrf_protect
@never_cache
def technical_login(request):
    """Optional direct hosting login; every success revalidates Console."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    from .technical_access import enabled, authenticate, TechnicalLoginRejected
    if not enabled():
        return core.clean(JsonResponse({"error": "Independent hosting login is not enabled."}, status=503))
    try:
        data = _limited_json(request)
        if set(data) != {"username", "password"}:
            raise ValueError("Unexpected login fields")
        identity = authenticate(
            data["username"], data["password"],
            request.META.get("REMOTE_ADDR", ""),
            console_post=core.console_post)
    except (ValueError, UnicodeError, TechnicalLoginRejected):
        return core.clean(JsonResponse({
            "error": "Credentials or current hosting authorization could not be verified."
        }, status=403))
    now = time.time()
    request.session.flush()
    request.session["opanel_identity"] = {
        **identity, "issued_at": now, "last_activity": now,
    }
    request.session["login_method"] = "technical"
    request.session.set_expiry(core.SESSION_IDLE)
    return core.clean(JsonResponse({"authenticated": True, "redirect": "/"}))

