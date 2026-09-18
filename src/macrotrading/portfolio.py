"""Explicit price units, base-currency conversion and bounded scenario approximations."""
from __future__ import annotations
from copy import deepcopy
from collections import deque
from datetime import date
from .validation import number,text,identifier,instant,stamp,collection,boolean

MODELS={'equity','bond','fx','option','future'}
DEFAULT_POLICY={'max_order_notional':300000.,'max_gross_exposure':2500000.,'max_net_exposure':1500000.,'max_option_contracts':100.,'max_future_contracts':20.,'max_scenario_loss':250000.,'max_adv_fraction':.05,'max_mark_age_days':5.,'max_fx_age_days':5.,'slippage_bps':2.,'commission_bps':1.,'allow_short':True,'allow_cash_overdraft':False,'require_limit_options':True,'risk_budget':25000.,'holding_days':20.}
SCENARIOS=[{'id':'risk_off','name':'Global risk-off','equity':-.12,'rates_bp':-100.,'fx':-.04,'commodity':-.08,'vol_points':10.},{'id':'inflation','name':'Inflation resurgence','equity':-.07,'rates_bp':125.,'fx':.02,'commodity':.16,'vol_points':6.},{'id':'usd_down','name':'Broad USD decline','equity':.04,'rates_bp':-25.,'fx':.09,'commodity':.10,'vol_points':2.},{'id':'rates_up','name':'Rates +100 bp','equity':0.,'rates_bp':100.,'fx':0.,'commodity':0.,'vol_points':0.}]

