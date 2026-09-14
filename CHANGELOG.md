# Changelog

## 0.4.0 — governed AI theme research

- Add a model-adapter boundary for structured AI theme proposals, with live providers failing closed.
- Demonstrate theme detection across synthetic alternative data, news, blogs, macro data, financials, research and catalysts.
- Independently score freshness, reliability, novelty, source breadth, evidence depth, catalysts and contradictions.
- Preserve provenance, model disclosure, AI confidence, horizon, invalidation conditions and tradeable-instrument hypotheses.
- Keep themes fully separate from target construction, order staging and execution.

## 0.3.0 — read-only broker reconciliation

- Import and validate a bounded broker-neutral account snapshot without network access or credentials.
- Compare cash and position quantities against the local portfolio.
- Identify matched positions, quantity breaks, missing broker positions and unmapped broker holdings.
- Mask account identifiers in the interface and persist the snapshot with workspace backups.
- Keep reconciliation strictly informational: it cannot mutate holdings, generate orders or submit trades.

## 0.2.0 — validated workspace portability

- Export instruments, portfolio, paper controls, order records and audit history as schema-versioned JSON.
- Validate identifiers, references, numeric ranges, collection limits and the paper-only execution declaration before import.
- Require confirmation before local replacement and record the import/export actions in the audit trail.
- Demote every imported unfilled order so it cannot bypass fresh staging and pre-trade controls.
- Add a responsive workspace portability surface under Execution controls.

## 0.1.0 — initial multi-asset paper workbench

- Cover stocks, indices, bonds, FX, FX options, equity options, ETFs, ETF options and commodities in one instrument model.
- Add portfolio exposure, P&L and sensitivity aggregation.
- Add deterministic cross-asset stress scenarios and target-rebalance generation.
- Add pre-trade order, portfolio and derivative controls.
- Add staged orders, simulated fills and local audit history.
- Keep every live brokerage route disabled by design.
