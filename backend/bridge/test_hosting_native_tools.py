"""Native config acceptance on disposable CI resources; never touches /etc."""
import os
import pwd
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase
from native_agent.dns import compile_zone
from native_agent.web import compile_site

class NativeConfigToolsTests(TestCase):
    def tool(self,name):
        executable=shutil.which(name)
        if not executable:
            if os.getenv('OPANEL_REQUIRE_NATIVE_TOOLS')=='true': self.fail('Required native validation tool missing: '+name)
            self.skipTest('Native tool unavailable locally: '+name)
        return executable
    def test_bind_accepts_compiled_zone(self):
        executable=self.tool('named-checkzone')
        with tempfile.TemporaryDirectory() as tmp:
            zone=Path(tmp)/'example.zone'
            zone.write_text(compile_zone('example.test',[{'name':'@','type':'A','value':'192.0.2.1','ttl':300}],serial=1,nameservers=['ns1.provider.test']))
            result=subprocess.run([executable,'example.test',str(zone)],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr+result.stdout)
    def test_nginx_accepts_generated_site_configuration(self):
        executable=self.tool('nginx')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); document=root/'public_html';document.mkdir(); (document/'index.html').write_text('Octalve local acceptance')
            config=root/'nginx.conf'
            config.write_text(f'user {pwd.getpwuid(os.getuid()).pw_name};\npid {root}/nginx.pid;\nerror_log stderr;\nevents {{}}\nhttp {{ access_log off; client_body_temp_path {root}/body; proxy_temp_path {root}/proxy; fastcgi_temp_path {root}/fastcgi; uwsgi_temp_path {root}/uwsgi; scgi_temp_path {root}/scgi;\n'+compile_site('example.test',document_root=str(document),aliases=[],port=18981)+'\n}')
            result=subprocess.run([executable,'-t','-p',str(root),'-c',str(config)],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
