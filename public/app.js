import { demoBrokerSnapshot, demoInstruments, demoPortfolio, defaultPolicy, demoScenarios, demoThemeEvidence, demoThemeDefinitions, defaultThemeSettings } from '../src/data/demo.js';
import { instrumentLabel, validateInstrument } from '../src/domain/instruments.js';
import { createOrder } from '../src/domain/orders.js';
import { analysePortfolio, rebalanceOrders } from '../src/engine/portfolio.js';
import { preTradeChecks, stressPortfolio } from '../src/engine/risk.js';
import { PaperBroker } from '../src/adapters/paperBroker.js';
import { createWorkspaceDocument, MAX_WORKSPACE_FILE_BYTES, parseWorkspaceDocument, validateWorkspaceState } from '../src/domain/workspace.js';
import { MAX_BROKER_SNAPSHOT_BYTES, maskAccountId, parseBrokerSnapshot, reconcilePortfolio } from '../src/domain/reconciliation.js';
import { detectThemes } from '../src/engine/themes.js';
import { normaliseThemeSettings } from '../src/domain/themes.js';
import { renderEvidenceDetail, renderThemeLab } from '../src/ui/themeView.js';

const STORAGE_KEY = 'macrotrading.workspace.v1';
const views = [
  ['overview','Overview'],['themes','Theme lab'],['positions','Positions'],['reconciliation','Broker reconciliation'],['universe','Instrument universe'],
  ['risk','Risk & scenarios'],['orders','Orders'],['controls','Execution controls'],['audit','Audit trail'],
];
const money = new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0});
const number = new Intl.NumberFormat('en-US',{maximumFractionDigits:2});
const signed = (value, formatter=money) => `<span class="${value>0?'positive':value<0?'negative':''}">${value>0?'+':''}${formatter.format(value)}</span>`;
const escapeHtml = (value) => String(value).replace(/[&<>"']/g,(char)=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const deepCopy = (value) => JSON.parse(JSON.stringify(value));

let state = load();
let currentView = location.hash.slice(1) || 'overview';
const broker = new PaperBroker();

function freshState(){return {portfolio:deepCopy(demoPortfolio),instruments:deepCopy(demoInstruments),policy:deepCopy(defaultPolicy),orders:[],audit:[{at:new Date().toISOString(),event:'Workspace initialized',detail:'Synthetic data · paper execution only',actor:'System'}],reconciliation:null,themeResearch:{evidence:deepCopy(demoThemeEvidence),themes:[],settings:deepCopy(defaultThemeSettings),lastRun:null}};}
function load(){try{const stored=JSON.parse(localStorage.getItem(STORAGE_KEY));return stored?validateWorkspaceState(stored):freshState();}catch{return freshState();}}
function save(){localStorage.setItem(STORAGE_KEY,JSON.stringify(state));}
function audit(event,detail,actor='User'){state.audit.unshift({at:new Date().toISOString(),event,detail,actor});}
function notify(message,error=false){const el=document.querySelector('#notice');el.textContent=message;el.className=`notice${error?' error':''}`;el.hidden=false;setTimeout(()=>el.hidden=true,4500);}
function analysis(){return analysePortfolio(state.portfolio,state.instruments);}
function instrument(id){return state.instruments.find((item)=>item.id===id);}

function renderNav(){document.querySelector('#nav').innerHTML=views.map(([id,label])=>`<button class="nav-link ${currentView===id?'active':''}" data-view="${id}">${label}</button>`).join('');}
function metrics(a){return `<div class="metric-grid">
  ${metric('Portfolio NAV',money.format(a.nav),'Market value + cash')}${metric('Gross delta',money.format(a.gross),'Absolute exposure')}
  ${metric('Net delta',money.format(a.net),'Directional exposure')}${metric('Unrealized P&L',signed(a.pnl),'Synthetic marks')}
  ${metric('Rates DV01',signed(a.dv01,number),'USD per 1 bp')}${metric('Option vega',signed(a.vega,number),'Model-input units')}
  </div>`;}
function metric(label,value,note){return `<article class="metric"><span>${label}</span><b>${value}</b><small>${note}</small></article>`;}
function positionsTable(rows,compact=false){return `<div class="table-wrap"><table><thead><tr><th>Instrument</th><th>Class</th><th>Qty</th><th>Price</th><th>Market value</th><th>Delta exposure</th><th>P&amp;L</th>${compact?'':'<th>Target</th>'}</tr></thead><tbody>${rows.map(row=>`<tr><td><span class="symbol">${escapeHtml(instrumentLabel(row.instrument))}</span><br><small>${escapeHtml(row.instrument.name)}</small></td><td><span class="asset-badge">${row.instrument.assetClass}</span></td><td>${number.format(row.position.quantity)}</td><td>${number.format(row.instrument.price)}</td><td>${signed(row.marketValue)}</td><td>${signed(row.deltaAdjusted)}</td><td>${signed(row.pnl)}</td>${compact?'':`<td>${Number.isFinite(row.position.targetWeight)?number.format(row.position.targetWeight*100)+'%':'—'}</td>`}</tr>`).join('')}</tbody></table></div>`;}
function exposureBars(a){const max=Math.max(...Object.values(a.byClass).map(Math.abs),1);return `<div class="exposure-list">${Object.entries(a.byClass).map(([key,value])=>`<div class="exposure-row"><span>${key}</span><div class="bar"><span class="${value<0?'short':''}" style="width:${Math.abs(value)/max*100}%"></span></div><b>${money.format(value)}</b></div>`).join('')}</div>`;}

function renderOverview(){const a=analysis();return `${metrics(a)}<div class="layout"><article class="card"><div class="card-head"><div><h2>Current positions</h2><p>Cross-asset positions normalized to USD risk views.</p></div><button class="button ghost" data-ticket>New order</button></div>${positionsTable(a.rows,true)}</article><article class="card"><div class="card-head"><div><h2>Delta exposure</h2><p>Net by requested asset class.</p></div></div>${exposureBars(a)}</article></div>`;}
function renderPositions(){const a=analysis();return `<div class="section-head"><div><h2>${state.portfolio.name}</h2><p>${a.rows.length} positions · ${state.portfolio.baseCurrency} reporting currency</p></div><button class="button primary" data-ticket>New order</button></div><article class="card">${positionsTable(a.rows)}</article>`;}
function renderThemes(){return renderThemeLab({research:state.themeResearch,instruments:state.instruments,escapeHtml,number});}
function renderReconciliation(){
  if(!state.reconciliation)return `<div class="section-head"><div><h2>Broker reconciliation</h2><p>Compare a read-only account snapshot with the local portfolio. No holdings or orders will be changed.</p></div></div><article class="card empty-state"><span class="asset-badge">Local · read only</span><h2>No broker snapshot loaded</h2><p>Import a broker-neutral JSON snapshot or load the synthetic example to inspect the workflow safely.</p><div class="actions"><button class="button primary" data-import-broker>Import snapshot</button><button class="button ghost" data-demo-broker>Load synthetic snapshot</button></div><p class="safety-note">Files are processed in this browser. Credentials, API keys and live account connections are not supported.</p></article>`;
  const result=reconcilePortfolio(state.portfolio,state.instruments,state.reconciliation), account=result.snapshot.account;
  return `<div class="section-head"><div><h2>Broker reconciliation</h2><p>Read-only comparison as of ${new Date(result.snapshot.asOf).toLocaleString()}.</p></div><div class="actions"><button class="button ghost" data-import-broker>Replace snapshot</button><button class="button danger" data-clear-broker>Clear</button></div></div><div class="metric-grid reconciliation-metrics">${metric('Broker',escapeHtml(account.broker),`Account ${escapeHtml(maskAccountId(account.accountId))}`)}${metric('Position breaks',number.format(result.positionBreaks),`${result.matchedPositions} matched`)}${metric('Cash difference',signed(result.cashDifference),`${money.format(account.cash)} at broker`)}${metric('Overall status',result.pass?'<span class="positive">Matched</span>':'<span class="negative">Review</span>',`${account.baseCurrency} broker vs ${state.portfolio.baseCurrency} model`)}</div><article class="card reconciliation-card"><div class="card-head"><div><h2>Position comparison</h2><p>Broker quantity minus model quantity. Breaks are informational and never generate orders.</p></div><span class="status-badge ${result.pass?'pass':'review'}">${result.pass?'Reconciled':'Review required'}</span></div><div class="table-wrap"><table><thead><tr><th>Instrument</th><th>Class</th><th>Model qty</th><th>Broker qty</th><th>Difference</th><th>Status</th></tr></thead><tbody>${result.rows.map(row=>`<tr><td><span class="symbol">${escapeHtml(row.symbol)}</span><br><small>${escapeHtml(row.name)}</small></td><td><span class="asset-badge">${escapeHtml(row.assetClass)}</span></td><td>${number.format(row.modelQuantity)}</td><td>${number.format(row.brokerQuantity)}</td><td>${signed(row.difference,number)}</td><td><span class="status-badge ${row.status==='Matched'?'pass':'review'}">${escapeHtml(row.status)}</span></td></tr>`).join('')}</tbody></table></div></article><p class="safety-note standalone-note">Reconciliation is read-only. Fix mappings and investigate breaks at the source; this release does not alter positions, cash, targets or staged orders.</p>`;
}
function renderUniverse(){return `<div class="section-head"><div><h2>Instrument universe</h2><p>Unified schema across cash, derivative and fund exposures.</p></div></div><div class="universe-grid">${state.instruments.map(item=>`<article class="card"><div class="card-head"><div><h2>${escapeHtml(instrumentLabel(item))}</h2><p>${escapeHtml(item.name)}</p></div><span class="asset-badge">${item.assetClass}</span></div><div class="policy-list"><div class="policy-item"><span>Price</span><b>${number.format(item.price)} ${item.currency}</b></div><div class="policy-item"><span>Multiplier</span><b>${number.format(item.multiplier)}</b></div>${item.delta!=null?`<div class="policy-item"><span>Delta</span><b>${number.format(item.delta)}</b></div><div class="policy-item"><span>Vega</span><b>${number.format(item.vega)}</b></div>`:''}${item.duration?`<div class="policy-item"><span>Duration</span><b>${number.format(item.duration)}</b></div><div class="policy-item"><span>DV01</span><b>${number.format(item.dv01)}</b></div>`:''}</div><div class="actions" style="margin-top:14px"><button class="button ghost" data-ticket="${item.id}">Trade</button></div></article>`).join('')}</div>`;}
function renderRisk(){const a=analysis();return `${metrics(a)}<div class="section-head" style="margin-top:23px"><div><h2>Deterministic stress scenarios</h2><p>Transparent first-order approximations; not a full revaluation engine.</p></div></div><div class="scenario-grid">${demoScenarios.map(s=>{const rows=stressPortfolio(state.portfolio,state.instruments,s),total=rows.reduce((v,r)=>v+r.pnl,0);return `<article class="card"><div class="card-head"><div><h2>${s.name}</h2><p>Equity ${number.format(s.shocks.equity*100)}% · Rates ${number.format(s.shocks.rates*10000)} bp · FX ${number.format(s.shocks.fx*100)}%</p></div></div><div class="scenario-result">${signed(total)}</div><div class="scenario-details">${rows.sort((x,y)=>Math.abs(y.pnl)-Math.abs(x.pnl)).slice(0,4).map(r=>`<span>${r.symbol} · ${signed(r.pnl)}</span>`).join('')}</div></article>`}).join('')}</div>`;}
function renderOrders(){return `<div class="section-head"><div><h2>Staged and filled orders</h2><p>All orders pass local pre-trade controls before paper submission.</p></div><button class="button primary" data-ticket>New order</button></div><article class="card">${state.orders.length?`<div class="table-wrap"><table><thead><tr><th>Order</th><th>Class</th><th>Type</th><th>Quantity</th><th>Notional</th><th>Checks</th><th>Status</th><th>Action</th></tr></thead><tbody>${state.orders.map(order=>{const imported=order.status==='Imported';return `<tr><td><b>${order.side} ${escapeHtml(order.symbol)}</b><br><small>${new Date(order.createdAt).toLocaleString()}</small></td><td>${order.assetClass}</td><td>${order.orderType}${order.limitPrice?' @ '+number.format(order.limitPrice):''}</td><td>${number.format(order.quantity)}</td><td>${money.format(order.risk?.notional||0)}</td><td><span class="status-badge ${imported?'review':order.risk?.pass?'pass':'fail'}">${imported?'Fresh checks required':order.risk?.pass?'Passed':'Blocked'}</span></td><td>${order.fill?.status||order.status}</td><td>${order.status==='Staged'&&order.risk?.pass?`<button class="button primary" data-submit="${order.id}">Paper execute</button>`:'—'}</td></tr>`;}).join('')}</tbody></table></div>`:'<div class="empty">No orders yet. Stage a rebalance or open the trade ticket.</div>'}</article>`;}
function renderControls(){const p=state.policy;return `<div class="section-head"><div><h2>Execution controls</h2><p>Version 1 · enforced before staging and again before submission.</p></div></div><div class="layout"><article class="card"><div class="card-head"><div><h2>Portfolio limits</h2><p>Local policy values for this prototype.</p></div></div><div class="policy-list">${[['Maximum order notional',money.format(p.maxOrderNotional)],['Maximum gross exposure',money.format(p.maxGrossExposure)],['Maximum net exposure',money.format(p.maxNetExposure)],['Option contract limit',number.format(p.maxOptionContracts)],['Commodity contract limit',number.format(p.maxCommodityContracts)],['Options limit-order rule',p.requireLimitForOptions?'Required':'Not required']].map(([a,b])=>`<div class="policy-item"><span>${a}</span><b>${b}</b></div>`).join('')}</div></article><article class="card"><div class="card-head"><div><h2>Broker routes</h2><p>Live routes are intentionally unavailable.</p></div></div><div class="policy-list"><div class="policy-item"><span>Paper broker</span><b class="positive">Enabled</b></div><div class="policy-item"><span>IBKR</span><b class="negative">Not configured</b></div><div class="policy-item"><span>Alpaca</span><b class="negative">Not configured</b></div><div class="policy-item"><span>Live order submission</span><b class="negative">Disabled</b></div></div></article></div><article class="card workspace-card"><div class="card-head"><div><h2>Workspace portability</h2><p>Download or restore a schema-versioned JSON snapshot. Imports are validated before this browser is changed.</p></div><span class="asset-badge">Paper only</span></div><div class="actions"><button class="button primary" data-export-workspace>Export workspace</button><button class="button ghost" data-import-workspace>Import workspace</button></div><p class="safety-note">Imported unfilled orders require fresh staging and controls; they cannot be submitted directly. No credentials are included.</p></article>`;}
function renderAudit(){return `<div class="section-head"><div><h2>Audit trail</h2><p>Local append-only activity view for the current workspace.</p></div></div><article class="card">${state.audit.map(row=>`<div class="audit-row"><span>${new Date(row.at).toLocaleString()}</span><div><b>${escapeHtml(row.event)}</b><p>${escapeHtml(row.detail)}</p></div><span>${escapeHtml(row.actor)}</span></div>`).join('')}</article>`;}

const renderers={overview:renderOverview,themes:renderThemes,positions:renderPositions,reconciliation:renderReconciliation,universe:renderUniverse,risk:renderRisk,orders:renderOrders,controls:renderControls,audit:renderAudit};
function render(){if(!renderers[currentView])currentView='overview';renderNav();document.querySelector('#page-title').textContent=views.find(([id])=>id===currentView)?.[1]||'Portfolio overview';document.querySelector('#app').innerHTML=renderers[currentView]();document.querySelectorAll('[data-ticket]').forEach(button=>button.addEventListener('click',()=>openTicket(button.dataset.ticket)));document.querySelectorAll('[data-submit]').forEach(button=>button.addEventListener('click',()=>submitOrder(button.dataset.submit)));document.querySelector('[data-export-workspace]')?.addEventListener('click',exportWorkspace);document.querySelector('[data-import-workspace]')?.addEventListener('click',()=>document.querySelector('#workspace-file').click());document.querySelector('[data-import-broker]')?.addEventListener('click',()=>document.querySelector('#broker-snapshot-file').click());document.querySelector('[data-demo-broker]')?.addEventListener('click',loadDemoBrokerSnapshot);document.querySelector('[data-clear-broker]')?.addEventListener('click',clearBrokerSnapshot);document.querySelector('[data-run-themes]')?.addEventListener('click',runThemeDetection);document.querySelector('#theme-settings-form')?.addEventListener('submit',saveThemeSettings);document.querySelectorAll('[data-evidence]').forEach(button=>button.addEventListener('click',()=>openEvidence(button.dataset.evidence)));}

function runThemeDetection(){
  const now=new Date();
  state.themeResearch.themes=detectThemes(state.themeResearch.evidence,demoThemeDefinitions,state.instruments,state.themeResearch.settings,now);
  state.themeResearch.lastRun=now.toISOString();
  audit('Theme research refreshed',`${state.themeResearch.themes.length} candidates · ${state.themeResearch.evidence.length} synthetic evidence records`,'Theme engine');
  save();render();notify('Synthetic theme candidates refreshed. No order or target was created.');
}
function saveThemeSettings(event){
  event.preventDefault();
  const data=new FormData(event.currentTarget);
  try{
    state.themeResearch.settings=normaliseThemeSettings({halfLifeDays:Number(data.get('halfLifeDays')),minimumSources:Number(data.get('minimumSources')),weights:{reliability:Number(data.get('weight-reliability')),freshness:Number(data.get('weight-freshness')),novelty:Number(data.get('weight-novelty')),breadth:Number(data.get('weight-breadth')),catalyst:Number(data.get('weight-catalyst'))}});
    audit('Theme scoring policy changed',`Half-life ${state.themeResearch.settings.halfLifeDays} days · minimum ${state.themeResearch.settings.minimumSources} sources`);
    save();render();notify('Theme scoring policy saved. Re-run detection to refresh scores.');
  }catch(error){notify(error.message,true);}
}
function openEvidence(id){
  const item=state.themeResearch.evidence.find((evidence)=>evidence.id===id);
  document.querySelector('#evidence-content').innerHTML=renderEvidenceDetail(item,escapeHtml,number);
  document.querySelector('#evidence-dialog').showModal();
}

function exportWorkspace(){
  const payload=createWorkspaceDocument(state), blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}), url=URL.createObjectURL(blob), link=document.createElement('a');
  link.href=url;link.download=`macrotrading-${state.portfolio.id}-${new Date().toISOString().slice(0,10)}.json`;link.click();URL.revokeObjectURL(url);
  audit('Workspace exported',`${state.portfolio.positions.length} positions · ${state.instruments.length} instruments`);save();render();notify('Workspace exported. The JSON contains no credentials.');
}

