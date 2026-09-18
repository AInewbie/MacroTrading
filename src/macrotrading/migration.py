"""Explicit migration of original browser workspace exports."""
from copy import deepcopy
from .portfolio import validate_workspace
from .validation import stamp

def migrate_document(document):
    if document.get('format')!='macrotrading-workspace':raise ValueError('unknown workspace format')
    version=document.get('schemaVersion')
    if version==3:
        w=validate_workspace(document['workspace'])
        for o in w['orders']:
            if o['status']!='Filled':o['status']='Imported'
        return w,[]
    if version not in (1,2):raise ValueError('unsupported workspace version')
    if document.get('executionMode')!='paper-only':raise ValueError('only paper workspaces can be imported')
    old=document['workspace'];p=old['portfolio'];models={'Stock':'equity','ETF':'equity','Bond':'bond','FX':'fx','FX Option':'option','Equity Option':'option','ETF Option':'option','Commodity':'future','Equity Index':'future'}
    instruments=[]
    for i in old['instruments']:
        r={'id':i['id'],'symbol':i['symbol'],'name':i['name'],'model':models[i['assetClass']],'currency':i['currency'],'price':i['price'],'multiplier':i['multiplier'],'lot_size':1,'tick_size':.0001 if i['assetClass'].startswith('FX') else .01,'risk_factor':'fx' if i['assetClass'].startswith('FX') else 'commodity' if i['assetClass']=='Commodity' else 'equity','factor_loadings':{}}
        for k in ('delta','gamma','vega','duration','dv01','expiry','strike'):
            if k in i:r[k]=i[k]
        if 'underlyingPrice' in i:r['underlying_price']=i['underlyingPrice']
        if 'optionType' in i:r['option_type']=i['optionType']
        if r['model']=='bond':r['price_convention']='dirty_per_100'
        instruments.append(r)
    w={'schema_version':3,'mode':'paper','demo':False,'name':p['name'],'base_currency':p['baseCurrency'],'cash':{p['baseCurrency']:p['cash']},'instruments':instruments,'positions':[{'instrument_id':x['instrumentId'],'quantity':x['quantity'],'average_price':x['averagePrice'],**({'target_weight':x['targetWeight']} if x.get('targetWeight') is not None else {})} for x in p['positions']],'fx_rates':[],'orders':[],'fills':[],'realized_pnl':{},'policy':{},'legacy_history':{'orders':old.get('orders',[]),'audit':old.get('audit',[])}}
    warnings=['Legacy fills were not replayed: original cash/cost accounting may need reconciliation. Original orders and audit were retained as legacy_history.','Add current mark timestamps, FX conversions, liquidity, margin and financing inputs before paper execution.','Commodity and index proxies now use futures-style unrealized value, changing NAV from the old notional-based display.']
    return validate_workspace(w),warnings
