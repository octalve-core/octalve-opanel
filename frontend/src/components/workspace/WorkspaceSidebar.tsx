"use client";
import Link from "next/link";
import {moduleGroups, modules} from "@/lib/modules";
import type {PanelSession} from "@/lib/session";
export function WorkspaceSidebar({menuOpen,setMenuOpen,selected,session}: {menuOpen:boolean;setMenuOpen:(value:boolean)=>void;selected:string;session:PanelSession}) {
return <>
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
</>;
}
