"""Account-scoped vendor readback: zero real network, negative tenant probes."""
import io
import json
import os
from unittest.mock import Mock, patch
from django.test import TestCase, override_settings
from .providers import AccountTarget, ProviderRejected, read_account, execute_technical_change

BINDING = "e60d4718-34b4-4e46-b171-04515159a7b1"


def fake_response(data, status=200):
    result = Mock(status_code=status, headers={})
    result.raw = io.BytesIO(data.encode("utf-8"))
    return result


def entitlement(_endpoint, _payload):
    return {"subject_id": 41, "service_id": 13, "binding_ref": BINDING, "capabilities": ["overview"]}


@override_settings(OPANEL_VENDOR_READBACK_ENABLED=True)
class ProviderSafetyTests(TestCase):
    def setUp(self):
        self.whm = AccountTarget(
            provider="whm", https_origin="https://whm.demo-host.test:2087",
            api_user="resellerops", api_token="fake-secret-never-print",
            expected_owner="resellerops", account="checkhost",
            domain="verified.example.test", subject_id=41, service_id=13,
            binding_ref=BINDING,
        )
        self.da = AccountTarget(
            provider="directadmin", https_origin="https://da.demo-host.test:2222",
            api_user="resellerops", api_token="fake-secret-never-print",
            expected_owner="resellerops", account="checkhost",
            domain="verified.example.test", subject_id=41, service_id=13,
            binding_ref=BINDING,
        )
        self.patcher = patch.dict(os.environ, {"OPANEL_PROVIDER_ALLOWED_HOSTS": "whm.demo-host.test,da.demo-host.test"})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    @patch("bridge.providers.console_post", side_effect=entitlement)
    def test_whm_readback_exact_account_and_two_entitlement_checks(self, console):
        data = {"metadata": {"result": 1}, "data": {"acct": [
            {"owner": "resellerops", "user": "checkhost", "domain": "verified.example.test", "suspended": 0}
        ]}}
        getter = Mock(return_value=fake_response(json.dumps(data)))
        result = read_account(self.whm, getter=getter)
        self.assertTrue(result.active)
        self.assertEqual(console.call_count, 2)
        url, kw = getter.call_args
        self.assertEqual(url[0], "https://whm.demo-host.test:2087/json-api/accountsummary")
        self.assertTrue(kw["verify"])
        self.assertFalse(kw["allow_redirects"])
        self.assertTrue(kw["stream"])
        self.assertNotIn("fake-secret-never-print", repr(result))
        self.assertNotIn("fake-secret-never-print", repr(self.whm))

    @patch("bridge.providers.console_post", side_effect=entitlement)
    def test_directadmin_server_only_get(self, _console):
        data = "error=0&username=checkhost&creator=resellerops&domain=verified.example.test&usertype=user&account=ON&suspended=no"
        get = Mock(return_value=fake_response(data))
        result = read_account(self.da, getter=get)
        self.assertEqual(result.owner, "resellerops")
        self.assertEqual(get.call_args.args[0], "https://da.demo-host.test:2222/CMD_API_SHOW_USER_CONFIG")

    @patch("bridge.providers.console_post", side_effect=entitlement)
    def test_wrong_owner_or_suspended_never_verifies(self, _console):
        for owner, suspended in (("another-owner", 0), ("resellerops", 1)):
            with self.subTest(owner=owner, suspended=suspended):
                info = {"metadata": {"result": 1}, "data": {"acct": [
                    {"owner": owner, "user": "checkhost", "domain": "verified.example.test", "suspended": suspended}
                ]}}
                with self.assertRaises(ProviderRejected):
                    read_account(self.whm, getter=Mock(return_value=fake_response(json.dumps(info))))

    @patch("bridge.providers.console_post", return_value={
        "subject_id": 99, "service_id": 13, "binding_ref": BINDING, "capabilities": ["overview"]})
    def test_cross_customer_denied_before_provider_request(self, _console):
        getter = Mock()
        with self.assertRaises(ProviderRejected):
            read_account(self.whm, getter=getter)
        getter.assert_not_called()

    @patch("bridge.providers.console_post", side_effect=entitlement)
    def test_disallowed_api_host_denied_before_entitlement(self, console):
        target = AccountTarget(**{**self.whm.__dict__, "https_origin": "https://internal.example:2087"})
        with self.assertRaises(ProviderRejected):
            read_account(target, getter=Mock())
        console.assert_not_called()

    def test_all_technical_changes_are_disabled(self):
        for operation in ("createacct", "suspend", "delete", "dns", "file_write", "mysql", "mailbox"):
            with self.subTest(operation=operation):
                with self.assertRaises(ProviderRejected):
                    execute_technical_change(operation, self.whm)

    @override_settings(OPANEL_VENDOR_READBACK_ENABLED=False)
    def test_disabled_feature_fails_before_network(self):
        with patch("bridge.providers.console_post") as console:
            with self.assertRaises(ProviderRejected):
                read_account(self.whm, getter=Mock())
        console.assert_not_called()
