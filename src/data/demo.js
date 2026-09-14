export const demoInstruments = [
  { id:'stk-aapl', symbol:'AAPL', name:'Apple', assetClass:'Stock', currency:'USD', price:232.4, multiplier:1, beta:1.18, region:'US' },
  { id:'idx-spx', symbol:'SPX', name:'S&P 500 Index', assetClass:'Equity Index', currency:'USD', price:5940, multiplier:1, beta:1, region:'US' },
  { id:'bond-ust10', symbol:'UST10Y', name:'US Treasury 10Y', assetClass:'Bond', currency:'USD', price:99.15, multiplier:1000, duration:8.1, dv01:82.5, region:'US' },
  { id:'fx-eurusd', symbol:'EURUSD', name:'Euro / US Dollar', assetClass:'FX', currency:'USD', price:1.105, multiplier:1, region:'Global' },
  { id:'fxo-eurusd', symbol:'EURUSD', name:'EURUSD 1.12 Call', assetClass:'FX Option', currency:'USD', price:0.018, underlyingPrice:1.105, multiplier:100000, optionType:'Call', strike:1.12, expiry:'2026-12-18', delta:0.43, gamma:0.00012, vega:420, region:'Global' },
  { id:'eqo-aapl', symbol:'AAPL', name:'Apple 240 Call', assetClass:'Equity Option', currency:'USD', price:12.8, underlyingPrice:232.4, multiplier:100, optionType:'Call', strike:240, expiry:'2026-12-18', delta:0.51, gamma:0.012, vega:31, region:'US' },
  { id:'etf-tlt', symbol:'TLT', name:'iShares 20+ Year Treasury Bond ETF', assetClass:'ETF', currency:'USD', price:91.7, multiplier:1, beta:0.18, region:'US' },
  { id:'etfo-tlt', symbol:'TLT', name:'TLT 95 Call', assetClass:'ETF Option', currency:'USD', price:3.25, underlyingPrice:91.7, multiplier:100, optionType:'Call', strike:95, expiry:'2026-12-18', delta:0.42, gamma:0.028, vega:14, region:'US' },
  { id:'cmd-gold', symbol:'GC', name:'Gold future proxy', assetClass:'Commodity', currency:'USD', price:2588, multiplier:100, region:'Global' },
];

export const demoPortfolio = {
  id:'global-macro', name:'Global Macro — Paper', baseCurrency:'USD', cash:1000000,
  positions:[
    { instrumentId:'stk-aapl', quantity:600, averagePrice:220, targetWeight:0.12 },
    { instrumentId:'bond-ust10', quantity:2, averagePrice:98.4, targetWeight:0.20 },
    { instrumentId:'fx-eurusd', quantity:180000, averagePrice:1.09, targetWeight:0.16 },
    { instrumentId:'fxo-eurusd', quantity:2, averagePrice:0.015, targetWeight:0.04 },
    { instrumentId:'eqo-aapl', quantity:-12, averagePrice:14.1, targetWeight:-0.03 },
    { instrumentId:'etf-tlt', quantity:1300, averagePrice:89.2, targetWeight:0.10 },
    { instrumentId:'etfo-tlt', quantity:18, averagePrice:2.9, targetWeight:0.02 },
    { instrumentId:'cmd-gold', quantity:1, averagePrice:2510, targetWeight:0.14 },
    { instrumentId:'idx-spx', quantity:-20, averagePrice:5800, targetWeight:-0.09 },
  ],
};

export const defaultPolicy = {
  maxOrderNotional: 300000, maxGrossExposure: 2500000, maxNetExposure: 1500000,
  maxOptionContracts: 100, maxCommodityContracts: 20,
  requireLimitForOptions: true, allowedAssetClasses: [
    'Stock','Equity Index','Bond','FX','FX Option','Equity Option','ETF','ETF Option','Commodity'
  ],
};

export const demoScenarios = [
  { id:'risk-off', name:'Global risk-off', shocks:{ equity:-0.12, rates:-0.01, fx:-0.04, volatility:0.25, commodity:-0.08 } },
  { id:'inflation', name:'Inflation resurgence', shocks:{ equity:-0.07, rates:0.0125, fx:0.02, volatility:0.15, commodity:0.16 } },
  { id:'usd-down', name:'Broad USD decline', shocks:{ equity:0.04, rates:-0.0025, fx:0.09, volatility:0.05, commodity:0.10 } },
];

export const demoBrokerSnapshot = {
  format:'macrotrading-broker-snapshot', schemaVersion:1, asOf:'2026-09-14T12:00:00.000Z',
  account:{ broker:'Synthetic Broker', accountId:'PAPER-U1234567', baseCurrency:'USD', cash:997500 },
  positions:[
    { instrumentId:'stk-aapl', brokerSymbol:'AAPL', quantity:610 },
    { instrumentId:'bond-ust10', brokerSymbol:'UST10Y', quantity:2 },
    { instrumentId:'fx-eurusd', brokerSymbol:'EUR.USD', quantity:180000 },
    { instrumentId:'eqo-aapl', brokerSymbol:'AAPL 20261218 C240', quantity:-12 },
    { instrumentId:'etf-tlt', brokerSymbol:'TLT', quantity:1300 },
    { instrumentId:'etfo-tlt', brokerSymbol:'TLT 20261218 C95', quantity:18 },
    { instrumentId:'cmd-gold', brokerSymbol:'GC', quantity:1 },
    { instrumentId:'idx-spx', brokerSymbol:'SPX', quantity:-20 },
    { instrumentId:'broker-only-vix', brokerSymbol:'VX', quantity:3 },
  ],
};

