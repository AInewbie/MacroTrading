# MacroTrading v0.6

A local macro research and paper-portfolio workbench: discover and challenge themes, review sources and market observations, inspect portfolio consequences, and preserve reproducible decisions.

**[Product blueprint](docs/BLUEPRINT.md)** · **[User guide](docs/user-guide.html)** · **[Release and validation record](docs/RELEASE-v0.6.md)**

## Start

```bash
git clone https://github.com/AInewbie/MacroTrading.git
cd MacroTrading
python3 run.py
```

Open **http://127.0.0.1:4173**. Keep the terminal running. Python 3.11+ with IANA timezone data is sufficient; install `tzdata` if your operating system does not provide it. Node is optional at runtime.

For an isolated workspace:

```bash
python3 run.py --port 4174 --data-dir ./var-second
```

The default portfolio is explicitly synthetic. Review/import your holdings and instrument economics, then turn off **Synthetic demo input mode** in Settings. Starting the app makes no provider requests. There is no scheduler or live brokerage execution.

## What is delivered

- Thirteen dashboard views sharing one calculation and persistence layer.
- Source review, immutable evidence provenance, WATCH prioritization, contradictions and persistent lifecycle decisions.
- Offline headline screening and optional AI proposals for **new** themes, with citations, counterarguments and configured instrument expressions. Acceptance is a separate, unscored human decision.
- An official ECB reference-FX history adapter, pair conversion, visible availability/freshness, reviewed proxy acceptance and published 2026–2028 calendars.
- Multi-asset paper accounting, foreign-currency cash/asset translation, rates/key-rate, spread, basis and funding stress, and before/after expression analysis.
- Version-checked state, paper-order idempotency, recoverable exports and hash-linked audit events.
- Evidence replay and portfolio evaluation with benchmark, Sharpe/Sortino/Calmar, attribution, carry and transaction costs.
- Portable HTML/JSON run archives and an implementation-independent blueprint for rebuilding the product in another stack.

## A practical workflow

1. **Sources & evidence:** refresh approved publishers and review candidates.
2. **Theme discovery:** screen headlines or ask the configured AI for proposals; inspect evidence and accept/reject explicitly.
3. **Research themes:** define a score baseline, fundamental tests, catalyst and invalidation.
4. **Market data:** fetch a reference pair, review the proxy and accept the history.
5. **Portfolio risk:** compare a user-sized expression with existing holdings, scenarios and implementation limits.
6. **Run archive:** open the exact saved report and input/result JSON.

ECB observations are daily reference rates for research/reporting, **not executable quotes**. Broad equity/bond/futures/options feeds are still provider extensions. Missing inputs remain unavailable.

## Reproduce the public-data example

```bash
python3 scripts/run_reference_example.py
```

This produces `var/reference-example/reference-workflow.html` and JSON using a labelled transcription of official ECB observations and **illustrative cash balances**, not your portfolio. It requires no network or API key. The reference-only expression remains blocked from paper execution.

## Optional AI

Set `OPENAI_API_KEY` and `OPENAI_MODEL` in the server environment and restart. No model is chosen implicitly; `.env` files are not loaded. Explicit AI actions send selected source summaries, theme definitions and, for discovery, instrument descriptions. Keys are never sent to the browser or included in exports.

Extraction and discovery share five attempted calls per day; output caps are 2,000 and 4,000 tokens respectively. Provider charges apply; these caps are not a monetary spending guarantee. AI cannot accept evidence, set component scores, change risk appetite, size positions or execute orders.

## Validation and development

See [CONTRIBUTING](CONTRIBUTING.md) for setup. GitHub Actions runs Python 3.11/3.12 regression/HTTP checks, coverage, JavaScript view checks, formatting/static checks, CLI reporting and desktop/mobile browser workflows.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
npm ci
npm run check
npm test
```

Tests use explicit fixtures for provider/model responses. A parser test is not evidence of live connectivity. See the [release record](docs/RELEASE-v0.6.md) for observed environment restrictions and actual validation results.

## Data and limits

State lives in `var/macrotrading.sqlite3`. Browser storage is not authoritative. Export a workspace or state backup from Settings. For a complete archive, stop the application and copy the full `var` directory, including SQLite sidecars.

WATCH is a prioritization rubric, not probability or expected return. Stress calculations use supplied sensitivities, not full repricing. Portfolio evaluation uses aligned base-currency indices, not raw derivative settlement. No optimizer, validated investment edge, live broker integration or multi-user hosting is included.

The [blueprint](docs/BLUEPRINT.md) states original objectives, design decisions, equations, units, data contracts, workflows, acceptance examples and remaining work. The canonical consolidated release is on `main`; earlier branches are retained or archived for history, not alternative application runtimes.
