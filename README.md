# MacroTrading v0.5

An integrated local workspace for macro research, portfolio risk and paper decisions. Python owns research, accounting and persistence; the browser uses the same API and stored snapshots. **Paper only.** There are no live broker execution routes.

## Start

The implementation is published on [`codex/integrated-research-workbench`](https://github.com/AInewbie/MacroTrading/tree/codex/integrated-research-workbench). Use that branch until the integration pull request is merged into `main`.

Use Python 3.11+ with IANA timezone data installed (included in most Linux/macOS systems; on systems without it, install `tzdata` in your Python environment).

```bash
git clone --branch codex/integrated-research-workbench https://github.com/AInewbie/MacroTrading.git
cd MacroTrading
python3 run.py
```

Open **http://127.0.0.1:4173**. Python's standard library is sufficient at runtime when timezone data is available. Node is optional: `node server.mjs` starts the same Python server. `python3 run.py --port 4174 --data-dir ./var-second` creates an isolated workspace.

**Read [the full feature and user guide](docs/user-guide.html)** (download/open the HTML, or choose *Features & user guide* inside the app). It contains a first-run walkthrough, every screen, data formats, valuation units, source setup, recovery and known limits.

## What changed

- Consolidated the browser and Python prototypes into a single application, SQLite database and domain model.
- Accepted evidence and component changes persist. Invalidation overrides scores. Explicit resume decisions and superseding evidence retain provenance.
- Market confirmation uses distinct adjacent eligible sessions, a versioned close calendar, matching timestamps/currencies and validated returns. Missing data remain unavailable.
- Corrected cash, average cost, realized P&L, futures NAV, FX conversion, limit execution, repeat submission and zero-position rebalance behavior.
- Added source acquisition and a manual evidence inbox, source-body hashes, immutable run HTML/JSON, a decision journal and a hash-chained action log.
- Added portfolio scenarios, option sensitivities, rates DV01, factor overlap, implementation constraints, expression proposals and estimated costs.
- Added chronological event replay and a single-expression paper backtest with next-observation execution and modeled costs.
- Added editable risk/scoring settings, research history, full data tables, ranking, import/export, explicit legacy migration and state recovery.
- Optional OpenAI extraction proposes source-cited claims for review. It cannot accept evidence, change scores or create orders.

## First run

1. Select **Load historical example** before committing a current-dated review.
2. Inspect **Research themes**, **Portfolio risk**, **All data** and the saved HTML report.
3. The portfolio is **synthetic**, and the dated research fixture's claims and prices are **not independently verified**. They demonstrate software behavior.
4. For your own work, import/edit your holdings and economics, turn off **Synthetic demo input mode** in Settings, and review the resulting data issues.
5. Refresh approved sources, then review candidates individually. No source is fetched automatically at startup.

The supplied XNYS calendar covers **2026 only**. Other venues/years require explicit verified calendars. The European defense proxy remains unconfigured because a matching listing/calendar has not been established.

## Optional AI

Set `OPENAI_API_KEY` and `OPENAI_MODEL` in the server's environment and restart. No model is selected automatically. The app does not load `.env` files. Click **Propose claims with AI** after selecting 1–10 pending candidates. This sends their titles/summaries and theme definitions to OpenAI; provider billing applies. The implementation limits output to 2,000 tokens and requests to five attempts per day, not a guaranteed currency spending cap. Manual research works without credentials.

## Data and recovery

The default database is `var/macrotrading.sqlite3`. Browser storage is not the authoritative store. Failed writes roll back; stale browser versions receive a conflict and must reload.

- **Workspace export**: instruments, holdings, cash, policy and paper history.
- **State backup**: current accepted research, workspace and configuration. Restoring rebuilds a run report; imported unfilled orders require fresh staging.
- **Full archive**: stop the server, then copy the complete `var` directory, including any SQLite sidecar files. This retains source bodies, immutable reports and action history.

Original browser v1/v2 workspace exports use the explicit import path. Their old fills are retained under `legacy_history` and never replayed. Supply missing economics and reconcile the resulting balances. Old Python v1 alert state cannot reconstruct accepted evidence; rebuild from archived inputs.

## Verification

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
npm run check
npm test
```

Python tests cover research persistence, timing/calendar gates, cash and derivative accounting, idempotency, source quarantine, migration, replay, mocked AI, backup/restart, conflicts and local HTTP guards. JavaScript tests cover output escaping, CSV formula protection and rendering every view against fresh/populated API snapshots. GitHub Actions runs these checks with Python 3.11 and 3.12 and Node 22.

Browser automation was not executed in the implementation environment: a browser binary was unavailable and its download failed. Live source access and paid AI requests also remain environment-dependent; their parser and adapter tests use fixtures/mocks.

## Command-line research reports

```bash
PYTHONPATH=src python3 -m macrotrading.cli \
  --config config/live_themes.json \
  --input examples/integrated_research_run.json \
  --full-review --html-out review.html --state-out state.json
```

Pass `--state state.json` on later chronological runs; `--json` emits the complete result. The CLI is a standalone research tool: it does not update the web app's SQLite database or include its portfolio.

## Scope

This is a single-user research/paper workbench. WATCH is a prioritisation rubric, not expected return or calibrated probability. Evidence quality is a source-breadth/freshness heuristic. Portfolio stress is an approximation using user-supplied sensitivities, not full option repricing or broker margin. No position optimizer, validated trading edge, scheduler, corporate-action service, cross-venue market feed, live broker integration or multi-user hosting is included.

See [architecture](docs/architecture.md), [data contracts](docs/data-contracts.md) and [the user guide](docs/user-guide.html) before extending or operating the app.