async function importWorkspace(file){
  if(!file)return;
  try{
    if(file.size>MAX_WORKSPACE_FILE_BYTES)throw new Error('Workspace import rejected: file exceeds the 2 MB limit.');
    const parsed=parseWorkspaceDocument(await file.text());
    if(!confirm(`Replace this browser workspace with “${parsed.state.portfolio.name}”? Imported unfilled orders will require fresh staging.`))return;
    state=parsed.state;
    audit('Workspace imported',`${state.portfolio.positions.length} positions · ${state.instruments.length} instruments · ${parsed.demotedOrders} unfilled orders require fresh staging`);
    save();currentView='overview';location.hash='overview';render();notify('Workspace imported and validated. No order was transmitted.');
  }catch(error){notify(error.message||'Workspace import failed.',true);}
  finally{document.querySelector('#workspace-file').value='';}
}
function loadDemoBrokerSnapshot(){state.reconciliation=parseBrokerSnapshot(deepCopy(demoBrokerSnapshot));audit('Broker snapshot loaded','Synthetic Broker · read-only reconciliation','System');save();render();notify('Synthetic broker snapshot loaded. Portfolio data was not changed.');}
function clearBrokerSnapshot(){state.reconciliation=null;audit('Broker snapshot cleared','Read-only reconciliation data removed');save();render();notify('Broker snapshot cleared. Portfolio data was not changed.');}
async function importBrokerSnapshot(file){
  if(!file)return;
  try{
    if(file.size>MAX_BROKER_SNAPSHOT_BYTES)throw new Error('Broker snapshot rejected: file exceeds the 1 MB limit.');
    const snapshot=parseBrokerSnapshot(await file.text());
    state.reconciliation=snapshot;
    audit('Broker snapshot imported',`${snapshot.account.broker} · ${snapshot.positions.length} positions · read only`);
    save();currentView='reconciliation';location.hash='reconciliation';render();notify('Broker snapshot validated and compared. Portfolio data was not changed.');
  }catch(error){notify(error.message||'Broker snapshot import failed.',true);}
  finally{document.querySelector('#broker-snapshot-file').value='';}
}
function openTicket(id){const select=document.querySelector('#ticket-instrument');select.innerHTML=state.instruments.map(i=>`<option value="${i.id}" ${i.id===id?'selected':''}>${escapeHtml(instrumentLabel(i))} · ${i.assetClass}</option>`).join('');syncTicket();document.querySelector('#ticket-dialog').showModal();}
function syncTicket(){const item=instrument(document.querySelector('#ticket-instrument').value);document.querySelector('#ticket-limit').value=item?.price||'';document.querySelector('#ticket-preview').innerHTML=item?`<b>${escapeHtml(item.name)}</b><br>${item.assetClass} · ${item.currency} · multiplier ${number.format(item.multiplier)}<br>Live execution unavailable; staged orders route only to paper.`:'';}
function stageInput(input){const item=instrument(input.instrumentId);const order=createOrder(input,item);order.risk=preTradeChecks(order,item,state.portfolio,state.instruments,state.policy);state.orders.unshift(order);audit(order.risk.pass?'Order staged':'Order blocked',`${order.side} ${order.quantity} ${order.symbol} · ${money.format(order.risk.notional)}`);save();return order;}
async function submitOrder(id){const order=state.orders.find(item=>item.id===id);const item=instrument(order.instrumentId);order.risk=preTradeChecks(order,item,state.portfolio,state.instruments,state.policy);if(!order.risk.pass)return notify('Order is blocked by current pre-trade controls.',true);order.fill=await broker.submit(order,item);order.status='Filled';const signedQuantity=order.side==='Buy'?order.quantity:-order.quantity;let position=state.portfolio.positions.find(p=>p.instrumentId===item.id);if(!position){position={instrumentId:item.id,quantity:0,averagePrice:order.fill.averageFillPrice};state.portfolio.positions.push(position);}position.quantity+=signedQuantity;audit('Paper order filled',`${order.side} ${order.quantity} ${order.symbol} @ ${order.fill.averageFillPrice}`,'Paper broker');save();render();notify('Paper order filled. No live brokerage instruction was sent.');}
function stageRebalance(){const candidates=rebalanceOrders(state.portfolio,state.instruments);if(!candidates.length)return notify('Portfolio already matches its rounded target quantities.');let passed=0;candidates.forEach(candidate=>{if(stageInput(candidate).risk.pass)passed++;});render();notify(`${candidates.length} rebalance orders staged; ${passed} passed all controls.`);}

