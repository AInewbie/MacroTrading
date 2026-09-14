import { analysePortfolio, positionMetrics } from './portfolio.js';
import { OPTION_CLASSES } from '../domain/instruments.js';

export function estimateOrderNotional(order, instrument) {
  const reference = instrument.underlyingPrice || order.limitPrice || instrument.price;
  return order.quantity * reference * (instrument.multiplier || 1);
}

export function preTradeChecks(order, instrument, portfolio, instruments, policy) {
  const checks = [];
  const notional = estimateOrderNotional(order, instrument);
  checks.push({ name:'Allowed asset class', pass:policy.allowedAssetClasses.includes(instrument.assetClass), value:instrument.assetClass });
  checks.push({ name:'Order notional', pass:notional <= policy.maxOrderNotional, value:notional, limit:policy.maxOrderNotional });
  if (OPTION_CLASSES.has(instrument.assetClass)) {
    checks.push({ name:'Option contract limit', pass:order.quantity <= policy.maxOptionContracts, value:order.quantity, limit:policy.maxOptionContracts });
    checks.push({ name:'Options use limit orders', pass:!policy.requireLimitForOptions || order.orderType === 'Limit', value:order.orderType });
  }
  if (instrument.assetClass === 'Commodity') checks.push({ name:'Commodity contract limit', pass:order.quantity <= policy.maxCommodityContracts, value:order.quantity, limit:policy.maxCommodityContracts });
  const signed = order.side === 'Buy' ? order.quantity : -order.quantity;
  const simulated = structuredClone(portfolio);
  const position = simulated.positions.find((item) => item.instrumentId === instrument.id);
  if (position) position.quantity += signed;
  else simulated.positions.push({ instrumentId:instrument.id, quantity:signed, averagePrice:instrument.price });
  const after = analysePortfolio(simulated, instruments);
  checks.push({ name:'Post-trade gross exposure', pass:after.gross <= policy.maxGrossExposure, value:after.gross, limit:policy.maxGrossExposure });
  checks.push({ name:'Post-trade net exposure', pass:Math.abs(after.net) <= policy.maxNetExposure, value:Math.abs(after.net), limit:policy.maxNetExposure });
  return { pass:checks.every((check) => check.pass), checks, notional, after };
}

export function stressPortfolio(portfolio, instruments, scenario) {
  return analysePortfolio(portfolio, instruments).rows.map((row) => {
    const { instrument } = row;
    let shock = 0;
    if (['Stock','Equity Index','ETF'].includes(instrument.assetClass)) shock = scenario.shocks.equity;
    else if (instrument.assetClass === 'Bond') shock = -(instrument.duration || 0) * scenario.shocks.rates;
    else if (instrument.assetClass === 'FX') shock = scenario.shocks.fx;
    else if (instrument.assetClass === 'Commodity') shock = scenario.shocks.commodity;
    else if (OPTION_CLASSES.has(instrument.assetClass)) {
      const underlyingShock = instrument.assetClass === 'FX Option' ? scenario.shocks.fx : scenario.shocks.equity;
      const dS = (instrument.underlyingPrice || 0) * underlyingShock;
      const optionMove = (instrument.delta || 0) * dS + 0.5 * (instrument.gamma || 0) * dS ** 2 + (instrument.vega || 0) / instrument.multiplier * scenario.shocks.volatility;
      return { symbol:instrument.symbol, assetClass:instrument.assetClass, pnl:row.position.quantity * instrument.multiplier * optionMove };
    }
    return { symbol:instrument.symbol, assetClass:instrument.assetClass, pnl:row.marketValue * shock };
  });
}
