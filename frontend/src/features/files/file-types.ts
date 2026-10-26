export type FileKind = "directory" | "file" | "restricted";
export type FileEntry = {
  name: string;
  kind: FileKind;
  size_bytes: number | null;
};
export type DirectoryListing = {
  connected: true;
  read_only: true;
  source: "verified_account_worker";
  service_id: number;
  path: string;
  entries: FileEntry[];
};
export type BrowserMode = "server" | "example";

export const sampleDirectories: Record<string, FileEntry[]> = {
  "": [
    {name:"public_html",kind:"directory",size_bytes:null},
    {name:"logs",kind:"directory",size_bytes:null},
    {name:"backups",kind:"directory",size_bytes:null},
    {name:"tmp",kind:"directory",size_bytes:null},
  ],
  "public_html": [
    {name:"assets",kind:"directory",size_bytes:null},
    {name:"images",kind:"directory",size_bytes:null},
    {name:"index.html",kind:"file",size_bytes:1324},
    {name:"robots.txt",kind:"file",size_bytes:83},
  ],
  "public_html/assets": [
    {name:"app.js",kind:"file",size_bytes:2145},
    {name:"styles.css",kind:"file",size_bytes:4582},
  ],
  "public_html/images": [
    {name:"logo.webp",kind:"file",size_bytes:8236},
  ],
  "logs": [
    {name:"access.log",kind:"file",size_bytes:16384},
  ],
  "backups": [],
  "tmp": [],
};

export function pathParts(path:string):string[] {
  return path ? path.split("/") : [];
}
export function joinPath(parent:string,child:string):string {
  if (!/^[^/\\\u0000-\u001f\u007f]{1,160}$/.test(child) ||
      child === "." || child === "..") throw new Error("Invalid folder");
  return parent ? `${parent}/${child}` : child;
}
export function parentPath(path:string):string {
  return pathParts(path).slice(0,-1).join("/");
}
export function normalizeListing(data:unknown,expectedPath:string,serviceId:number):DirectoryListing {
  if (!data || typeof data!=="object") throw new Error("Invalid server response");
  const result=data as Record<string,unknown>;
  if (result.connected!==true || result.read_only!==true ||
      result.source!=="verified_account_worker" ||
      result.path!==expectedPath || result.service_id!==serviceId ||
      !Array.isArray(result.entries) || result.entries.length>1000) throw new Error("File authority mismatch");
  const names=new Set<string>();
  const entries:FileEntry[]=result.entries.map((e:unknown)=>{
    if (!e || typeof e!=="object") throw new Error("Invalid file entry");
    const item=e as Record<string,unknown>;
    if (typeof item.name!=="string" ||
        !/^[^/\\\u0000-\u001f\u007f]{1,160}$/.test(item.name) ||
        item.name==="." || item.name===".." ||
        names.has(item.name) ||
        !["directory","file","restricted"].includes(String(item.kind)) ||
        (item.kind==="file" ?
          (!Number.isSafeInteger(item.size_bytes) || Number(item.size_bytes)<0) :
          item.size_bytes!==null)) throw new Error("Invalid account file metadata");
    names.add(item.name);
    return {name:item.name,kind:item.kind as FileKind,size_bytes:item.size_bytes as number|null};
  });
  return {...result,connected:true,read_only:true,source:"verified_account_worker",
    service_id:serviceId,path:expectedPath,entries};
}
