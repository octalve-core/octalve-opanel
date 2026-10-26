"use client";
import Link from "next/link";
import {consoleDestination} from "@/lib/session";
export type ViewState = "loading" | "ready" | "locked" | "error";
export function WorkspaceGate({view,csrf,signingOut,signOut}: {view:ViewState;csrf:string|null;signingOut:boolean;signOut:()=>Promise<void>}) {
  const consoleUrl = consoleDestination();
  return <main className="gate">
    <div className="gate-brand"><span className="logo-mark">O</span> Octalve <b>OPANEL</b></div>
    {view === "loading" ? <><h1>Verifying hosting access</h1><p>Checking your current Console service entitlement.</p></> :
      view === "locked" ? <><h1>Hosting access is unavailable</h1>
        <p>Open an eligible hosting service in Console. If separately enabled, you may also sign in using your service-specific technical credentials.</p>{process.env.NEXT_PUBLIC_OPANEL_TECHNICAL_LOGIN_ENABLED === "true" && <Link href="/login/">Use technical hosting login</Link>}</> :
        <><h1>Unable to verify access</h1><p>The authorization service is unavailable. Technical actions are blocked.</p></>}
    <div className="gate-actions">
      {consoleUrl && <a className="primary-link" href={consoleUrl}>Return to Octalve Console</a>}
      <button type="button" onClick={() => window.location.reload()}>Retry check</button>
      <button type="button" onClick={signOut} disabled={!csrf || signingOut}>{signingOut ? "Signing out…" : "Sign out"}</button>
    </div>
  </main>;
}
