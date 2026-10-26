"""Read-only hosting integration contracts; no customer-visible provider actions."""
from django.test import SimpleTestCase
from bridge.integrations import resolve_integrations, REGISTRY, IntegrationRejected


class IntegrationRegistryTests(SimpleTestCase):
    def test_overview_grant_enables_no_integrations_even_with_runtimes(self):
        data = resolve_integrations(
            {"capabilities": ["overview"]},
            runtimes=("static", "php", "mysql"),
            zone_owned=True, installer_verified=True, repository_approved=True)
        self.assertEqual({x["slug"] for x in data}, {"wordpress", "cloudflare", "github"})
        self.assertTrue(all(not x["enabled"] and not x["authorized"] for x in data))
        self.assertTrue(all(x["status"] == "not_connected" for x in data))

    def test_package_runtime_gating_and_separate_integration_authorities(self):
        all_caps = sorted(set().union(*(item.required_capabilities for item in REGISTRY)))
        bare = resolve_integrations(
            {"capabilities": all_caps}, runtimes=("static",), zone_owned=True,
            installer_verified=True, repository_approved=True)
        self.assertFalse(next(x for x in bare if x["slug"] == "wordpress")["authorized"])
        full = resolve_integrations(
            {"capabilities": all_caps}, runtimes=("static", "php", "mysql"),
            zone_owned=True, installer_verified=True, repository_approved=True)
        self.assertTrue(all(x["authorized"] for x in full))
        self.assertTrue(all(not x["enabled"] for x in full))

    def test_missing_zone_or_repo_permission_must_not_be_inferred(self):
        all_caps = sorted(set().union(*(item.required_capabilities for item in REGISTRY)))
        result = resolve_integrations({"capabilities": all_caps},
                                      runtimes=("static", "php", "mysql"),
                                      zone_owned=False,
                                      installer_verified=False,
                                      repository_approved=False)
        self.assertTrue(all(not x["authorized"] for x in result))

    def test_invalid_auth_fails_closed(self):
        for x in (None, [], {}, {"capabilities": "*"}, {"capabilities": [True]}):
            with self.subTest(value=x), self.assertRaises(IntegrationRejected):
                resolve_integrations(x)
