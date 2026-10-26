"use client";
import type {PanelSession} from "@/lib/session";
import {findModule} from "@/lib/modules";
import {PlannedModuleDetail} from "@/components/PlannedModuleDetail";
import {IntegrationHub} from "@/components/IntegrationHub";
import {TechnicalAccessSettings} from "@/components/TechnicalAccessSettings";
import {WebsiteUpload} from "@/components/WebsiteUpload";
import {DomainConnection} from "@/components/DomainConnection";
import {UsageMeter} from "./UsageMeter";
export function HostingModule({slug, session}: {slug:string; session:PanelSession}) {
  const module = findModule(slug);
  if (!module) return null;
  if (slug === "statistics") return <div className="detail-panel"><h2>Recorded resource usage</h2>
    <p>Historical snapshots received from Console after your hosting entitlement is rechecked.</p>
    {session.overview?.usage ? <div className="metrics compact">
      <div className="metric"><h3>Disk</h3><UsageMeter used={session.overview.usage.disk_used_mb} limit={session.overview.usage.disk_limit_mb}/></div>
      <div className="metric"><h3>Bandwidth</h3><UsageMeter used={session.overview.usage.bandwidth_used_mb} limit={session.overview.usage.bandwidth_limit_mb}/></div>
    </div> : <div className="empty-slate">No recorded usage is available.</div>}</div>;
  if (slug === "files" || slug === "websites") return <WebsiteUpload />;
  if (slug === "domains" || slug === "dns") return <DomainConnection session={session} />;
  if (slug === "integrations") return <IntegrationHub />;
  if (slug === "settings") return <div className="detail-panel"><h2>Hosting access</h2>
    <div className="property"><span>Console service</span><strong>#{session.service_id}</strong></div>
    <div className="property"><span>Sign-in authority</span><strong>Octalve Console</strong></div>
    <div className="property"><span>Session scope</span><strong>One verified hosting service</strong></div>
    <div className="property"><span>Technical operations</span><strong>Not enabled</strong></div>
    <p>Console remains the authority for this hosting service. An optional separate technical login can be enrolled only after successful Console sign-in; it is not a provider administrator password.</p><TechnicalAccessSettings /></div>;
  return <PlannedModuleDetail slug={slug} />;
}