document.querySelector('#nav').addEventListener('click',event=>{const view=event.target.dataset.view;if(view){currentView=view;location.hash=view;document.querySelector('.sidebar').classList.remove('open');render();}});
document.querySelector('#menu-button').addEventListener('click',()=>document.querySelector('.sidebar').classList.toggle('open'));
document.querySelector('#stage-rebalance').addEventListener('click',stageRebalance);
document.querySelector('#reset-demo').addEventListener('click',()=>{if(confirm('Reset positions, orders and audit history to the synthetic demo?')){state=freshState();save();render();notify('Synthetic workspace reset.');}});
document.querySelector('#workspace-file').addEventListener('change',event=>importWorkspace(event.target.files?.[0]));
document.querySelector('#broker-snapshot-file').addEventListener('change',event=>importBrokerSnapshot(event.target.files?.[0]));
document.querySelector('#ticket-instrument').addEventListener('change',syncTicket);
document.querySelector('#ticket-type').addEventListener('change',event=>{document.querySelector('#ticket-limit').disabled=event.target.value!=='Limit';});
document.querySelector('#ticket-form').addEventListener('submit',event=>{if(event.submitter?.value==='cancel')return;event.preventDefault();try{const order=stageInput({instrumentId:document.querySelector('#ticket-instrument').value,side:document.querySelector('#ticket-side').value,quantity:document.querySelector('#ticket-quantity').value,orderType:document.querySelector('#ticket-type').value,limitPrice:document.querySelector('#ticket-limit').value});document.querySelector('#ticket-dialog').close();currentView='orders';location.hash='orders';render();notify(order.risk.pass?'Order staged after passing controls.':'Order staged but blocked by controls.',!order.risk.pass);}catch(error){notify(error.message,true);}});
window.addEventListener('hashchange',()=>{currentView=location.hash.slice(1)||'overview';render();});
render();