def validate_workspace(value):
    if not isinstance(value,dict) or value.get('schema_version')!=3:raise ValueError('workspace schema_version must be 3; use the legacy migration endpoint for v1/v2')
    w=deepcopy(value);w['name']=text(w.get('name'),'portfolio name',160)
    if w.get('mode')!='paper':raise ValueError('only paper mode is supported')
    w['base_currency']=currency(w.get('base_currency'))
    w['demo']=boolean(w.get('demo',False),'demo')
    if not isinstance(w.get('cash'),dict) or len(w['cash'])>100:raise ValueError('cash must map currencies to balances')
    w['cash']={currency(c):number(v,'cash') for c,v in w['cash'].items()}
    ids=set()
    for i in collection(w.get('instruments'),'instruments',1000):
        identifier(i.get('id'));text(i.get('symbol'),'symbol',50);text(i.get('name'),'instrument name',200)
        if i['id'] in ids:raise ValueError('duplicate instrument id')
        ids.add(i['id']);i['currency']=currency(i.get('currency'))
        if i.get('model') not in MODELS:raise ValueError('unknown valuation model')
        number(i.get('price'),'price',0,1e12);number(i.get('multiplier'),'multiplier',1e-12,1e12)
        number(i.get('lot_size',1),'lot size',1e-12,1e9);number(i.get('tick_size',.01),'tick size',1e-12,1e6)
        if i.get('price_at'):instant(i['price_at'],'price_at')
        for field in ('delta','gamma','vega','dv01','duration','underlying_price','adv','borrow_bps','financing_bps','margin_rate','beta'):
            if i.get(field) is not None:number(i[field],field,-1 if field=='delta' else 0,1 if field in ('delta','margin_rate') else 1e12)
        if i['model']=='option':
            if i.get('option_type') not in ('Call','Put'):raise ValueError('option type must be Call or Put')
            date.fromisoformat(i.get('expiry',''));number(i.get('strike'),'strike',0)
        if i['model']=='bond' and i.get('price_convention')!='dirty_per_100':raise ValueError('bond marks must use dirty_per_100; multiplier is face value per contract / 100')
        if i['model']=='future' and i.get('risk_factor') not in ('equity','commodity','fx'):raise ValueError('future requires an explicit risk_factor')
        if 'tradable' in i:boolean(i['tradable'],'tradable')
        if not isinstance(i.get('factor_loadings',{}),dict):raise ValueError('factor loadings must be an object')
        for f,v in i.get('factor_loadings',{}).items():identifier(f);number(v,'factor loading',-10,10)
    positions=set()
    for p in collection(w.get('positions',[]),'positions',5000):
        if p.get('instrument_id') not in ids:raise ValueError('position references unknown instrument')
        if p['instrument_id'] in positions:raise ValueError('duplicate position')
        positions.add(p['instrument_id']);number(p.get('quantity'),'position quantity',-1e12,1e12);number(p.get('average_price'),'average price',0)
        if p.get('target_weight') is not None:number(p['target_weight'],'target weight',-10,10)
        if p.get('theme_id'):identifier(p['theme_id'],'theme id')
    for r in collection(w.get('fx_rates',[]),'FX rates',1000):
        currency(r.get('from'));currency(r.get('to'));number(r.get('rate'),'FX rate',1e-12,1e12);instant(r.get('as_of'),'FX as_of')
    policy={**DEFAULT_POLICY,**w.get('policy',{})}
    if set(policy)!=set(DEFAULT_POLICY):raise ValueError('unknown risk policy setting')
    for k,v in policy.items():
        if isinstance(DEFAULT_POLICY[k],bool):boolean(v,k)
        else:number(v,k,0 if k.endswith('bps') else 1e-12,1 if k=='max_adv_fraction' else 1000 if k in ('slippage_bps','commission_bps') else 1e15)
    w['policy']=policy
    w.setdefault('orders',[]);w.setdefault('fills',[]);w.setdefault('realized_pnl',{})
    for o in collection(w['orders'],'orders',10000):
        identifier(o.get('id'),'order id')
        if o.get('instrument_id') not in ids:raise ValueError('order references missing instrument')
        if o.get('status') not in ('Staged','Filled','Unfilled','Imported','Cancelled','Blocked'):raise ValueError('invalid order status')
        if o.get('side') not in ('Buy','Sell') or o.get('order_type') not in ('Market','Limit'):raise ValueError('unsupported order contract')
        number(o.get('quantity'),'order quantity',1e-12);instant(o.get('created_at'),'order timestamp')
        if o['order_type']=='Limit':number(o.get('limit_price'),'limit price',1e-12)
    if len({o['id'] for o in w['orders']})!=len(w['orders']):raise ValueError('duplicate order ids')
    for f in collection(w['fills'],'fills',10000):
        identifier(f.get('id'),'fill id');identifier(f.get('order_id'),'fill order id');number(f.get('quantity'),'fill quantity',1e-12);number(f.get('price'),'fill price',0);number(f.get('commission',0),'commission',0)
    if len({f['id'] for f in w['fills']})!=len(w['fills']):raise ValueError('duplicate fill ids')
    if not isinstance(w['realized_pnl'],dict):raise ValueError('realized_pnl must map currencies to balances')
    for c,v in w['realized_pnl'].items():currency(c);number(v,'realized P&L')
    return w

def currency(c):
    if not isinstance(c,str) or len(c)!=3 or not c.isalpha() or not c.isascii():raise ValueError('currency must contain three letters')
    return c.upper()

def fx_rate(workspace,ccy,as_of):
    base=workspace['base_currency']
    if ccy==base:return 1.
    edges={};cutoff=instant(as_of)
    for r in workspace.get('fx_rates',[]):
        age=(cutoff-instant(r['as_of'])).total_seconds()/86400
        if age<0 or (not workspace.get('demo') and age>workspace['policy']['max_fx_age_days']):continue
        edges.setdefault(r['from'],[]).append((r['to'],r['rate']));edges.setdefault(r['to'],[]).append((r['from'],1/r['rate']))
    todo=deque([(ccy,1.)]);seen=set()
    while todo:
        here,value=todo.popleft()
        if here==base:return value
        if here in seen:continue
        seen.add(here)
        todo.extend((there,value*rate) for there,rate in edges.get(here,[]) if there not in seen)
    raise ValueError(f'missing or stale FX conversion: {ccy} → {base}')

