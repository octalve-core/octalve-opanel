import tempfile
from pathlib import Path
from unittest import TestCase
from bridge.practice.engine import Store, Rejected

class PracticeTests(TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'practice.sqlite3'); self.counter=0
    def apply(self,operation,data=None,confirmed=False,workspace='one'):
        self.counter+=1
        return self.store.apply(workspace, self.store.read(workspace)['revision'], str(self.counter),operation,data or {},confirmed)
    def domain(self): self.apply('domains.add',{'name':'example.test'})
    def test_isolation_and_duplicate_replay(self):
        result=self.store.apply('one',0,'request','domains.add',{'name':'example.test'},False)
        self.assertEqual(self.store.read('two')['domains'],[])
        self.assertEqual(self.store.apply('one',0,'request','domains.add',{'name':'example.test'},False),result)
        with self.assertRaises(Rejected): self.store.apply('one',0,'different','domains.add',{'name':'other.test'},False)
        with self.assertRaises(Rejected): self.store.apply('one',1,'request','domains.add',{'name':'other.test'},False)
    def test_domain_and_subdomain_dependencies(self):
        self.domain(); child=self.apply('subdomains.add',{'name':'www','domain':'example.test'})['domains'][-1]
        with self.assertRaises(Rejected): self.apply('domains.remove',{'id':self.store.read('one')['domains'][0]['id']},True)
        self.assertEqual(child['name'],'www.example.test')
    def test_dns_validation_and_cname_conflict(self):
        self.domain()
        self.apply('dns.add',{'domain':'example.test','name':'www','type':'A','value':'192.0.2.1','ttl':300})
        for data in ({'type':'A','value':'not-an-ip'},{'type':'CNAME','value':'target.test'}):
            with self.assertRaises(Rejected): self.apply('dns.add',{'domain':'example.test','name':'www','ttl':300,**data})
    def test_ssl_is_explicitly_simulated(self):
        self.domain(); result=self.apply('ssl.add',{'domain':'example.test'})
        self.assertEqual(result['ssl'][0]['status'],'simulation-pending')
        result=self.apply('ssl.verify',{'id':result['ssl'][0]['id']})
        self.assertEqual(result['ssl'][0]['status'],'simulation-valid')
        self.assertNotIn('certificate',result['ssl'][0])
    def test_release_rollback_and_restore(self):
        self.domain(); site=self.apply('websites.add',{'domain':'example.test','name':'My site'})['websites'][0]
        self.apply('websites.release',{'id':site['id'],'label':'First'})
        backup=self.apply('backups.add',{'name':'Checkpoint'})['backups'][0]
        self.apply('websites.release',{'id':site['id'],'label':'Second'})
        state=self.apply('websites.rollback',{'id':site['id']},True)
        self.assertEqual(state['websites'][0]['current_release'],'First')
        state=self.apply('backups.restore',{'id':backup['id']},True)
        self.assertEqual(state['websites'][0]['current_release'],'First')
    def test_dangerous_files_and_unconfirmed_delete_rejected(self):
        for name in ('../secret','/etc/passwd','a\\b'):
            with self.assertRaises(Rejected): self.apply('files.add',{'name':name,'kind':'file','content':'test'})
        file=self.apply('files.add',{'name':'readme.txt','kind':'file','content':'hello'})['files'][0]
        with self.assertRaises(Rejected): self.apply('files.remove',{'id':file['id']})
        self.assertEqual(self.apply('files.remove',{'id':file['id']},True)['files'],[])
    def test_database_and_mailbox_validation(self):
        self.domain()
        self.apply('databases.add',{'name':'app_db','user':'app_user'})
        self.apply('email.add',{'domain':'example.test','name':'hello','quota':500})
        with self.assertRaises(Rejected): self.apply('databases.add',{'name':'drop;table','user':'root'})
        with self.assertRaises(Rejected): self.apply('email.add',{'domain':'foreign.test','name':'hello','quota':500})

    def test_edit_dns_and_file_content(self):
        self.domain()
        record=self.apply('dns.add',{'domain':'example.test','name':'www','type':'A','value':'192.0.2.1','ttl':300})['dns'][0]
        state=self.apply('dns.update',{**record,'value':'192.0.2.2'})
        self.assertEqual(state['dns'][0]['value'],'192.0.2.2')
        self.assertEqual(state['dns'][0]['id'],record['id'])
        file=self.apply('files.add',{'name':'note.txt','kind':'file','content':'old'})['files'][0]
        state=self.apply('files.update',{**file,'content':'new text'})
        self.assertEqual(state['files'][0]['content'],'new text')

