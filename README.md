# MacroTrading

Risk-first macro theme analysis and multi-asset portfolio tooling. Live brokerage execution is disabled by default.

## Theme analysis engine

The first implementation turns structured evidence and completed-session market observations into reproducible research alerts. It separates observed facts, company or policy plans, economist forecasts, market-implied pricing and analyst inference.

The engine provides:

- deterministic WATCH-v1 scoring;
- material-evidence and score-change alerts;
- two-completed-session confirmation for ordinary market thresholds;
- event and persistent-breach deduplication through explicit state;
- Markdown and JSON output;
- no trade placement, paper activation or inferred portfolio P&L.

Run the included live-theme example:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
macrotrading --config config/live_themes.json --input examples/live_evidence_2026-09-16.json --state-out state.json
```

Generate the complete five-theme review instead of alert-only output:

```bash
macrotrading --config config/live_themes.json --input examples/five_theme_review_2026-09-16.json --full-review
```

Write a portable visual report on every run:

```bash
macrotrading --config config/live_themes.json --input examples/five_theme_review_2026-09-16.json --full-review --generated-at 2026-09-16T16:55:00Z --html-out MacroTrading-five-theme-review-2026-09-16.html
```

Visual system documentation: [`docs/workflow-architecture.html`](docs/workflow-architecture.html) maps the implemented research workflow, module boundaries, alert gates, portfolio approval controls and target production roadmap.

Run tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Data contract

Evidence is analyst- or model-coded before entering the deterministic layer. Every non-inference event requires a direct URL and publication date. Component changes must be explicit; missing data never become negative evidence. Market observations must identify completed sessions and use matching close conventions.

`config/live_themes.json` contains the oil/refined-fuel theme plus the four WATCH-v1 themes. The oil theme deliberately has no score until a reproducible model is specified; the historical score of 66 is not relabeled.
