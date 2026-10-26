"use client";
import {pathParts,parentPath,type BrowserMode} from "@/features/files/file-types";
type Props={path:string;mode:BrowserMode;onNavigate:(path:string)=>void;onRefresh:()=>void;onMode:(mode:BrowserMode)=>void;busy:boolean};
export function FileToolbar({path,mode,onNavigate,onRefresh,onMode,busy}:Props){
 const parts=pathParts(path);
 return <div className="fm-toolbar">
   <div className="fm-mode" role="group" aria-label="Directory source">
     <button type="button" aria-pressed={mode==="server"} onClick={()=>onMode("server")}>My server files</button>
     <button type="button" aria-pressed={mode==="example"} onClick={()=>onMode("example")}>Example preview</button>
   </div>
   <div className="fm-breadcrumb" aria-label="Current directory">
     <button type="button" onClick={()=>onNavigate("")}>Home</button>
     {parts.map((part,index)=><span key={index}>
       <span className="fm-separator">/</span>
       <button type="button" onClick={()=>onNavigate(parts.slice(0,index+1).join("/"))}>{part}</button>
     </span>)}
   </div>
   <div className="fm-toolbar-actions">
     <button type="button" disabled={!path} onClick={()=>onNavigate(parentPath(path))} title="Parent folder">↑ Up</button>
     <button type="button" disabled={busy} onClick={onRefresh} title="Reload current directory">↻ Refresh</button>
     <button type="button" disabled title="Requires approved account write authority">+ New folder</button>
   </div>
 </div>;
}
