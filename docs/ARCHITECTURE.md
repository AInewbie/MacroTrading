# Architecture and roadmap

## Product boundary

MacroTrading separates portfolio intent from broker execution:

1. **Instrument master** normalizes asset-class-specific identifiers and economics.
2. **Portfolio engine** converts positions to market-value and risk views.
3. **Strategy layer** will convert signals and objectives into target exposures.
4. **Order planner** converts targets into executable quantities.
5. **Risk gateway** evaluates versioned pre-trade policies.
6. **Broker adapter** maps approved orders to a broker contract and reconciles acknowledgements and fills.

The current release implements items 1, 2, 4 and 5, plus a deterministic paper adapter and broker-neutral read-only reconciliation for item 6, with schema-versioned local workspace portability. It deliberately does not claim production valuations or live connectivity.

## Normalized asset model

Common fields include instrument id, display symbol, asset class, reporting currency, price and contract multiplier. Options add underlying price, expiry, strike, put/call, delta, gamma and vega. Bonds add duration and DV01. A production instrument master should add vendor/broker identifiers, exchange, trading calendar, settlement, tick size, lot size, curve and volatility-surface references.

## Planned increments

1. Editable instrument master with identifier, lot-size and calendar metadata.
2. Historical price adapter and FX conversion graph.
3. Return, volatility, correlation, beta, VaR/ES and drawdown analytics.
4. Constraint-aware optimizer with turnover, liquidity and concentration controls.
5. Strategy/signal interface with regime and confidence metadata.
6. Broker-specific read-only account adapters with identifier mapping and freshness checks. The broker-neutral snapshot comparison is delivered.
7. Broker preview/what-if order endpoint with idempotency.
8. Separately approved live routing behind dual confirmation and kill switch.

## Data quality

Every calculated output should eventually carry valuation time, data source, staleness, currency-conversion source and model version. Missing or stale inputs should fail visibly rather than silently falling back to zero.
