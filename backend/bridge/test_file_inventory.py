"""File Manager: real-data-only inventory contract and fail-closed HTTP entry."""
import tempfile
import time
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings

from .file_inventory import (
    FileInventoryUnavailable, parse_listing, safe_directory_path,
    list_account_files, resolve_live_file_provider,
)
from .management import NativeAdapter, ServiceScope
from native_agent.worker import Worker


BINDING = "e60d4718-34b4-4e46-b171-04515159a7b1"
KEY = b"test-only-account-hmac-key-0123456789"


class FileInventoryContractTests(TestCase):
    def test_account_relative_directories_only(self):
        for valid in ("", "public_html", "public_html/assets"):
            self.assertEqual(safe_directory_path(valid),valid)
        for value in (None, 13, "/etc", "../etc", ".", "a/../b",
                      "a//b", "a\\secret", "a\x00b", "public_html/./x"):
            with self.subTest(path=value), self.assertRaises(FileInventoryUnavailable):
                safe_directory_path(value)

    def test_inventory_metadata_rejects_poisoned_and_cross_account_entries(self):
        clean = {"entries": [
            {"name":"index.html","kind":"file","size_bytes":80},
            {"name":"assets","kind":"directory","size_bytes":None},
        ]}
        parsed = parse_listing(clean,path="public_html")
        self.assertEqual([x["name"] for x in parsed["entries"]],["assets","index.html"])
        self.assertTrue(parsed["read_only"])
        for unsafe in ("../secret", ".", "/", "folder\\secret", "bad\nname"):
            with self.subTest(name=unsafe), self.assertRaises(FileInventoryUnavailable):
                parse_listing({"entries":[{"name":unsafe,"kind":"file","size_bytes":3}]},path="")
        for changes in ({"kind":"unknown"}, {"size_bytes":-1},
                        {"size_bytes":True}, {"size_bytes":"200"}):
            with self.subTest(changes=changes), self.assertRaises(FileInventoryUnavailable):
                parse_listing({"entries":[{"name":"demo.js","kind":"file","size_bytes":10,**changes}]},path="")
        with self.assertRaises(FileInventoryUnavailable):
            parse_listing({"entries":[
                {"name":"same","kind":"file","size_bytes":1},
                {"name":"same","kind":"file","size_bytes":2},
            ]},path="")

    def test_real_local_worker_inventory_through_operation_scope(self):
        with tempfile.TemporaryDirectory() as home:
            account=Path(home)/"hosting"
            account.mkdir()
            (account/"public_html").mkdir()
            (account/"public_html"/"index.html").write_text("hello")
            scope=ServiceScope(41,13,BINDING)
            worker=Worker(account,Path(home)/"replay.sqlite",KEY,node_id="node-test",
                          service_id=13,binding_ref=BINDING)
            adapter=NativeAdapter(scope,"node-test",KEY,worker.execute)
            grant={"subject_id":41,"service_id":13,"binding_ref":BINDING,
                   "capabilities":["overview"],
                   "management":{"version":1,"capabilities":["files.list"]}}
            audit=[]
            listing=list_account_files(subject_id=41,service_id=13,binding_ref=BINDING,
                path="public_html",adapter=adapter,entitlement=lambda:grant,
                audit=audit.append)
            self.assertEqual(listing["entries"],[
                {"name":"index.html","kind":"file","size_bytes":5}])
            self.assertEqual([x["outcome"] for x in audit],["started","succeeded"])
            with self.assertRaises(FileInventoryUnavailable):
                list_account_files(subject_id=99,service_id=13,binding_ref=BINDING,
                    path="public_html",adapter=adapter,entitlement=lambda:grant,
                    audit=audit.append)
            with self.assertRaises(FileInventoryUnavailable):
                list_account_files(subject_id=41,service_id=13,binding_ref=BINDING,
                    path="public_html",adapter=adapter,entitlement=lambda:{
                        **grant,"management":{"version":1,"capabilities":[]}},
                    audit=audit.append)

    def test_unconnected_live_provider_is_always_denied(self):
        with self.assertRaises(FileInventoryUnavailable):
            resolve_live_file_provider({"service_id":13})


class FileInventoryHttpTests(TestCase):
    def test_anonymous_and_wrong_methods_are_denied(self):
        browser=Client()
        self.assertEqual(browser.get("/api/files/list/").status_code,401)
        self.assertEqual(browser.post("/api/files/list/").status_code,405)

    def test_verified_session_has_no_fabricated_server_listing(self):
        browser=Client()
        session=browser.session
        now=time.time()
        session["opanel_identity"]={
            "subject_id":41,"service_id":13,"binding_ref":BINDING,
            "issued_at":now,"last_activity":now,
        }
        session.save()
        with patch("bridge.views.console_post",return_value={
            "subject_id":41,"service_id":13,"binding_ref":BINDING,
            "capabilities":["overview"]}):
            result=browser.get("/api/files/list/?path=public_html")
        self.assertEqual(result.status_code,503)
        self.assertEqual(result.json()["connected"],False)
        self.assertNotIn("entries",result.json())
        self.assertIn("no-store",result["Cache-Control"])
