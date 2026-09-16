from __future__ import annotations

from copy import deepcopy
from typing import Any

from .models import EvidenceEvent, MarketClose
from .scoring import score_band, validate_components, watch_v1_score


class AnalysisEngine:
    """Apply evidence, market confirmation, scoring and deduplication rules."""

    def __init__(self, config: dict[str, Any], state: dict[str, Any] | None = None):
        self.config = config
        self.state = deepcopy(state or {"seen_event_ids": [], "active_breaches": {}})

    def analyze(
        self,
        evidence: list[EvidenceEvent],
        closes: list[MarketClose] | None = None,
    ) -> dict[str, Any]:
        closes = closes or []
        seen = set(self.state.setdefault("seen_event_ids", []))
        alerts: list[dict[str, Any]] = []
        results: dict[str, Any] = {}

        by_theme: dict[str, list[EvidenceEvent]] = {}
        for event in evidence:
            if event.theme_id not in self.config["themes"]:
                raise ValueError(f"unknown theme: {event.theme_id}")
            by_theme.setdefault(event.theme_id, []).append(event)

        closes_by_theme: dict[str, list[MarketClose]] = {}
        for close in closes:
            if close.completed:
                closes_by_theme.setdefault(close.theme_id, []).append(close)

        for theme_id, spec in self.config["themes"].items():
            components = deepcopy(spec.get("components"))
            prior_score = watch_v1_score(components) if components else None
            new_events = [e for e in by_theme.get(theme_id, []) if e.id not in seen]

            for event in sorted(new_events, key=lambda item: item.observed_at):
                if components and event.component_updates:
                    components.update(event.component_updates)
                    validate_components(components)
                if event.material:
                    alerts.append({"type": "material_evidence", "theme_id": theme_id, "event_id": event.id})
                seen.add(event.id)

            market = self._evaluate_market(theme_id, spec, closes_by_theme.get(theme_id, []))
            if components and market["m_component"] is not None:
                components["M"] = market["m_component"]

            score = watch_v1_score(components) if components else None
            if (
                score is not None
                and prior_score is not None
                and abs(score - prior_score) >= 10
                and new_events
            ):
                alerts.append({"type": "score_change", "theme_id": theme_id, "from": prior_score, "to": score})

            if market["new_breach"]:
                alerts.append({"type": "confirmed_market_breach", "theme_id": theme_id, "side": market["breach_side"]})

            results[theme_id] = {
                "title": spec["title"],
                "hypothesis": spec["hypothesis"],
                "status": score_band(score) if score is not None else spec["status"],
                "score": score,
                "components": components,
                "new_evidence": [self._event_dict(e) for e in new_events],
                "market": market,
                "counterdrivers": list(spec.get("counterdrivers", [])),
                "expression": dict(spec.get("expression", {})),
                "fundamental_tests": list(spec.get("fundamental_tests", [])),
                "catalysts": list(spec.get("catalysts", [])),
                "invalidation": spec.get("invalidation", "Not specified."),
                "paper_risks": list(spec.get("paper_risks", [])),
                "decisions": list(spec.get("decisions", [])),
                "invalidation_met": any(e.metadata.get("invalidation_met", False) for e in new_events),
                "research_only": True,
            }

        self.state["seen_event_ids"] = sorted(seen)
        return {"themes": results, "alerts": alerts, "state": self.state}

    def _evaluate_market(self, theme_id: str, spec: dict[str, Any], closes: list[MarketClose]) -> dict[str, Any]:
        proxy = spec.get("proxy")
        if not proxy or not closes:
            return {"m_component": None, "relative_from_anchor_pct": None, "new_breach": False, "breach_side": None}

        ordered = sorted(closes, key=lambda x: x.session_date)
        qualifying: list[bool] = []
        direction = proxy["hypothesis_direction"]
        for close in ordered[-2:]:
            if close.proxy_return_pct is None:
                qualifying.append(False)
                continue
            if close.benchmark_return_pct is None:
                daily_signal = close.proxy_return_pct
                cutoff = 0.5
            else:
                daily_signal = close.proxy_return_pct - close.benchmark_return_pct
                cutoff = 1.0
            qualifying.append(daily_signal >= cutoff if direction == "positive" else daily_signal <= -cutoff)

        m_component = 0.0
        if qualifying and qualifying[-1]:
            m_component = 0.5
            if len(qualifying) == 2 and qualifying[-2]:
                m_component = 1.0

        latest = ordered[-1]
        if latest.benchmark_close is None:
            rel = 100 * (latest.proxy_close / proxy["anchor_proxy"] - 1)
        else:
            rel = 100 * (
                (latest.proxy_close / latest.benchmark_close)
                / (proxy["anchor_proxy"] / proxy["anchor_benchmark"])
                - 1
            )

        threshold = float(proxy["threshold_pct"])
        latest_sides = []
        for close in ordered[-2:]:
            if close.benchmark_close is None:
                value = 100 * (close.proxy_close / proxy["anchor_proxy"] - 1)
            else:
                value = 100 * (
                    (close.proxy_close / close.benchmark_close)
                    / (proxy["anchor_proxy"] / proxy["anchor_benchmark"])
                    - 1
                )
            latest_sides.append("up" if value >= threshold else "down" if value <= -threshold else None)
        confirmed_side = latest_sides[-1] if len(latest_sides) == 2 and latest_sides[0] == latest_sides[1] else None
        active = self.state.setdefault("active_breaches", {}).get(theme_id)
        new_breach = bool(confirmed_side and confirmed_side != active)
        if confirmed_side:
            self.state["active_breaches"][theme_id] = confirmed_side
        elif latest_sides and latest_sides[-1] is None:
            self.state["active_breaches"].pop(theme_id, None)

        return {
            "m_component": m_component,
            "relative_from_anchor_pct": round(rel, 4),
            "new_breach": new_breach,
            "breach_side": confirmed_side,
        }

    @staticmethod
    def _event_dict(event: EvidenceEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "observed_at": event.observed_at,
            "kind": event.kind,
            "direction": event.direction,
            "material": event.material,
            "summary": event.summary,
            "sources": [source.__dict__ for source in event.sources],
        }