export const demoThemeEvidence = [
  { id:'ev-cpi', title:'Core inflation trend cools across recent observations', sourceName:'Synthetic macro release', sourceType:'Macro data', observedAt:'2026-09-12T12:30:00.000Z', reliability:0.94, novelty:0.54, summary:'A synthetic inflation series shows sequential core price pressure easing while services remain sticky.' },
  { id:'ev-yields', title:'Duration demand rises in institutional flow proxy', sourceName:'Synthetic alternative flow monitor', sourceType:'Alternative data', observedAt:'2026-09-13T16:00:00.000Z', reliability:0.72, novelty:0.81, summary:'A synthetic custody-flow proxy records broadening demand for long-duration government bonds.' },
  { id:'ev-fed', title:'Policy meeting and projections approach', sourceName:'Synthetic catalyst calendar', sourceType:'Catalyst', observedAt:'2026-09-14T08:00:00.000Z', reliability:0.98, novelty:0.40, summary:'A scheduled synthetic central-bank decision could validate or invalidate the duration thesis.' },
  { id:'ev-wages', title:'Wage tracker remains above comfort range', sourceName:'Synthetic research brief', sourceType:'Research', observedAt:'2026-09-11T10:00:00.000Z', reliability:0.78, novelty:0.63, summary:'A synthetic wage tracker contradicts a rapid-disinflation narrative and argues for position-size restraint.' },
  { id:'ev-ai-capex', title:'Large-cap technology capex guidance remains elevated', sourceName:'Synthetic company basket', sourceType:'Financials', observedAt:'2026-09-10T20:00:00.000Z', reliability:0.88, novelty:0.69, summary:'Synthetic earnings commentary points to sustained AI infrastructure spending and near-term free-cash-flow pressure.' },
  { id:'ev-power', title:'Data-centre power demand accelerates', sourceName:'Synthetic grid-load estimator', sourceType:'Alternative data', observedAt:'2026-09-13T06:00:00.000Z', reliability:0.70, novelty:0.91, summary:'A synthetic grid-load proxy indicates faster electricity demand near major data-centre clusters.' },
  { id:'ev-tech-news', title:'AI infrastructure bottlenecks broaden beyond chips', sourceName:'Synthetic financial newswire', sourceType:'News', observedAt:'2026-09-14T07:00:00.000Z', reliability:0.82, novelty:0.76, summary:'Synthetic reporting highlights power, cooling and construction constraints as the next capex bottlenecks.' },
  { id:'ev-blog', title:'Crowding risk rises in mega-cap AI basket', sourceName:'Synthetic specialist blog', sourceType:'Blog', observedAt:'2026-09-09T09:00:00.000Z', reliability:0.55, novelty:0.84, summary:'A synthetic positioning essay argues consensus exposure is concentrated and vulnerable to guidance disappointments.' },
  { id:'ev-earnings', title:'Large-cap earnings catalyst enters focus', sourceName:'Synthetic catalyst calendar', sourceType:'Catalyst', observedAt:'2026-09-14T08:30:00.000Z', reliability:0.97, novelty:0.44, summary:'A synthetic earnings window provides a near-term test of capex durability and monetisation.' },
];

export const demoThemeProposals = [
  {
    id:'theme-duration', title:'Cooling inflation supports duration',
    thesis:'Disinflation evidence and strengthening duration flows may favor long government-bond exposure, while sticky wages keep the theme conditional rather than definitive.',
    horizon:'1–3 months', modelConfidence:0.76,
    evidenceIds:['ev-cpi','ev-yields','ev-fed'], contradictingEvidenceIds:['ev-wages'], catalystEvidenceIds:['ev-fed'],
    invalidation:'A renewed acceleration in services inflation or a materially more restrictive policy-rate path.',
    mappings:[
      { instrumentId:'bond-ust10', stance:'Long', rationale:'Direct duration exposure to easing rate expectations.' },
      { instrumentId:'etf-tlt', stance:'Long', rationale:'Liquid long-duration ETF expression for research monitoring.' },
      { instrumentId:'fx-eurusd', stance:'Watch', rationale:'Monitor USD-rate repricing before assigning an FX direction.' },
    ],
  },
  {
    id:'theme-ai-power', title:'AI capex broadens into power constraints',
    thesis:'Persistent technology capex and accelerating data-centre load suggest the AI investment cycle is broadening, but crowded mega-cap positioning raises asymmetric catalyst risk.',
    horizon:'3–12 months', modelConfidence:0.72,
    evidenceIds:['ev-ai-capex','ev-power','ev-tech-news','ev-earnings'], contradictingEvidenceIds:['ev-blog'], catalystEvidenceIds:['ev-earnings'],
    invalidation:'Capex guidance is cut, grid-load growth decelerates, or AI monetisation fails to support spending plans.',
    mappings:[
      { instrumentId:'idx-spx', stance:'Long', rationale:'Broad equity exposure while the investment cycle remains intact.' },
      { instrumentId:'stk-aapl', stance:'Watch', rationale:'Track company-specific participation rather than infer it from the broad theme.' },
      { instrumentId:'eqo-aapl', stance:'Watch', rationale:'Options require separate volatility, strike and premium analysis before use.' },
    ],
  },
];
