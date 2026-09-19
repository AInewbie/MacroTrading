# Contributing

Start with [the blueprint](docs/BLUEPRINT.md), especially data units, action boundaries and behavioral acceptance examples. Keep research, valuation, source adapters, orchestration and presentation separate.

Use an isolated data directory. Do not commit personal positions, credentials, source-account tokens, databases or generated local state. Existing source examples are clearly labelled; preserve those labels.

```bash
python3 -m pip install -r requirements-dev.txt
npm ci
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m ruff check --select F src tests scripts run.py
python3 -m ruff format --check src tests scripts run.py
npm run check
npm test
npm run format:check
npx playwright install chromium
npm run test:browser
```

Browser tests create temporary synthetic workspaces on ports 4173 and 4174. Stop a normal local application using either port before running them. The tests do not require an API key or market-data network connection.

Add meaningful regression cases for changes to financial math, timing, imports, persistence or review boundaries. Avoid tests that simply restate implementation lines. Document changes to units, time conventions or score meaning as product decisions. Keep provider/model mocks distinguishable from successful live requests. Do not turn missing risk into zero or generate quantities from research scores.
