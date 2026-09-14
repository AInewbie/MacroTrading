# Governed AI theme research

MacroTrading 0.4 introduces a research layer for detecting market themes across heterogeneous evidence. It deliberately separates probabilistic model output from deterministic evidence controls and from the order lifecycle.

## Pipeline

1. Source adapters provide timestamped evidence with a source type, provenance label, reliability prior, novelty estimate and summary.
2. A theme-model adapter proposes a structured thesis, horizon, model confidence, supporting and contradicting evidence, catalysts, invalidation conditions and possible instrument mappings.
3. Deterministic code validates every reference and scores evidence freshness, reliability, novelty, source breadth, depth, catalysts and contradictions.
4. The interface shows AI confidence separately from the evidence score. It never converts a theme into a target or order.

The included demonstration uses fixed synthetic evidence and `SyntheticThemeModel`; `LiveThemeModelDisabled` fails closed. No external article, account, model endpoint or paid data service is accessed.

## Evidence model

Supported source types are alternative data, news, blogs, macro data, financials, research and catalysts. Evidence IDs must be unique, timestamps valid, numeric priors between zero and one, and summaries bounded. Theme references must resolve to preserved evidence items so a claim cannot silently lose its provenance.

The evidence score ranges from 0 to 100 and combines:

- freshness: 25%;
- reliability: 25%;
- source breadth: 15%;
- novelty: 15%;
- supporting-evidence depth: 10%;
- explicit catalysts: 10%;
- a contradiction penalty of up to 15 points.

These weights are transparent research defaults, not a forecast calibration. The model-supplied confidence is never included in the deterministic evidence score.

## Instrument mappings and safety

Mappings express only `Long`, `Short` or `Watch` research stances with a rationale. They are hypotheses, not target weights, expected returns, sizing recommendations or orders. There is intentionally no code path from a theme result to `createOrder`, the rebalance engine or a broker adapter.

Before enabling live inputs, the project requires licensed data sources, source-specific freshness and reliability policies, duplicate/rumour controls, prompt-injection isolation, citation retrieval, model/version logging, evaluation against historical outcomes, cost limits and secrets management. Converting research into portfolio targets requires a separately reviewed signal contract, risk budget and human approval policy.
