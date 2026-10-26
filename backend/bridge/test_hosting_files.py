import hashlib
import os
import tempfile
from pathlib import Path
from unittest import TestCase

class HostingFilesTests(TestCase):
    def setUp(self):
        from native_agent.filesystem import AccountFiles
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'account'; self.root.mkdir()
        self.fs=AccountFiles(self.root); self.addCleanup(self.fs.close)
    def test_real_bytes_and_optimistic_edit(self):
        from native_agent.filesystem import Refused
        self.fs.mkdir('site')
        digest=self.fs.write('site/index.html',b'first')
        self.assertEqual(self.fs.read('site/index.html'),b'first')
        with self.assertRaises(Refused): self.fs.write('site/index.html',b'wrong')
        with self.assertRaises(Refused): self.fs.write('site/index.html',b'wrong',expected='0'*64)
        self.fs.write('site/index.html',b'second',expected=digest)
        self.assertEqual((self.root/'site/index.html').read_bytes(),b'second')
    def test_rename_delete_and_directory_dependencies(self):
        from native_agent.filesystem import Refused
        self.fs.mkdir('site'); digest=self.fs.write('site/a.txt',b'content')
        with self.assertRaises(Refused): self.fs.remove('site')
        self.fs.rename('site/a.txt','site/b.txt',expected=digest)
        self.assertFalse((self.root/'site/a.txt').exists())
        self.fs.remove('site/b.txt',expected=digest)
        self.fs.remove('site'); self.assertFalse((self.root/'site').exists())
    def test_paths_links_and_size_refused(self):
        from native_agent.filesystem import Refused
        for path in ('../secret','/etc/passwd','a//b','a/./b','a\\b'):
            with self.assertRaises(Refused): self.fs.write(path,b'bad')
        outside=Path(self.tmp.name)/'secret'; outside.write_bytes(b'secret')
        (self.root/'link').symlink_to(outside)
        os.link(outside,self.root/'hard')
        for path in ('link','hard'):
            with self.assertRaises(Refused): self.fs.read(path)
            with self.assertRaises(Refused): self.fs.write(path,b'bad',expected=hashlib.sha256(b'secret').hexdigest())
        with self.assertRaises(Refused): self.fs.write('big',b'x'*(self.fs.max_file_bytes+1))
        self.assertEqual(outside.read_bytes(),b'secret')
    def test_inventory_captures_empty_directories_and_actual_sizes(self):
        self.fs.mkdir('empty'); self.fs.write('a.txt',b'abc')
        rows=self.fs.inventory()
        self.assertEqual(rows,[{'path':'a.txt','kind':'file','size':3},{'path':'empty','kind':'directory','size':0}])
