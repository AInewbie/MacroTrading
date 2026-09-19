"""Official ECB reference history, staged for review before changing a theme.

These are daily reference observations, not executable FX prices. The feed
contains dates, not historical release timestamps. Every row is conservatively
first-known at retrieval, preventing a current download from masquerading as
a historical point-in-time dataset.
"""

from datetime import date
from hashlib import sha256

from .calendars import expected_close, is_session
from .ingestion import fetch_bytes, xml_root
from .portfolio import currency
from .validation import identifier, instant, stamp, number, digest

ECB_HISTORY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
ECB_SOURCE = {
    "id": "ecb-history",
    "name": "ECB 90-day reference FX history",
    "kind": "ecb_fx",
    "url": ECB_HISTORY_URL,
    "allowed_hosts": ["www.ecb.europa.eu"],
    "enabled": True,
}


def parse_ecb_history(raw, retrieved_at):
    cutoff = instant(retrieved_at)
    rows = {}
    warnings = []
    for node in xml_root(raw).iter():
        if "time" not in node.attrib:
            continue
        day = date.fromisoformat(node.attrib["time"])
        if day > cutoff.date():
            raise ValueError("ECB feed contains a future observation date")
        rates = {"EUR": 1.0}
        for child in node:
            if "currency" in child.attrib and "rate" in child.attrib:
                code = currency(child.attrib["currency"])
                if code in rates:
                    raise ValueError("duplicate ECB currency observation")
                rates[code] = number(
                    float(child.attrib["rate"]), "ECB rate", 1e-12, 1e12
                )
        if day.isoformat() in rows:
            raise ValueError("duplicate ECB observation date")
        rows[day.isoformat()] = rates
    if len(rows) < 2:
        raise ValueError("ECB history requires at least two dated observations")
    return {
        "observations": dict(sorted(rows.items())),
        "content_hash": sha256(raw).hexdigest(),
        "retrieved_at": stamp(cutoff),
        "source_url": ECB_HISTORY_URL,
        "warnings": warnings,
    }


def build_snapshot(parsed, theme_id, base, quote, calendar, sessions=60):
    identifier(theme_id)
    base = currency(base)
    quote = currency(quote)
    if base == quote:
        raise ValueError("choose two different currencies")
    if (
        isinstance(sessions, bool)
        or not isinstance(sessions, int)
        or not 3 <= sessions <= 65
    ):
        raise ValueError("lookback must be 3–65 sessions")
    rows = []
    issues = []
    retrieved = instant(parsed["retrieved_at"])
    for day_text, rates in parsed["observations"].items():
        day = date.fromisoformat(day_text)
        if base not in rates or quote not in rates:
            issues.append(day_text + ": currency pair unavailable")
            continue
        if not is_session(day, calendar):
            issues.append(day_text + ": calendar unavailable or closed")
            continue
        clock = stamp(expected_close(day, calendar))
        if instant(clock) > retrieved:
            issues.append(day_text + ": reference observation window not complete")
            continue
        rows.append(
            {
                "theme_id": theme_id,
                "session_date": day_text,
                "proxy_close": rates[quote] / rates[base],
                "completed": True,
                "source_url": parsed["source_url"],
                "close_at": clock,
                "convention": "reference_rate",
                "currency": quote,
                "known_at": parsed["retrieved_at"],
                "content_hash": parsed["content_hash"],
                "series_id": "ECB-" + base + quote,
            }
        )
    rows = rows[-sessions:]
    if len(rows) < 3:
        raise ValueError(
            "fewer than three eligible reference observations; check calendar and pair"
        )
    from .calendars import consecutive

    for previous, current in zip(rows, rows[1:]):
        if not consecutive(
            date.fromisoformat(previous["session_date"]),
            date.fromisoformat(current["session_date"]),
            calendar,
        ):
            issues.append(
                "missing reference session between "
                + previous["session_date"]
                + " and "
                + current["session_date"]
            )
    latest_day = rows[-1]["session_date"]
    age = (retrieved - instant(rows[-1]["close_at"])).total_seconds() / 86400
    latest_rates = parsed["observations"][latest_day]
    snapshot = {
        "provider": "ECB",
        "pair": base + "/" + quote,
        "base": base,
        "quote": quote,
        "theme_id": theme_id,
        "retrieved_at": parsed["retrieved_at"],
        "known_at_policy": "retrieval time; historical release timestamps unavailable",
        "source_url": parsed["source_url"],
        "content_hash": parsed["content_hash"],
        "latest_session": latest_day,
        "age_days": round(age, 2),
        "stale": age > 5,
        "issues": issues,
        "market_closes": rows,
        "fx_rates": [
            {
                "from": "EUR",
                "to": c,
                "rate": v,
                "as_of": rows[-1]["close_at"],
                "source": "ECB reference; not executable",
            }
            for c, v in latest_rates.items()
            if c != "EUR"
        ],
        "proxy": {
            "symbol": base + quote,
            "series_id": "ECB-" + base + quote,
            "anchor_proxy": rows[0]["proxy_close"],
            "anchor_at": rows[0]["close_at"],
            "calendar": "ECB_REFERENCE_2026_2028",
            "convention": "reference_rate",
            "currency": quote,
            "threshold_pct": 3,
            "invalidation_threshold_pct": 8,
            "daily_threshold_pct": 0.25,
            "hypothesis_direction": "positive",
        },
        "warning": "Reference rates for research and reporting; not executable prices. Review the proxy, anchor and direction before accepting.",
    }
    snapshot["id"] = "market-" + digest(snapshot)[:24]
    return snapshot


def acquire_ecb(
    theme_id, base, quote, calendar, sessions=60, fetcher=fetch_bytes, now=None
):
    try:
        raw = fetcher(ECB_SOURCE)
    except OSError as exc:
        raise ValueError(
            "ECB acquisition failed: check network/DNS access. No research or holdings were changed."
        ) from exc
    at = now or stamp()
    parsed = parse_ecb_history(raw, at)
    return raw, build_snapshot(parsed, theme_id, base, quote, calendar, sessions)
