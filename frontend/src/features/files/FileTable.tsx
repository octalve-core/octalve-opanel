"use client";
import {joinPath,type FileEntry} from "@/features/files/file-types";

type Props={path:string;entries:FileEntry[];selected:string|null;onSelect:(entry:FileEntry)=>void;onOpen:(path:string)=>void};
function readableSize(bytes:number|null):string {
  if(bytes===null) return "—";
  if(bytes<1024) return `${bytes} B`;
  if(bytes<1024*1024) return `${(bytes/1024).toFixed(1)} KB`;
  return `${(bytes/(1024*1024)).toFixed(1)} MB`;
}
export function FileTable({path,entries,selected,onSelect,onOpen}:Props){
 const ordered=[...entries].sort((a,b)=>
    Number(b.kind==="directory")-Number(a.kind==="directory") ||
    a.name.localeCompare(b.name));
 return <div className="fm-file-area">
   <div className="fm-file-caption"><strong>Files and folders</strong><span>{ordered.length} items</span></div>
   {ordered.length===0 ?
      <div className="fm-empty"><span aria-hidden>📁</span>
        <strong>This folder has no visible files.</strong>
        <span>No entries were returned for this directory.</span>
      </div> :
      <div className="fm-table-wrap">
        <table className="fm-table"><thead><tr>
          <th>Name</th><th>Type</th><th>Size</th><th>Modified</th>
        </tr></thead><tbody>
        {ordered.map(entry=><tr key={entry.name} className={selected===entry.name?"fm-selected-row":""}>
          <td><button type="button" onClick={()=>entry.kind==="directory"?
             onOpen(joinPath(path,entry.name)):onSelect(entry)}>
             <span aria-hidden>{entry.kind==="directory"?"📁":entry.kind==="restricted"?"🔒":"📄"}</span>
             <span>{entry.name}</span>
          </button></td>
          <td>{entry.kind==="directory"?"Folder":entry.kind==="file"?"File":"Restricted"}</td>
          <td>{readableSize(entry.size_bytes)}</td>
          <td><span className="fm-unknown" title="Provider timestamp unavailable">Not available</span></td>
        </tr>)}
        </tbody></table>
      </div>}
 </div>;
}
