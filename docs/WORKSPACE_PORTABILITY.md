# Workspace portability

MacroTrading exports one schema-versioned JSON document containing the normalized instrument universe, portfolio, paper-execution policy, order records, local audit history, optional broker snapshot and optional theme-research results.

## Use

1. Open **Execution controls** and choose **Export workspace**.
2. Keep the downloaded JSON as a browser-independent backup.
3. Choose **Import workspace**, select a MacroTrading JSON file and review the replacement confirmation.
4. After import, inspect the portfolio, universe, controls and orders before staging new paper activity.

## Validation and execution boundary

- The format and schema version must match exactly.
- Instrument identifiers must be unique; every position and order must reference an included instrument.
- Asset classes, currencies, quantities, prices, limits and option fields are range-checked.
- Collections and the file itself have explicit size limits.
- Unknown fields are discarded instead of becoming application state.
- Unfilled imported orders are marked **Imported**, fail closed and have no submit action. They must be recreated and pass current controls before paper submission.
- Historical filled orders remain read-only records and are never replayed.
- The document declares `paper-only`; any other execution mode is rejected.
- No brokerage credential, API key or browser secret is exported. Account identifiers and research provenance are retained, so workspace files should still be handled as sensitive data.

Import replaces only this browser's local workspace after explicit confirmation. It sends no data to a broker or external service.
