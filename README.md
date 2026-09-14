# MacroTrading

Risk-first multi-asset portfolio construction and paper-execution workbench.

## Current release: 0.4.0

The first release provides one normalized portfolio and order model for:

- stocks and equity indices;
- sovereign/corporate-style bond instruments;
- spot FX and FX options;
- equity options;
- ETFs and ETF options;
- commodities/futures-style instruments.

It calculates market value, delta-adjusted exposure, P&L, DV01, vega and gamma; aggregates exposure by asset class; runs transparent deterministic scenarios; generates target-rebalance orders; applies pre-trade limits; and fills approved orders through a simulated paper broker.

The workspace can be exported as schema-versioned JSON and restored in another browser. Imports validate the entire portfolio and instrument graph before replacing local state. Unfilled imported orders are made non-executable and require fresh staging and controls.

A read-only reconciliation workspace accepts a validated broker-neutral account snapshot, masks the account identifier, and compares broker cash and quantities with the local model. It surfaces matched positions, quantity differences, missing broker positions and unmapped holdings without changing the portfolio or creating orders. Use the built-in synthetic snapshot or follow [the snapshot contract](docs/BROKER_RECONCILIATION.md).

The **Theme lab** introduces evidence-first, AI-assisted signal research across news, blogs, macro releases, financial data, alternative data and catalysts. Candidate themes retain evidence provenance, confidence, trade-expression fit, catalysts and invalidation conditions. Deterministic policy code scores reliability, freshness, novelty, source breadth and catalyst support. The included run is synthetic and offline; the AI provider boundary is specified but remains disabled until a server-side provider, approved sources and usage budget are configured.

**Live brokerage execution is disabled.** Synthetic prices and simplified sensitivities are provided only to exercise the workflow. This release is not investment advice, a valuation system, or a production order-management system.

## Run

Requires Node.js 22.13 or newer. No installation or compilation is needed.

```bash
node server.mjs
```

Open the complete address printed in the terminal. The interface works at phone and desktop widths and persists the synthetic workspace in browser local storage.

## Verify

```bash
npm test
npm run check
```

## Architecture

```text
src/domain      normalized instrument and order contracts
src/engine      portfolio analytics, risk checks and scenarios
src/adapters    paper broker and fail-closed live broker boundary
src/data        synthetic demonstration universe, portfolio and theme evidence
src/ui          modular theme-research presentation
public          zero-build browser interface
test            deterministic unit and integration tests
docs            design, roadmap and execution controls
```

## Production path

Before any live use, the project requires a chosen broker, authenticated account discovery, real instrument identifiers, live/reference market data, currency conversion, trading calendars, full option and bond valuation, margin estimates, reconciliation, idempotent order submission, durable audit storage, secrets management, monitoring and a separately approved versioned risk policy.

See [architecture and roadmap](docs/ARCHITECTURE.md), [theme detection](docs/THEME_DETECTION.md), [execution safety](docs/EXECUTION_SAFETY.md) and [broker reconciliation](docs/BROKER_RECONCILIATION.md).
Workspace backup and restore behavior is documented in [workspace portability](docs/WORKSPACE_PORTABILITY.md).
