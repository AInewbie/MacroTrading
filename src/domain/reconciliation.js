export const BROKER_SNAPSHOT_FORMAT = 'macrotrading-broker-snapshot';
export const BROKER_SNAPSHOT_SCHEMA_VERSION = 1;
export const MAX_BROKER_SNAPSHOT_BYTES = 1_000_000;

const MAX_POSITIONS = 2_000;

function fail(message) { throw new Error(`Broker snapshot rejected: ${message}`); }
function object(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${label} must be an object.`);
  return value;
}
function text(value, label, maximum=160) {
  if (typeof value !== 'string' || !value.trim()) fail(`${label} is required.`);
  if (value.length > maximum) fail(`${label} exceeds ${maximum} characters.`);
  return value.trim();
}
function finite(value, label, minimum=-1e15, maximum=1e15) {
  if (!Number.isFinite(value) || value < minimum || value > maximum) fail(`${label} is outside the allowed range.`);
  return value;
}

export function normaliseBrokerSnapshot(value) {
  const source = object(value, 'snapshot');
  if (source.format !== BROKER_SNAPSHOT_FORMAT) fail(`expected format ${BROKER_SNAPSHOT_FORMAT}.`);
  if (source.schemaVersion !== BROKER_SNAPSHOT_SCHEMA_VERSION) fail(`schema version ${source.schemaVersion ?? 'missing'} is not supported.`);
  const account = object(source.account, 'account');
  const asOf = text(source.asOf, 'as-of time', 40);
  if (!Number.isFinite(Date.parse(asOf))) fail('as-of time is not a valid date.');
  const baseCurrency = text(account.baseCurrency, 'account base currency', 3).toUpperCase();
  if (!/^[A-Z]{3}$/.test(baseCurrency)) fail('account base currency must use three letters.');
  if (!Array.isArray(source.positions)) fail('positions must be an array.');
  if (source.positions.length > MAX_POSITIONS) fail(`positions exceeds the ${MAX_POSITIONS.toLocaleString('en-US')} item limit.`);
  const seen = new Set();
  const positions = source.positions.map((value, index) => {
    const position = object(value, `position ${index + 1}`);
    const instrumentId = text(position.instrumentId, `position ${index + 1} instrument id`, 80);
    if (!/^[A-Za-z0-9._:-]+$/.test(instrumentId)) fail(`position ${index + 1} has an unsafe instrument id.`);
    if (seen.has(instrumentId)) fail(`positions contains duplicate instrument ${instrumentId}.`);
    seen.add(instrumentId);
    return {
      instrumentId,
      brokerSymbol:text(position.brokerSymbol ?? instrumentId, `position ${instrumentId} broker symbol`, 60),
      quantity:finite(position.quantity, `position ${instrumentId} quantity`, -1e12, 1e12),
    };
  });
  return {
    format:BROKER_SNAPSHOT_FORMAT,
    schemaVersion:BROKER_SNAPSHOT_SCHEMA_VERSION,
    asOf:new Date(asOf).toISOString(),
    account:{
      broker:text(account.broker, 'broker name', 120),
      accountId:text(account.accountId, 'account id', 120),
      baseCurrency,
      cash:finite(account.cash, 'account cash'),
    },
    positions,
  };
}

export function parseBrokerSnapshot(input) {
  let value;
  try { value = typeof input === 'string' ? JSON.parse(input) : input; }
  catch { fail('the file is not valid JSON.'); }
  return normaliseBrokerSnapshot(value);
}

export function reconcilePortfolio(portfolio, instruments, snapshotInput) {
  const snapshot = normaliseBrokerSnapshot(snapshotInput);
  const instrumentMap = new Map(instruments.map((item) => [item.id, item]));
  const modelMap = new Map(portfolio.positions.map((item) => [item.instrumentId, item.quantity]));
  const brokerMap = new Map(snapshot.positions.map((item) => [item.instrumentId, item]));
  const ids = new Set([...modelMap.keys(), ...brokerMap.keys()]);
  const rows = [...ids].map((instrumentId) => {
    const item = instrumentMap.get(instrumentId), brokerPosition = brokerMap.get(instrumentId);
    const modelQuantity = modelMap.get(instrumentId) ?? 0;
    const brokerQuantity = brokerPosition?.quantity ?? 0;
    const difference = brokerQuantity - modelQuantity;
    let status = 'Matched';
    if (!item) status = 'Unmapped';
    else if (!brokerPosition && modelMap.has(instrumentId)) status = 'Missing at broker';
    else if (!modelMap.has(instrumentId)) status = 'Broker only';
    else if (Math.abs(difference) > 1e-9) status = 'Quantity break';
    return {
      instrumentId,
      symbol:item?.symbol ?? brokerPosition?.brokerSymbol ?? instrumentId,
      name:item?.name ?? 'No matching instrument in the local universe',
      assetClass:item?.assetClass ?? 'Unmapped',
      modelQuantity, brokerQuantity, difference, status,
    };
  }).sort((a, b) => (a.status === 'Matched') - (b.status === 'Matched') || a.symbol.localeCompare(b.symbol));
  const positionBreaks = rows.filter((row) => row.status !== 'Matched').length;
  const cashDifference = snapshot.account.cash - portfolio.cash;
  return {
    snapshot,
    rows,
    positionBreaks,
    matchedPositions:rows.length - positionBreaks,
    cashDifference,
    cashMatched:Math.abs(cashDifference) <= 0.01,
    pass:positionBreaks === 0 && Math.abs(cashDifference) <= 0.01 && snapshot.account.baseCurrency === portfolio.baseCurrency,
  };
}

export function maskAccountId(value) {
  const id = String(value);
  return id.length <= 4 ? '••••' : `${'•'.repeat(Math.min(id.length - 4, 8))}${id.slice(-4)}`;
}
