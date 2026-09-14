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
  { id:'ev-01', type:'Macro', source:'Synthetic macro release', url:null, title:'Manufacturing power demand revisions rise', summary:'Synthetic regional data shows upward revisions to grid demand associated with data-centre construction.', publishedAt:'2026-09-12T08:30:00.000Z', dataTimestamp:'2026-08-31T00:00:00.000Z', reliability:0.86, novelty:0.72, sentiment:0.64, themes:['ai-power'], entities:['US power','Data centres'] },
  { id:'ev-02', type:'Alternative', source:'Synthetic satellite index', url:null, title:'Construction activity broadens near grid interconnects', summary:'Synthetic geospatial indicator records a broadening in large-site construction around selected grid nodes.', publishedAt:'2026-09-11T15:00:00.000Z', reliability:0.68, novelty:0.83, sentiment:0.72, themes:['ai-power'], entities:['Grid infrastructure','Construction'] },
  { id:'ev-03', type:'Financial', source:'Synthetic company filings set', url:null, title:'Capital expenditure guidance remains elevated', summary:'Synthetic aggregate guidance shows sustained spending on compute and electrical infrastructure.', publishedAt:'2026-09-10T20:00:00.000Z', reliability:0.90, novelty:0.55, sentiment:0.58, themes:['ai-power'], entities:['Capital expenditure','Semiconductors'] },
  { id:'ev-04', type:'Catalyst', source:'Synthetic policy calendar', url:null, title:'Grid permitting decision window approaches', summary:'A synthetic policy calendar flags decisions that could accelerate or delay transmission projects.', publishedAt:'2026-09-13T09:00:00.000Z', reliability:0.78, novelty:0.66, sentiment:0.30, themes:['ai-power'], entities:['Grid permitting'] },
  { id:'ev-05', type:'News', source:'Synthetic wire', url:null, title:'Central banks emphasize divergent inflation risks', summary:'Synthetic reporting highlights greater expected policy dispersion across developed markets.', publishedAt:'2026-09-13T12:00:00.000Z', reliability:0.88, novelty:0.48, sentiment:0.22, themes:['policy-divergence'], entities:['Federal Reserve','ECB'] },
  { id:'ev-06', type:'Blog', source:'Synthetic research blog', url:null, title:'FX volatility may underprice policy dispersion', summary:'A synthetic analyst note argues that rate-path divergence is not fully reflected in selected FX volatility surfaces.', publishedAt:'2026-09-12T11:00:00.000Z', reliability:0.58, novelty:0.74, sentiment:0.46, themes:['policy-divergence'], entities:['EURUSD','FX volatility'] },
  { id:'ev-07', type:'Macro', source:'Synthetic rates monitor', url:null, title:'Front-end curves decouple across regions', summary:'Synthetic curve data shows rising cross-market dispersion in expected policy paths.', publishedAt:'2026-09-11T16:00:00.000Z', reliability:0.92, novelty:0.60, sentiment:0.40, themes:['policy-divergence'], entities:['Rates','EURUSD'] },
  { id:'ev-08', type:'Financial', source:'Synthetic positioning data', url:null, title:'Gold positioning rises but is not extreme', summary:'Synthetic futures positioning suggests participation has increased while remaining below historical crowding thresholds.', publishedAt:'2026-09-09T14:00:00.000Z', reliability:0.75, novelty:0.44, sentiment:0.56, themes:['hard-assets'], entities:['Gold','USD'] },
  { id:'ev-09', type:'Macro', source:'Synthetic inflation monitor', url:null, title:'Goods disinflation loses momentum', summary:'Synthetic high-frequency inflation components indicate a slower decline in selected goods prices.', publishedAt:'2026-09-12T07:00:00.000Z', reliability:0.84, novelty:0.63, sentiment:0.52, themes:['hard-assets'], entities:['Inflation','Gold'] },
];

export const demoThemeDefinitions = [
  { id:'ai-power', name:'AI infrastructure meets power scarcity', thesis:'Compute investment is shifting bottlenecks toward electricity, grids and permitting, with cross-asset implications for growth, inflation and capital spending.', horizon:'Structural', catalysts:['Grid-permitting decisions','Capex guidance revisions'], invalidation:['Power-demand revisions reverse','Compute capex contracts materially'], expressions:[{ instrumentId:'idx-spx', stance:'Long', fit:0.55, rationale:'Broad but diluted exposure to investment beneficiaries.' },{ instrumentId:'cmd-gold', stance:'Hedge', fit:0.38, rationale:'Potential hedge for inflationary infrastructure constraints.' }] },
  { id:'policy-divergence', name:'Developed-market policy divergence', thesis:'Divergent inflation and growth paths may increase relative-value opportunities across rates and FX volatility.', horizon:'Months', catalysts:['Central-bank meetings','Inflation surprises'], invalidation:['Forward curves reconverge','Cross-market inflation dispersion collapses'], expressions:[{ instrumentId:'fx-eurusd', stance:'Relative value', fit:0.88, rationale:'Direct expression of US–euro-area policy dispersion.' },{ instrumentId:'fxo-eurusd', stance:'Long', fit:0.91, rationale:'Defined-risk exposure to larger-than-priced currency moves.' },{ instrumentId:'bond-ust10', stance:'Hedge', fit:0.52, rationale:'Duration can offset the risk-off branch of the theme.' }] },
  { id:'hard-assets', name:'Hard assets against sticky inflation', thesis:'Slower disinflation and continued real-asset demand may support selective inflation hedges, subject to USD and real-yield sensitivity.', horizon:'Months', catalysts:['Inflation releases','Real-yield reversal'], invalidation:['Disinflation reaccelerates','Real yields rise sharply'], expressions:[{ instrumentId:'cmd-gold', stance:'Long', fit:0.90, rationale:'Direct hard-asset expression with meaningful real-yield sensitivity.' },{ instrumentId:'etf-tlt', stance:'Short', fit:0.45, rationale:'Potential rates hedge, but not a pure inflation exposure.' }] },
];

export const defaultThemeSettings = { halfLifeDays:21, minimumSources:2, weights:{ reliability:0.30, freshness:0.25, novelty:0.15, breadth:0.20, catalyst:0.10 } };
