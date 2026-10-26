"""Independent SQLite practice state; serializable revision and replay checks."""
import hashlib
import json
import sqlite3
from .resources import empty, change
from .validation import Rejected

class Store:
    def __init__(self,path):
        self.path=path
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS workspaces (id TEXT PRIMARY KEY, state TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS requests (workspace TEXT, id TEXT, digest TEXT, result TEXT, PRIMARY KEY(workspace,id))')
    def read(self,workspace):
        with sqlite3.connect(self.path) as db:
            row=db.execute('SELECT state FROM workspaces WHERE id=?',(workspace,)).fetchone()
        return json.loads(row[0]) if row else empty()
    def apply(self,workspace,revision,request_id,operation,data,confirmed):
        if type(revision) is not int or not isinstance(request_id,str) or not 1<=len(request_id)<=64 or not isinstance(data,dict): raise Rejected('Invalid request.')
        payload=json.dumps([operation,data,confirmed],sort_keys=True,separators=(',',':'))
        if len(payload)>16000: raise Rejected('Request too large.')
        digest=hashlib.sha256(payload.encode()).hexdigest()
        with sqlite3.connect(self.path,timeout=5) as db:
            db.execute('BEGIN IMMEDIATE')
            prior=db.execute('SELECT digest,result FROM requests WHERE workspace=? AND id=?',(workspace,request_id)).fetchone()
            if prior:
                if prior[0]!=digest: raise Rejected('Request ID was already used for another action.')
                return json.loads(db.execute('SELECT state FROM workspaces WHERE id=?',(workspace,)).fetchone()[0])
            row=db.execute('SELECT state FROM workspaces WHERE id=?',(workspace,)).fetchone()
            state=json.loads(row[0]) if row else empty()
            if state['revision']!=revision: raise Rejected('Workspace changed. Refresh before trying again.')
            if state['revision']>=500: raise Rejected('Practice workspace action limit reached.')
            change(state,operation,data,confirmed)
            state['revision']+=1
            state['activity']=([{'operation':operation,'revision':state['revision'],'outcome':'simulated'}]+state['activity'])[:50]
            serialized=json.dumps(state)
            if len(serialized.encode())>1048576: raise Rejected("Practice workspace storage limit reached.")
            db.execute('INSERT OR REPLACE INTO workspaces VALUES (?,?)',(workspace,serialized))
            db.execute('INSERT INTO requests VALUES (?,?,?,?)',(workspace,request_id,digest,str(state["revision"])))
        return state
