"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { consoleDestination, currentSession, logoutToken, type HostingUsage, type PanelSession } from "@/lib/session";
import { findModule, moduleGroups, modules } from "@/lib/modules";
import { PlannedModuleDetail } from "@/components/PlannedModuleDetail";

type ViewState = "loading" | "ready" | "locked" | "error";
const ACTIVE = new Set(["overview", "statistics", "settings"]);

function Amount({ used, limit }: { used: number; limit: number }) {
  const percent = limit > 0 ? Math.min(100, Math.round(100 * used / limit)) : 0;
  return <div className="meter">
    <div className="meter-values"><strong>{used.toLocaleString()} MB</strong><span>of {limit.toLocaleString()} MB</span></div>
    <progress max={100} value={percent} aria-label="Recorded resource usage" />
    <span className="quiet">{limit > 0 ? Math.round(100 * used / limit) + "% used" : "No configured limit"}</span>
  </div>;
}

function Overview({ session }: { session: PanelSession }) {
  const view = session.overview;
  const usage: HostingUsage | null = view?.usage ?? null;
  return <>
    <div className="service-hero">
      <div><span className="hero-eyebrow">● &nbsp; VERIFIED SERVICE ACCESS</span>
        <h2>{view?.label || "Your hosting service"}</h2>
        <p>{view?.domain || "Hosting domain is not available"}</p></div>
      <div className="service-tag"><span>HOSTING ID</span><b>#{session.service_id}</b></div>
    </div>
    <div className="metrics">
      <article className="metric"><span className="metric-kicker">Disk usage</span>
        {usage ? <Amount used={usage.disk_used_mb} limit={usage.disk_limit_mb} /> : <p>Snapshot not available</p>}</article>
      <article className="metric"><span className="metric-kicker">Bandwidth usage</span>
        {usage ? <Amount used={usage.bandwidth_used_mb} limit={usage.bandwidth_limit_mb} /> : <p>Snapshot not available</p>}</article>
      <article className="metric"><span className="metric-kicker">Next billing date</span>
        <strong className="metric-date">{view?.next_due_date ? view.next_due_date.slice(0, 10) : "Unavailable"}</strong>
        <p>Billing is managed in Octalve Console</p></article>
    </div>
    <p className="snapshot-note">Recorded usage only—not live provider telemetry. {usage?.recorded_at ? "Captured " + new Date(usage.recorded_at).toLocaleString() : "No resource usage has been recorded."}</p>
    <div className="section-heading"><h3>Hosting tools</h3><span>Modules under development</span></div>
    <div className="module-grid">{modules.filter(m => !ACTIVE.has(m.slug)).map(module =>
      <Link className="module-card" href={`/modules/${module.slug}`} key={module.slug}>
        <span className="module-icon">{module.symbol}</span><span className="module-desc">
          <strong>{module.name}</strong><small>{module.description}</small>
        </span><span className="module-state">Planned</span>
      </Link>
    )}</div>
    <div className="info-box"><strong>Management operations are disabled.</strong>
      <p>DNS updates, files, websites, databases, mail, SSL and backups will become available only after each provider operation is independently verified, account-scoped and approved. This workspace does not provision or change hosting.</p></div>
  </>;
}

function ReadOnlyModule({slug, session}: {slug:string; session:PanelSession}) {
  const module = findModule(slug);
  if (!module) return null;
  if (slug === "statistics") return <div className="detail-panel"><h2>Recorded resource usage</h2>
    <p>Historical snapshots received from Console after your hosting entitlement is rechecked.</p>
    {session.overview?.usage ? <div className="metrics compact">
      <div className="metric"><h3>Disk</h3><Amount used={session.overview.usage.disk_used_mb} limit={session.overview.usage.disk_limit_mb}/></div>
      <div className="metric"><h3>Bandwidth</h3><Amount used={session.overview.usage.bandwidth_used_mb} limit={session.overview.usage.bandwidth_limit_mb}/></div>
    </div> : <div className="empty-slate">No recorded usage is available.</div>}</div>;
  if (slug === "settings") return <div className="detail-panel"><h2>Hosting access</h2>
    <div className="property"><span>Console service</span><strong>#{session.service_id}</strong></div>
    <div className="property"><span>Sign-in authority</span><strong>Octalve Console</strong></div>
    <div className="property"><span>Session scope</span><strong>One verified hosting service</strong></div>
    <div className="property"><span>Technical operations</span><strong>Not enabled</strong></div>
    <p>No separate OPanel password, billing record, or provider administrator account is stored in this interface.</p></div>;
  return <PlannedModuleDetail slug={slug} />;
}

