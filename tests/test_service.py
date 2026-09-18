import json
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from macrotrading.service import Service
from macrotrading.server import AppServer
from macrotrading.storage import Conflict
from macrotrading.validation import digest
from helpers import ROOT,config,event,workspace,AT
from test_data import SOURCE,FEED

class ServiceTests(unittest.TestCase):
 def setUp(self):
  self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.s=Service(ROOT,self.temp.name)
  with self.s.store.transaction() as db:self.s.store.put(db,'config',config());self.s.store.put(db,'workspace',workspace())
 def test_restart_retains_runs_state_and_audit(self):
  r=self.s.run({'as_of':AT,'evidence':[event()]});again=Service(ROOT,self.temp.name);snap=again.snapshot()
  self.assertEqual(snap['research']['themes']['test']['score'],52.5);self.assertEqual(snap['runs'][0]['id'],r['run_id']);self.assertTrue(snap['audit_integrity']['valid']);self.assertIn('Accepted evidence',again.store.run(r['run_id'])['html'])
 def test_rejected_run_and_stale_write_commit_nothing(self):
  before=self.s.snapshot();bad=event();bad['material']='false'
  with self.assertRaises(ValueError):self.s.run({'as_of':AT,'evidence':[bad]})
  self.assertEqual(len(self.s.snapshot()['runs']),0)
  self.s.save_workspace({'workspace':before['workspace'],'expected_version':before['workspace_version'],'reason':'Test first writer'})
  with self.assertRaises(Conflict):self.s.save_workspace({'workspace':before['workspace'],'expected_version':before['workspace_version'],'reason':'Stale second writer'})
 def test_sources_deduplicate_and_accept_exactly_once(self):
  self.s.save_sources({'sources':[SOURCE],'expected_version':self.s.snapshot()['sources_version']});self.s.refresh_sources(fetcher=lambda s:FEED);self.s.refresh_sources(fetcher=lambda s:FEED)
  snap=self.s.snapshot();self.assertEqual(len(snap['inbox']),1);self.assertIsNone(snap['research']);c=snap['inbox'][0]
  body={'candidate_id':c['id'],'theme_id':'test','kind':'policy_plan','direction':'support','summary':'Reviewed plan','component_updates':{'P':1}}
  self.s.accept_candidate(body)
  with self.assertRaises(ValueError):self.s.accept_candidate(body)
  snap=self.s.snapshot();self.assertEqual(snap['inbox'][0]['status'],'accepted');self.assertEqual(snap['research']['themes']['test']['components']['P'],1)
 def test_backup_restore_rebuilds_report_and_preserves_lifecycle(self):
  self.s.run({'as_of':AT,'evidence':[event(metadata={'invalidation_met':True})]});backup=self.s.backup();version=self.s.snapshot()['workspace_version'];self.s.restore({'backup':backup,'expected_version':version})
  snap=self.s.snapshot();self.assertEqual(snap['research']['themes']['test']['lifecycle'],'invalidated');self.assertIn('run_id',snap['research']);self.assertTrue(self.s.store.run(snap['research']['run_id'])['html']);self.assertTrue(snap['audit_integrity']['valid'])
 def test_empty_backup_clears_current_research_without_deleting_archive(self):
  backup=self.s.backup();self.s.run({'as_of':AT,'evidence':[event()]});self.s.restore({'backup':backup,'expected_version':self.s.snapshot()['workspace_version']});snap=self.s.snapshot();self.assertIsNone(snap['research']);self.assertEqual(len(snap['runs']),1)
 def test_audit_detects_modification(self):
  with self.s.store.transaction() as db:db.execute("UPDATE audit SET action='tampered' WHERE seq=1")
  self.assertFalse(self.s.store.verify_audit()['valid'])
 def test_staged_order_retry_never_duplicates_fill(self):
  # Use demo timestamps here so the test is independent of wall-clock date.
  w=workspace();w['demo']=True;v=self.s.snapshot()['workspace_version'];self.s.save_workspace({'workspace':w,'expected_version':v,'reason':'Deterministic synthetic fixture'})
  v=self.s.snapshot()['workspace_version'];r=self.s.stage({'expected_version':v,'order':{'instrument_id':'asset','side':'Buy','quantity':1,'order_type':'Market'}});v=self.s.snapshot()['workspace_version']
  one=self.s.execute({'expected_version':v,'order_id':r['order']['id']});again=self.s.execute({'expected_version':v,'order_id':r['order']['id']})
  self.assertEqual(one['status'],'Filled');self.assertEqual(again['status'],'Already filled');self.assertEqual(len(self.s.snapshot()['workspace']['fills']),1)

class HttpTests(unittest.TestCase):
 def setUp(self):
  self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.s=Service(ROOT,self.temp.name);self.server=AppServer(('127.0.0.1',0),self.s);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop);self.base='http://127.0.0.1:'+str(self.server.server_address[1])
 def stop(self):self.server.shutdown();self.server.server_close();self.thread.join()
 def request(self,path,body=None,token=True,extra=None):
  headers={'Content-Type':'application/json',**(extra or {})}
  if token:headers['X-MacroTrading-Token']=self.server.csrf
  req=Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
  try:
   with urlopen(req) as r:return r.status,r.read(),r.headers
  except HTTPError as e:return e.code,e.read(),e.headers
 def test_application_assets_and_real_api_round_trip(self):
  for path in ('/','/styles.css','/js/app.js','/api/state','/api/example'):
   status,body,headers=self.request(path);self.assertEqual(status,200,path);self.assertTrue(body);self.assertIn('Content-Security-Policy',headers)
  status,body,_=self.request('/api/run/example',{});self.assertEqual(status,200,body);r=json.loads(body)
  status,body,_=self.request('/api/runs/'+r['run_id']+'/html');self.assertEqual(status,200);self.assertIn(b'Portfolio snapshot',body)
 def test_csrf_cross_origin_host_and_path_guards(self):
  self.assertEqual(self.request('/api/run',{},token=False)[0],403);self.assertEqual(self.request('/api/run',{},extra={'Origin':'https://evil.example'})[0],403)
  self.assertEqual(self.request('/api/state',extra={'Host':'evil.example'})[0],403)
  self.assertEqual(self.request('/%2e%2e/config/demo_workspace.json')[0],404);self.assertEqual(self.request('/api/unknown',{})[0],404)
