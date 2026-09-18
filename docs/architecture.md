# Architecture and invariants

MacroTrading v0.5 consolidates the previous browser-only paper workbench and Python research branch. Python is the sole calculation authority. The modular browser UI renders API snapshots and submits explicit actions; it does not maintain a second portfolio engine.

| Layer | Modules | Responsibility |
|---|---|---|
| Research | `models`, `scoring`, `calendars`, `engine` | Validate evidence, replay accepted state, derive WATCH, apply lifecycle and confirm eligible sessions |
| Portfolio | `portfolio`, `execution` | Currency conversion, explicit valuation units, cash/cost accounting, scenarios and paper controls |
| Data | `ingestion`, `ai`, `migration`, `evaluation` | Bounded retrieval, source review proposals, explicit legacy import and isolated evaluation |
| Application | `service`, `storage` | Atomic domain transitions, version conflicts, immutable run records and audit history |
| Transport | `server`, `run.py` | Loopback HTTP, same-origin token checks, limited static serving and validated JSON requests |
| Presentation | `public/js`, `html_report` | Eleven browser views and portable reports from the authoritative result |

## Durable state

SQLite runs in WAL mode. `objects` stores versioned current configuration, workspace and accepted research. `runs` retains the exact input, previous research state, configuration, portfolio snapshot, manifest, JSON result and rendered HTML. `source_fetches` stores raw responses and hashes; `inbox` tracks pending/accepted/rejected candidates. `decisions` holds analyst decisions. `audit` chains action hashes.

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

## Integration boundary

The integration commit joins the browser snapshot at `45f7af025f2035b98b4c733b97ee09f6121e8706` and Python snapshot at `f87f24ec7346966f55701a2edc5639994435396c` in one source tree, retaining both histories as commit parents. The implementation is published on `codex/integrated-research-workbench` for review before merging into `main`. Old browser calculations are replaced by the server model. Browser workspace exports migrate explicitly; old fills are preserved as historical records, not replayed. The original Python examples remain as dated reference inputs and are not a live data source.

## Limits and next work

Only a 2026 XNYS calendar is supplied. Add tested venue/year calendars and point-in-time licensed price adapters before expanding automatic confirmation. Corrected historical market observations currently require a reviewed rebuilt input/archive, not an in-place overwrite.

Scenarios use delta/gamma/vega, duration or supplied DV01 and simple linear shocks. Full option surfaces, contract-specific settlement, variation-margin journals, corporate actions and calibrated factor covariance are not implemented. The backtest is a research diagnostic, not a multi-asset execution simulator or evidence of an edge.

Sources are refreshed on demand, not scheduled. Source fetching has size/timeout/host controls, but the app is intended for a trusted local operator using known publishers. The loopback server is not a multi-user or Internet-facing service.
