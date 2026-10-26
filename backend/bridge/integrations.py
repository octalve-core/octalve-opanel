"""Integration registry: independent hosting panel connectors, deny by default.

An integration installed in OPanel does not imply the hosting provider
supports the runtime, the zone belongs to the customer, or the GitHub
installation has repository permission. Currently ALL execution is disabled.
"""
from dataclasses import dataclass
from .views import valid_binding


@dataclass(frozen=True)
class Integration:
    slug: str
    label: str
    required_capabilities: frozenset[str]
    required_runtime: frozenset[str]
    authority: str


REGISTRY = (
    Integration("wordpress", "WordPress / Softaculous",
                frozenset({"wordpress.install", "database.create"}),
                frozenset({"php", "mysql"}), "verified_software_installer"),
    Integration("cloudflare", "Cloudflare DNS",
                frozenset({"integration.cloudflare.connect", "dns.zone.write"}),
                frozenset(), "verified_zone_owner"),
    Integration("github", "GitHub static deployment",
                frozenset({"integration.github.connect", "files.publish"}),
                frozenset({"static"}), "selected_repository_installation"),
)


class IntegrationRejected(ValueError):
    pass


def resolve_integrations(entitlement, *, runtimes=(), zone_owned=False,
                         installer_verified=False, repository_approved=False):
    """Pure read-only preview. Never infer runtime support from package names.

    Console presently grants only overview, so every integration MUST remain
    disabled. Do not wire actions until per-operation Console scopes exist.
    """
    if not isinstance(entitlement, dict):
        raise IntegrationRejected("Authenticated technical service required.")
    caps = entitlement.get("capabilities")
    if not isinstance(caps, list) or any(not isinstance(x, str) for x in caps):
        raise IntegrationRejected("Invalid technical capabilities.")
    if not isinstance(runtimes, (tuple, list, frozenset, set)):
        raise IntegrationRejected("Invalid verified hosting runtimes.")
    verified = frozenset(runtimes)
    results = []
    for app in REGISTRY:
        allowed = app.required_capabilities.issubset(caps)
        runtime = app.required_runtime.issubset(verified)
        proof = {
            "wordpress": installer_verified,
            "cloudflare": zone_owned,
            "github": repository_approved,
        }[app.slug] is True
        # No live adapter resolver is mounted. Even an available scope must
        # not advertise a working command before adapter conformance testing.
        results.append({
            "slug": app.slug, "label": app.label,
            "required_runtime": sorted(app.required_runtime),
            "supported_by_package": runtime,
            "authorized": allowed and runtime and proof,
            "enabled": False,
            "status": "not_connected",
        })
    return results
