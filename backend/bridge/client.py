"""Strict, fail-closed server-side API client for trusted Console endpoints."""
import json
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from django.conf import settings


class ConsoleUnavailable(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _valid_url(url):
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        or (settings.DEBUG and parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1"))
    ) and bool(parsed.hostname) and not parsed.username and not parsed.password and not parsed.fragment and not parsed.query


def configured():
    api = settings.CONSOLE_API_BASE
    web = settings.CONSOLE_WEB_ORIGIN
    callback = settings.OPANEL_CALLBACK_URL
    return (
        all(_valid_url(x) for x in (api, web, callback))
        and api.endswith("/api")
        and urlparse(web).path in ("", "/")
        and urlparse(callback).path == "/auth/callback/"
        and len(settings.OPANEL_CLIENT_SECRET) >= 32
        and bool(settings.OPANEL_CLIENT_ID)
    )


def console_post(endpoint, payload):
    if endpoint not in ("exchange/", "entitlement/") or not configured():
        raise ConsoleUnavailable("Console SSO integration is unavailable.")
    url = settings.CONSOLE_API_BASE.rstrip("/") + "/integrations/opanel/v1/" + endpoint
    req = Request(url, method="POST",
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + settings.OPANEL_CLIENT_SECRET,
            "X-OPanel-Client-ID": settings.OPANEL_CLIENT_ID,
        },
    )
    try:
        with build_opener(NoRedirect()).open(req, timeout=5) as response:
            if response.status != 200:
                raise ConsoleUnavailable("Access not verified.")
            raw = response.read(16385)
            if len(raw) > 16384:
                raise ConsoleUnavailable("Oversized response.")
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise ConsoleUnavailable("Malformed response.")
            return data
    except (ValueError, OSError, UnicodeError, TypeError, KeyError) as exc:
        raise ConsoleUnavailable("Console entitlement check failed.") from exc
