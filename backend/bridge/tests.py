"""Independent OPanel security regression: browser state, session scope and revocation."""
import time
from unittest.mock import patch
from django.test import Client, TestCase, override_settings

WEB = "https://console.example.test"
API = "https://api.example.test/api"
CALLBACK = "https://panel.example.test/auth/callback/"
SECRET = "fixture-console-client-secret-0123456789abcdef"


@override_settings(
    CONSOLE_WEB_ORIGIN=WEB, CONSOLE_API_BASE=API, OPANEL_CALLBACK_URL=CALLBACK,
    OPANEL_CLIENT_ID="octalve-opanel", OPANEL_CLIENT_SECRET=SECRET,
)
class PanelSessionTests(TestCase):
    def setUp(self):
        self.client = Client()

    def initial_state(self, service_id=13):
        result = self.client.get("/auth/start/", {"service_id": service_id})
        self.assertEqual(result.status_code, 302)
        self.assertTrue(result["Location"].startswith(WEB + "/client/services/"))
        pending = self.client.session["pending"]
        self.assertEqual(pending["service_id"], service_id)
        self.assertNotIn("verifier", result["Location"])
        return pending

    def fake_console(self, endpoint, payload):
        if endpoint == "exchange/":
            self.assertEqual(payload["redirect_uri"], CALLBACK)
            self.assertIn("code_verifier", payload)
        elif endpoint == "entitlement/":
            self.assertEqual(payload, {"subject_id": 41, "service_id": 13})
        else:
            self.fail("OPanel called an unapproved Console endpoint")
        return {
            "subject_id": 41, "service_id": 13,
            "binding_ref": "e60d4718-34b4-4e46-b171-04515159a7b1",
            "capabilities": ["overview"],
        }

    def login(self):
        pending = self.initial_state()
        old_key = self.client.session.session_key
        with patch("bridge.views.console_post", side_effect=self.fake_console):
            result = self.client.get("/auth/callback/", {
                "code": "c" * 64, "state": pending["state"],
            })
        self.assertEqual(result.status_code, 302)
        self.assertEqual(result["Location"], "/")
        self.assertIn("no-store", result["Cache-Control"])
        self.assertEqual(result["Referrer-Policy"], "no-referrer")
        self.assertNotEqual(old_key, self.client.session.session_key)
        self.assertNotIn("pending", self.client.session)
        self.assertEqual(self.client.session["opanel_identity"]["subject_id"], 41)

    def test_launch_and_one_independent_session_without_passwords(self):
        self.login()
        with patch("bridge.views.console_post", side_effect=self.fake_console) as console:
            status = self.client.get("/api/session/")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["service_id"], 13)
        self.assertEqual(status.json()["capabilities"], ["overview"])
        self.assertNotIn("provider_identifier", status.content.decode())
        self.assertEqual(console.call_count, 1)

    def test_console_outage_blocks_session_view(self):
        self.login()
        from bridge.client import ConsoleUnavailable
        with patch("bridge.views.console_post", side_effect=ConsoleUnavailable()):
            status = self.client.get("/api/session/")
        self.assertEqual(status.status_code, 503)
        self.assertFalse(status.json()["authenticated"])

    def test_suspended_or_revoked_binding_blocks_existing_session(self):
        self.login()
        with patch("bridge.views.console_post", return_value={
            "subject_id": 41, "service_id": 13,
            "binding_ref": "a0000000-0000-4000-8000-000000000001",
            "capabilities": ["overview"],
        }):
            status = self.client.get("/api/session/")
        self.assertEqual(status.status_code, 403)
        self.assertNotIn("opanel_identity", self.client.session)

    def test_forged_subject_and_cross_service_response_fails(self):
        self.login()
        for field, value in (("subject_id", 42), ("service_id", 99)):
            with self.subTest(field=field):
                pending = self.initial_state()
                fake = self.fake_console("entitlement/", {"subject_id": 41, "service_id": 13})
                fake[field] = value
                good = self.fake_console("entitlement/", {"subject_id": 41, "service_id": 13})
                def simulated_console(endpoint, payload):
                    return fake if endpoint == "exchange/" else good
                with patch("bridge.views.console_post", side_effect=simulated_console):
                    result = self.client.get("/auth/callback/", {
                        "code": "c" * 64, "state": pending["state"],
                    })
                self.assertEqual(result.status_code, 403)

    def test_mismatched_state_stops_exchange_before_network(self):
        pending = self.initial_state()
        with patch("bridge.views.console_post") as outgoing:
            result = self.client.get("/auth/callback/", {
                "code": "c" * 64, "state": "x" * 43,
            })
        self.assertEqual(result.status_code, 403)
        outgoing.assert_not_called()
        self.assertNotIn("pending", self.client.session)
        self.assertTrue(pending["state"])

    def test_expired_login_state_denied(self):
        self.initial_state()
        session = self.client.session
        state = session["pending"]["state"]
        session["pending"] = {**session["pending"], "created_at": time.time() - 400}
        session.save()
        with patch("bridge.views.console_post") as outgoing:
            result = self.client.get("/auth/callback/", {
                "code": "c" * 64, "state": state,
            })
        self.assertEqual(result.status_code, 403)
        outgoing.assert_not_called()

    def test_expired_idle_and_absolute_session_fail(self):
        self.login()
        for field, value in (("last_activity", time.time() - 901), ("issued_at", time.time() - 7201)):
            with self.subTest(field=field):
                self.login()
                session = self.client.session
                current = session["opanel_identity"]
                current[field] = value
                session["opanel_identity"] = current
                session.save()
                with patch("bridge.views.console_post") as outgoing:
                    result = self.client.get("/api/session/")
                self.assertEqual(result.status_code, 401)
                outgoing.assert_not_called()

    def test_logout_requires_post_and_csrf(self):
        self.login()
        self.assertEqual(self.client.get("/auth/logout/").status_code, 405)
        self.assertIn("opanel_identity", self.client.session)
        self.assertEqual(self.client.post("/auth/logout/").status_code, 302)
        self.assertNotIn("opanel_identity", self.client.session)
        csrf_client = Client(enforce_csrf_checks=True)
        self.assertEqual(csrf_client.post("/auth/logout/").status_code, 403)

    def test_start_rejects_invalid_service_and_disabled_integration(self):
        self.assertEqual(self.client.get("/auth/start/?service_id=abc").status_code, 400)
        with override_settings(OPANEL_CLIENT_SECRET=""):
            self.assertEqual(self.client.get("/auth/start/?service_id=13").status_code, 503)

    def test_get_session_never_uses_console_credentials_in_cookie(self):
        self.login()
        cookie_names = list(self.client.cookies)
        self.assertTrue(all("octalve_console" not in k for k in cookie_names))
        self.assertTrue(all("password" not in str(v).lower() for v in self.client.cookies.values()))