export function Workspace({ selected }: { selected: string }) {
  const [session, setSession] = useState<PanelSession | null>(null);
  const [view, setView] = useState<ViewState>("loading");
  const [menuOpen, setMenuOpen] = useState(false);
  const [csrf, setCsrf] = useState<string | null>(null);
  const [signingOut, setSigningOut] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setView("loading"); setSession(null);
    logoutToken(controller.signal).then(token => { if (!controller.signal.aborted) setCsrf(token); }).catch(() => {});
    currentSession(controller.signal).then(data => {
      if (data.csrf_token) setCsrf(data.csrf_token);
      setSession(data); setView(data.authenticated ? "ready" : "locked");
    }).catch(() => { if (!controller.signal.aborted) setView("error"); });
    return () => controller.abort();
  }, [selected]);
  async function signOut() {
    if (signingOut) return;
    setSigningOut(true);
    try {
      const freshToken = await logoutToken();
      const response = await fetch("/auth/logout/", {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "X-CSRFToken": freshToken },
      });
      if (!response.ok) throw new Error("Server did not accept logout");
      window.location.assign("/");
    } catch { setSigningOut(false); setView("error"); }
  }
  const consoleUrl = consoleDestination();
  if (view !== "ready" || !session) return <main className="gate">
    <div className="gate-brand"><span className="logo-mark">O</span> Octalve <b>OPANEL</b></div>
    {view === "loading" ? <><h1>Verifying hosting access</h1><p>Checking your current Console service entitlement.</p></> :
      view === "locked" ? <><h1>Hosting access is unavailable</h1>
        <p>Sign into Octalve Console and open an eligible, provider-confirmed hosting service. OPanel does not use a separate customer password.</p></> :
        <><h1>Unable to verify access</h1><p>The authorization service is unavailable. Technical actions are blocked.</p></>}
    <div className="gate-actions">
      {consoleUrl && <a className="primary-link" href={consoleUrl}>Return to Octalve Console</a>}
      <button type="button" onClick={() => window.location.reload()}>Retry check</button>
      <button type="button" onClick={signOut} disabled={!csrf || signingOut}>{signingOut ? "Signing out…" : "Sign out"}</button>
    </div>
  </main>;
  const active = findModule(selected) || modules[0];
  return <div className="workspace">
    <aside className={`sidebar ${menuOpen ? "open" : ""}`} aria-label="Hosting navigation">
      <Link href="/" className="brand"><span className="logo-mark">O</span>
        <span>Octalve<small>OPANEL</small></span></Link>
      <div className="sidebar-service"><span>ACTIVE HOSTING</span><strong>{session.overview?.label || `Service #${session.service_id}`}</strong>
        <small>{session.overview?.domain || "Verified hosting entitlement"}</small></div>
      <nav aria-label="Workspace modules">{moduleGroups.map(group =>
        <div className="nav-group" key={group}><div className="nav-title">{group}</div>
          {modules.filter(m => m.group === group).map(module =>
            <Link key={module.slug} href={module.slug === "overview" ? "/" : `/modules/${module.slug}`}
              onClick={() => setMenuOpen(false)} aria-current={selected === module.slug ? "page" : undefined}
              className={`nav-link ${selected === module.slug ? "selected" : ""}`}>
              <span className="nav-symbol">{module.symbol}</span><span>{module.name}</span>
              {!module.available && <span className="nav-lock" aria-label="Not enabled">·</span>}
            </Link>
          )}</div>
      )}</nav>
      <div className="sidebar-bottom">Independent hosting management<br/>Commercial identity stays with Console.</div>
    </aside>
    {menuOpen && <button type="button" className="scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)}/>}
    <div className="work-main"><header className="topbar">
      <div className="top-left"><button className="menu-toggle" type="button" aria-label="Toggle navigation"
          aria-expanded={menuOpen} onClick={() => setMenuOpen(open => !open)}>☰</button>
        <span className="crumb">Hosting <span>/</span> {active.name}</span></div>
      <div className="top-right"><span className="secure-indicator">● &nbsp; Authenticated</span>
        <button className="logout" type="button" onClick={signOut} disabled={signingOut}>
          {signingOut ? "Signing out…" : "Sign out"}</button></div>
    </header>
    <main className="content" id="main-content"><div className="page-heading">
      <span className="eyebrow">OCTALVE CLOUD / OPANEL</span>
      <h1>{selected === "overview" ? "Hosting overview" : active.name}</h1>
      <p>{selected === "overview" ? "A secure workspace for your verified hosting service." : active.description}</p>
    </div>
    {selected === "overview" ? <Overview session={session}/> : <ReadOnlyModule slug={selected} session={session}/>}
    <footer className="page-footer">© Octalve · Secure hosting management · Read-only technical release</footer>
    </main></div>
  </div>;
}
