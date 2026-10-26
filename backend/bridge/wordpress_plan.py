"""Host-package proof for WordPress; no Softaculous assumption or installation."""
from dataclasses import dataclass
import re

DOMAIN = re.compile(r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{1,62}$")


class WordPressNotSupported(ValueError):
    pass


@dataclass(frozen=True)
class WordPressInstallPlan:
    service_id: int
    domain: str
    installer: str
    php_version: str
    database_engine: str
    runtime_eligible: bool = True
    installation_enabled: bool = False


def plan_wordpress(*, service_id, domain, verified_hosting_account,
                   verified_runtimes, installer_name, supported_php_version,
                   database_engine, granted_capabilities):
    if (type(service_id) is not int or service_id < 1
            or not isinstance(domain, str) or not DOMAIN.fullmatch(domain)
            or verified_hosting_account is not True
            or not {"php","mysql"}.issubset(set(verified_runtimes))
            or installer_name not in ("softaculous", "qualified-native")
            or not isinstance(supported_php_version, str)
            or not re.fullmatch(r"8\.[2-9](?:\.\d{1,2})?", supported_php_version)
            or database_engine not in ("mysql", "mariadb")
            or not {"wordpress.install","database.create"}.issubset(set(granted_capabilities))):
        raise WordPressNotSupported("Verified PHP/database/installer and scoped account permissions are required.")
    return WordPressInstallPlan(service_id, domain, installer_name,
                                supported_php_version, database_engine)


def execute_wordpress_install(*_args, **_kwargs):
    raise WordPressNotSupported("WordPress installation requires a qualified provider installer.")
