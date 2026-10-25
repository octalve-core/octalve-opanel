"""OPanel's independent read-only hosting dashboard.

All displayed values originate from a fresh, service-bound Console entitlement,
NOT from provider administrator endpoints or browser-supplied query strings.
No technical-management capability is represented as enabled.
"""
from datetime import datetime
from html import escape


FEATURES = (
    ("Files", "Manage files", "Folder access and file uploads"),
    ("DNS", "DNS records", "Create and edit zone records"),
    ("Mail", "Email accounts", "Mailboxes and webmail settings"),
    ("DB", "Databases", "Database creation and access"),
    ("SSL", "SSL certificates", "Certificates and HTTPS status"),
    ("Site", "Websites", "Domains and site configuration"),
    ("Save", "Backups", "Restore points and downloads"),
    ("Usage", "Advanced metrics", "Detailed provider-backed graphs"),
)


def normalize_overview(data, service_id):
    """Validate external JSON structure before allowing it into UI rendering."""
    if not isinstance(data, dict):
        return None
    try:
        if type(data.get("service_id")) is not int or data["service_id"] != service_id:
            return None
        if data.get("status") != "active":
            return None
        label = data.get("label")
        domain = data.get("domain")
        if not isinstance(label, str) or not isinstance(domain, str):
            return None
        if len(label) > 255 or len(domain) > 255:
            return None
        if not label.strip():
            return None
        due = data.get("next_due_date")
        if not isinstance(due, str) or len(due) > 64:
            return None
        if datetime.fromisoformat(due.replace("Z", "+00:00")).tzinfo is None:
            return None
        raw = data.get("usage")
        usage = None
        if isinstance(raw, dict):
            names = ("disk_used_mb", "disk_limit_mb", "bandwidth_used_mb", "bandwidth_limit_mb")
            if all(type(raw.get(n)) is int and 0 <= raw[n] <= 10**15 for n in names):
                recorded = raw.get("recorded_at")
                if isinstance(recorded, str) and len(recorded) <= 64:
                    if datetime.fromisoformat(recorded.replace("Z", "+00:00")).tzinfo is not None:
                        usage = {key: raw[key] for key in names}
                        usage["recorded_at"] = recorded
        return {"label": label, "domain": domain, "next_due_date": due, "usage": usage}
    except (ValueError, TypeError, OverflowError):
        return None


def _meter(title, data, used_key, limit_key):
    if data is None:
        return f"<article class='card'><div class='stat-top'>{escape(title)}</div><strong>Not available</strong><p>No provider usage snapshot has been recorded.</p></article>"
    used, limit = data[used_key], data[limit_key]
    ratio = round(100 * used / limit) if limit > 0 else 0
    capped = min(100, max(0, ratio))
    return (
        "<article class='card'>"
        f"<div class='stat-top'>{escape(title)} <span class='muted'>Recorded</span></div>"
        f"<strong>{used:,} <span class='units'>/ {limit:,} MB</span></strong>"
        f"<div class='progress' role='progressbar' aria-valuenow='{capped}' aria-valuemin='0' aria-valuemax='100' aria-label='{escape(title)} usage'>"
        f"<span style='width:{capped}%'></span></div>"
        f"<p>{ratio}% of recorded limit used</p></article>"
    )


def dashboard_html(identity, csrf_token):
    service_id = int(identity["service_id"])
    overview = identity.get("overview")
    details = overview if isinstance(overview, dict) else None
    label = escape(details["label"]) if details else f"Service #{service_id}"
    domain = escape(details["domain"]) if details and details["domain"] else "Domain information unavailable"
    due = escape(details["next_due_date"][:10]) if details else "Not available"
    usage = details["usage"] if details else None
    recorded = escape(usage["recorded_at"].replace("T", " ")[:19] + " UTC") if usage else "No usage snapshot available"
    features = "".join(
        "<article class='tool'><div class='tool-icon'>"+escape(icon)+"</div>"
        "<div><h3>"+escape(name)+"</h3><p>"+escape(summary)+"</p></div>"
        "<span class='locked'>Coming later</span></article>"
        for icon, name, summary in FEATURES
    )
    csrf = escape(str(csrf_token), quote=True)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer"><title>Hosting overview | Octalve OPanel</title>
