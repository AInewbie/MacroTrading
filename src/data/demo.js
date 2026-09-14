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
