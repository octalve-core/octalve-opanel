"""Server-side account-scoped filesystem inventory schema.

The customer cannot directly choose a worker, root path, provider token,
server IP or grant. Adapter and confidential Console entitlement are resolved
by trusted infrastructure, unavailable until node/vendor onboarding.
"""
from dataclasses import dataclass
import re

from .management import ManagementRejected, ServiceScope, run_operation


class FileInventoryUnavailable(ValueError):
    pass


SEGMENT = re.compile(r"^[^/\\\x00-\x1f\x7f]{1,160}$")
MAX_DIRECTORY_DEPTH = 20
MAX_ROWS = 1000


def safe_directory_path(value):
    if not isinstance(value, str) or len(value) > 1024 or value.startswith("/"):
        raise FileInventoryUnavailable("Invalid account-relative folder path.")
    if value and (len(value.split("/")) > MAX_DIRECTORY_DEPTH or any(
        not SEGMENT.fullmatch(component) or component in (".", "..")
        for component in value.split("/")
    )):
        raise FileInventoryUnavailable("Invalid account-relative folder path.")
    return value


def parse_listing(raw, *, path):
    """Reject malformed/provider-controlled filenames before browser JSON."""
    if not isinstance(raw, dict) or set(raw) != {"entries"} or not isinstance(raw["entries"], list):
        raise FileInventoryUnavailable("Provider folder response unavailable.")
    if len(raw["entries"]) > MAX_ROWS:
        raise FileInventoryUnavailable("Folder exceeds read-only inventory limit.")
    seen = set()
    entries = []
    for item in raw["entries"]:
        if not isinstance(item, dict) or set(item) != {"name", "kind", "size_bytes"}:
            raise FileInventoryUnavailable("Invalid provider file metadata.")
        name = item["name"]
        kind = item["kind"]
        size = item["size_bytes"]
        if (not isinstance(name, str) or not SEGMENT.fullmatch(name)
                or name in (".", "..") or name in seen
                or kind not in ("directory", "file", "restricted")
                or (kind == "file" and (type(size) is not int or not 0 <= size <= 10**15))
                or (kind != "file" and size is not None)):
            raise FileInventoryUnavailable("Untrusted filesystem inventory.")
        seen.add(name)
        entries.append({"name": name, "kind": kind, "size_bytes": size})
    entries.sort(key=lambda e: (e["kind"] != "directory", e["name"].casefold()))
    return {"path":path, "entries":entries, "read_only":True,
            "source":"verified_account_worker", "connected":True}


def list_account_files(*, subject_id, service_id, binding_ref,
                       path, adapter, entitlement, audit):
    path = safe_directory_path(path)
    if (type(subject_id) is not int or subject_id <= 0
            or type(service_id) is not int or service_id <= 0
            or not isinstance(binding_ref, str)):
        raise FileInventoryUnavailable("Verified hosting identity required.")
    if adapter is None or entitlement is None or audit is None:
        raise FileInventoryUnavailable("Account file provider not connected.")
    scope = ServiceScope(subject_id, service_id, binding_ref)
    try:
        raw = run_operation(scope, adapter, "files.list",
                            entitlement=entitlement, audit=audit, path=path)
        return parse_listing(raw, path=path)
    except ManagementRejected as exc:
        raise FileInventoryUnavailable("Current file inventory authority unavailable.") from exc


def resolve_live_file_provider(_identity):
    """Strictly OFF. Future resolver must bind a dedicated verified node/account.

    No generic supplier credentials, Console Django session, browser-supplied
    provider origin or native filesystem root may be accepted as substitute.
    """
    raise FileInventoryUnavailable("No authorized hosting file adapter is installed.")
