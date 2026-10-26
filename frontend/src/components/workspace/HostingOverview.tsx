"use client";
import Link from "next/link";
import {modules} from "@/lib/modules";
import type {HostingUsage, PanelSession} from "@/lib/session";
import {UsageMeter} from "./UsageMeter";
const ACTIVE = new Set(["overview","statistics","settings"]);
export function HostingOverview({ session }: { session: PanelSession }) {
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
        {usage ? <UsageMeter used={usage.disk_used_mb} limit={usage.disk_limit_mb} /> : <p>Snapshot not available</p>}</article>
      <article className="metric"><span className="metric-kicker">Bandwidth usage</span>
        {usage ? <UsageMeter used={usage.bandwidth_used_mb} limit={usage.bandwidth_limit_mb} /> : <p>Snapshot not available</p>}</article>
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
