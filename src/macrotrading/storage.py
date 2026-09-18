"""Atomic SQLite state, immutable run snapshots and an append-only audit log."""
from __future__ import annotations
from contextlib import contextmanager,closing
from pathlib import Path
import sqlite3
import json
from .validation import canonical,digest,stamp

class Conflict(ValueError):pass

class Store:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with closing(self.connect()) as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS objects(key TEXT PRIMARY KEY,version INTEGER NOT NULL,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,as_of TEXT NOT NULL,created_at TEXT NOT NULL,manifest TEXT NOT NULL,input TEXT NOT NULL,result TEXT NOT NULL,html TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT NOT NULL,action TEXT NOT NULL,payload TEXT NOT NULL,previous_hash TEXT NOT NULL,hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS source_fetches(id INTEGER PRIMARY KEY AUTOINCREMENT,source_id TEXT NOT NULL,at TEXT NOT NULL,status TEXT NOT NULL,content_hash TEXT,raw BLOB,error TEXT,items INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY,source_id TEXT NOT NULL,first_known_at TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending');
            CREATE TABLE IF NOT EXISTS decisions(id TEXT PRIMARY KEY,at TEXT NOT NULL,theme_id TEXT,action TEXT NOT NULL,reason TEXT NOT NULL,payload TEXT NOT NULL);
            ''')
    def connect(self):
        db=sqlite3.connect(self.path,timeout=15);db.row_factory=sqlite3.Row;db.execute('PRAGMA busy_timeout=15000');return db
    @contextmanager
    def transaction(self):
        db=self.connect()
        try:db.execute('BEGIN IMMEDIATE');yield db;db.commit()
        except BaseException:db.rollback();raise
        finally:db.close()
    def get(self,key,default=None,db=None):
        if db is None:
            with closing(self.connect()) as connection:return self.get(key,default,connection)
        row=db.execute('SELECT version,payload FROM objects WHERE key=?',(key,)).fetchone()
        return (json.loads(row['payload']),row['version']) if row else (default,0)
    def put(self,db,key,value,expected=None):
        old,version=self.get(key,None,db)
        if expected is not None and version!=expected:raise Conflict('Workspace changed in another window. Reload before retrying.')
        db.execute('INSERT INTO objects(key,version,payload) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET version=excluded.version,payload=excluded.payload',(key,version+1,canonical(value)))
        return version+1
    def audit(self,db,action,payload):
        previous=db.execute('SELECT hash FROM audit ORDER BY seq DESC LIMIT 1').fetchone();prior=previous['hash'] if previous else ''
        at=stamp();item={'at':at,'action':action,'payload':payload,'previous_hash':prior};h=digest(item)
        db.execute('INSERT INTO audit(at,action,payload,previous_hash,hash) VALUES(?,?,?,?,?)',(at,action,canonical(payload),prior,h));return h
    def audit_rows(self,limit=300):
        with closing(self.connect()) as db:return [{**dict(r),'payload':json.loads(r['payload'])} for r in db.execute('SELECT * FROM audit ORDER BY seq DESC LIMIT ?',(limit,))]
    def verify_audit(self):
        previous='';count=0
        with closing(self.connect()) as db:
            for r in db.execute('SELECT * FROM audit ORDER BY seq'):
                item={'at':r['at'],'action':r['action'],'payload':json.loads(r['payload']),'previous_hash':r['previous_hash']}
                if r['previous_hash']!=previous or digest(item)!=r['hash']:return {'valid':False,'row':r['seq']}
                previous=r['hash'];count+=1
        return {'valid':True,'rows':count,'head':previous}
    def runs(self):
        with closing(self.connect()) as db:return [{**dict(r),'manifest':json.loads(r['manifest'])} for r in db.execute('SELECT id,as_of,created_at,manifest FROM runs ORDER BY created_at DESC LIMIT 200')]
    def run(self,id):
        with closing(self.connect()) as db:
            r=db.execute('SELECT * FROM runs WHERE id=?',(id,)).fetchone()
            if r is None:raise ValueError('unknown run')
            return {**dict(r),**{k:json.loads(r[k]) for k in ('manifest','input','result')}}
    def inbox(self):
        with closing(self.connect()) as db:return [{**dict(r),'payload':json.loads(r['payload'])} for r in db.execute("SELECT * FROM inbox ORDER BY first_known_at DESC LIMIT 1000")]
    def source_health(self):
        with closing(self.connect()) as db:return [dict(r) for r in db.execute('SELECT id,source_id,at,status,content_hash,error,items FROM source_fetches WHERE id IN (SELECT MAX(id) FROM source_fetches GROUP BY source_id)')]
    def decisions(self):
        with closing(self.connect()) as db:return [{**dict(r),'payload':json.loads(r['payload'])} for r in db.execute('SELECT * FROM decisions ORDER BY at DESC LIMIT 500')]
