"""Disposable filesystem proof of first static site publishing. No live site claims."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import zipfile
from django.test import SimpleTestCase
from native_agent.static_publish import publish_new_site, LocalPublishRejected


def archive(content=b"<h1>Octalve</h1>"):
    stream=BytesIO()
    with zipfile.ZipFile(stream,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("index.html",content)
        z.writestr("assets/site.css",b"body{color:#0064e0}")
    return stream.getvalue()


class StaticNativePublishingTests(SimpleTestCase):
    def test_first_site_written_only_to_bound_disposable_account(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            result=publish_new_site(archive(),account_root=root,service_id=13,
                worker_bound_service_id=13,writes_enabled=True)
            self.assertEqual(result.status,"staged_on_account_filesystem")
            self.assertFalse(result.public_http_verified)
            self.assertEqual(result.file_count,2)
            self.assertEqual((root/"public_html/index.html").read_bytes(),b"<h1>Octalve</h1>")
            self.assertEqual((root/"public_html/assets/site.css").read_bytes(),b"body{color:#0064e0}")
            self.assertFalse(list(root.glob(".octalve-staging-*")))

    def test_disabled_wrong_owner_and_existing_site_never_overwritten(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(LocalPublishRejected):
                publish_new_site(archive(),account_root=root,service_id=13,
                    worker_bound_service_id=13)
            with self.assertRaises(LocalPublishRejected):
                publish_new_site(archive(),account_root=root,service_id=13,
                    worker_bound_service_id=999,writes_enabled=True)
            result=publish_new_site(archive(),account_root=root,service_id=13,
                                    worker_bound_service_id=13,writes_enabled=True)
            self.assertEqual(result.file_count,2)
            with self.assertRaises(LocalPublishRejected):
                publish_new_site(archive(b"REPLACEMENT"),account_root=root,service_id=13,
                    worker_bound_service_id=13,writes_enabled=True)
            self.assertEqual((root/"public_html/index.html").read_bytes(),b"<h1>Octalve</h1>")

    def test_symlink_account_root_and_unsafe_archive_are_rejected(self):
        with TemporaryDirectory() as d:
            root=Path(d)/"account"
            root.mkdir()
            link=Path(d)/"alias"
            link.symlink_to(root,target_is_directory=True)
            with self.assertRaises(LocalPublishRejected):
                publish_new_site(archive(),account_root=link,service_id=13,
                    worker_bound_service_id=13,writes_enabled=True)
            bad=BytesIO()
            with zipfile.ZipFile(bad,"w") as z:
                z.writestr("index.html","ok")
                z.writestr("../outside.html","secrets")
            with self.assertRaises((LocalPublishRejected, ValueError)):
                publish_new_site(bad.getvalue(),account_root=root,service_id=13,
                    worker_bound_service_id=13,writes_enabled=True)
            self.assertFalse((root/"public_html").exists())
            self.assertFalse((Path(d)/"outside.html").exists())
