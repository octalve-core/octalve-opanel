import datetime
import tempfile
from pathlib import Path
from unittest import TestCase

class HostingDNSTests(TestCase):
    def test_real_zone_parser_reads_typed_records(self):
        import dns.zone
        from native_agent.dns import compile_zone
        records=[{'name':'@','type':'A','value':'192.0.2.5','ttl':300},
                 {'name':'www','type':'CNAME','value':'example.test','ttl':300},
                 {'name':'@','type':'MX','value':'mail.example.test','priority':10,'ttl':300},
                 {'name':'_dmarc','type':'TXT','value':'v=DMARC1; p=reject','ttl':300},
                 {'name':'@','type':'CAA','value':'letsencrypt.org','tag':'issue','flags':0,'ttl':300},
                 {'name':'_sip._tcp','type':'SRV','value':'sip.example.test','priority':10,'weight':5,'port':5060,'ttl':300}]
        result=compile_zone('example.test',records,serial=2,nameservers=['ns1.example.test'])
        zone=dns.zone.from_text(result,origin='example.test')
        self.assertEqual(zone.get_rdataset('@','SOA')[0].serial,2)
        self.assertEqual(str(zone.get_rdataset('@','A')[0]),'192.0.2.5')
        self.assertEqual(zone.get_rdataset('_sip._tcp','SRV')[0].port,5060)
    def test_zone_escape_cname_conflict_and_injection_refused(self):
        from native_agent.dns import compile_zone
        from native_agent.filesystem import Refused
        for records in ([{'name':'foreign.test.','type':'A','value':'192.0.2.1','ttl':300}],
                        [{'name':'@','type':'CNAME','value':'other.test','ttl':300}],
                        [{'name':'www','type':'CNAME','value':'other.test','ttl':300},{'name':'www','type':'A','value':'192.0.2.1','ttl':300}],
                        [{'name':'@','type':'TXT','value':'bad\n$INCLUDE /etc/passwd','ttl':300}],
                        [{'name':'@','type':'A','value':'192.0.2.1','ttl':True}]):
            with self.assertRaises(Refused): compile_zone('example.test',records,serial=2,nameservers=['ns1.example.test'])

class HostingWebConfigTests(TestCase):
    def test_static_site_has_scoped_root_and_no_php_execution(self):
        from native_agent.web import compile_site
        config=compile_site('example.test',document_root='/srv/opanel/13/public_html',aliases=['www.example.test'],port=8080)
        self.assertIn('server_name example.test www.example.test;',config)
        self.assertIn('disable_symlinks on;',config)
        self.assertIn('try_files $uri $uri/ =404;',config)
        self.assertNotIn('fastcgi_pass',config)
    def test_site_injection_and_unbounded_root_refused(self):
        from native_agent.web import compile_site
        from native_agent.filesystem import Refused
        for domain,root in [('example.test; return 200','/srv/13'),('example.test','/'),('example.test','/srv/x";include /etc/*;')]:
            with self.assertRaises(Refused): compile_site(domain,document_root=root,aliases=[],port=8080)

class HostingCertificateTests(TestCase):
    def certificate(self,domain='example.test',expired=False):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes,serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,domain)])
        now=datetime.datetime.now(datetime.timezone.utc)
        cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
              .serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(days=2))
              .not_valid_after(now+datetime.timedelta(days=-1 if expired else 10))
              .add_extension(x509.SubjectAlternativeName([x509.DNSName(domain)]),critical=False).sign(key,hashes.SHA256()))
        return cert.public_bytes(serialization.Encoding.PEM),key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    def test_key_domain_dates_and_public_metadata(self):
        from native_agent.certificates import inspect_certificate
        cert,key=self.certificate(); result=inspect_certificate(cert,key,domains=['example.test'])
        self.assertEqual(result['domains'],['example.test'])
        self.assertFalse(result['public_trust_verified'])
        self.assertNotIn('PRIVATE',str(result))
    def test_wrong_key_domain_and_expired_refused(self):
        from native_agent.certificates import inspect_certificate
        from native_agent.filesystem import Refused
        cert,key=self.certificate(); _,other=self.certificate(); expired,old_key=self.certificate(expired=True)
        for c,k,domains in [(cert,other,['example.test']),(cert,key,['foreign.test']),(expired,old_key,['example.test'])]:
            with self.assertRaises(Refused): inspect_certificate(c,k,domains=domains)
