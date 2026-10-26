"""Independent OPanel session service. No Console account/password database."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
import environ

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv("DEBUG", "").lower() in ("1", "true")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is required.")
    SECRET_KEY = "TEST-ONLY-local-opanel-key-never-deploy-01234567890123456789"
ALLOWED_HOSTS = [x.strip() for x in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if x.strip()]
if not DEBUG and not os.getenv("DATABASE_URL"):
    raise ImproperlyConfigured("Persistent DATABASE_URL is required for OPanel.")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "bridge",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "opanel_project.urls"
WSGI_APPLICATION = "opanel_project.wsgi.application"
DATABASES = {
    "default": environ.Env().db("DATABASE_URL") if os.getenv("DATABASE_URL") else {
        "ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "test-local.sqlite3",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
APPEND_SLASH = False

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_NAME = "opanel_dev_sid" if DEBUG else "__Host-opanel_sid"
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = "/"
SESSION_COOKIE_AGE = 900
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
# Explicit first-party public origin for trusted external Next.js rewrites.
# Never take this from request headers. The reverse proxy MUST restrict who can
# supply X-Forwarded-Proto if OPANEL_TRUST_PROXY is opted into.
OPANEL_PUBLIC_ORIGIN = os.getenv("OPANEL_PUBLIC_ORIGIN", "")
if OPANEL_PUBLIC_ORIGIN:
    from urllib.parse import urlparse
    parsed_public = urlparse(OPANEL_PUBLIC_ORIGIN)
    if (parsed_public.scheme != "https" or not parsed_public.hostname
            or parsed_public.username or parsed_public.password
            or parsed_public.query or parsed_public.fragment
            or parsed_public.path not in ("", "/")):
        raise ImproperlyConfigured("OPANEL_PUBLIC_ORIGIN must be one HTTPS origin.")
CSRF_TRUSTED_ORIGINS = [OPANEL_PUBLIC_ORIGIN.rstrip("/")] if OPANEL_PUBLIC_ORIGIN else []
if os.getenv("OPANEL_TRUST_PROXY", "").lower() in ("1", "true"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 3600 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
REFERRER_POLICY = "no-referrer"

# Both origins and the callback MUST be explicit; never use the request Host
# header, user-provided redirect_uri, or Console/WHM credentials as an origin.
CONSOLE_WEB_ORIGIN = os.getenv("CONSOLE_WEB_ORIGIN", "")
CONSOLE_API_BASE = os.getenv("CONSOLE_API_BASE", "")
OPANEL_CALLBACK_URL = os.getenv("OPANEL_CALLBACK_URL", "")
OPANEL_CLIENT_ID = os.getenv("OPANEL_CLIENT_ID", "octalve-opanel")
OPANEL_CLIENT_SECRET = os.getenv("OPANEL_CLIENT_SECRET", "")

# Provider adapters are backend-only and default off until approved egress, token
# storage and an account-scoped reconciliation worker are deployed.
OPANEL_VENDOR_READBACK_ENABLED = os.getenv("OPANEL_VENDOR_READBACK_ENABLED", "").lower() in ("1", "true")

# Optional direct hosting panel login is independent of Console SSO and OFF
# until HTTPS, trusted email onboarding, MFA and abuse-prevention acceptance.
OPANEL_TECHNICAL_LOGIN_ENABLED = os.getenv("OPANEL_TECHNICAL_LOGIN_ENABLED", "").lower() in ("1", "true")

# Static ZIP upload INSPECTION only; does not write to any hosting server.
OPANEL_STATIC_UPLOAD_INSPECT_ENABLED = os.getenv("OPANEL_STATIC_UPLOAD_INSPECT_ENABLED", "").lower() in ("1", "true")

# Local practice only. The endpoint also requires DEBUG and a loopback host.
OPANEL_PRACTICE_ENABLED = os.getenv("OPANEL_PRACTICE_ENABLED", "") == "true"
OPANEL_PRACTICE_DATABASE = os.getenv("OPANEL_PRACTICE_DATABASE", "")
