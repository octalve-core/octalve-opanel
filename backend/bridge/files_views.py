"""Read-only account directory endpoint, no network/native resolver installed."""
from django.http import HttpResponseNotAllowed, JsonResponse
from django.views.decorators.cache import never_cache

from . import views as core
from .file_inventory import (
    FileInventoryUnavailable, resolve_live_file_provider,
    list_account_files, safe_directory_path,
)


@never_cache
def list_account_directory(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    identity, status = core.authorize_session(request)
    if identity is None:
        return core.clean(JsonResponse({
            "connected": False, "error": "Active hosting entitlement is required."
        }, status=status))
    try:
        path = safe_directory_path(request.GET.get("path", ""))
        adapter, entitlement, audit = resolve_live_file_provider(identity)
        listing = list_account_files(
            subject_id=identity["subject_id"], service_id=identity["service_id"],
            binding_ref=request.session["opanel_identity"]["binding_ref"],
            path=path, adapter=adapter, entitlement=entitlement, audit=audit,
        )
    except FileInventoryUnavailable:
        # Do not leak host file paths, vendor keys or internal infrastructure.
        return core.clean(JsonResponse({
            "connected": False,
            "error": "No verified account-scoped file connection is available."
        }, status=503))
    return core.clean(JsonResponse({"service_id":identity["service_id"], **listing}))
