"""Replayable accepted evidence, explicit lifecycle, and notification deduplication."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from urllib.parse import urlsplit
from .models import EvidenceEvent, MarketClose
from .scoring import watch_v1_score,score_band,validate_components,validate_weights,DEFAULT_WEIGHTS
from .validation import digest,instant,stamp,number,text,identifier
from .calendars import eligible,consecutive

def validate_config(config):
    if not isinstance(config,dict) or not isinstance(config.get('themes'),dict) or not 1<=len(config['themes'])<=100:raise ValueError('config requires 1–100 themes')
    instant(config['as_of'],'config baseline time')
    validate_weights(config.get('weights',DEFAULT_WEIGHTS))
    for key,spec in config['themes'].items():
        identifier(key);text(spec.get('title'),'theme title',300);text(spec.get('hypothesis'),'hypothesis',6000)
        if spec.get('components') is not None:validate_components(spec['components'])
        for field in ('counterdrivers','fundamental_tests','catalysts','paper_risks','decisions'):
            if not isinstance(spec.get(field,[]),list) or any(not isinstance(x,str) for x in spec.get(field,[])):raise ValueError(field+' must be an array of text')
        if not isinstance(spec.get('expression',{}),dict):raise ValueError('expression must be an object')
        if spec.get('proxy'):
            p=spec['proxy'];number(p.get('anchor_proxy'),'anchor proxy',1e-12);number(p.get('threshold_pct'),'threshold',0.001,100)
            if p.get('anchor_benchmark') is not None:number(p['anchor_benchmark'],'anchor benchmark',1e-12)
            if p.get('hypothesis_direction') not in ('positive','negative'):raise ValueError('proxy direction must be positive or negative')
        number(spec.get('evidence_max_age_days',30),'evidence max age',1,3650)
        number(spec.get('market_max_age_days',5),'market max age',1,365)
    number(config.get('alert_score_change',10),'score change alert threshold',.01,100)
    for calendar in config.get('calendars',{}).values():
        from datetime import date,time
        from zoneinfo import ZoneInfo
        if date.fromisoformat(calendar['valid_from'])>date.fromisoformat(calendar['valid_to']):raise ValueError('calendar date range is reversed')
        ZoneInfo(calendar['timezone']);time.fromisoformat(calendar['close_time'])
        for day in calendar.get('holidays',[]):date.fromisoformat(day)
        for day,clock in calendar.get('early_closes',{}).items():date.fromisoformat(day);time.fromisoformat(clock)
    return config

class AnalysisEngine:
    def __init__(self,config,state=None):
        self.config=deepcopy(validate_config(config))
        self.state=deepcopy(state or {})
        # Old v1 state cannot reproduce accepted updates; require explicit migration.
        if self.state and self.state.get('schema_version')!=2:
            raise ValueError('v1 alert state lacks accepted evidence. Rebuild from archived inputs; do not silently reuse it.')
        self.state.setdefault('schema_version',2)
        for key,default in [('events',{}),('closes',{}),('notifications',[]),('active_breaches',{}),('theme_snapshots',{})]:self.state.setdefault(key,default)

    def analyze(self,evidence,closes=None,as_of=None):
        cutoff=instant(as_of) if isinstance(as_of,str) else as_of or datetime.now(timezone.utc)
        if cutoff.tzinfo is None:raise ValueError('run cutoff needs timezone')
        if instant(self.config['as_of'])>cutoff:raise ValueError('config baseline is after run cutoff')
        if self.state.get('last_as_of') and instant(self.state['last_as_of'])>cutoff:raise ValueError('historical evaluation requires a fresh state, not a rewind of current state')
        work=deepcopy(self.state);notes=[];new_ids=[]
        for event in evidence:
            if event.theme_id not in self.config['themes']:raise ValueError(f'unknown theme: {event.theme_id}')
            if event.component_updates and self.config['themes'][event.theme_id].get('components') is None:raise ValueError('Theme is unscored; define a reproducible baseline before changing components')
            if instant(event.first_known_at or event.observed_at)>cutoff or instant(event.observed_at)>cutoff:raise ValueError(f'{event.id}: future evidence')
            if any(instant(s.published_at)>cutoff or (s.retrieved_at and instant(s.retrieved_at)>cutoff) for s in event.sources):raise ValueError('source is after run cutoff')
            item=event.to_dict();old=work['events'].get(event.id)
            if old:
                if digest(old)!=digest(item):raise ValueError(f'event id {event.id} was reused with different content; create a revision')
                continue
            if event.supersedes and event.supersedes not in work['events']:raise ValueError('superseded evidence id does not exist')
            if event.supersedes and work['events'][event.supersedes]['theme_id']!=event.theme_id:raise ValueError('revision must preserve theme')
            if event.supersedes and instant(work['events'][event.supersedes]['first_known_at'])>instant(event.first_known_at):raise ValueError('revision predates original')
            work['events'][event.id]=item;new_ids.append(event.id)
        for close in closes or []:
            if close.theme_id not in self.config['themes']:raise ValueError(f'unknown market theme: {close.theme_id}')
            if close.session_date>cutoff.date() or (close.close_at and instant(close.close_at)>cutoff):raise ValueError('future market observation')
            key=close.theme_id+':'+close.session_date.isoformat();item=close.to_dict();old=work['closes'].get(key)
            if old and digest(old)!=digest(item):raise ValueError('conflicting session observation; use a separately reviewed corrected input archive')
            work['closes'][key]=item
        notified=set(work['notifications']);alerts=[];results={}
        def alert(kind,theme_id,key,**extra):
            identity=f'{kind}:{theme_id}:{key}'
            if identity not in notified:
                alerts.append({'type':kind,'theme_id':theme_id,**extra});notified.add(identity)
        policy_changed=bool(work.get('config_hash') and work['config_hash']!=digest(self.config))
        for tid,spec in self.config['themes'].items():
            components=deepcopy(spec.get('components'));lifecycle='watch';reason=None
            events=sorted([e for e in work['events'].values() if e['theme_id']==tid],key=lambda e:(instant(e['first_known_at']),e['id']))
            superseded={e['supersedes'] for e in events if e.get('supersedes')}
            current=[e for e in events if e['id'] not in superseded]
            for event in current:
                if components is not None:components.update(event.get('component_updates',{}));validate_components(components)
                meta=event.get('metadata',{})
                if meta.get('lifecycle_action')=='resume':lifecycle='watch';reason=event['summary']
                elif meta.get('lifecycle_action') in ('suspend','archive'):lifecycle={'suspend':'suspended','archive':'archived'}[meta['lifecycle_action']];reason=event['summary']
                if meta.get('invalidation_met'):lifecycle='invalidated';reason=event['summary']
                if event['id'] in new_ids and event['material']:alert('material_evidence',tid,event['id'],event_id=event['id'])
            observations=[MarketClose.from_dict(c) for c in work['closes'].values() if c['theme_id']==tid]
            previous=work['theme_snapshots'].get(tid,{})
            market=self._evaluate_market(tid,spec,observations,cutoff,work)
            if components is not None and market['m_component'] is not None:components['M']=market['m_component']
            elif components is not None and previous.get('components') and not policy_changed and not any(e['id'] in new_ids and ('M' in e.get('component_updates',{}) or 'M' in work['events'].get(e.get('supersedes'),{}).get('component_updates',{})) for e in current):components['M']=previous['components']['M']
            if market.get('invalidates') and lifecycle not in ('invalidated','archived'):
                lifecycle='suspended';reason='Confirmed market setup invalidation: '+market['breach_side']
            elif previous.get('lifecycle')=='suspended' and previous.get('lifecycle_reason','').startswith('Confirmed market'):
                last_resume=max((instant(e['first_known_at']) for e in current if e.get('metadata',{}).get('lifecycle_action')=='resume'),default=None)
                if not last_resume or last_resume<=instant(previous['as_of']):lifecycle='suspended';reason=previous['lifecycle_reason']
            score=watch_v1_score(components,self.config.get('weights')) if components else None
            baseline=watch_v1_score(spec['components'],self.config.get('weights')) if spec.get('components') else None
            prior=previous.get('score',baseline)
            if score is not None and prior is not None and abs(score-prior)>=self.config.get('alert_score_change',10):
                alert('score_change',tid,digest({'previous':previous.get('decision_hash','baseline'),'score':score,'inputs':sorted(new_ids),'market':market.get('latest_session'),'config':digest(self.config)}),**{'from':prior,'to':score})
            if market['new_breach']:alert('confirmed_market_breach',tid,market.get('latest_session','')+str(market['breach_side']),side=market['breach_side'])
            if lifecycle!=previous.get('lifecycle','watch'):alert('lifecycle_change',tid,digest([lifecycle,reason,sorted(new_ids)]),status=lifecycle,reason=reason)
            last_known=max((instant(e['first_known_at']) for e in current),default=None)
            age=(cutoff-last_known).total_seconds()/86400 if last_known else None
            coverage='missing' if not current else 'stale' if age>spec.get('evidence_max_age_days',30) else 'current'
            source_groups={s.get('source_group') or urlsplit(s['url']).hostname for e in current for s in e['sources']}
            quality=None if not current else round(100*(.6*min(len(source_groups)/2,1)+.4*(2**(-age/21))),1)
            changes=[]
            if previous.get('components') and components:
                changes=[{'component':k,'before':previous['components'][k],'after':components[k]} for k in components if components[k]!=previous['components'][k]]
            theme={k:deepcopy(spec.get(k,[] if k in ('counterdrivers','fundamental_tests','catalysts','paper_risks','decisions') else {} if k=='expression' else '')) for k in ('title','hypothesis','counterdrivers','fundamental_tests','catalysts','paper_risks','decisions','expression','invalidation')}
            theme.update({'score':score,'score_band':score_band(score) if score is not None else 'Unscored research','status':lifecycle.title() if lifecycle!='watch' else score_band(score) if score is not None else spec.get('status','Research review'),'lifecycle':lifecycle,'lifecycle_reason':reason,'components':components,'component_changes':changes,'evidence':events,'active_evidence_ids':[e['id'] for e in current],'new_evidence':[e for e in events if e['id'] in new_ids],'market':market,'invalidation_met':lifecycle=='invalidated','evidence_quality':quality,'evidence_age_days':round(age,2) if age is not None else None,'source_groups':len(source_groups),'coverage':coverage,'research_only':True,'market_required':bool(spec.get('proxy')),'as_of':stamp(cutoff),'baseline_as_of':self.config['as_of']})
            theme['decision_hash']=digest({k:theme[k] for k in ('score','components','lifecycle','active_evidence_ids')})
            results[tid]=theme
            work['theme_snapshots'][tid]={k:deepcopy(theme[k]) for k in ('score','components','lifecycle','lifecycle_reason','as_of','decision_hash')}
        work['notifications']=sorted(notified);work['last_as_of']=stamp(cutoff);work['config_hash']=digest(self.config)
        self.state=work
        return {'schema_version':2,'as_of':stamp(cutoff),'config_version':self.config.get('version'),'themes':results,'alerts':alerts,'warnings':notes,'new_evidence_count':len(new_ids),'state':deepcopy(work)}

    def _evaluate_market(self,tid,spec,closes,cutoff,state):
        empty={'m_component':None,'relative_from_anchor_pct':None,'new_breach':False,'breach_side':None,'invalidates':False,'coverage':'missing','issues':[],'latest_session':None}
        proxy=spec.get('proxy')
        if not proxy or not closes:return empty
        calendar=self.config.get('calendars',{}).get(proxy.get('calendar',''))
        good=[];issues=[]
        for close in sorted(closes,key=lambda c:c.session_date):
            problems=eligible(close,calendar,cutoff,'anchor_benchmark' in proxy)
            if problems:issues.append({'session_date':str(close.session_date),'reasons':problems})
            else:good.append(close)
        if not good:return {**empty,'coverage':'unverified','issues':issues}
        latest=good[-1];age=(cutoff-instant(latest.close_at)).total_seconds()/86400
        if age>spec.get('market_max_age_days',5):return {**empty,'coverage':'stale','issues':issues,'latest_session':str(latest.session_date)}
        def relative(c):
            return 100*((c.proxy_close/c.benchmark_close)/(proxy['anchor_proxy']/proxy['anchor_benchmark'])-1) if 'anchor_benchmark' in proxy else 100*(c.proxy_close/proxy['anchor_proxy']-1)
        returns=[]
        for index,c in enumerate(good):
            pr=c.proxy_return_pct;br=c.benchmark_return_pct
            if index and consecutive(good[index-1].session_date,c.session_date,calendar):
                prev=good[index-1];derived=100*(c.proxy_close/prev.proxy_close-1)
                if pr is not None and abs(pr-derived)>.06:raise ValueError('reported proxy return conflicts with validated price history')
                pr=derived
                if 'anchor_benchmark' in proxy:
                    derived_b=100*(c.benchmark_close/prev.benchmark_close-1)
                    if br is not None and abs(br-derived_b)>.06:raise ValueError('reported benchmark return conflicts with history')
                    br=derived_b
            signal=None if pr is None or ('anchor_benchmark' in proxy and br is None) else pr-(br or 0)
            threshold=proxy.get('daily_threshold_pct',1. if 'anchor_benchmark' in proxy else .5)
            returns.append(None if signal is None else signal>=threshold if proxy['hypothesis_direction']=='positive' else signal<=-threshold)
        m=None if returns[-1] is None else .5 if returns[-1] else 0.
        adjacent=len(good)>=2 and consecutive(good[-2].session_date,latest.session_date,calendar)
        if adjacent and returns[-1] and returns[-2]:m=1.
        def side(c,threshold):return 'up' if relative(c)>=threshold else 'down' if relative(c)<=-threshold else None
        sides=[side(c,proxy['threshold_pct']) for c in good[-2:]]
        confirmed=sides[-1] if adjacent and sides[0] is not None and sides[0]==sides[1] else None
        active=state['active_breaches'].get(tid)
        new=bool(confirmed and confirmed!=active)
        if confirmed:state['active_breaches'][tid]=confirmed
        elif sides[-1] is None:state['active_breaches'].pop(tid,None)
        invalid_threshold=proxy.get('invalidation_threshold_pct');invalidates=False
        if invalid_threshold is not None and adjacent:
            bad='down' if proxy['hypothesis_direction']=='positive' else 'up'
            invalidates=all(side(c,invalid_threshold)==bad for c in good[-2:])
        return {'m_component':m,'relative_from_anchor_pct':round(relative(latest),4),'new_breach':new,'breach_side':confirmed,'invalidates':invalidates,'coverage':'current' if m is not None else 'partial','issues':issues,'latest_session':str(latest.session_date),'as_of':latest.close_at,'eligible_sessions':len(good),'return_observations':len([r for r in returns if r is not None])}