def position_metrics(p,i):
    q=p['quantity'];m=i['multiplier'];price=i['price'];model=i['model']
    pnl=q*m*(price-p['average_price'])
    mv=pnl if model=='future' else q*m*price
    issues=[];delta=q*m*price;dv01=0.;vega=0.;gamma=0.
    if model=='option':
        missing=[k for k in ('underlying_price','delta','gamma','vega') if i.get(k) is None]
        if missing and q:issues.append('missing option economics: '+', '.join(missing));delta=vega=gamma=None
        elif not missing:
            delta=q*m*i['underlying_price']*i['delta'];vega=q*i['vega'];gamma=.5*q*m*i['gamma']*(i['underlying_price']*.01)**2
    if model=='bond':
        dv01=q*i['dv01'] if i.get('dv01') is not None else mv*i['duration']/10000 if i.get('duration') is not None else None
        if dv01 is None and q:issues.append('bond needs DV01 per contract or duration')
    margin=abs(q*m*(i.get('underlying_price') or price))*i.get('margin_rate',0) if model=='future' or (model=='option' and q<0) else 0.
    if (model=='future' or (model=='option' and q<0)) and i.get('margin_rate') is None and q:issues.append('margin rate missing')
    return {'market_value':mv,'unrealized_pnl':pnl,'delta_exposure':delta,'dv01':dv01,'vega':vega,'gamma_1pct_pnl':gamma,'margin':margin,'issues':issues}

def analyse_portfolio(workspace,as_of=None):
    w=validate_workspace(workspace);as_of=as_of or stamp();cutoff=instant(as_of);byid={i['id']:i for i in w['instruments']};rows=[];issues=[];cash_base=0.
    for c,amount in w['cash'].items():
        try:cash_base+=amount*fx_rate(w,c,as_of)
        except ValueError as exc:issues.append(str(exc));cash_base=None;break
    for p in w['positions']:
        i=byid[p['instrument_id']];metrics=position_metrics(p,i);row={**deepcopy(p),'symbol':i['symbol'],'currency':i['currency'],'model':i['model'],'price':i['price'],**metrics}
        try:conversion=fx_rate(w,i['currency'],as_of)
        except ValueError as exc:row['issues'].append(str(exc));conversion=None
        row['conversion_rate']=conversion
        for k in ('market_value','unrealized_pnl','delta_exposure','dv01','vega','gamma_1pct_pnl','margin'):row[k]=row[k]*conversion if row[k] is not None and conversion is not None else None
        if p['quantity'] and not w.get('demo'):
            if not i.get('price_at'):row['issues'].append('mark timestamp missing')
            else:
                age=(cutoff-instant(i['price_at'])).total_seconds()/86400
                if age<0 or age>w['policy']['max_mark_age_days']:row['issues'].append('mark is future-dated or stale')
            if i['model']=='option' and date.fromisoformat(i['expiry'])<cutoff.date():row['issues'].append('option has expired')
        issues.extend(i['symbol']+': '+x for x in row['issues']);rows.append(row)
    def total(field,absolute=False):
        values=[r[field] for r in rows]
        return None if any(v is None for v in values) else sum(abs(v) if absolute else v for v in values)
    mv=total('market_value');nav=cash_base+mv if cash_base is not None and mv is not None else None
    factors={};themes={}
    for row in rows:
        i=byid[row['instrument_id']];theme=row.get('theme_id') or 'unassigned'
        if row['delta_exposure'] is not None:
            for factor,loading in i.get('factor_loadings',{}).items():
                amount=row['delta_exposure']*loading;factors[factor]=factors.get(factor,0)+amount
                themes.setdefault(theme,{})[factor]=themes.setdefault(theme,{}).get(factor,0)+amount
    realized=None
    try:realized=sum(v*fx_rate(w,c,as_of) for c,v in w.get('realized_pnl',{}).items())
    except ValueError as exc:issues.append(str(exc))
    return {'base_currency':w['base_currency'],'as_of':as_of,'rows':rows,'cash':cash_base,'nav':nav,'gross':total('delta_exposure',True),'net':total('delta_exposure'),'unrealized_pnl':total('unrealized_pnl'),'realized_pnl':realized,'dv01':total('dv01'),'vega':total('vega'),'gamma_1pct_pnl':total('gamma_1pct_pnl'),'margin':total('margin'),'factor_exposures':factors,'theme_factor_exposures':themes,'issues':list(dict.fromkeys(issues)),'complete':not issues,'demo':w['demo']}

