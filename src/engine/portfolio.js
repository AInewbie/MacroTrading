import { OPTION_CLASSES } from '../domain/instruments.js';

export function positionMetrics(position, instrument) {
  const multiplier = instrument.multiplier || 1;
  const marketValue = position.quantity * instrument.price * multiplier;
  const underlying = instrument.underlyingPrice || instrument.price;
  const deltaAdjusted = OPTION_CLASSES.has(instrument.assetClass)
    ? position.quantity * multiplier * underlying * (instrument.delta || 0)
    : marketValue;
  return {
    marketValue,
    deltaAdjusted,
    pnl: position.quantity * multiplier * (instrument.price - position.averagePrice),
    dv01: instrument.assetClass === 'Bond' ? position.quantity * (instrument.dv01 || 0) : 0,
    vega: OPTION_CLASSES.has(instrument.assetClass) ? position.quantity * (instrument.vega || 0) : 0,
    gamma: OPTION_CLASSES.has(instrument.assetClass) ? position.quantity * multiplier * (instrument.gamma || 0) : 0,
  };
}

export function analysePortfolio(portfolio, instruments) {
  const byId = new Map(instruments.map((item) => [item.id, item]));
  const rows = portfolio.positions.map((position) => {
    const instrument = byId.get(position.instrumentId);
    if (!instrument) throw new Error(`Missing instrument ${position.instrumentId}`);
    return { position, instrument, ...positionMetrics(position, instrument) };
  });
  const sum = (field) => rows.reduce((total, row) => total + row[field], 0);
  const gross = rows.reduce((total, row) => total + Math.abs(row.deltaAdjusted), 0);
  const net = sum('deltaAdjusted');
  const nav = portfolio.cash + sum('marketValue');
  const byClass = Object.fromEntries([...new Set(rows.map((row) => row.instrument.assetClass))]
    .map((assetClass) => [assetClass, rows.filter((row) => row.instrument.assetClass === assetClass)
      .reduce((total, row) => total + row.deltaAdjusted, 0)]));
  return { rows, gross, net, nav, pnl:sum('pnl'), dv01:sum('dv01'), vega:sum('vega'), gamma:sum('gamma'), byClass };
}

export function rebalanceOrders(portfolio, instruments, targetNav = null) {
  const analysis = analysePortfolio(portfolio, instruments);
  const capital = targetNav || Math.max(Math.abs(analysis.nav), portfolio.cash);
  return analysis.rows.flatMap((row) => {
    if (!Number.isFinite(row.position.targetWeight)) return [];
    const desired = capital * row.position.targetWeight;
    const unitDelta = row.deltaAdjusted / row.position.quantity;
    if (!Number.isFinite(unitDelta) || unitDelta === 0) return [];
    const change = Math.round((desired - row.deltaAdjusted) / unitDelta);
    if (!change) return [];
    return [{ instrumentId:row.instrument.id, symbol:row.instrument.symbol, assetClass:row.instrument.assetClass,
      side:change > 0 ? 'Buy' : 'Sell', quantity:Math.abs(change), orderType:'Limit',
      limitPrice:row.instrument.price, source:'Target rebalance' }];
  });
}
