# Architecture and invariants

MacroTrading v0.6 consolidates the previous browser-only paper workbench and Python research branch, and adds reviewed discovery, reference-data acquisition and portfolio evaluation. Python is the sole calculation authority. The modular browser UI renders API snapshots and submits explicit actions; it does not maintain a second portfolio engine. The [blueprint](BLUEPRINT.md) defines the complete delivered behavior and implementation-independent acceptance criteria.

| Layer | Modules | Responsibility |
|---|---|---|
| Research | `models`, `scoring`, `calendars`, `engine` | Validate evidence, replay accepted state, derive WATCH, apply lifecycle and confirm eligible sessions |
| Portfolio | `portfolio`, `scenarios`, `execution` | Currency conversion, explicit valuation units, cash/cost accounting, currency/curve/spread/basis/funding stress and paper controls |
| Data | `ingestion`, `market_data`, `ai`, `discovery`, `migration` | Bounded retrieval, source and theme proposals, reference history and explicit legacy import |
| Evaluation | `evaluation`, `portfolio_evaluation` | Isolated research replay, expression and allocation-policy evaluation |
| Application | `service`, `research_workflow`, `storage` | Reviewed acceptance, atomic domain transitions, version conflicts, immutable run records and audit history |
| Transport | `server`, `run.py` | Loopback HTTP, same-origin token checks, limited static serving and validated JSON requests |
| Presentation | `public/js`, `html_report` | Thirteen browser views and portable reports from the authoritative result |

## Durable state

SQLite runs in WAL mode. `objects` stores versioned current configuration, workspace, accepted research, pending market snapshots and theme drafts. `runs` retains the exact input, previous research state, configuration, portfolio snapshot, manifest, JSON result and rendered HTML. `source_fetches` stores raw responses and hashes; `inbox` tracks pending/accepted/rejected candidates. `decisions` holds analyst decisions. `audit` chains action hashes.

Research runs and portfolio actions use `BEGIN IMMEDIATE` transactions. An exception rolls back the complete transition. Browser edits carry an expected object version; stale writes return HTTP 409. An already-filled execution retry returns the original fill without moving cash again. The local database is not an independently tamper-proof record: its administrator can rewrite both records and hashes.

## Key invariants

1. Missing observations do not become negative evidence. Freshness and coverage remain distinct from scores.
2. Accepted evidence is identified by immutable ID/content. Corrections use a new ID and `supersedes`.
3. Invalidated, suspended and archived states override the score band. Resume requires a new explicit analyst event; an active market invalidation still suspends the theme.
4. Repeated dates never count as two sessions. Matching benchmark timestamps, currency, source, convention and a configured calendar are required.
5. Research scores and AI claims never generate position quantities. Proposals evaluate user-specified quantities; paper staging and execution are separate actions.
6. Funded-asset buys debit currency cash. Closing a position realizes P&L and preserves the remaining cost basis; flipping resets the basis. Futures contribute unrealized value to NAV, with notional exposure tracked separately.
7. Order controls are rechecked against current holdings and marks at execution. A simulated limit cannot fill outside its price after slippage.
8. Replay uses a fresh research state. Backtest signals take effect only at the next observed close and incur modeled costs.
9. Discovery acceptance creates an unscored theme. Numerical component baselines and market proxies need separate review; no discovery path creates orders.
10. Currency stress includes foreign cash and foreign asset translation. Missing required risk sensitivities make scenario totals unavailable instead of silently zero.
11. Repeated reference downloads preserve the first accepted availability time. Retrieval time is not rewritten as an assumed historical publication time.

## Integration boundary

The integration commit joins the browser snapshot at `45f7af025f2035b98b4c733b97ee09f6121e8706` and Python snapshot at `f87f24ec7346966f55701a2edc5639994435396c` in one source tree, retaining both histories as commit parents. The v0.6 release builds on that integration and its tutorial commit, consolidating the working application on `main`. Old browser calculations are replaced by the server model. Browser workspace exports migrate explicitly; old fills are preserved as historical records, not replayed. The original Python examples remain as dated reference inputs and are not a live data source.

## Limits and next work

Published XNYS and ECB/TARGET calendars cover 2026–2028. The ECB adapter supplies reference FX history with conservative retrieval-time availability. Other venues, years and point-in-time licensed price adapters remain extensions. Corrected historical market observations currently require a reviewed rebuilt input/archive, not an in-place overwrite.

Scenarios use currency translation, delta/gamma/vega, duration or supplied scalar/key-rate DV01, spread DV01, signed basis sensitivities and incremental funding costs. Full option surfaces, contract-specific settlement, variation-margin journals, corporate actions and calibrated factor covariance are not implemented. The portfolio evaluator is self-financing over aligned base-currency series; it is not a raw-derivative execution simulator or evidence of an edge.

Sources are refreshed on demand, not scheduled. Source fetching has size/timeout/host controls, but the app is intended for a trusted local operator using known publishers. The loopback server is not a multi-user or Internet-facing service.
