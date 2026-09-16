from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse


EVIDENCE_KINDS = {
    "observed_fact",
    "company_plan",
    "policy_plan",
    "economist_forecast",
    "market_implied",
    "inference",
}
DIRECTIONS = {"support", "contradict", "neutral"}


@dataclass(frozen=True)
class Source:
    url: str
    title: str
    published_at: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Source":
        url = value["url"]
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"invalid source URL: {url}")
        return cls(url=url, title=value["title"], published_at=value["published_at"])


@dataclass(frozen=True)
class EvidenceEvent:
    id: str
    theme_id: str
    observed_at: str
    kind: str
    direction: str
    material: bool
    summary: str
    sources: tuple[Source, ...]
    component_updates: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EvidenceEvent":
        kind = value["kind"]
        direction = value["direction"]
        if kind not in EVIDENCE_KINDS:
            raise ValueError(f"unsupported evidence kind: {kind}")
        if direction not in DIRECTIONS:
            raise ValueError(f"unsupported direction: {direction}")
        datetime.fromisoformat(value["observed_at"].replace("Z", "+00:00"))
        sources = tuple(Source.from_dict(item) for item in value.get("sources", []))
        if kind != "inference" and not sources:
            raise ValueError(f"event {value['id']} requires a direct source")
        return cls(
            id=value["id"],
            theme_id=value["theme_id"],
            observed_at=value["observed_at"],
            kind=kind,
            direction=direction,
            material=bool(value.get("material", False)),
            summary=value["summary"],
            sources=sources,
            component_updates={k: float(v) for k, v in value.get("component_updates", {}).items()},
            metadata=dict(value.get("metadata", {})),
        )


@dataclass(frozen=True)
class MarketClose:
    theme_id: str
    session_date: date
    proxy_close: float
    benchmark_close: float | None = None
    proxy_return_pct: float | None = None
    benchmark_return_pct: float | None = None
    completed: bool = True
    source_url: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MarketClose":
        return cls(
            theme_id=value["theme_id"],
            session_date=date.fromisoformat(value["session_date"]),
            proxy_close=float(value["proxy_close"]),
            benchmark_close=(float(value["benchmark_close"]) if value.get("benchmark_close") is not None else None),
            proxy_return_pct=(float(value["proxy_return_pct"]) if value.get("proxy_return_pct") is not None else None),
            benchmark_return_pct=(float(value["benchmark_return_pct"]) if value.get("benchmark_return_pct") is not None else None),
            completed=bool(value.get("completed", True)),
            source_url=value.get("source_url", ""),
        )

