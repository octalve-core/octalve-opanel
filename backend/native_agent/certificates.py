"""Certificate import validation; neither ACME issuance nor public trust proof."""
import datetime
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from .dns import hostname
from .filesystem import Refused


def inspect_certificate(chain_pem,key_pem,*,domains,now=None):
    if not isinstance(chain_pem,bytes) or not isinstance(key_pem,bytes) or len(chain_pem)>65536 or len(key_pem)>16384:
        raise Refused('Certificate input exceeds budget.')
    if not isinstance(domains,list) or not 1<=len(domains)<=100 or len(set(domains))!=len(domains): raise Refused('Verified domain set required.')
    for domain in domains: hostname(domain)
    try:
        chain=x509.load_pem_x509_certificates(chain_pem); cert=chain[0]
        key=serialization.load_pem_private_key(key_pem,password=None)
        if not ((isinstance(key,rsa.RSAPrivateKey) and key.key_size>=2048) or (isinstance(key,ec.EllipticCurvePrivateKey) and key.key_size>=256)):
            raise Refused('Unsupported or weak key.')
        public=lambda k:k.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
        if public(key)!=public(cert): raise Refused('Certificate key mismatch.')
        now=now or datetime.datetime.now(datetime.timezone.utc)
        if not cert.not_valid_before_utc<=now<cert.not_valid_after_utc: raise Refused('Certificate is not currently valid.')
        names=cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
        def covers(domain,name):
            return domain==name or (name.startswith('*.') and domain.count('.')==name.count('.') and domain.endswith(name[1:]))
        if any(not any(covers(domain,name) for name in names) for domain in domains): raise Refused('Certificate does not cover requested domains.')
        return {'domains':sorted(domains),'sha256':cert.fingerprint(hashes.SHA256()).hex(),
                'not_before':cert.not_valid_before_utc.isoformat(),'not_after':cert.not_valid_after_utc.isoformat(),
                'public_trust_verified':False,'chain_certificates':len(chain)}
    except (ValueError,TypeError,IndexError,x509.ExtensionNotFound) as exc:
        raise Refused('Certificate validation failed.') from exc
