"""Separate hosting login never bypasses Console SSO or current service proof."""
import json
from unittest.mock import patch

from django.contrib.auth.hashers import check_password
from django.test import Client, TestCase, override_settings

from bridge.models import HostingLoginThrottle, HostingTechnicalLogin
from bridge.technical_access import technical_username
from bridge.client import ConsoleUnavailable

WEB = "https://console.example.test"
API = "https://api.example.test/api"
CALLBACK = "https://panel.example.test/auth/callback/"
SECRET = "fixture-console-client-secret-0123456789abcdef"
BINDING = "e60d4718-34b4-4e46-b171-04515159a7b1"
PASSWORD = "A_Very_Strong_2026!_Panel_Password"


@override_settings(
    DEBUG=True,
    CONSOLE_WEB_ORIGIN=WEB, CONSOLE_API_BASE=API,
    OPANEL_CALLBACK_URL=CALLBACK, OPANEL_PUBLIC_ORIGIN="https://panel.example.test",
    OPANEL_CLIENT_ID="octalve-opanel", OPANEL_CLIENT_SECRET=SECRET,
    OPANEL_TECHNICAL_LOGIN_ENABLED=True,
)
class IndependentTechnicalLoginTests(TestCase):
    def setUp(self):
        self.browser = Client()
        self.username = technical_username(13)

    def console(self, endpoint, payload):
        self.assertIn(endpoint, ("exchange/", "entitlement/"))
        return {"subject_id": 41, "service_id": 13,
                "binding_ref": BINDING, "capabilities": ["overview"]}

    def sso(self):
        response = self.browser.get("/auth/start/?service_id=13")
        self.assertEqual(response.status_code, 302)
        state = self.browser.session["pending"]["state"]
        with patch("bridge.views.console_post", side_effect=self.console):
            response = self.browser.get("/auth/callback/", {
                "code": "c" * 64, "state": state})
        self.assertEqual(response.status_code, 302)

    def enable_technical(self):
        self.sso()
        with patch("bridge.views.console_post", side_effect=self.console):
            token = self.browser.get("/api/session/").json()["csrf_token"]
            response = self.browser.post("/api/technical-access/enroll/",
                                         data=json.dumps({"password": PASSWORD}),
                                         content_type="application/json",
                                         HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["username"], self.username)
        return token

    def test_enroll_requires_console_sso_and_hashes_password(self):
        unauthorized = self.browser.post("/api/technical-access/enroll/",
                                         data=json.dumps({"password": PASSWORD}),
                                         content_type="application/json")
        self.assertEqual(unauthorized.status_code, 401)
        self.enable_technical()
        obj = HostingTechnicalLogin.objects.get(service_id=13)
        self.assertEqual(obj.subject_id, 41)
        self.assertEqual(str(obj.binding_ref), BINDING)
        self.assertTrue(check_password(PASSWORD, obj.password_hash))
        self.assertNotIn(PASSWORD, obj.password_hash)
        self.assertEqual(HostingTechnicalLogin.objects.count(), 1)

    def test_second_technical_login_works_with_fresh_console_entitlement(self):
        self.enable_technical()
        self.browser = Client()
        csrf = self.browser.get("/api/csrf/").json()["csrf_token"]
        with patch("bridge.views.console_post", side_effect=self.console) as mocked:
            logged = self.browser.post("/auth/technical-login/",
                                       data=json.dumps({
                                           "username": self.username, "password": PASSWORD,
                                       }), content_type="application/json",
                                       HTTP_X_CSRFTOKEN=csrf)
            self.assertEqual(logged.status_code, 200, logged.content)
            self.assertEqual(self.browser.session["login_method"], "technical")
            session = self.browser.get("/api/session/")
        self.assertTrue(session.json()["authenticated"])
        self.assertEqual(session.json()["service_id"], 13)
        self.assertEqual(mocked.call_count, 2)
        with patch("bridge.views.console_post", return_value={
            **self.console("entitlement/", {}), "binding_ref":
            "00000000-0000-4000-8000-000000000001",
        }):
            denied = self.browser.get("/api/session/")
        self.assertEqual(denied.status_code, 403)

    def test_wrong_password_and_cross_binding_cannot_reuse_account(self):
        self.enable_technical()
        other = Client()
        first = other.post("/auth/technical-login/",
                           data=json.dumps({
                               "username": self.username, "password": "Invalid_2026!_Password",
                           }), content_type="application/json")
        self.assertEqual(first.status_code, 403)
        self.assertNotIn("opanel_identity", other.session)
        with patch("bridge.views.console_post", return_value={
            **self.console("entitlement/", {}),
            "subject_id": 999,
        }):
            denied = other.post("/auth/technical-login/",
                                data=json.dumps({
                                    "username": self.username, "password": PASSWORD,
                                }), content_type="application/json")
        self.assertEqual(denied.status_code, 403)
        self.assertNotIn("opanel_identity", other.session)

    def test_console_outage_prevents_password_login(self):
        self.enable_technical()
        other = Client()
        with patch("bridge.views.console_post", side_effect=ConsoleUnavailable()):
            response = other.post("/auth/technical-login/",
                                  data=json.dumps({
                                      "username": self.username, "password": PASSWORD,
                                  }), content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("opanel_identity", other.session)

    def test_technical_password_cannot_reenroll_other_password(self):
        self.enable_technical()
        other = Client()
        with patch("bridge.views.console_post", side_effect=self.console):
            result = other.post("/auth/technical-login/",
                                data=json.dumps({
                                    "username": self.username, "password": PASSWORD,
                                }), content_type="application/json")
            self.assertEqual(result.status_code, 200)
            again = other.post("/api/technical-access/enroll/",
                               data=json.dumps({"password": "New_Different_2026!_Password"}),
                               content_type="application/json")
        self.assertEqual(again.status_code, 403)
        self.assertTrue(check_password(
            PASSWORD, HostingTechnicalLogin.objects.get(service_id=13).password_hash))

    def test_repeated_bad_password_locks_attempts_durably(self):
        self.enable_technical()
        other = Client()
        for i in range(6):
            reply = other.post("/auth/technical-login/",
                               data=json.dumps({
                                   "username": self.username, "password": "bad-password",
                               }), content_type="application/json")
            self.assertEqual(reply.status_code, 403)
        self.assertTrue(HostingLoginThrottle.objects.filter(
            locked_until__isnull=False).exists())
        with patch("bridge.views.console_post", side_effect=self.console) as verify:
            reply = other.post("/auth/technical-login/",
                               data=json.dumps({
                                   "username": self.username, "password": PASSWORD,
                               }), content_type="application/json")
        self.assertEqual(reply.status_code, 403)
        verify.assert_not_called()

    @override_settings(OPANEL_TECHNICAL_LOGIN_ENABLED=False)
    def test_login_is_off_by_default(self):
        self.assertEqual(self.browser.post("/auth/technical-login/",
                           data=json.dumps({"username": self.username, "password": PASSWORD}),
                           content_type="application/json").status_code, 503)
        self.assertEqual(self.browser.post("/api/technical-access/enroll/",
                           data=json.dumps({"password": PASSWORD}),
                           content_type="application/json").status_code, 503)

    def test_csrf_required_for_direct_login_and_enrollment(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/auth/technical-login/",
                                    data=json.dumps({"username": self.username, "password": PASSWORD}),
                                    content_type="application/json").status_code, 403)
        client.get("/api/csrf/")
        with patch("bridge.views.console_post", side_effect=self.console):
            init = client.get("/auth/start/?service_id=13")
            self.assertEqual(init.status_code, 302)
            state = client.session["pending"]["state"]
            client.get("/auth/callback/", {"code": "c"*64, "state": state})
        self.assertEqual(client.post("/api/technical-access/enroll/",
                                    data=json.dumps({"password": PASSWORD}),
                                    content_type="application/json").status_code, 403)
