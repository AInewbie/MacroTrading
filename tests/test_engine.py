import unittest
from copy import deepcopy
from macrotrading.engine import AnalysisEngine
from macrotrading.models import EvidenceEvent,MarketClose
from macrotrading.validation import digest
from helpers import config,event,close,AT

class ResearchTests(unittest.TestCase):
 def run_engine(self,engine,events=(),closes=(),at=AT):
  return engine.analyze([EvidenceEvent.from_dict(e) for e in events],[MarketClose.from_dict(c) for c in closes],at)
 def test_accepted_components_survive_empty_and_duplicate_runs(self):
  engine=AnalysisEngine(config());first=self.run_engine(engine,[event()]);next_=self.run_engine(engine);duplicate=self.run_engine(engine,[event()])
  self.assertEqual(first['themes']['test']['score'],52.5)
  self.assertEqual(first['themes']['test']['components'],next_['themes']['test']['components']);self.assertEqual(duplicate['alerts'],[]);self.assertEqual(duplicate['new_evidence_count'],0)
 def test_invalidation_persists_and_overrides_score(self):
  engine=AnalysisEngine(config());e=event(metadata={'invalidation_met':True},component_updates={'P':1,'F':1,'M':1,'C':1,'X':1,'R':0})
  first=self.run_engine(engine,[e]);next_=self.run_engine(engine)
  self.assertEqual(next_['themes']['test']['score'],100);self.assertEqual(next_['themes']['test']['status'],'Invalidated')
  self.assertEqual(first['themes']['test']['lifecycle'],next_['themes']['test']['lifecycle'])
 def test_explicit_resume_is_a_reviewed_transition(self):
  engine=AnalysisEngine(config());self.run_engine(engine,[event(metadata={'lifecycle_action':'suspend'})])
  resume=event('resume',first_known_at=AT,metadata={'lifecycle_action':'resume'})
  self.assertEqual(self.run_engine(engine,[resume])['themes']['test']['lifecycle'],'watch')
 def test_same_session_duplicate_never_confirms(self):
  engine=AnalysisEngine(config());result=self.run_engine(engine,closes=[close(ret=2),close(ret=2)])
  m=result['themes']['test']['market'];self.assertEqual(m['eligible_sessions'],1);self.assertFalse(m['new_breach']);self.assertEqual(m['m_component'],.5)
 def test_consecutive_closes_confirm_and_alert_without_evidence(self):
  engine=AnalysisEngine(config());self.run_engine(engine)
  result=self.run_engine(engine,closes=[close(ret=2),close('2026-09-18',106)])
  self.assertEqual(result['themes']['test']['components']['M'],1)
  self.assertIn('score_change',[a['type'] for a in result['alerts']]);self.assertIn('confirmed_market_breach',[a['type'] for a in result['alerts']])
  self.assertEqual(self.run_engine(engine)['alerts'],[])
 def test_missing_returns_do_not_lower_component(self):
  engine=AnalysisEngine(config());result=self.run_engine(engine,closes=[close()]);self.assertEqual(result['themes']['test']['market']['coverage'],'partial');self.assertEqual(result['themes']['test']['components']['M'],.5)
 def test_market_invalidation_persists_after_staleness(self):
  engine=AnalysisEngine(config());self.run_engine(engine,closes=[close(price=90,ret=-2),close('2026-09-18',89)])
  result=self.run_engine(engine,at='2026-10-02T21:00:00Z');self.assertEqual(result['themes']['test']['lifecycle'],'suspended');self.assertEqual(result['themes']['test']['market']['coverage'],'stale')
 def test_unverified_calendar_and_future_inputs_do_not_confirm(self):
  engine=AnalysisEngine(config());r=self.run_engine(engine,closes=[close('2026-09-12')]);self.assertEqual(r['themes']['test']['market']['coverage'],'unverified')
 def test_future_inputs_rollback_entire_run(self):
  engine=AnalysisEngine(config());before=digest(engine.state)
  with self.assertRaisesRegex(ValueError,'future'):self.run_engine(engine,[event(),event('future',observed_at='2026-09-20',first_known_at='2026-09-20')])
  self.assertEqual(before,digest(engine.state))
 def test_strict_boolean_nonfinite_and_source_time(self):
  for e in [event(material='false'),event(component_updates={'F':float('nan')}),event(first_known_at='2026-09-16T10:00:00Z')]:
   with self.assertRaises(ValueError):EvidenceEvent.from_dict(e)
  with self.assertRaises(ValueError):MarketClose.from_dict(close(completed='false'))
 def test_conflicting_event_and_close_are_rejected(self):
  engine=AnalysisEngine(config());self.run_engine(engine,[event()],closes=[close()]);before=digest(engine.state)
  with self.assertRaises(ValueError):self.run_engine(engine,[event(summary='Changed content')])
  with self.assertRaises(ValueError):self.run_engine(engine,closes=[close(price=105)])
  self.assertEqual(before,digest(engine.state))
 def test_supersession_removes_old_update_without_deleting_provenance(self):
  engine=AnalysisEngine(config());self.run_engine(engine,[event()]);r=self.run_engine(engine,[event('revision',first_known_at=AT,supersedes='one',component_updates={'F':0})])
  self.assertEqual(r['themes']['test']['components']['F'],0);self.assertEqual(len(r['themes']['test']['evidence']),2);self.assertEqual(r['themes']['test']['active_evidence_ids'],['revision'])
 def test_prices_and_reported_returns_must_agree(self):
  with self.assertRaisesRegex(ValueError,'conflicts'):self.run_engine(AnalysisEngine(config()),closes=[close(),close('2026-09-18',106,ret=10)])
 def test_holiday_and_early_close_rules(self):
  engine=AnalysisEngine(config());r=self.run_engine(engine,closes=[close('2026-09-04',104,2),close('2026-09-08',106)],at='2026-09-08T21:00:00Z');self.assertEqual(r['themes']['test']['market']['eligible_sessions'],2)
  # November 27 is a half-day, closing at 18:00 UTC.
  r=self.run_engine(engine,closes=[close('2026-11-27',107,close_at='2026-11-27T18:00:00Z',benchmark_close_at='2026-11-27T18:00:00Z')],at='2026-11-27T19:00:00Z');self.assertNotEqual(r['themes']['test']['market']['coverage'],'unverified')
 def test_rewind_and_old_state_are_explicit_errors(self):
  engine=AnalysisEngine(config());self.run_engine(engine)
  with self.assertRaisesRegex(ValueError,'rewind'):self.run_engine(engine,at='2026-09-17T21:00:00Z')
  with self.assertRaisesRegex(ValueError,'v1'):AnalysisEngine(config(),{'schema_version':1})
