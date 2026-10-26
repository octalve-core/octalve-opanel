"""Static website ZIP inspection before an authorized hosting-account publish.

No extraction, filesystem writes, provider API calls, arbitrary executable
sources, shell or remote URLs. This is the account-independent FIRST half of
the future static uploader. A successful inspection is NOT a deployment.
"""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
import re
import stat
import zipfile

MAX_ARCHIVE = 8 * 1024 * 1024
MAX_UNPACKED = 32 * 1024 * 1024
MAX_FILE = 8 * 1024 * 1024
MAX_FILES = 250
MAX_DEPTH = 12
ALLOWED_EXT = frozenset({
    ".html", ".htm", ".css", ".js", ".mjs", ".json",
    ".txt", ".xml", ".svg", ".png", ".jpg", ".jpeg", ".gif",
    ".webp", ".ico", ".woff", ".woff2", ".webmanifest",
})
COMPONENT = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,100}$")
FORBIDDEN_NAMES = frozenset({
    ".htaccess", ".htpasswd", ".user.ini", "web.config",
    "package.json", "composer.json", "php.ini", "node_modules",
    "cgi-bin", "__macosx", "con", "aux", "prn", "nul",
})


class UploadRefused(ValueError):
    pass


@dataclass(frozen=True)
class UploadInspection:
    sha256_digest: str
    files: tuple[tuple[str, int, str], ...]
    total_unpacked_bytes: int
    has_root_index: bool
    publish_enabled: bool = False


def _safe_name(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 720:
        raise UploadRefused("Unsafe static file path.")
    if "\\" in value or value.startswith("/") or "\x00" in value or ":" in value:
        raise UploadRefused("Unsafe static file path.")
    parts = value.split("/")
    if len(parts) > MAX_DEPTH or any(
        not COMPONENT.fullmatch(p) or p in (".", "..") or p.startswith(".")
        or p.lower().split(".")[0] in FORBIDDEN_NAMES
        or p.endswith((".", " "))
        for p in parts
    ):
        raise UploadRefused("Unsafe static file path.")
    # Windows and Unix hostnames must not be rewritten under another account.
    if any(p.lower() in FORBIDDEN_NAMES for p in parts):
        raise UploadRefused("Forbidden website asset.")
    filename = PurePosixPath(value)
    if filename.suffix.lower() not in ALLOWED_EXT:
        raise UploadRefused("Unsupported static website asset type.")
    return value


def inspect_static_zip(payload):
    """Bounded ZIP validation; returns metadata, NEVER writes a hosting file."""
    if not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_ARCHIVE:
        raise UploadRefused("Archive must be a nonempty ZIP under 8 MB.")
    try:
        archive = zipfile.ZipFile(BytesIO(payload), "r", allowZip64=False)
    except (OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile):
        raise UploadRefused("Invalid ZIP archive.") from None
    files, seen, total = [], set(), 0
    try:
        with archive:
            for item in archive.infolist():
                if item.is_dir():
                    continue
                if item.flag_bits & 0x1 or item.compress_type not in (
                    zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise UploadRefused("Encrypted or unsupported ZIP entry.")
                mode = item.external_attr >> 16
                if mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                    raise UploadRefused("Links and device files are forbidden.")
                name = _safe_name(item.filename)
                lowered = name.casefold()
                if lowered in seen:
                    raise UploadRefused("Duplicate or case-colliding website asset.")
                seen.add(lowered)
                if item.file_size > MAX_FILE or item.file_size < 0:
                    raise UploadRefused("One static asset exceeds the limit.")
                if item.file_size and item.file_size > max(1, item.compress_size) * 100:
                    raise UploadRefused("Unsafe archive decompression ratio.")
                total += item.file_size
                if total > MAX_UNPACKED or len(seen) > MAX_FILES:
                    raise UploadRefused("Archive exceeds website asset limits.")
                digest = sha256()
                consumed = 0
                with archive.open(item) as src:
                    while True:
                        chunk = src.read(65536)
                        if not chunk:
                            break
                        consumed += len(chunk)
                        if consumed > item.file_size or consumed > MAX_FILE:
                            raise UploadRefused("Unbounded archive entry.")
                        digest.update(chunk)
                if consumed != item.file_size:
                    raise UploadRefused("Website asset size mismatch.")
                files.append((name, item.file_size, digest.hexdigest()))
    except (ValueError, OSError, RuntimeError, EOFError, zipfile.BadZipFile) as exc:
        if isinstance(exc, UploadRefused):
            raise
        raise UploadRefused("Corrupt or unsupported ZIP file.") from None
    if not files or "index.html" not in {name for name,_,_ in files}:
        raise UploadRefused("Static website archive must have index.html at its root.")
    files.sort()
    return UploadInspection(
        sha256_digest=sha256(payload).hexdigest(), files=tuple(files),
        total_unpacked_bytes=total, has_root_index=True,
    )


def publish_static_site(*_args, **_kwargs):
    """No account filesystem write until scoped worker and rollback qualify."""
    raise UploadRefused("Website publication requires an authorized hosting worker.")
