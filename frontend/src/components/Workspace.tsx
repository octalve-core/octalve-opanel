"use client";

import { useEffect, useState } from "react";
import { currentSession, logoutToken, type PanelSession } from "@/lib/session";
import { findModule, modules } from "@/lib/modules";
import { WorkspaceGate, type ViewState } from "./workspace/WorkspaceGate";
import { WorkspaceSidebar } from "./workspace/WorkspaceSidebar";
import { HostingOverview } from "./workspace/HostingOverview";
import { HostingModule } from "./workspace/HostingModule";

/** Thin composition shell. Each page, card and hosting tool lives separately. */
export function Workspace({ selected }: { selected: string }) {
  const [session, setSession] = useState<PanelSession | null>(null);
  const [view, setView] = useState<ViewState>("loading");
  const [menuOpen, setMenuOpen] = useState(false);
  const [csrf, setCsrf] = useState<string | null>(null);
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setView("loading"); setSession(null);
    logoutToken(controller.signal).then(token => {
      if (!controller.signal.aborted) setCsrf(token);
    }).catch(() => {});
    currentSession(controller.signal).then(data => {
      if (controller.signal.aborted) return;
      if (data.csrf_token) setCsrf(data.csrf_token);
      setSession(data);
      setView(data.authenticated ? "ready" : "locked");
    }).catch(() => {
      if (!controller.signal.aborted) setView("error");
    });
    return () => controller.abort();
  }, [selected]);

  async function signOut() {
    if (signingOut) return;
    setSigningOut(true);
    try {
      const token = await logoutToken();
      const response = await fetch("/auth/logout/", {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "X-CSRFToken": token },
      });
      if (!response.ok) throw new Error("Logout refused");
      window.location.assign("/");
    } catch {
      setSigningOut(false);
      setView("error");
    }
  }

  if (view !== "ready" || !session) return <WorkspaceGate
    view={view} csrf={csrf} signingOut={signingOut} signOut={signOut}
  />;

  const active = findModule(selected) || modules[0];
  return <div className="workspace">
    <WorkspaceSidebar session={session} selected={selected}
      menuOpen={menuOpen} setMenuOpen={setMenuOpen}/>
    <div className="work-main">
      <header className="topbar">
        <div className="top-left">
          <button className="menu-toggle" type="button" aria-label="Toggle navigation"
            aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>☰</button>
          <span className="crumb">Hosting <span>/</span> {active.name}</span>
        </div>
        <div className="top-right">
          <span className="secure-indicator">● &nbsp; Authenticated</span>
          <button className="logout" type="button" onClick={signOut} disabled={signingOut}>
            {signingOut ? "Signing out…" : "Sign out"}
          </button>
        </div>
      </header>
      <main className="content" id="main-content">
        <div className="page-heading">
          <span className="eyebrow">OCTALVE CLOUD / OPANEL</span>
          <h1>{selected === "overview" ? "Hosting overview" : active.name}</h1>
          <p>{selected === "overview" ? "A secure workspace for your verified hosting service." : active.description}</p>
        </div>
        {selected === "overview" ? <HostingOverview session={session}/> :
          <HostingModule slug={selected} session={session}/>}
        <footer className="page-footer">© Octalve · Secure hosting management · Technical release in Review</footer>
      </main>
    </div>
  </div>;
}
