# Data contracts — v0.6

The [blueprint](BLUEPRINT.md) is the complete product specification. This document provides compact input and unit references.

Inputs are JSON unless a market CSV is explicitly imported. Numbers must be finite numeric values, booleans must be actual `true`/`false`, and timestamps must include a timezone. Date-only values are treated as UTC midnight where supported; use full timestamps for point-in-time analysis. The server limits request bodies to 8 MB and each run to 5,000 evidence events and 5,000 market observations.

## Research run

```json
{
  "as_of": "2026-09-18T21:00:00Z",
  "label": "Reviewed daily research",
  "evidence": [{
    "id": "manual-unique-id",
    "theme_id": "japan_normalization",
    "observed_at": "2026-09-18T10:00:00Z",
    "first_known_at": "2026-09-18T12:00:00Z",
    "kind": "inference",
    "direction": "neutral",
    "material": false,
    "summary": "Example analyst inference, not a market claim.",
    "sources": [],
    "component_updates": {},
    "metadata": {}
  }],
  "market_closes": []
}
```

Kinds: `observed_fact`, `company_plan`, `policy_plan`, `economist_forecast`, `market_implied`, `inference`. Directions: `support`, `contradict`, `neutral`. Non-inference events require at least one direct source containing `url`, `title` and `published_at`. Optional source fields: `retrieved_at`, `content_hash` (SHA-256), `source_group`. Source publication/retrieval must not follow the event's first-known time or the run cutoff.

Optional event `supersedes` identifies an earlier accepted event in the same theme. Component values are 0/0.5/1 for P/F/M/C/X, and 0/1/2 for R. An unscored theme needs a defined component baseline before updates are accepted. Lifecycle metadata accepts `lifecycle_action` = `suspend`/`resume`/`archive` or `invalidation_met: true`; prefer the Decision journal UI for reviewed changes.

## Market CSV

```csv
theme_id,session_date,proxy_close,benchmark_close,proxy_return_pct,benchmark_return_pct,completed,source_url,close_at,benchmark_close_at,convention,currency,benchmark_currency
japan_normalization,2026-09-17,100,100,0,0,true,https://example.com/synthetic-fixture,2026-09-17T20:00:00Z,2026-09-17T20:00:00Z,official_close,USD,USD
```

The row above is synthetic. Use values, symbols, anchors and timestamps consistent with your actual configured proxy. `convention` is `official_close`, `adjusted_close`, `reference_rate` or `unverified`; unverified prices cannot confirm. The convention must match the configured calendar. Returns are percentage points, e.g. `1.25` = +1.25%. When consecutive validated prices are available, returns are derived and supplied values must agree within 0.06 percentage points. Two eligible adjacent sessions are required for full M and ordinary threshold confirmation. Missing returns for a single row do not lower M. Exact duplicate sessions are harmless; conflicting same-series/session observations are rejected.

Optional JSON/CSV fields `known_at`, `content_hash` and `series_id` identify availability, raw provenance and the selected economic series. The ECB adapter supplies actual retrieval as `known_at` and a 16:00 Europe/Brussels reference-observation convention; the latter is not a historical publication timestamp. A repeated identical observation keeps its original accepted availability time. A current download cannot establish point-in-time availability before retrieval.

## Workspace v3

Export wrapper: `format: "macrotrading-workspace"`, `schemaVersion: 3`, `executionMode: "paper-only"`, `workspace: {...}`. The workspace uses snake_case keys: `schema_version`, `mode: "paper"`, `demo`, `name`, `base_currency`, `cash` currency map, `instruments`, `positions`, `fx_rates`, `policy`, `orders`, `fills`, `realized_pnl` currency map.

Each instrument requires a stable `id`, `symbol`, `name`, `model`, `currency`, `price`, `multiplier`. Supply `price_at`, `lot_size`, `tick_size`, `adv`, `financing_bps` and `borrow_bps` for reviewed use. `factor_loadings` is a map of manual factor IDs to loadings. `adv` is instrument units/contracts per day, consistent with order quantity.

