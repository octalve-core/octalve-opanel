"use client";
import Link from "next/link";
import { useState } from "react";

/** Optional separate hosting credentials; does not authenticate against WHM.
 * The independent Django server always rechecks Console service entitlement.
 */
export function TechnicalLoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const enabled = process.env.NEXT_PUBLIC_OPANEL_TECHNICAL_LOGIN_ENABLED === "true";

  async function logIn(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (working || !enabled) return;
    setWorking(true); setError("");
    try {
      const csrfRes = await fetch("/api/csrf/", {credentials:"same-origin",cache:"no-store"});
      if (!csrfRes.ok) throw new Error("Secure login is unavailable.");
      const {csrf_token}: {csrf_token?: string} = await csrfRes.json();
      if (!csrf_token) throw new Error("Secure login is unavailable.");
      const res = await fetch("/auth/technical-login/", {
        method:"POST",credentials:"same-origin",cache:"no-store",
        headers:{"Content-Type":"application/json","X-CSRFToken":csrf_token},
        body:JSON.stringify({username,password}),
      });
      if (!res.ok) throw new Error("Could not verify credentials or hosting authorization.");
      window.location.assign("/");
    } catch (e) {setError(e instanceof Error ? e.message : "Login unavailable.");}
    finally {setWorking(false);setPassword("");}
  }
  return <main className="gate">
    <div className="gate-brand"><span className="logo-mark">O</span> Octalve <b>OPANEL</b></div>
    <h1>Technical hosting sign in</h1>
    {!enabled ? <><p>Independent hosting login has not been enabled. Sign in to Console and open your verified hosting service.</p>
      <Link className="primary-link" href="/">Return to OPanel</Link></> :
      <><p>Use your optional, service-specific OPanel technical credentials. This is not a cPanel or WordPress password.</p>
      <form className="technical-setup" onSubmit={logIn}>
        <label htmlFor="technical-user">Hosting username</label>
        <input id="technical-user" autoComplete="username" required value={username}
          onChange={e=>setUsername(e.target.value)} maxLength={32}/>
        <label htmlFor="technical-password">Hosting password</label>
        <input id="technical-password" type="password" autoComplete="current-password"
          required value={password} onChange={e=>setPassword(e.target.value)}/>
        <button disabled={working || !username || !password} type="submit">
          {working ? "Verifying…" : "Sign in securely"}</button>
        {error && <p role="alert">{error}</p>}
      </form>
      <p>First time here? Sign in through Console and set your technical password in OPanel Settings.</p>
      <Link href="/">Return to Console sign-in guidance</Link></>}
  </main>;
}
