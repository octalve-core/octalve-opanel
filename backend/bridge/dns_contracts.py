"""Account/zone-scoped public DNS-change preview; no Cloudflare API writes."""
from dataclasses import dataclass
import ipaddress
import re


class DNSPlanRejected(ValueError):
    pass


LABEL = re.compile(r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{1,62}$")
ZONE_ID = re.compile(r"^[a-f0-9]{32}$")


@dataclass(frozen=True)
class DNSChangePlan:
    service_id: int
    zone_id: str
    zone_name: str
    name: str
    record_type: str
    value: str
    ttl: int
    approved_for_execution: bool = False


def preview_dns_change(*, service_id, zone_id, zone_name, owner_verified,
                       current_entitlement, record_name, record_type,
                       value, ttl):
    """Input current_entitlement/zone evidence must originate server-side.

    Merely mentioning a domain in hosting is NOT Cloudflare zone ownership.
    """
    if (type(service_id) is not int or service_id < 1
            or type(zone_id) is not str or not ZONE_ID.fullmatch(zone_id)
            or not isinstance(zone_name, str) or not LABEL.fullmatch(zone_name)
            or owner_verified is not True
            or not isinstance(current_entitlement, dict)
            or current_entitlement.get("service_id") != service_id
            or "dns.zone.write" not in current_entitlement.get("capabilities", ())
            or type(ttl) is not int or not 60 <= ttl <= 86400):
        raise DNSPlanRejected("Verified zone, current account scope and TTL are required.")
    if not isinstance(record_name, str) or not isinstance(value, str):
        raise DNSPlanRejected("DNS record values are invalid.")
    record_name = zone_name if record_name == "@" else record_name
    if (not LABEL.fullmatch(record_name)
            or not (record_name == zone_name or record_name.endswith("." + zone_name))):
        raise DNSPlanRejected("Record name is outside the verified DNS zone.")
    if record_type not in ("A", "AAAA", "CNAME", "TXT"):
        raise DNSPlanRejected("This record type needs separate qualification.")
    if any(ord(c)<32 or ord(c)==127 for c in value):
        raise DNSPlanRejected("Invalid DNS record value.")
    if record_type in ("A","AAAA"):
        try:
            addr = ipaddress.ip_address(value)
        except ValueError:
            raise DNSPlanRejected("Invalid public website IP address.") from None
        if addr.version != (4 if record_type=="A" else 6) or not addr.is_global:
            raise DNSPlanRejected("DNS must not point websites at internal addresses.")
    elif record_type == "CNAME":
        if (not LABEL.fullmatch(value) or value == record_name
                or record_name == zone_name):
            raise DNSPlanRejected("Invalid CNAME target or apex.")
    elif not 1 <= len(value) <= 1024:
        raise DNSPlanRejected("TXT record exceeds preview size.")
    return DNSChangePlan(service_id, zone_id, zone_name,
                         record_name, record_type, value, ttl)


def execute_dns_change(*_args, **_kwargs):
    raise DNSPlanRejected("Cloudflare API writes are disabled pending live zone authority.")
