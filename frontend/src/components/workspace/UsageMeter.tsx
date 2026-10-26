"use client";
export function UsageMeter({ used, limit }: { used: number; limit: number }) {
  const percent = limit > 0 ? Math.min(100, Math.round(100 * used / limit)) : 0;
  return <div className="meter">
    <div className="meter-values"><strong>{used.toLocaleString()} MB</strong><span>of {limit.toLocaleString()} MB</span></div>
    <progress max={100} value={percent} aria-label="Recorded resource usage" />
    <span className="quiet">{limit > 0 ? Math.round(100 * used / limit) + "% used" : "No configured limit"}</span>
  </div>;
}
