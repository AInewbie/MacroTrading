from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any
from .validation import boolean, identifier, instant, number, stamp, text, url

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
    retrieved_at: str | None = None
    content_hash: str | None = None
    source_group: str | None = None

    @classmethod
    def from_dict(cls, value):
        published = stamp(instant(value["published_at"], "publication time"))
        retrieved = (
            stamp(instant(value["retrieved_at"], "retrieval time"))
            if value.get("retrieved_at")
            else None
        )
        if retrieved and instant(published) > instant(retrieved):
            raise ValueError("publication time is later than retrieval time")
        content_hash = value.get("content_hash")
        if content_hash and (
            not isinstance(content_hash, str)
            or len(content_hash) != 64
            or any(c not in "0123456789abcdef" for c in content_hash)
        ):
            raise ValueError("content_hash must be a SHA-256 hex digest")
        group = (
            text(value["source_group"], "source group", 200)
            if value.get("source_group") is not None
            else None
        )
        return cls(
            url(value["url"]),
            text(value["title"], "source title", 500),
            published,
            retrieved,
            content_hash,
            group,
        )


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
    first_known_at: str | None = None
    data_at: str | None = None
    supersedes: str | None = None

    @classmethod
    def from_dict(cls, value):
        if value.get("kind") not in EVIDENCE_KINDS:
            raise ValueError("unsupported evidence kind")
        if value.get("direction") not in DIRECTIONS:
            raise ValueError("unsupported evidence direction")
        observed = stamp(instant(value["observed_at"], "observed_at"))
        sources = tuple(Source.from_dict(s) for s in value.get("sources", []))
        if len(sources) > 30:
            raise ValueError("at most 30 sources per event")
        if value["kind"] != "inference" and not sources:
            raise ValueError("non-inference evidence requires a direct source")
        updates = value.get("component_updates", {})
        if not isinstance(updates, dict) or set(updates) - set("PFMCXR"):
            raise ValueError("unknown score component")
        updates = {k: number(v, k) for k, v in updates.items()}
        for k, v in updates.items():
            if v not in ({0.0, 1.0, 2.0} if k == "R" else {0.0, 0.5, 1.0}):
                raise ValueError(f"invalid {k} component")
        metadata = value.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be an object")
        if "invalidation_met" in metadata:
            boolean(metadata["invalidation_met"], "invalidation_met")
        if metadata.get("lifecycle_action") not in (
            None,
            "resume",
            "suspend",
            "archive",
        ):
            raise ValueError("unsupported lifecycle action")
        known = stamp(instant(value.get("first_known_at", observed), "first_known_at"))
        if instant(known) < instant(observed):
            raise ValueError("first_known_at precedes observation")
        if any(
            instant(s.published_at) > instant(known)
            or (s.retrieved_at and instant(s.retrieved_at) > instant(known))
            for s in sources
        ):
            raise ValueError("source was published or retrieved after first_known_at")
        return cls(
            identifier(value["id"]),
            identifier(value["theme_id"], "theme_id"),
            observed,
            value["kind"],
            value["direction"],
            boolean(value.get("material", False), "material"),
            text(value["summary"], "summary", 6000),
            sources,
            updates,
            metadata,
            known,
            stamp(instant(value["data_at"])) if value.get("data_at") else None,
            identifier(value["supersedes"]) if value.get("supersedes") else None,
        )

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class MarketClose:
    theme_id: str
    session_date: date
    proxy_close: float
    benchmark_close: float | None = None
    proxy_return_pct: float | None = None
    benchmark_return_pct: float | None = None
    completed: bool = False
    source_url: str = ""
    close_at: str | None = None
    benchmark_close_at: str | None = None
    convention: str = "unverified"
    currency: str = "USD"
    benchmark_currency: str | None = None
    known_at: str | None = None
    content_hash: str | None = None
    series_id: str | None = None

    @classmethod
    def from_dict(cls, value):
        completed = boolean(value.get("completed", False), "completed")
        close_at = stamp(instant(value["close_at"])) if value.get("close_at") else None
        benchmark_at = (
            stamp(instant(value["benchmark_close_at"]))
            if value.get("benchmark_close_at")
            else None
        )
        convention = value.get("convention", "unverified")
        if convention not in (
            "official_close",
            "adjusted_close",
            "reference_rate",
            "unverified",
        ):
            raise ValueError("unsupported close convention")
        currency = text(value.get("currency", "USD"), "currency", 3).upper()
        benchmark_currency = value.get("benchmark_currency")
        if benchmark_currency:
            benchmark_currency = text(
                benchmark_currency, "benchmark_currency", 3
            ).upper()
        return cls(
            identifier(value["theme_id"]),
            date.fromisoformat(value["session_date"]),
            number(value["proxy_close"], "proxy close", 1e-12, 1e12),
            number(value["benchmark_close"], "benchmark close", 1e-12, 1e12)
            if value.get("benchmark_close") is not None
            else None,
            number(value["proxy_return_pct"], "proxy return", -100, 10000)
            if value.get("proxy_return_pct") is not None
            else None,
            number(value["benchmark_return_pct"], "benchmark return", -100, 10000)
            if value.get("benchmark_return_pct") is not None
            else None,
            completed,
            url(value["source_url"]) if value.get("source_url") else "",
            close_at,
            benchmark_at,
            convention,
            currency,
            benchmark_currency,
            stamp(instant(value["known_at"])) if value.get("known_at") else None,
            value.get("content_hash"),
            identifier(value["series_id"]) if value.get("series_id") else None,
        )

    def to_dict(self):
        result = asdict(self)
        result["session_date"] = self.session_date.isoformat()
        return result