from django.test import TestCase as DjangoTestCase, Client, override_settings

class PracticeAPITests(DjangoTestCase):
    def test_practice_disabled_by_default(self):
        self.assertEqual(self.client.get('/api/practice/').status_code,404)
    @override_settings(DEBUG=True,OPANEL_PRACTICE_ENABLED=True)
    def test_csrf_isolation_and_persistence(self):
        with tempfile.TemporaryDirectory() as tmp, override_settings(OPANEL_PRACTICE_DATABASE=str(Path(tmp)/'practice.db')):
            first=Client(enforce_csrf_checks=True); second=Client()
            response=first.get('/api/practice/',HTTP_HOST='localhost')
            self.assertEqual(response.status_code,200)
            body={'revision':0,'request_id':'create','operation':'domains.add','data':{'name':'example.test'}}
            self.assertEqual(first.post('/api/practice/',body,content_type='application/json',HTTP_HOST='localhost').status_code,403)
            self.assertEqual(first.post('/api/practice/',body,content_type='application/json',HTTP_HOST='localhost',HTTP_X_CSRFTOKEN=response.json()['csrf_token']).status_code,200)
            self.assertEqual(len(first.get('/api/practice/',HTTP_HOST='localhost').json()['state']['domains']),1)
            self.assertEqual(second.get('/api/practice/',HTTP_HOST='localhost').json()['state']['domains'],[])
    @override_settings(DEBUG=False,OPANEL_PRACTICE_ENABLED=True,SECURE_SSL_REDIRECT=False)
    def test_practice_never_enabled_in_production(self):
        self.assertEqual(self.client.get('/api/practice/',HTTP_HOST='localhost').status_code,404)

class PracticeIntegrityTests(PracticeTests):
    def test_subdomain_delete_alias_preserves_dependencies(self):
        self.domain()
        child=self.apply('subdomains.add',{'name':'www','domain':'example.test'})['domains'][-1]
        self.apply('ssl.add',{'domain':child['name']})
        before=self.store.read('one')
        for operation,record in [('subdomains.remove',child),('domains.remove',child),('subdomains.remove',before['domains'][0])]:
            with self.assertRaises(Rejected): self.apply(operation,{'id':record['id']},True)
            self.assertEqual(self.store.read('one'),before)
    def test_populated_directory_cannot_become_file(self):
        folder=self.apply('files.add',{'name':'docs','kind':'directory'})['files'][0]
        self.apply('files.add',{'name':'docs/note.txt','kind':'file'})
        before=self.store.read('one')
        with self.assertRaises(Rejected): self.apply('files.update',{**folder,'kind':'file'})
        self.assertEqual(self.store.read('one'),before)

class PracticeIdentityTests(DjangoTestCase):
    @override_settings(DEBUG=True,OPANEL_PRACTICE_ENABLED=True)
    def test_identity_independent_of_hosting_session_and_tamper_resistant(self):
        from unittest.mock import patch
        import time
        with tempfile.TemporaryDirectory() as tmp, override_settings(OPANEL_PRACTICE_DATABASE=str(Path(tmp)/'practice.db')):
            client=Client()
            session=client.session; session['hosting_marker']='unchanged'; session.set_expiry(900); session.save()
            key=session.session_key
            client.get('/api/practice/',HTTP_HOST='localhost')
            body={'revision':0,'request_id':'create','operation':'domains.add','data':{'name':'example.test'}}
            client.post('/api/practice/',body,content_type='application/json',HTTP_HOST='localhost')
            self.assertIn('opanel_practice',client.cookies)
            self.assertEqual(client.session.session_key,key)
            self.assertNotIn('practice_workspace',client.session)
            with patch('django.core.signing.time.time',return_value=time.time()+901):
                result=client.get('/api/practice/',HTTP_HOST='localhost')
                self.assertEqual(len(result.json()['state']['domains']),1)
            client.cookies['opanel_practice']='tampered'
            self.assertEqual(client.get('/api/practice/',HTTP_HOST='localhost').json()['state']['domains'],[])
