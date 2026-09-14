# AI-assisted theme detection

## Objective

Detect emerging macro and cross-asset themes from licensed news, blogs, macro releases, financial data, alternative data and explicit catalyst calendars. Theme research is not an order or recommendation.

## Hybrid architecture

1. Source adapters normalize evidence and retain source, URL, publication time, underlying data time, retrieval time, entitlement and content hash.
2. Deterministic filters reject invalid, stale, duplicated or unentitled evidence.
3. An AI detector proposes structured themes, cites evidence identifiers, distinguishes observation from inference and records uncertainties.
4. Deterministic code scores reliability, freshness, novelty, independent-source breadth and catalyst support with user-visible weights.
5. An instrument mapper suggests expressions only from the validated universe, including stance, fit and rationale.
6. A separate governed signal-promotion step will require historical evaluation and explicit approval before portfolio optimization can consume a theme.

The current release implements normalized synthetic evidence, the deterministic scorer, a strict AI output contract, instrument-expression mapping and the research UI. No external source or AI endpoint is called.

## Anti-leakage and evaluation

- Store both publication time and the timestamp of the underlying observation.
- Build historical snapshots using only information available at each evaluation time.
- Deduplicate syndicated stories and related sources before measuring corroboration.
- Measure theme precision, time-to-detection, stability, decay, realized forward returns, drawdown and turnover by horizon.
- Maintain golden historical cases and explicit non-theme/noise cases.
- Compare AI-assisted detection with deterministic and naive keyword baselines out of sample.
- Version prompts, models, schemas, source sets, scoring weights and instrument mappings.

## Safety boundary

Evidence is untrusted data, not instructions. The AI output schema contains no quantity, target-weight or order field. Theme candidates cannot call the order planner or broker. Credentials must stay server-side; source licensing and redistribution constraints must be enforced before any production ingestion.
