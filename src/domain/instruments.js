export const ASSET_CLASSES = Object.freeze([
  'Stock', 'Equity Index', 'Bond', 'FX', 'FX Option',
  'Equity Option', 'ETF', 'ETF Option', 'Commodity',
]);

export const OPTION_CLASSES = new Set(['FX Option', 'Equity Option', 'ETF Option']);

export function validateInstrument(instrument) {
  const errors = [];
  if (!instrument?.id) errors.push('Instrument id is required.');
  if (!instrument?.symbol) errors.push('Symbol is required.');
  if (!ASSET_CLASSES.includes(instrument?.assetClass)) errors.push('Unsupported asset class.');
  if (!instrument?.currency || instrument.currency.length !== 3) errors.push('Currency must be an ISO-style three-letter code.');
  if (!Number.isFinite(instrument?.price) || instrument.price < 0) errors.push('Price must be non-negative.');
  if (!Number.isFinite(instrument?.multiplier) || instrument.multiplier <= 0) errors.push('Multiplier must be positive.');
  if (OPTION_CLASSES.has(instrument?.assetClass)) {
    if (!['Call', 'Put'].includes(instrument.optionType)) errors.push('Options require Call or Put.');
    if (!instrument.expiry || !Number.isFinite(instrument.strike)) errors.push('Options require expiry and strike.');
  }
  return errors;
}

export function instrumentLabel(instrument) {
  if (!OPTION_CLASSES.has(instrument.assetClass)) return instrument.symbol;
  return `${instrument.symbol} ${instrument.expiry} ${instrument.strike} ${instrument.optionType[0]}`;
}
