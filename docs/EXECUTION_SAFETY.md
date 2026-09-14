# Execution safety

## Current state

Only `PaperBroker` can fill an order. `LiveBrokerDisabled` always throws. No credentials are read, no external host is contacted, and no real order can leave the application.

## Requirements before enabling a live adapter

- Explicit broker and account selection; never infer an account.
- Read-only reconciliation completed before order permissions are requested.
- Versioned limits for order notional, gross/net exposure, concentration, option contracts, commodities, leverage, liquidity and stale market data.
- Broker-side preview or margin check where supported.
- Idempotency keys and duplicate-order protection.
- Trading-hours, tick-size, lot-size and instrument-identifier validation.
- Human-readable final order summary and explicit live confirmation.
- Durable append-only request, acknowledgement, fill, rejection and cancellation log.
- Global kill switch, per-strategy disable switch and cancel-all procedure.
- Reconciliation of partial fills, corporate actions, expiries, exercises and assignments.
- Secrets stored outside source control and redacted from logs.

The risk gateway must run again immediately before submission; a staged approval cannot be assumed valid after prices, positions or limits change.
