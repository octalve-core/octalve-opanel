import {useState} from 'react';
import type {Module,Row} from './catalog';
export function ResourceForm({module,domains,busy,submit,initial}:{initial?:Record<string,string>;module:Module;domains:Row[];busy:boolean;submit:(data:Record<string,string>)=>Promise<boolean>}){
 const [values,setValues]=useState<Record<string,string>>(initial||Object.fromEntries(module.fields.map(f=>[f.key,f.value||''])));
 return <form className="practice-form" onSubmit={async event=>{event.preventDefault();if(await submit(values))setValues(Object.fromEntries(module.fields.map(f=>[f.key,f.value||''])));}}>
  {module.fields.map(field=><label key={field.key}>{field.label}
   {field.options||field.domain?<select aria-label={field.label} required value={values[field.key]} onChange={e=>setValues({...values,[field.key]:e.target.value})}>
    {field.domain&&<option value="">Select a domain</option>}
    {(field.domain?domains.map(d=>d.name!):field.options!).map(option=><option key={option} value={option}>{option}</option>)}
   </select>:<input required={!field.optional} maxLength={field.key==='content'?4096:1024} value={values[field.key]} onChange={e=>setValues({...values,[field.key]:e.target.value})}/>}
  </label>)}
  <button className="primary-link" disabled={busy}>{busy?'Saving…':initial?'Save changes':module.collection==='ssl'?'Request certificate':`Add ${module.singular}`}</button>
 </form>;
}