| Model | Units and additional data |
|---|---|
| equity | Price in quote currency per share/unit; multiplier normally 1. ETFs can use this model. |
| bond | `price_convention: "dirty_per_100"`; multiplier = face value per contract / 100. Supply `dv01` per contract per bp, or `duration` in years. |
| fx | Funded spot-unit asset priced in quote currency per unit, with explicit multiplier; not an FX forward/swap valuation model. |
| option | Premium × quantity × multiplier. Require `option_type` Call/Put, `expiry`, `strike`, `underlying_price`, `delta`, `gamma`, `vega`. Vega is quote currency per contract per **one volatility percentage point**, without another multiplier. Short options require `margin_rate`. |
| future | Price × multiplier × quantity is notional exposure. NAV receives quantity × multiplier × (mark − average entry). Require `risk_factor` equity/commodity/fx/rates and `margin_rate`. |

A position contains `instrument_id`, signed `quantity`, `average_price`, optional `theme_id`, and optional `target_weight` as a signed fraction of NAV in delta exposure. A zero-quantity row can retain a target. The app uses average cost, not tax lots.

Additional risk inputs: `fx_base` identifies the currency represented by a funded FX unit; `key_rate_dv01` maps tenor IDs to quote-currency DV01 per contract per bp; `spread_dv01` uses the same units; `basis_sensitivity` maps factor IDs to signed P&L per contract per bp; `funding_notional` is a nonnegative quote-currency amount per contract. An explicit zero is different from a missing value. If scalar and key-rate DV01 are both supplied, their sum must agree within 0.1%.

Optional `workspace.scenarios` replaces the default scenario list. A scenario has `id`, `name`, bounded scalar market shocks and optional `currency_shocks`, `curve_bp`, `spread_bp`, `basis_bp`, `funding_bp` and `horizon_days`. See the blueprint and the dashboard's editable templates for exact formulas and examples. Missing required inputs make the affected scenario total unavailable and block a risk-constrained proposal.

FX rows: `{"from":"EUR","to":"USD","rate":1.1,"as_of":"2026-09-18T12:00:00Z"}`. Rate means units of `to` per unit of `from`. The graph can invert/chain current quotes; missing conversion makes affected totals unavailable. ECB reference rates have date precision and are not intraday execution marks. Cross-currency trades require sufficient cash in the order's own currency; FX conversion for reporting does not move cash.

## Broker reconciliation

```json
{
  "format": "macrotrading-broker-snapshot",
  "schemaVersion": 1,
  "asOf": "2026-09-18T21:00:00Z",
  "account": {"accountId":"example-1234","broker":"Example","baseCurrency":"USD","cash":100000},
  "positions": [{"instrumentId":"stk-aapl","quantity":10}]
}
```

Instrument IDs must match the workspace. Quantity differences and missing mappings are reported. Cash is only compared when currencies are genuinely comparable under the implemented single-base-cash contract. Account identifiers are masked in the output. Reconciliation never changes holdings.

## Evaluation

Research replay: `{"batches":[{"as_of":"...","evidence":[],"market_closes":[],"expected_alerts":["material_evidence:theme_id"]}]}`. Batches must be chronological and use the current configuration's baseline/anchors. Label sets are optional; precision/recall remain unavailable without labels. This replay does not reconstruct historical configuration changes automatically.

Backtest: `{"prices":[{"at":"...","close":100}],"signals":[{"known_at":"...","target":1}],"transaction_bps":5,"borrow_bps":200,"financing_bps":0}`. Supply at least three ascending unique observations. Targets range −1 to +1. Costs apply at turnover and final liquidation; borrowing/financing accrue over actual elapsed days. Volatility annualization assumes daily trading observations. No market calendar or corporate-action adjustment is inferred for this diagnostic.

Portfolio evaluation: pass `kind: "portfolio"` with the contract illustrated by [`examples/portfolio_evaluation.json`](../examples/portfolio_evaluation.json). Supply aligned positive base-currency series, timestamped target weights and a declared `data_mode` (`synthetic`, `historical_ex_post` or `point_in_time`). Historical inputs require source URLs; point-in-time observations require availability no later than valuation. Signals execute at the next observed close; holdings drift between new signals. The result includes equity, drawdown, benchmark comparison, ratios, costs and reconciling P&L attribution. Undefined statistics remain null. Raw derivative settlement, corporate actions and currency conversion are not inferred.
