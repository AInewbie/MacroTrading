"""Explicit versioned calendars. Unknown years never confirm a two-session rule."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from .validation import instant


def is_session(day, calendar):
    return (
        calendar["valid_from"] <= day.isoformat() <= calendar["valid_to"]
        and day.weekday() < 5
        and day.isoformat() not in calendar.get("holidays", [])
    )


def consecutive(first, second, calendar):
    if (
        not is_session(first, calendar)
        or not is_session(second, calendar)
        or second <= first
    ):
        return False
    d = first + timedelta(days=1)
    while d < second:
        if is_session(d, calendar):
            return False
        d += timedelta(days=1)
    return True


def expected_close(day, calendar):
    hhmm = calendar.get("early_closes", {}).get(day.isoformat(), calendar["close_time"])
    return datetime.combine(
        day, time.fromisoformat(hhmm), ZoneInfo(calendar["timezone"])
    )


def eligible(close, calendar, as_of, needs_benchmark):
    reasons = []
    if not close.completed:
        reasons.append("session not explicitly completed")
    if not calendar or not is_session(close.session_date, calendar):
        reasons.append("session calendar unavailable or closed")
    if not close.close_at:
        reasons.append("close timestamp missing")
    elif instant(close.close_at) > as_of:
        reasons.append("close occurs after run cutoff")
    elif calendar and is_session(close.session_date, calendar):
        if (
            abs(
                (
                    instant(close.close_at)
                    - expected_close(close.session_date, calendar)
                ).total_seconds()
            )
            > 60
        ):
            reasons.append("close does not match calendar convention")
    if calendar and close.convention not in calendar.get(
        "conventions", ["official_close", "adjusted_close"]
    ):
        reasons.append("price convention does not match calendar")
    if close.known_at and instant(close.known_at) > as_of:
        reasons.append("observation was not yet known")
    if close.convention == "unverified":
        reasons.append("price convention unverified")
    if not close.source_url:
        reasons.append("market source missing")
    if needs_benchmark:
        if close.benchmark_close is None:
            reasons.append("required benchmark missing")
        if not close.benchmark_close_at or close.benchmark_close_at != close.close_at:
            reasons.append("benchmark close is not aligned")
        if close.benchmark_currency != close.currency:
            reasons.append("benchmark currency differs or is missing")
    return reasons
