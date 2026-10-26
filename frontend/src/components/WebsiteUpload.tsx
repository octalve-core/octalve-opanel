"use client";

import { useState } from "react";

const MAX_ZIP_BYTES = 8 * 1024 * 1024;
const inspectEnabled = process.env.NEXT_PUBLIC_OPANEL_UPLOAD_INSPECT_ENABLED === "true";

type InspectResult = {
  valid: true;
  service_id: number;
  file_count: number;
  total_unpacked_bytes: number;
  archive_sha256: string;
  files: Array<{path: string; size_bytes: number}>;
  published: false;
  deployment_enabled: false;
};

export function WebsiteUpload() {
  const [archive, setArchive] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<InspectResult | null>(null);
  const [error, setError] = useState("");
  function choose(file: File | undefined) {
    setReport(null); setError("");
    if (!file) {setArchive(null); return;}
    if (!file.name.toLowerCase().endsWith(".zip") || file.size === 0 ||
        file.size > MAX_ZIP_BYTES) {
      setArchive(null);
      setError("Choose a nonempty ZIP file smaller than 8 MB.");
      return;
    }
    setArchive(file);
  }
  async function inspect() {
    if (busy || !archive || !inspectEnabled) return;
    setBusy(true); setReport(null); setError("");
    try {
      const csrfRes = await fetch("/api/session/", {credentials:"same-origin",cache:"no-store"});
      if (!csrfRes.ok) throw new Error("Your hosting service needs fresh verification.");
      const session: { csrf_token?: string } = await csrfRes.json();
      if (!session.csrf_token) throw new Error("Secure request token unavailable.");
      const response = await fetch("/api/websites/static/inspect/", {
        method:"POST",credentials:"same-origin",cache:"no-store",
        headers:{"Content-Type":"application/zip","X-CSRFToken":session.csrf_token},
        body:archive,
      });
      if (!response.ok) throw new Error(
        response.status===400 ? "The ZIP contains invalid or unsafe website files." :
        "Website inspection is not available for this account."
      );
      const data: InspectResult = await response.json();
      if (data.valid !== true || data.published !== false ||
          data.deployment_enabled !== false) throw new Error("Unexpected inspection response.");
      setReport(data);
    } catch(e) {
      setError(e instanceof Error ? e.message : "Upload validation failed.");
    } finally {setBusy(false);}
  }
  return <div className="website-upload">
    <section className="module-toolbar">
      <div><span className="preview-tag">STATIC WEBSITE UPLOAD</span>
        <h2>Upload website files</h2>
        <p>Choose a ZIP containing an <code>index.html</code> at its root, plus your CSS, JavaScript, images and fonts.</p>
      </div>
    </section>
    <section className="module-hint">
      <h3>Direct file upload stays part of OPanel</h3>
      <p>Manual upload and GitHub deployment are separate ways to publish. This first implementation inspects an uploaded archive for unsafe paths, symlinks, unsupported executable files and excessive decompression. It does not install or replace a hosted website until the account-scoped publishing worker is approved.</p>
    </section>
    <section className="upload-card">
      <label htmlFor="website-zip"><strong>Website ZIP archive</strong></label>
      <input id="website-zip" type="file" accept=".zip,application/zip"
        onChange={e=>choose(e.target.files?.[0])}/>
      {archive && <p className="quiet">{archive.name} · {(archive.size/1024).toFixed(1)} KB selected</p>}
      <div className="upload-actions">
        <button type="button" disabled={!archive || busy || !inspectEnabled} onClick={inspect}>
          {busy ? "Checking archive…" : "Validate website files"}</button>
        <button type="button" disabled title="Account-scoped deployment is awaiting real provider qualification">Publish website (coming soon)</button>
      </div>
      {!inspectEnabled && <p className="quiet">Server-side upload inspection is not enabled for this Review environment yet. ZIP selection is available; no files are transmitted.</p>}
      {error && <p role="alert" className="upload-error">{error}</p>}
      {report && <div role="status" className="upload-report">
        <h3>Archive validated — not published</h3>
        <p>{report.file_count} static files · {(report.total_unpacked_bytes/1024).toFixed(1)} KB expanded</p>
        <p className="quiet">Inspection SHA-256: <code>{report.archive_sha256.slice(0,16)}…</code></p>
        <ul>{report.files.slice(0,20).map(asset=>
          <li key={asset.path}>{asset.path} <span>{asset.size_bytes.toLocaleString()} bytes</span></li>
        )}</ul>
        {report.files.length>20 && <p className="quiet">Showing the first 20 inspected assets.</p>}
      </div>}
    </section>
    <section className="module-hint">
      <h3>What you can deploy first</h3>
      <p>Prebuilt HTML/CSS/JavaScript websites and exported static frontend bundles. PHP, WordPress, databases and Node.js/Next.js server-rendered applications need their own verified hosting runtime and integration. Simply uploading their source code cannot make them run.</p>
    </section>
  </div>;
}
