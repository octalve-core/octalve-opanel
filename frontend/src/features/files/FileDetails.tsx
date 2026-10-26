import type {FileEntry} from "@/features/files/file-types";
type Props={entry:FileEntry|null;path:string;connected:boolean};
export function FileDetails({entry,path,connected}:Props) {
  return <section className="fm-details" aria-label="Selected file details">
    <h3>Details</h3>
    {!entry ? <div className="fm-detail-empty">
      <span aria-hidden>▤</span>
      <p>Select a file to see its verified metadata. File content and edits require separately approved operations.</p>
    </div> : <>
      <div className="fm-detail-icon" aria-hidden>{entry.kind==="restricted"?"🔒":entry.kind==="directory"?"📁":"📄"}</div>
      <strong className="fm-detail-name">{entry.name}</strong>
      <dl>
        <div><dt>Type</dt><dd>{entry.kind}</dd></div>
        <div><dt>Location</dt><dd>{path?path+"/":"Home /"}{entry.name}</dd></div>
        <div><dt>Size</dt><dd>{entry.size_bytes===null?"Not reported":`${entry.size_bytes.toLocaleString()} bytes`}</dd></div>
        <div><dt>Source</dt><dd>{connected?"Verified worker":"Example only"}</dd></div>
      </dl>
      <div className="fm-detail-actions">
        <button disabled type="button">Preview content</button>
        <button disabled type="button">Rename</button>
        <button disabled type="button">Delete</button>
      </div>
      <p>Actions stay disabled until scoped read/write permissions, audit and recovery are qualified.</p>
    </>}
  </section>;
}
