# Broker reconciliation

MacroTrading 0.3 accepts a local, broker-neutral JSON snapshot and compares it with the current portfolio. The workflow is read-only: importing or clearing a snapshot cannot change cash, positions, targets, staged orders or fills.

## Snapshot contract

```json
{
  "format": "macrotrading-broker-snapshot",
  "schemaVersion": 1,
  "asOf": "2026-09-14T12:00:00.000Z",
  "account": {
    "broker": "Example Broker",
    "accountId": "PAPER-U1234567",
    "baseCurrency": "USD",
    "cash": 997500
  },
  "positions": [
    { "instrumentId": "stk-aapl", "brokerSymbol": "AAPL", "quantity": 610 }
  ]
}
```

The file is limited to 1 MB and 2,000 unique position identifiers. Dates, currencies, identifiers, strings and numeric ranges are validated before state changes. Unknown `instrumentId` values are accepted as unmapped breaks so they remain visible instead of being discarded.

## Comparison states

- **Matched**: broker and model quantities agree.
- **Quantity break**: the mapped instrument exists in both, but quantities differ.
- **Missing at broker**: a model position is absent from the snapshot.
- **Broker only**: a known instrument is present only at the broker.
- **Unmapped**: the broker position has no matching local instrument.

Cash is compared separately. A successful reconciliation requires matching cash, base currency and all position quantities.

## Safety boundary

Snapshots are processed locally in the browser and may be preserved in a workspace export. The interface masks the account ID, but exported JSON retains it for future comparison. Do not include credentials, API keys or tokens. No broker connection, order generation, portfolio mutation or live execution is available in this workflow.
