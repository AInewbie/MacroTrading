import { ASSET_CLASSES, validateInstrument } from './instruments.js';
import { ORDER_SIDES, ORDER_TYPES } from './orders.js';
import { normaliseBrokerSnapshot } from './reconciliation.js';

export const WORKSPACE_FORMAT = 'macrotrading-workspace';
export const WORKSPACE_SCHEMA_VERSION = 1;
export const MAX_WORKSPACE_FILE_BYTES = 2_000_000;

const limits = Object.freeze({ instruments:500, positions:2_000, orders:5_000, audit:10_000 });
const instrumentFields = [
  'id','symbol','name','assetClass','currency','price','multiplier','beta','region',
  'duration','dv01','underlyingPrice','optionType','strike','expiry','delta','gamma','vega',
];

function fail(message) { throw new Error(`Workspace import rejected: ${message}`); }
function object(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${label} must be an object.`);
  return value;
}
function array(value, label, maximum) {
  if (!Array.isArray(value)) fail(`${label} must be an array.`);
  if (value.length > maximum) fail(`${label} exceeds the ${maximum.toLocaleString('en-US')} item limit.`);
  return value;
}
function text(value, label, maximum=160) {
  if (typeof value !== 'string' || !value.trim()) fail(`${label} is required.`);
  if (value.length > maximum) fail(`${label} exceeds ${maximum} characters.`);
  return value.trim();
}
function finite(value, label, { minimum=-Number.MAX_VALUE, maximum=Number.MAX_VALUE }={}) {
  if (!Number.isFinite(value) || value < minimum || value > maximum) fail(`${label} is outside the allowed range.`);
  return value;
}
function isoDate(value, label) {
  const result = text(value, label, 40);
  if (!Number.isFinite(Date.parse(result))) fail(`${label} is not a valid date.`);
  return result;
}
function optionalFinite(source, target, field, label, range) {
  if (source[field] != null) target[field] = finite(source[field], `${label} ${field}`, range);
}

function normaliseInstrument(value, index) {
  const source = object(value, `instrument ${index + 1}`), result = {};
  for (const field of instrumentFields) if (source[field] != null) result[field] = source[field];
  result.id = text(source.id, `instrument ${index + 1} id`, 80);
  if (!/^[A-Za-z0-9._:-]+$/.test(result.id)) fail(`instrument ${result.id} has an unsafe id.`);
  result.symbol = text(source.symbol, `instrument ${result.id} symbol`, 40);
  result.name = text(source.name, `instrument ${result.id} name`, 160);
  result.currency = text(source.currency, `instrument ${result.id} currency`, 3).toUpperCase();
  if (!/^[A-Z]{3}$/.test(result.currency)) fail(`instrument ${result.id} currency must use three letters.`);
  const errors = validateInstrument(result);
  if (errors.length) fail(`instrument ${result.id}: ${errors.join(' ')}`);
  for (const field of ['beta','duration','dv01','underlyingPrice','strike','delta','gamma','vega']) {
    if (result[field] != null) finite(result[field], `instrument ${result.id} ${field}`, { minimum:-1e12, maximum:1e12 });
  }
  if (result.region != null) result.region = text(result.region, `instrument ${result.id} region`, 80);
  if (result.expiry != null && !/^\d{4}-\d{2}-\d{2}$/.test(result.expiry)) fail(`instrument ${result.id} expiry must be YYYY-MM-DD.`);
  return result;
}

function normalisePortfolio(value, instrumentIds) {
  const source = object(value, 'portfolio');
  const portfolio = {
    id:text(source.id, 'portfolio id', 80),
    name:text(source.name, 'portfolio name', 160),
    baseCurrency:text(source.baseCurrency, 'portfolio base currency', 3).toUpperCase(),
    cash:finite(source.cash, 'portfolio cash', { minimum:-1e15, maximum:1e15 }),
    positions:[],
  };
  if (!/^[A-Z]{3}$/.test(portfolio.baseCurrency)) fail('portfolio base currency must use three letters.');
  const seen = new Set();
  portfolio.positions = array(source.positions, 'positions', limits.positions).map((value, index) => {
    const position = object(value, `position ${index + 1}`);
    const instrumentId = text(position.instrumentId, `position ${index + 1} instrument id`, 80);
    if (!instrumentIds.has(instrumentId)) fail(`position ${index + 1} references missing instrument ${instrumentId}.`);
    if (seen.has(instrumentId)) fail(`portfolio contains duplicate position ${instrumentId}.`);
    seen.add(instrumentId);
    const result = {
      instrumentId,
      quantity:finite(position.quantity, `position ${instrumentId} quantity`, { minimum:-1e12, maximum:1e12 }),
      averagePrice:finite(position.averagePrice, `position ${instrumentId} average price`, { minimum:0, maximum:1e12 }),
    };
    optionalFinite(position, result, 'targetWeight', `position ${instrumentId}`, { minimum:-10, maximum:10 });
    return result;
  });
  return portfolio;
}

function normalisePolicy(value) {
  const source = object(value, 'policy'), result = {};
  for (const field of ['maxOrderNotional','maxGrossExposure','maxNetExposure','maxOptionContracts','maxCommodityContracts']) {
    result[field] = finite(source[field], `policy ${field}`, { minimum:Number.EPSILON, maximum:1e15 });
  }
  if (typeof source.requireLimitForOptions !== 'boolean') fail('policy requireLimitForOptions must be true or false.');
  result.requireLimitForOptions = source.requireLimitForOptions;
  result.allowedAssetClasses = [...new Set(array(source.allowedAssetClasses, 'allowed asset classes', ASSET_CLASSES.length)
    .map((item) => text(item, 'allowed asset class', 40)))];
  if (!result.allowedAssetClasses.length || result.allowedAssetClasses.some((item) => !ASSET_CLASSES.includes(item))) {
    fail('policy contains an unsupported or empty asset-class list.');
  }
  return result;
}

function normaliseRisk(value, imported) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined;
  const result = {
    pass: imported ? false : value.pass === true,
    notional:Number.isFinite(value.notional) && value.notional >= 0 ? value.notional : 0,
    checks:[],
  };
  if (Array.isArray(value.checks)) result.checks = value.checks.slice(0, 30).map((check) => ({
    name:typeof check?.name === 'string' ? check.name.slice(0, 120) : 'Imported check',
    pass: imported ? false : check?.pass === true,
    ...(Number.isFinite(check?.value) ? { value:check.value } : {}),
    ...(Number.isFinite(check?.limit) ? { limit:check.limit } : {}),
  }));
  return result;
}

function normaliseOrder(value, index, instruments, imported) {
  const source = object(value, `order ${index + 1}`);
  const instrumentId = text(source.instrumentId, `order ${index + 1} instrument id`, 80);
  const instrument = instruments.get(instrumentId);
  if (!instrument) fail(`order ${index + 1} references missing instrument ${instrumentId}.`);
  if (!ORDER_SIDES.includes(source.side) || !ORDER_TYPES.includes(source.orderType)) fail(`order ${index + 1} has an invalid side or type.`);
  const order = {
    id:text(source.id, `order ${index + 1} id`, 120), instrumentId,
    symbol:instrument.symbol, assetClass:instrument.assetClass, side:source.side,
    quantity:finite(source.quantity, `order ${index + 1} quantity`, { minimum:Number.EPSILON, maximum:1e12 }),
    orderType:source.orderType,
    limitPrice:source.orderType === 'Limit' ? finite(source.limitPrice, `order ${index + 1} limit price`, { minimum:Number.EPSILON, maximum:1e12 }) : null,
    status:imported && source.status !== 'Filled' ? 'Imported' : ['Staged','Filled','Imported'].includes(source.status) ? source.status : 'Imported',
    createdAt:isoDate(source.createdAt, `order ${index + 1} created time`),
    source:typeof source.source === 'string' ? source.source.slice(0, 120) : 'Imported workspace',
  };
  order.risk = normaliseRisk(source.risk, imported && order.status !== 'Filled');
  if (source.status === 'Filled') {
    const fill = object(source.fill, `order ${index + 1} fill`);
    order.fill = {
      broker:text(fill.broker, `order ${index + 1} fill broker`, 80),
      brokerOrderId:text(fill.brokerOrderId, `order ${index + 1} broker order id`, 160),
      status:'Filled',
      filledQuantity:finite(fill.filledQuantity, `order ${index + 1} filled quantity`, { minimum:Number.EPSILON, maximum:1e12 }),
      averageFillPrice:finite(fill.averageFillPrice, `order ${index + 1} fill price`, { minimum:0, maximum:1e12 }),
      filledAt:isoDate(fill.filledAt, `order ${index + 1} fill time`),
    };
  }
  return order;
}

function normaliseAudit(value, index) {
  const source = object(value, `audit row ${index + 1}`);
  return {
    at:isoDate(source.at, `audit row ${index + 1} time`),
    event:text(source.event, `audit row ${index + 1} event`, 160),
    detail:text(source.detail, `audit row ${index + 1} detail`, 500),
    actor:text(source.actor, `audit row ${index + 1} actor`, 80),
  };
}

export function validateWorkspaceState(value, { imported=false }={}) {
  const source = object(value, 'workspace state');
  const instruments = array(source.instruments, 'instruments', limits.instruments).map(normaliseInstrument);
  if (!instruments.length) fail('at least one instrument is required.');
  const ids = new Set(instruments.map((item) => item.id));
  if (ids.size !== instruments.length) fail('instrument ids must be unique.');
  const instrumentMap = new Map(instruments.map((item) => [item.id, item]));
  const state = {
    portfolio:normalisePortfolio(source.portfolio, ids), instruments,
    policy:normalisePolicy(source.policy),
    orders:array(source.orders ?? [], 'orders', limits.orders).map((item, index) => normaliseOrder(item, index, instrumentMap, imported)),
    audit:array(source.audit ?? [], 'audit trail', limits.audit).map(normaliseAudit),
    reconciliation:source.reconciliation == null ? null : normaliseBrokerSnapshot(source.reconciliation),
  };
  return state;
}

export function createWorkspaceDocument(state, now=new Date()) {
  return {
    format:WORKSPACE_FORMAT,
    schemaVersion:WORKSPACE_SCHEMA_VERSION,
    exportedAt:now.toISOString(),
    executionMode:'paper-only',
    workspace:validateWorkspaceState(state),
  };
}

export function parseWorkspaceDocument(input) {
  let document;
  try { document = typeof input === 'string' ? JSON.parse(input) : input; }
  catch { fail('the file is not valid JSON.'); }
  object(document, 'document');
  if (document.format !== WORKSPACE_FORMAT) fail(`expected format ${WORKSPACE_FORMAT}.`);
  if (document.schemaVersion !== WORKSPACE_SCHEMA_VERSION) fail(`schema version ${document.schemaVersion ?? 'missing'} is not supported.`);
  if (document.executionMode !== 'paper-only') fail('execution mode must be paper-only.');
  const state = validateWorkspaceState(document.workspace, { imported:true });
  const demoted = state.orders.filter((order) => order.status === 'Imported').length;
  return { state, demotedOrders:demoted, exportedAt:isoDate(document.exportedAt, 'export time') };
}
