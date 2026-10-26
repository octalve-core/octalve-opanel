"use client";
import {sampleDirectories,joinPath,pathParts,type BrowserMode} from "@/features/files/file-types";
type Props={path:string;mode:BrowserMode;onNavigate:(path:string)=>void};
export function DirectoryTree({path,mode,onNavigate}:Props){
  const parts=pathParts(path);
  // Provider tree enumeration would require multiple separately authorized
  // requests; do not fabricate sibling directories for a real customer.
  return <aside className="fm-tree" aria-label="Folder navigation">
    <h3><span aria-hidden>▣</span> Folder tree</h3>
    <button type="button" className={path===""?"fm-tree-selected":""}
      onClick={()=>onNavigate("")}><span aria-hidden>⌂</span> Home</button>
    {mode==="example" ?
      (sampleDirectories[""]??[]).filter(x=>x.kind==="directory").map(root=>{
        const expanded=parts[0]===root.name;
        const children=(sampleDirectories[root.name]??[]).filter(e=>e.kind==="directory");
        return <div key={root.name}>
          <button type="button" className={path===root.name?"fm-tree-selected":""}
            aria-expanded={expanded} onClick={()=>onNavigate(root.name)}>
            <span aria-hidden>{expanded?"▾":"▸"}</span> <span aria-hidden>📁</span> {root.name}
          </button>
          {expanded && children.map(folder=>{
            const childPath=joinPath(root.name,folder.name);
            return <button key={childPath} type="button" className={path===childPath?"fm-tree-selected fm-tree-child":"fm-tree-child"}
              onClick={()=>onNavigate(childPath)}>
              <span aria-hidden>📁</span> {folder.name}
            </button>;
          })}
        </div>;
      }) :
      <p className="fm-tree-note">Verified server folders appear after the account-specific read-only connection is approved. No directory names are assumed.</p>}
  </aside>;
}
