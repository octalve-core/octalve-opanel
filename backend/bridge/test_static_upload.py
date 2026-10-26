"""Adversarial static website inspection; no hosting filesystem writes."""
from io import BytesIO
import stat
import time
import zipfile
from unittest.mock import patch

from django.test import Client, SimpleTestCase, TestCase, override_settings
from bridge.static_upload import inspect_static_zip, publish_static_site, UploadRefused


def zipped(entries, *, compression=zipfile.ZIP_DEFLATED):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
        for filename, body in entries:
            archive.writestr(filename, body)
    return buffer.getvalue()


class StaticZipValidationTests(SimpleTestCase):
    def test_index_html_and_assets_inspected_without_writing(self):
        blob = zipped([("index.html", b"<h1>Octalve test website</h1>"),
                       ("assets/site.css", b"body { color: #0064e0; }"),
                       ("assets/app.js", b"document.title='Test';"),
                       ("images/logo.png", b"\x89PNG\r\n")])
        info = inspect_static_zip(blob)
        self.assertEqual(len(info.files), 4)
        self.assertEqual(info.files[0][0], "assets/app.js")
        self.assertTrue(info.has_root_index)
        self.assertFalse(info.publish_enabled)
        self.assertEqual(len(info.sha256_digest), 64)
        with self.assertRaises(UploadRefused):
            publish_static_site(blob)

    def test_reject_traversal_dangerous_files_unsupported_runtime_and_missing_index(self):
        for invalid in ("../other/index.html", "/absolute/index.html",
                        "site/../../index.html", "assets\\secret.js",
                        ".htaccess", "site/index.php", "server.js.php",
                        "cgi-bin/run.js", "index.html:evil",
                        "web.config", "images/.private.png"):
            with self.subTest(invalid=invalid), self.assertRaises(UploadRefused):
                inspect_static_zip(zipped([("index.html", b"home"),
                                           (invalid, b"payload")]))
        with self.assertRaises(UploadRefused):
            inspect_static_zip(zipped([("nested/index.html", b"wrong-root")]))
        with self.assertRaises(UploadRefused):
            inspect_static_zip(zipped([("INDEX.HTML", b"not a server index")]))

    def test_duplicate_case_collision_and_zip_bomb(self):
        with self.assertRaises(UploadRefused):
            inspect_static_zip(zipped([("index.html", b"a"),("Index.html", b"b")]))
        with self.assertRaises(UploadRefused):
            inspect_static_zip(zipped([("index.html", b"a"),("assets/big.txt", b"0"*1000000)]))

    def test_symlink_and_unsupported_compression_rejected(self):
        b = BytesIO()
        item = zipfile.ZipInfo("index.html")
        item.create_system = 3
        item.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(b,"w") as archive:
            archive.writestr(item, "other-customer/secret")
        with self.assertRaises(UploadRefused):
            inspect_static_zip(b.getvalue())

    def test_limits_and_invalid_archives(self):
        for blob in (b"",b"not a zip",b"0"*(8*1024*1024+1)):
            with self.subTest(length=len(blob)), self.assertRaises(UploadRefused):
                inspect_static_zip(blob)
        entries = [("index.html", b"x")]+[(f"a{i}.txt", b"x") for i in range(250)]
        with self.assertRaises(UploadRefused):
            inspect_static_zip(zipped(entries))


@override_settings(OPANEL_STATIC_UPLOAD_INSPECT_ENABLED=True)
class StaticWebsiteInspectionHttpTests(TestCase):
    url = "/api/websites/static/inspect/"
    binding = "e60d4718-34b4-4e46-b171-04515159a7b1"

    def setUp(self):
        self.client = Client()
        now = time.time()
        session = self.client.session
        session["opanel_identity"] = {
            "subject_id": 41,"service_id": 13,"binding_ref": self.binding,
            "issued_at": now,"last_activity": now,
        }
        session.save()
        self.body = zipped([("index.html", b"<h1>Ready to preview</h1>")])

    def console(self, endpoint, request):
        self.assertEqual(endpoint, "entitlement/")
        self.assertEqual(request, {"subject_id":41,"service_id":13})
        return {"subject_id":41,"service_id":13,
                "binding_ref":self.binding,"capabilities":["overview"]}

    def test_valid_account_scoped_zip_is_only_inspected(self):
        with patch("bridge.views.console_post", side_effect=self.console):
            response = self.client.post(self.url,data=self.body,
                                        content_type="application/zip")
        self.assertEqual(response.status_code, 200,response.content)
        data = response.json()
        self.assertTrue(data["valid"])
        self.assertEqual(data["file_count"],1)
        self.assertEqual(data["service_id"],13)
        self.assertFalse(data["published"])
        self.assertFalse(data["deployment_enabled"])

    def test_expired_or_wrong_binding_never_inspects_file(self):
        with patch("bridge.views.console_post", return_value={
            "subject_id":41,"service_id":13,
            "binding_ref":"11111111-1111-4111-8111-111111111111",
            "capabilities":["overview"]}):
            result = self.client.post(self.url,self.body,content_type="application/zip")
        self.assertEqual(result.status_code, 403)
        self.assertNotIn("files",result.json())

    def test_wrong_type_and_unsafe_content_refused(self):
        with patch("bridge.views.console_post",side_effect=self.console):
            for contents,typ in ((self.body,"text/plain"),
                                 (zipped([("index.html",b"x"),("../x.js",b"y")]),"application/zip")):
                response=self.client.post(self.url,contents,content_type=typ)
                self.assertEqual(response.status_code,400)

    @override_settings(OPANEL_STATIC_UPLOAD_INSPECT_ENABLED=False)
    def test_disabled_by_default_and_no_provider_side_effects(self):
        result=self.client.post(self.url,self.body,content_type="application/zip")
        self.assertEqual(result.status_code,503)

    def test_csrf_protection_required(self):
        browser=Client(enforce_csrf_checks=True)
        now=time.time()
        sess=browser.session
        sess["opanel_identity"]={
            "subject_id":41,"service_id":13,"binding_ref":self.binding,
            "issued_at":now,"last_activity":now,
        }
        sess.save()
        result=browser.post(self.url,self.body,content_type="application/zip")
        self.assertEqual(result.status_code,403)
