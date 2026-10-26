'use client';
import Link from 'next/link';
import {useEffect,useState} from 'react';
import {catalog,type State,type Row} from './catalog';
import {ResourceForm} from './ResourceForm';
import {ResourceTable} from './ResourceTable';
export function PracticeWorkspace({slug='domains'}:{slug?:string}){
 const [state,setState]=useState<State|null>(null),[csrf,setCsrf]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false);
 async function refresh(){
  try {const response=await fetch('/api/practice/',{cache:'no-store',credentials:'same-origin'});if(!response.ok)throw Error('Start the local practice server to use this workspace.');const data=await response.json();if(data.state?.mode!=='simulation')throw Error('Unexpected workspace response.');setState(data.state);setCsrf(data.csrf_token);setError('');}
  catch(err){setError(err instanceof Error?err.message:'Unable to load workspace.');}
 }
 useEffect(()=>{void refresh();},[]);
 async function act(operation:string,data:Record<string,string>,confirmed=false){
  if(!state||busy)return false;
  setBusy(true);setError('');setNotice('');
  try{const response=await fetch('/api/practice/',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify({revision:state.revision,request_id:crypto.randomUUID(),operation,data,confirmed})});const result=await response.json();if(!response.ok)throw Error(result.detail||'Unable to apply action.');setState(result.state);setCsrf(result.csrf_token);setNotice('Simulation updated. No live hosting changes were made.');return true;}
  catch(err){setError(err instanceof Error?err.message:'Unable to apply action.');return false;}finally{setBusy(false);}
 }
 const module=catalog[slug];
 const rows=state&&module?(state[module.collection] as Row[]).filter(row=>module.collection!=='domains'||(slug==='subdomains'?!!row.parent:!row.parent)):[];
 return <div className="practice-shell"><aside><Link href="/practice/" className="practice-brand">Octalve <b>OPanel</b></Link><nav aria-label="Practice modules">{Object.entries(catalog).map(([key,item])=><Link aria-current={slug===key?'page':undefined} href={`/practice/${key}/`} key={key}>{item.title}</Link>)}<Link href="/practice/activity/">Activity</Link><Link href="/">Hosting workspace</Link></nav></aside>
 <main><div className="practice-banner"><strong>Local simulation</strong><span>Explore hosting tools without a server. DNS, certificates, mail and backups here are simulated.</span></div>
 <header><p>OPANEL / PRACTICE</p><h1>{module?.title||'Activity'}</h1><button disabled={busy} onClick={refresh}>Refresh workspace</button></header>
 {error&&<p role="alert" className="practice-error">{error}</p>}{notice&&<p role="status">{notice}</p>}
 {state&&module&&<><section><h2>{module.collection==='ssl'?'Request a simulated certificate':`Add ${module.singular}`}</h2><ResourceForm key={slug} module={module} domains={state.domains as Row[]} busy={busy} submit={data=>act(module.action,data)}/></section><section><h2>Your {module.title.toLowerCase()}</h2><ResourceTable domains={state.domains as Row[]} slug={slug} rows={rows} busy={busy} act={act}/></section></>}
 {state&&!module&&<section><h2>Workspace history</h2>{state.activity.length?state.activity.map(event=><p key={event.revision}>#{event.revision} · {event.operation} · {event.outcome}</p>):<p>No changes yet.</p>}</section>}
 <footer>Practice data is isolated from Console services and live hosting accounts.</footer></main></div>;
}
