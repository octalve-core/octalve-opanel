"""Native confined-worker first publication of a static ZIP.

This is an OPERATOR-ONLY filesystem routine, never mounted via HTTP.
No provider/vendor API, DNS, HTTPS, server-side runtime, or filesystem
privilege escalation is implied. OS account separation/enrollment remains a
separate deployment gate.

For now we support only the FIRST publication into an absent public_html.
Future site replacements require durable rollback/atomic release pointers.
"""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import os
import secrets
import shutil
import stat
import zipfile

from bridge.static_upload import inspect_static_zip, UploadRefused


class LocalPublishRejected(ValueError):
    pass


@dataclass(frozen=True)
class LocalPublishResult:
    service_id: int
    archive_sha256: str
    file_count: int
    status: str = "staged_on_account_filesystem"
    public_http_verified: bool = False


def publish_new_site(archive_bytes, *, account_root, service_id,
                     worker_bound_service_id, writes_enabled=False):
    """A single confined-worker write: private staging then rename.

    Caller must use a preconfigured isolated Linux account root, not a path
    supplied by a website owner in a browser payload.
    """
    if (writes_enabled is not True or type(service_id) is not int
            or service_id < 1 or type(worker_bound_service_id) is not int
            or service_id != worker_bound_service_id
            or not isinstance(account_root, (str, Path))):
        raise LocalPublishRejected("Verified account-scoped writer is unavailable.")
    root = Path(account_root)
    if root.is_symlink() or not root.is_dir():
        raise LocalPublishRejected("Approved account root is missing or unsafe.")
    report = inspect_static_zip(archive_bytes)
    root_fd = None
    staging = ".octalve-staging-" + secrets.token_hex(12)
    created = False
    try:
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        root_info = os.fstat(root_fd)
        if not stat.S_ISDIR(root_info.st_mode):
            raise LocalPublishRejected("Account root must be a directory.")
        try:
            os.stat("public_html", dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise LocalPublishRejected("Existing website requires an approved replacement plan.")
        os.mkdir(staging, mode=0o700, dir_fd=root_fd)
        created = True
        stage = root / staging
        with zipfile.ZipFile(BytesIO(archive_bytes)) as z:
            for name, size, expected_digest in report.files:
                segments = name.split("/")
                base_fd = os.open(staging, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
                try:
                    for segment in segments[:-1]:
                        try:
                            os.mkdir(segment, mode=0o700, dir_fd=base_fd)
                        except FileExistsError:
                            pass
                        next_fd = os.open(segment, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                          dir_fd=base_fd)
                        if os.fstat(next_fd).st_dev != root_info.st_dev:
                            os.close(next_fd)
                            raise LocalPublishRejected("Cross-device website write forbidden.")
                        os.close(base_fd)
                        base_fd = next_fd
                    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW
                    file_fd = os.open(segments[-1], flags, 0o600, dir_fd=base_fd)
                    try:
                        count = 0
                        with z.open(name) as source:
                            while True:
                                chunk = source.read(65536)
                                if not chunk:
                                    break
                                count += len(chunk)
                                if count > size:
                                    raise LocalPublishRejected("Static asset changed after validation.")
                                view = memoryview(chunk)
                                while view:
                                    written = os.write(file_fd, view)
                                    if written <= 0:
                                        raise LocalPublishRejected("Static asset write could not complete.")
                                    view = view[written:]
                        if count != size:
                            raise LocalPublishRejected("Static asset length mismatch.")
                        os.fsync(file_fd)
                    finally:
                        os.close(file_fd)
                finally:
                    os.close(base_fd)
        # One-site bootstrap: absent target only. No existing website replaced.
        try:
            os.stat("public_html", dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise LocalPublishRejected("Concurrent account website exists; do not overwrite.")
        os.rename(staging, "public_html", src_dir_fd=root_fd, dst_dir_fd=root_fd)
        created = False
        os.fsync(root_fd)
        return LocalPublishResult(service_id, report.sha256_digest, len(report.files))
    except (ValueError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise LocalPublishRejected("First website publication failed; no existing website was replaced.") from exc
    finally:
        if root_fd is not None:
            if created:
                # Staging dir is mode 0700 and created only for this request.
                shutil.rmtree(root / staging, ignore_errors=True)
            os.close(root_fd)
