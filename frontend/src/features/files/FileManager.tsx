"use client";
import {useCallback,useEffect,useState} from "react";
import type {PanelSession} from "@/lib/session";
import {
  type BrowserMode,type DirectoryListing,type FileEntry,
  sampleDirectories,normalizeListing,
} from "@/features/files/file-types";
import {FileToolbar} from "./FileToolbar";
import {DirectoryTree} from "./DirectoryTree";
import {FileTable} from "./FileTable";
import {FileDetails} from "./FileDetails";

type Props={session:PanelSession};
type Status="idle"|"loading"|"connected"|"unavailable"|"error";

export function FileManager({session}:Props){
  const [mode,setMode]=useState<BrowserMode>("server");
  const [path,setPath]=useState("");
  const [entries,setEntries]=useState<FileEntry[]>([]);
  const [selected,setSelected]=useState<FileEntry|null>(null);
  const [status,setStatus]=useState<Status>("idle");
  const [revision,setRevision]=useState(0);

  const navigate=useCallback((target:string)=>{
    setPath(target);setSelected(null);
  },[]);
  const chooseMode=useCallback((next:BrowserMode)=>{
    setMode(next);setPath("");setSelected(null);setEntries([]);
  },[]);
  useEffect(()=>{
    if(mode==="example"){
      setEntries(sampleDirectories[path]??[]);
      setStatus("connected");
      return;
    }
    const controller=new AbortController();
    setStatus("loading");setEntries([]);
    (async()=>{
      const response=await fetch(`/api/files/list/?path=${encodeURIComponent(path)}`,{
        method:"GET",cache:"no-store",credentials:"same-origin",
        headers:{"Accept":"application/json"},signal:controller.signal,
      });
      if(!response.ok){
        if(!controller.signal.aborted)setStatus("unavailable");
        return;
      }
      const listing:DirectoryListing=normalizeListing(
        await response.json(),path,session.service_id!);
      if(!controller.signal.aborted){
        setEntries(listing.entries);setStatus("connected");
      }
    })().catch(()=>{
      if(!controller.signal.aborted)setStatus("error");
    });
    return ()=>controller.abort();
  },[mode,path,revision,session.service_id]);

  return <section className="fm-page" aria-label="Hosting file manager">
    <div className="module-toolbar fm-heading">
      <div>
        <span className="preview-tag">OCTALVE OPANEL / FILE MANAGER</span>
        <h2>My hosting files</h2>
        <p>Browse folders, inspect metadata and manage website uploads for this hosting account.</p>
      </div>
    </div>
    <FileToolbar mode={mode} path={path} onNavigate={navigate}
      onMode={chooseMode} onRefresh={()=>setRevision(x=>x+1)} busy={status==="loading"}/>
    {mode==="example" && <div className="fm-preview-banner" role="status">
      <strong>Example preview — not your server</strong>
      <span>These illustrative folders and filenames are provided to show the File Manager interface. No real hosting data is displayed or modified.</span>
    </div>}
    {mode==="server" && status!=="connected" && <div className="fm-connection-note" role="status">
      <strong>{status==="loading"?"Checking your hosting file connection…":"Server folders are not connected yet"}</strong>
      <span>OPanel will only show your actual files after its account-specific worker and read-only authority pass Review acceptance. It will not display invented folders or files.</span>
    </div>}
    <div className="fm-layout">
      <DirectoryTree mode={mode} path={path} onNavigate={navigate}/>
      <div className="fm-center">
        <FileTable path={path}
          entries={mode==="server"&&status!=="connected"?[]:entries}
          selected={selected?.name??null} onSelect={setSelected} onOpen={navigate}/>
      </div>
      <FileDetails entry={selected} path={path} connected={mode==="server"&&status==="connected"}/>
    </div>
    <div className="fm-actions-bottom">
      <div><strong>Website files and publishing</strong>
        <p>Manual upload is available separately from GitHub integration. You can inspect a static ZIP today when the Review inspection feature is enabled; actual hosting publication remains gated.</p>
      </div>
      <a href="/modules/websites/" className="fm-upload-link">Open website upload</a>
    </div>
  </section>;
}
