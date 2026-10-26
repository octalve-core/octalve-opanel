"use client";
import { useState } from "react";

const enabled = process.env.NEXT_PUBLIC_OPANEL_TECHNICAL_LOGIN_ENABLED === "true";

export function TechnicalAccessSettings() {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState("");
  const [username, setUsername] = useState("");
  if (!enabled) return <p>Optional separate hosting credentials are currently disabled. Console single sign-on remains available.</p>;

  async function configure() {
    if (working) return;
    if (password !== confirm) {setMessage("Passwords do not match."); return;}
    setWorking(true); setMessage("");
    try {
      const auth = await fetch("/api/session/", {credentials: "same-origin", cache: "no-store"});
      if (!auth.ok) throw new Error("Your Console hosting session must be verified.");
      const data: { csrf_token?: string } = await auth.json();
      if (!data.csrf_token) throw new Error("Secure session token unavailable.");
      const res = await fetch("/api/technical-access/enroll/", {
        method: "POST", cache: "no-store", credentials: "same-origin",
        headers: {"Content-Type": "application/json", "X-CSRFToken": data.csrf_token},
        body: JSON.stringify({password}),
      });
      if (!res.ok) throw new Error("Password not accepted. Reopen this service through Console and choose a stronger password.");
      const result: {username: string} = await res.json();
      setUsername(result.username); setPassword(""); setConfirm("");
      setMessage("Technical hosting login enabled. Your password was not sent by email.");
    } catch (err) {setMessage(err instanceof Error ? err.message : "Could not update hosting access.");}
    finally {setWorking(false);}
  }
  return <section className="technical-setup">
    <h3>Optional separate OPanel login</h3>
    <p>This is separate from your Console password and is only available for this verified hosting service. Console continues to approve access, even after login.</p>
    {username && <p><strong>Technical username:</strong> <code>{username}</code></p>}
    <label htmlFor="hosting-new-password">Create technical password</label>
    <input id="hosting-new-password" type="password" autoComplete="new-password"
      value={password} onChange={e=>setPassword(e.target.value)} minLength={14} maxLength={128}/>
    <label htmlFor="hosting-confirm-password">Confirm technical password</label>
    <input id="hosting-confirm-password" type="password" autoComplete="new-password"
      value={confirm} onChange={e=>setConfirm(e.target.value)} minLength={14} maxLength={128}/>
    <p className="quiet">Use at least 14 characters with uppercase, lowercase, number and symbol. We never email or show your password again.</p>
    <button type="button" disabled={!password || !confirm || working} onClick={configure}>
      {working ? "Saving…" : "Enable / rotate password"}</button>
    {message && <p role="status">{message}</p>}
  </section>;
}
