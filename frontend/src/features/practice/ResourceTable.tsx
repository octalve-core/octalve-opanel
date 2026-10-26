import {useState} from 'react';
import {catalog,type Row} from './catalog';
import {ResourceForm} from './ResourceForm';
export function ResourceTable({slug,rows,busy,act,domains}:{domains:Row[];slug:string;rows:Row[];busy:boolean;act:(operation:string,data:Record<string,string>,confirmed?:boolean)=>Promise<boolean>}){
 const [pending,setPending]=useState<{operation:string;row:Row}|null>(null);
 const [release,setRelease]=useState<Row|null>(null);
 const [label,setLabel]=useState('');
 const [editing,setEditing]=useState<Row|null>(null);
 const removeModule=slug==='subdomains'?'domains':slug;
 return <>
  {!rows.length?<div className="empty-slate">No items yet. Add your first item above.</div>:<div className="practice-table"><table><thead><tr><th>Name</th><th>Details</th><th>Actions</th></tr></thead><tbody>
   {rows.map(row=><tr key={row.id}><td>{row.name||row.domain}</td><td>{Object.entries(row).filter(([key])=>!['id','name','domain','snapshot','content','releases'].includes(key)).map(([key,value])=><div key={key}><span>{key.replaceAll('_',' ')}: </span>{String(value??'—')}</div>)}</td><td className="practice-actions">
    {['dns','files','databases','email'].includes(slug)&&<button disabled={busy} onClick={()=>setEditing(row)}>Edit</button>}
    {slug==='ssl'&&<><button disabled={busy} onClick={()=>act('ssl.verify',{id:row.id})}>Simulate validation</button><button disabled={busy} onClick={()=>act('ssl.renew',{id:row.id})}>Simulate renewal</button></>}
    {slug==='websites'&&<><button disabled={busy} onClick={()=>setRelease(row)}>New release</button><button disabled={busy} onClick={()=>setPending({operation:'websites.rollback',row})}>Roll back</button></>}
    {slug==='backups'&&<button disabled={busy} onClick={()=>setPending({operation:'backups.restore',row})}>Restore</button>}
    <button disabled={busy} onClick={()=>setPending({operation:`${removeModule}.remove`,row})}>Delete</button>
   </td></tr>)}
  </tbody></table></div>}
  {editing&&<div className="practice-confirm" role="dialog" aria-modal="true" aria-label="Edit item"><h2>Edit item</h2><ResourceForm module={catalog[slug]} domains={domains} busy={busy} initial={Object.fromEntries(catalog[slug].fields.map(f=>[f.key,String(f.key==='quota'?editing.quota_mb:f.key==='name'&&slug==='email'?editing.name?.split('@')[0]:editing[f.key]??f.value??'')]))} submit={async data=>{const ok=await act(slug+'.update',{...data,id:editing.id});if(ok)setEditing(null);return ok;}}/><button onClick={()=>setEditing(null)}>Cancel</button></div>}
  {pending&&<div className="practice-confirm" role="dialog" aria-modal="true" aria-label="Confirm action"><h2>Confirm {pending.operation.split('.')[1]}</h2><p>This changes only the practice workspace. {pending.operation==='backups.restore'?'Current simulated resources will be replaced by this snapshot.':''}</p><button disabled={busy} onClick={async()=>{if(await act(pending.operation,{id:pending.row.id},true))setPending(null);}}>Confirm action</button><button onClick={()=>setPending(null)}>Cancel</button></div>}
  {release&&<form className="practice-confirm" onSubmit={async e=>{e.preventDefault();if(await act('websites.release',{id:release.id,label})){setRelease(null);setLabel('');}}}><label>Release label<input required maxLength={64} value={label} onChange={e=>setLabel(e.target.value)}/></label><button disabled={busy}>Save simulated release</button><button type="button" onClick={()=>setRelease(null)}>Cancel</button></form>}
 </>;
}
