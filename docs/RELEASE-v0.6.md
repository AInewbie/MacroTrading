# MacroTrading v0.6 release record

## Delivered changes

- Consolidated release based on the integrated application plus tutorial branch.
- Expanded and formatted Python/JavaScript for reviewability, with formatter/static checks and coverage output in CI.
- Added reviewed theme discovery, explicit citations/counterarguments, new-theme acceptance and existing-universe expression proposals.
- Added an official ECB reference-history adapter, cross-pair calculations, staged acceptance, conservative known-at timestamps and 2026–2028 calendar definitions.
- Corrected foreign-currency cash stress and combined local/translation P&L; added explicit key-rate, spread, basis and funding scenarios with missing-input handling.
- Added multi-series allocation evaluation, benchmark comparison, Sharpe/Sortino/Calmar, attribution and exact cost reconciliation.
- Added dashboard views and controls, report regressions, browser workflow tests and the implementation-independent [blueprint](BLUEPRINT.md).

## Validation

Local Python suite: 69 tests passed after these changes, including financial examples, chronological availability, reviewed acceptance, accounting, persistence and report escaping. Statement coverage is 81% across the application (the separate CLI smoke check is outside that coverage run).

All five JavaScript tests pass, including rendering of every original and new view on both fresh and populated state. Python/JavaScript formatters, static checks and all nine JavaScript module syntax checks pass. GitHub Actions runs Python 3.11/3.12, JavaScript checks and desktop/mobile browser workflows. Final CI result is recorded in the release pull request.

No paid model request was made. Optional AI generation is validated with structured-output contracts and mocks; it requires the operator's server-side credentials and model selection.

## Public-data worked example

`examples/ecb_eurusd_2026-09-18.json` contains reference observations transcribed from the [official ECB daily USD table](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/eurofxref-graph-usd.en.html), checked 19 September 2026. It is labelled as a page transcription, not a raw XML capture or a point-in-time archive. The example portfolio balances and expression size are illustrative, not the user's holdings.

Run:

```bash
python3 scripts/run_reference_example.py
```

The command writes a report and reproducible JSON under `var/reference-example`. It uses no network or API key and marks the reference instrument non-tradable. The default application still starts with its explicitly synthetic sample portfolio; it does not silently load this example into user state.

## Environment limitations observed during development

Direct ECB acquisition from the development sandbox failed at DNS resolution. The cloud browser also could not open the XML resource. The parser, pair normalization and acceptance path were tested using explicit synthetic XML fixtures. Official numerical observations for the worked example were independently read from the ECB's public HTML table. A successful application-side live download is not claimed here.

The cloud browser could not access the local dashboard in this environment. Desktop/mobile interaction tests are therefore supplied and run through GitHub Actions on isolated synthetic workspaces. These tests do not make live-provider availability claims.

## Preserved history and exclusions

The release retains prior implementation and tutorial history. The divergent `builder/ai-theme-research` commit is preserved in `archive/ai-theme-research-2026-09-19`. Prior open PRs are superseded by the consolidated release after merge; historical branches are retained.

Live brokerage execution, broad exchange market-data coverage, derivative settlement, full repricing, covariance estimation, optimization and a validated investment edge remain outside this release. See the blueprint for exact boundaries.
