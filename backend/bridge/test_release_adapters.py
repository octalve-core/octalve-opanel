"""No internet writes: contract-level Batch 3/4 regression."""
from io import BytesIO
import zipfile
from django.test import SimpleTestCase
from bridge.dns_contracts import (
    preview_dns_change, execute_dns_change, DNSPlanRejected)
from bridge.github_static import (
    prepare_github_static, execute_github_deploy, GitHubDeployRejected)
from bridge.wordpress_plan import (
    plan_wordpress, execute_wordpress_install, WordPressNotSupported)
from bridge.static_upload import inspect_static_zip


class ReleaseAdaptersTests(SimpleTestCase):
    def test_cloudflare_public_record_only_for_verified_owner_zone(self):
        cfg=dict(service_id=13,zone_id="a"*32,zone_name="example.com",
            owner_verified=True,current_entitlement={
                "service_id":13,"capabilities":["dns.zone.write"]},
            record_name="www.example.com",record_type="A",
            value="1.1.1.1",ttl=300)
        plan=preview_dns_change(**cfg)
        self.assertFalse(plan.approved_for_execution)
        self.assertEqual(plan.zone_name,"example.com")
        with self.assertRaises(DNSPlanRejected):
            execute_dns_change(plan)

    def test_dns_preflight_blocks_foreign_tenant_internal_ips_and_unowned_zone(self):
        base=dict(service_id=13,zone_id="a"*32,zone_name="example.com",
            owner_verified=True,current_entitlement={
                "service_id":13,"capabilities":["dns.zone.write"]},
            record_name="example.com",record_type="A",value="1.1.1.1",ttl=300)
        variants=({"record_name":"evil.com"},
                  {"owner_verified":False},
                  {"current_entitlement":{"service_id":999,"capabilities":["dns.zone.write"]}},
                  {"current_entitlement":{"service_id":13,"capabilities":["overview"]}},
                  {"value":"127.0.0.1"},
                  {"value":"169.254.169.254"},
                  {"value":"10.0.0.5"},
                  {"record_type":"AAAA","value":"::1"},
                  {"record_type":"MX"},
                  {"ttl":20},
                  {"zone_id":"not-a-validated-zone"})
        for v in variants:
            with self.subTest(v=v), self.assertRaises(DNSPlanRejected):
                preview_dns_change(**{**base,**v})

    def test_github_only_selected_repo_pinned_commit_static_artifact(self):
        stream=BytesIO()
        with zipfile.ZipFile(stream,"w",compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("index.html","<h1>Demo</h1>")
        report=inspect_static_zip(stream.getvalue())
        input=dict(service_id=13,installation_id=42,repository="octalve-core/sample-static",
            commit_sha="a"*40,installed_repositories=("octalve-core/sample-static",),
            inspected_artifact=report,trusted_installation=True,runtimes=("static",))
        spec=prepare_github_static(**input)
        self.assertFalse(spec.deploy_enabled)
        self.assertEqual(spec.file_count,1)
        with self.assertRaises(GitHubDeployRejected):
            execute_github_deploy(spec)
        for over in ({"trusted_installation":False},
                     {"repository":"other/private"},
                     {"commit_sha":"main"},
                     {"runtimes":("node",)},
                     {"service_id":0}):
            with self.subTest(over=over), self.assertRaises(GitHubDeployRejected):
                prepare_github_static(**{**input,**over})

    def test_wordpress_not_on_static_plan_or_unverified_hosting(self):
        cfg=dict(service_id=13,domain="example.com",
            verified_hosting_account=True,
            verified_runtimes=("php","mysql"),
            installer_name="softaculous",
            supported_php_version="8.3.1",
            database_engine="mariadb",
            granted_capabilities=("wordpress.install","database.create"))
        plan=plan_wordpress(**cfg)
        self.assertTrue(plan.runtime_eligible)
        self.assertFalse(plan.installation_enabled)
        with self.assertRaises(WordPressNotSupported):
            execute_wordpress_install(plan)
        for over in ({"verified_hosting_account":False},
                     {"verified_runtimes":("static",)},
                     {"installer_name":"assume-installed"},
                     {"granted_capabilities":("overview",)},
                     {"supported_php_version":"7.4"},
                     {"domain":"wrong domain"}):
            with self.subTest(over=over), self.assertRaises(WordPressNotSupported):
                plan_wordpress(**{**cfg,**over})
