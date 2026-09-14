# Changelog

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