def scenario_pnl(p,i,s):
    q=p['quantity'];m=i['multiplier'];model=i['model'];price=i['price']
    if model=='bond':
        metrics=position_metrics(p,i)
        return None if metrics['dv01'] is None else -metrics['dv01']*s.get('rates_bp',0)
    if model=='option':
        if any(i.get(k) is None for k in ('underlying_price','delta','gamma','vega')):return None
        shock=s.get(i.get('risk_factor','equity'),0);ds=i['underlying_price']*shock
        # Vega input is currency / contract / ONE volatility percentage point.
        return q*m*(i['delta']*ds+.5*i['gamma']*ds*ds)+q*i['vega']*s.get('vol_points',0)
    factor='fx' if model=='fx' else i.get('risk_factor','equity')
    return q*m*price*s.get(factor,0)*i.get('beta',1)

def stress_portfolio(workspace,as_of=None,scenarios=None):
    w=validate_workspace(workspace);as_of=as_of or stamp();byid={i['id']:i for i in w['instruments']};results=[]
    for s in scenarios or SCENARIOS:
        rows=[]
        for p in w['positions']:
            i=byid[p['instrument_id']];value=scenario_pnl(p,i,s)
            try:value=value*fx_rate(w,i['currency'],as_of) if value is not None else None
            except ValueError:value=None
            rows.append({'instrument_id':i['id'],'symbol':i['symbol'],'theme_id':p.get('theme_id'),'pnl':value})
        total=None if any(r['pnl'] is None for r in rows) else sum(r['pnl'] for r in rows)
        results.append({**s,'pnl':total,'rows':rows,'method':'Delta/gamma/vega and DV01 approximation; no full repricing'})
    return results

def reconcile(workspace,snapshot):
    if snapshot.get('format')!='macrotrading-broker-snapshot' or snapshot.get('schemaVersion')!=1:raise ValueError('unsupported broker snapshot')
    instant(snapshot['asOf']);account=snapshot['account'];currency(account['baseCurrency']);number(account['cash'],'broker cash')
    model={p['instrument_id']:p['quantity'] for p in workspace['positions']};broker={};ids={i['id'] for i in workspace['instruments']}
    for p in collection(snapshot.get('positions'),'broker positions',5000):
        identifier(p['instrumentId']);number(p['quantity'],'broker quantity')
        if p['instrumentId'] in broker:raise ValueError('duplicate broker position')
        broker[p['instrumentId']]=p['quantity']
    rows=[]
    for key in sorted(set(model)|set(broker)):
        diff=broker.get(key,0)-model.get(key,0)
        status='Unmapped' if key not in ids else 'Missing at broker' if key not in broker else 'Broker only' if key not in model else 'Quantity break' if abs(diff)>1e-9 else 'Matched'
        rows.append({'instrument_id':key,'model':model.get(key,0),'broker':broker.get(key,0),'difference':diff,'status':status})
    comparable=account['baseCurrency']==workspace['base_currency'] and all(c==workspace['base_currency'] or v==0 for c,v in workspace['cash'].items())
    cash=account['cash']-workspace['cash'].get(workspace['base_currency'],0) if comparable else None
    account_id=str(account.get('accountId',''));masked='••••'+account_id[-4:] if len(account_id)>4 else '••••'
    return {'as_of':snapshot['asOf'],'account':masked,'broker':account.get('broker'),'rows':rows,'cash_difference':cash,'cash_comparable':comparable,'pass':comparable and abs(cash)<.01 and all(r['status']=='Matched' for r in rows)}
