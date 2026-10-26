export type Field = {key:string; label:string; options?:string[]; value?:string; domain?:boolean; optional?:boolean};
export type Module = {title:string; singular:string; fields:Field[]; action:string; collection:string};
const domain:Field={key:'domain',label:'Domain',domain:true};
export const catalog:Record<string,Module>={
 domains:{title:'Domains',singular:'domain',collection:'domains',action:'domains.add',fields:[{key:'name',label:'Domain name'}]},
 subdomains:{title:'Subdomains',singular:'subdomain',collection:'domains',action:'subdomains.add',fields:[domain,{key:'name',label:'Subdomain label'}]},
 dns:{title:'DNS records',singular:'DNS record',collection:'dns',action:'dns.add',fields:[domain,{key:'name',label:'Record name'},{key:'type',label:'Type',options:['A','AAAA','CNAME','MX','TXT'],value:'A'},{key:'value',label:'Value'},{key:'ttl',label:'TTL (seconds)',value:'300'},{key:'priority',label:'MX priority',value:'10'}]},
 ssl:{title:'SSL certificates',singular:'certificate',collection:'ssl',action:'ssl.add',fields:[domain]},
 websites:{title:'Websites',singular:'website',collection:'websites',action:'websites.add',fields:[domain,{key:'name',label:'Website name'}]},
 files:{title:'Files',singular:'file or folder',collection:'files',action:'files.add',fields:[{key:'name',label:'Relative path'},{key:'kind',label:'Kind',options:['file','directory'],value:'file'},{key:'content',label:'Text content (up to 4 KB)',optional:true}]},
 databases:{title:'Databases',singular:'database',collection:'databases',action:'databases.add',fields:[{key:'name',label:'Database name'},{key:'user',label:'Database user'}]},
 email:{title:'Email accounts',singular:'mailbox',collection:'email',action:'email.add',fields:[domain,{key:'name',label:'Mailbox name'},{key:'quota',label:'Quota (MB)',value:'500'}]},
 backups:{title:'Backups',singular:'backup',collection:'backups',action:'backups.add',fields:[{key:'name',label:'Backup name'}]},
};
export type Row = Record<string,unknown> & {id:string;name?:string;domain?:string;parent?:string|null};
export type State={mode:'simulation';revision:number;activity:{operation:string;revision:number;outcome:string}[]}&Record<string,unknown>;
