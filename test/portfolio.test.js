import test from 'node:test';
import assert from 'node:assert/strict';
import { demoInstruments, demoPortfolio, defaultPolicy, demoScenarios } from '../src/data/demo.js';
import { analysePortfolio, positionMetrics, rebalanceOrders } from '../src/engine/portfolio.js';
import { preTradeChecks, stressPortfolio } from '../src/engine/risk.js';
import { validateInstrument } from '../src/domain/instruments.js';
import { createOrder } from '../src/domain/orders.js';
import { PaperBroker, LiveBrokerDisabled } from '../src/adapters/paperBroker.js';
import { createWorkspaceDocument, parseWorkspaceDocument } from '../src/domain/workspace.js';

function workspaceState(overrides={}) {
  return {
    portfolio:structuredClone(demoPortfolio), instruments:structuredClone(demoInstruments),
    policy:structuredClone(defaultPolicy), orders:[],
    audit:[{ at:'2026-09-14T00:00:00.000Z', event:'Test workspace', detail:'Synthetic fixture', actor:'Test' }],
    ...overrides,
  };
}

test('demo universe covers all requested asset classes with valid instruments', () => {
  const expected = ['Stock','Equity Index','Bond','FX','FX Option','Equity Option','ETF','ETF Option','Commodity'];
  assert.deepEqual([...new Set(demoInstruments.map((item) => item.assetClass))].sort(), expected.sort());
  assert.deepEqual(demoInstruments.flatMap(validateInstrument), []);
});

test('portfolio analysis reconciles row totals', () => {
  const result = analysePortfolio(demoPortfolio, demoInstruments);
  assert.equal(result.rows.length, demoPortfolio.positions.length);
  assert.equal(result.net, result.rows.reduce((sum, row) => sum + row.deltaAdjusted, 0));
  assert.equal(result.gross, result.rows.reduce((sum, row) => sum + Math.abs(row.deltaAdjusted), 0));
  assert.ok(Number.isFinite(result.nav));
});

test('option metrics use delta-adjusted underlying exposure', () => {
  const instrument = demoInstruments.find((item) => item.id === 'eqo-aapl');
  const metrics = positionMetrics({ quantity: 2, averagePrice:10 }, instrument);
  assert.equal(metrics.deltaAdjusted, 2 * 100 * instrument.underlyingPrice * instrument.delta);
  assert.equal(metrics.vega, 2 * instrument.vega);
});

test('pre-trade controls block oversized and market option orders', () => {
  const instrument = demoInstruments.find((item) => item.id === 'eqo-aapl');
  const order = createOrder({ side:'Buy', quantity:200, orderType:'Market' }, instrument);
  const result = preTradeChecks(order, instrument, demoPortfolio, demoInstruments, defaultPolicy);
  assert.equal(result.pass, false);
  assert.equal(result.checks.find((item) => item.name === 'Option contract limit').pass, false);
  assert.equal(result.checks.find((item) => item.name === 'Options use limit orders').pass, false);
});

test('valid small order passes and paper broker returns an auditable fill', async () => {
  const instrument = demoInstruments.find((item) => item.id === 'stk-aapl');
  const order = createOrder({ side:'Buy', quantity:10, orderType:'Limit', limitPrice:instrument.price }, instrument);
  const result = preTradeChecks(order, instrument, demoPortfolio, demoInstruments, defaultPolicy);
  assert.equal(result.pass, true);
  const fill = await new PaperBroker().submit(order, instrument);
  assert.equal(fill.status, 'Filled');
  assert.equal(fill.filledQuantity, 10);
  assert.match(fill.brokerOrderId, /^paper-/);
});

test('live broker route fails closed', async () => {
  await assert.rejects(() => new LiveBrokerDisabled().submit(), /Live execution is disabled/);
});

test('stress and rebalance engines produce finite outputs', () => {
  for (const scenario of demoScenarios) {
    const rows = stressPortfolio(demoPortfolio, demoInstruments, scenario);
    assert.equal(rows.length, demoPortfolio.positions.length);
    assert.ok(rows.every((row) => Number.isFinite(row.pnl)));
  }
  const orders = rebalanceOrders(demoPortfolio, demoInstruments);
  assert.ok(orders.length > 0);
  assert.ok(orders.every((order) => order.quantity > 0));
});

test('workspace export round-trips the normalized multi-asset state', () => {
  const original = workspaceState();
  const document = createWorkspaceDocument(original, new Date('2026-09-14T10:00:00.000Z'));
  const restored = parseWorkspaceDocument(JSON.stringify(document));
  assert.equal(document.schemaVersion, 1);
  assert.equal(document.executionMode, 'paper-only');
  assert.deepEqual(restored.state.portfolio, original.portfolio);
  assert.deepEqual(restored.state.instruments, original.instruments);
  assert.deepEqual(restored.state.policy, original.policy);
});

test('workspace import demotes unfilled orders so they cannot be submitted', () => {
  const instrument = demoInstruments[0];
  const order = createOrder({ side:'Buy', quantity:10, orderType:'Limit', limitPrice:instrument.price }, instrument);
  order.risk = { pass:true, notional:2324, checks:[{ name:'Synthetic check', pass:true }] };
  const document = createWorkspaceDocument(workspaceState({ orders:[order] }), new Date('2026-09-14T10:00:00.000Z'));
  const restored = parseWorkspaceDocument(document);
  assert.equal(restored.demotedOrders, 1);
  assert.equal(restored.state.orders[0].status, 'Imported');
  assert.equal(restored.state.orders[0].risk.pass, false);
});

test('workspace import rejects unsupported versions and broken position references', () => {
  const document = createWorkspaceDocument(workspaceState(), new Date('2026-09-14T10:00:00.000Z'));
  assert.throws(() => parseWorkspaceDocument({ ...document, schemaVersion:2 }), /schema version 2 is not supported/);
  document.workspace.portfolio.positions[0].instrumentId = 'missing-instrument';
  assert.throws(() => parseWorkspaceDocument(document), /references missing instrument/);
});