<style>
:root{{--blue:#0064E0;--ink:#000A16;--line:#e5ebf2;--slate:#566474;--white:#fff}}
*{{box-sizing:border-box}}body{{margin:0;font:15px/1.55 system-ui,-apple-system,'Segoe UI',sans-serif;color:#17243a;background:#f5f8fc}}
a{{color:inherit}}.frame{{display:grid;grid-template-columns:236px minmax(0,1fr);min-height:100vh}}
aside{{background:#000A16;color:white;padding:26px 18px;display:flex;flex-direction:column;gap:24px}}
.brand{{display:flex;align-items:center;gap:10px;font-size:19px;font-weight:800;letter-spacing:-.6px;text-decoration:none}}
.symbol{{display:grid;place-items:center;background:var(--blue);border-radius:12px;width:40px;height:40px;color:#fff;font-size:24px}}
.brand small{{display:block;color:#96b2cd;font-size:10px;font-weight:600;letter-spacing:1.7px}}
.nav-label{{text-transform:uppercase;letter-spacing:1.7px;font-size:10px;color:#8ca2ba;margin:6px 12px 12px}}
.nav-current{{background:#0064E0;display:flex;gap:12px;padding:12px 14px;border-radius:11px;font-weight:650}}
.nav-muted{{display:block;padding:10px 14px;color:#8ea7c0}}.side-footer{{margin-top:auto;border-top:1px solid #1f3348;padding:18px 10px 0;color:#a1b4ca;font-size:12px}}
main{{min-width:0}}.top{{background:white;border-bottom:1px solid var(--line);padding:18px clamp(20px,4vw,50px);display:flex;align-items:center;justify-content:space-between;gap:10px}}
.top b{{font-size:14px}}.secure{{color:#196b47;background:#e9f8f1;border-radius:999px;padding:6px 12px;font-size:12px;font-weight:700}}
.content{{max-width:1250px;margin:auto;padding:35px clamp(20px,4vw,50px) 60px}}.eyebrow{{color:var(--blue);font-size:12px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase}}
h1{{font-size:clamp(27px,3vw,38px);margin:7px 0 7px;letter-spacing:-1.2px}}.desc{{color:var(--slate);margin:0 0 28px}}
.hero{{border-radius:19px;padding:27px 29px;background:linear-gradient(120deg,#061a33,#003f88);color:#fff;display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:20px;margin-bottom:23px}}
.hero h2{{font-size:23px;margin:3px 0;overflow-wrap:anywhere}}.hero p{{color:#c5def7;margin:0}}.pill{{display:inline-flex;align-items:center;gap:7px;background:#173d5e;color:#d3f8e4;padding:7px 12px;border-radius:30px;font-size:12px;font-weight:700}}
.cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}}.card{{background:white;border:1px solid var(--line);border-radius:16px;padding:23px;min-width:0}}
.stat-top{{font-size:13px;font-weight:700;color:#52667a;display:flex;justify-content:space-between;gap:8px}}strong{{display:block;font-size:26px;letter-spacing:-.7px;margin-top:14px;overflow-wrap:anywhere}}
.units{{font-size:13px;color:#778798;font-weight:500}}.muted{{font-size:11px;color:#8b9bae;font-weight:500}}
.card p{{font-size:12px;color:#6b7c90;margin:10px 0 0}}.progress{{height:8px;margin:20px 0 0;background:#e9f0f7;border-radius:20px;overflow:hidden}}
.progress span{{display:block;height:100%;background:var(--blue);border-radius:20px}}
.section-title{{margin:37px 0 17px;font-size:21px;letter-spacing:-.5px}}.tools{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}}
.tool{{display:flex;gap:13px;align-items:flex-start;background:#fff;border:1px solid var(--line);padding:18px;border-radius:14px;min-width:0}}
.tool-icon{{background:#eaf2ff;color:#0052b8;font-size:11px;font-weight:850;border-radius:11px;min-width:43px;height:43px;display:grid;place-items:center}}
.tool h3{{margin:0;font-size:14px}}.tool p{{font-size:12px;color:var(--slate);margin:2px 0 0}}
.locked{{margin-left:auto;white-space:nowrap;font-size:11px;color:#69788b;background:#f0f3f7;border-radius:30px;padding:5px 9px}}
.notice{{border:1px solid #d3e3fa;background:#f1f7ff;border-radius:14px;padding:19px;margin-top:25px;color:#234c79;font-size:13px}}
button{{border:1px solid #dfebf7;color:#243c54;background:white;padding:10px 14px;border-radius:10px;font-weight:650;cursor:pointer}}
button:hover{{background:#e9f3fd}}.signout{{margin:0}}footer{{margin-top:38px;color:#8796a7;font-size:12px}}
@media(max-width:980px){{.frame{{grid-template-columns:1fr}}aside{{padding:14px 20px;flex-direction:row;align-items:center;justify-content:space-between}}.side-footer,.nav-label,.nav-muted{{display:none}}.nav-current{{padding:8px 10px;font-size:12px}}.brand{{font-size:15px}}.cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
@media(max-width:640px){{.top{{padding:14px 20px}}.top b{{font-size:12px}}.content{{padding:26px 16px}}.cards,.tools{{grid-template-columns:1fr}}.hero{{padding:22px}}.tool{{flex-wrap:wrap}}.locked{{margin-left:56px}}.nav-current{{display:none}}}}
</style></head><body>
<div class="frame">
<aside aria-label="OPanel navigation">
  <div class="brand"><span class="symbol">O</span><span>Octalve <small>OPANEL</small></span></div>
  <div><div class="nav-label">Workspace</div><div class="nav-current">◫ &nbsp; Hosting overview</div>
    <span class="nav-muted">Technical tools — coming later</span></div>
  <p class="side-footer">An independent Octalve Cloud product.<br>Identity and service entitlement are verified by Octalve Console.</p>
</aside>
<main>
 <header class="top"><b>Hosting management <span class="muted">/ Overview</span></b>
   <form class="signout" method="post" action="/auth/logout/"><input type="hidden" name="csrfmiddlewaretoken" value="{csrf}"><button type="submit">Sign out</button></form>
 </header>
 <div class="content"><div class="eyebrow">Welcome to your hosting workspace</div>
 <h1>Hosting overview</h1><p class="desc">A secure, read-only view of your verified hosting service.</p>
 <section class="hero" aria-label="Hosting service"><div><span class="pill">● &nbsp; Active Console entitlement</span>
  <h2>{label}</h2><p>{domain}</p></div>
  <div><div class="muted">HOSTING SERVICE</div><div>#{service_id}</div></div>
 </section>
 <div class="cards">
  {_meter("Disk space",usage,"disk_used_mb","disk_limit_mb")}
  {_meter("Bandwidth",usage,"bandwidth_used_mb","bandwidth_limit_mb")}
  <article class="card"><div class="stat-top">Next billing date</div><strong>{due}</strong><p>Provided by Octalve Console; no payment action occurs in OPanel.</p></article>
 </div>
 <p class="muted" style="margin-top:12px">Usage snapshot: {recorded}. These figures are recorded historical data, not a real-time server measurement.</p>
 <h2 class="section-title">Hosting tools</h2>
 <section class="tools" aria-label="Unavailable technical management features">{features}</section>
 <aside class="notice" style="display:block;background:#f1f7ff;color:#234c79;border:1px solid #d3e3fa;border-radius:14px;padding:19px;margin-top:25px">
  <b>Technical controls are not enabled yet.</b> Hosting files, DNS, email, databases, certificates and backups will be added only after account-scoped provider adapters pass security and acceptance tests. No operation can change your server here.
 </aside>
 <footer>Octalve OPanel &nbsp;·&nbsp; Independent hosting management &nbsp;·&nbsp; Secure Console SSO</footer>
 </div>
</main></div></body></html>"""
