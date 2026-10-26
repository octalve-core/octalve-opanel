"""Static archive inspection HTTP boundary, intentionally never publishes."""
from django.conf import settings
from django.http import HttpResponseNotAllowed, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from . import views as core
@csrf_protect
@never_cache
def inspect_static_website(request):
    """Service-scoped static ZIP inspection; no upload storage or deployment."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not getattr(settings, "OPANEL_STATIC_UPLOAD_INSPECT_ENABLED", False):
        return core.clean(JsonResponse({"error": "Website upload inspection is not available."}, status=503))
    identity, status = core.authorize_session(request)
    if not identity:
        return core.clean(JsonResponse({"error": "Active hosting access is required."}, status=status))
    try:
        from .static_upload import inspect_static_zip, UploadRefused, MAX_ARCHIVE
        length = int(request.META.get("CONTENT_LENGTH", "-1"))
        if (request.content_type != "application/zip"
                or not 0 < length <= MAX_ARCHIVE):
            raise UploadRefused("Provide a ZIP archive under the upload limit.")
        report = inspect_static_zip(request.body)
    except (ValueError, TypeError, UploadRefused):
        return core.clean(JsonResponse({"error": "Invalid or unsafe static website ZIP."}, status=400))
    # Response is a manifest ONLY. No file/path is persisted or deployed.
    return core.clean(JsonResponse({
        "valid": True, "service_id": identity["service_id"],
        "file_count": len(report.files),
        "total_unpacked_bytes": report.total_unpacked_bytes,
        "archive_sha256": report.sha256_digest,
        "files": [{"path": n, "size_bytes": size} for n,size,_ in report.files],
        "published": False, "deployment_enabled": False,
        "message": "Archive inspected only; publishing requires an approved hosting worker.",
    }))

