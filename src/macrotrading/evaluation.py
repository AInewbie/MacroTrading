"""Point-in-time replay metrics and transparent single-expression paper evaluation."""

from math import sqrt
from statistics import stdev
from .engine import AnalysisEngine
from .models import EvidenceEvent, MarketClose
from .validation import instant, number, collection, digest


def replay(config, batches):
    engine = AnalysisEngine(config)
    rows = []
    tp = fp = fn = 0
    dates = [instant(b["as_of"]) for b in batches]
    if dates != sorted(dates):
        raise ValueError("replay batches must be chronological")
    for batch in collection(batches, "replay batches", 1000):
        result = engine.analyze(
            [EvidenceEvent.from_dict(e) for e in batch.get("evidence", [])],
            [MarketClose.from_dict(c) for c in batch.get("market_closes", [])],
            batch["as_of"],
        )
        predicted = {a["type"] + ":" + a["theme_id"] for a in result["alerts"]}
        expected = (
            set(batch.get("expected_alerts", []))
            if "expected_alerts" in batch
            else None
        )
        if expected is not None:
            tp += len(predicted & expected)
            fp += len(predicted - expected)
            fn += len(expected - predicted)
        rows.append(
            {
                "as_of": batch["as_of"],
                "scores": {k: t["score"] for k, t in result["themes"].items()},
                "lifecycle": {k: t["lifecycle"] for k, t in result["themes"].items()},
                "alerts": sorted(predicted),
                "expected": sorted(expected) if expected is not None else None,
            }
        )
    labelled = any("expected_alerts" in b for b in batches)
    return {
        "runs": rows,
        "labelled": labelled,
        "true_positives": tp if labelled else None,
        "false_positives": fp if labelled else None,
        "false_negatives": fn if labelled else None,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "config_hash": digest(config),
        "input_hash": digest(batches),
        "method": "Chronological accepted-evidence replay; fresh state; no future inputs accepted",
    }


def backtest(payload):
    """Targets decided at close t take effect at t+1 close, earning t+1→t+2 returns."""
    prices = collection(payload.get("prices"), "prices", 20000)
    signals = collection(payload.get("signals"), "signals", 20000)
    if len(prices) < 3:
        raise ValueError("at least three prices required")
    times = [instant(p["at"]) for p in prices]
    if times != sorted(set(times)):
        raise ValueError("prices must have unique ascending timestamps")
    for p in prices:
        number(p["close"], "close", 1e-12)
    for s in signals:
        instant(s["known_at"])
        number(s["target"], "target", -1, 1)
    signals = sorted(signals, key=lambda s: instant(s["known_at"]))
    fee = number(payload.get("transaction_bps", 5), "transaction bps", 0, 1000) / 10000
    borrow = number(payload.get("borrow_bps", 200), "borrow bps", 0, 10000) / 10000
    financing = (
        number(payload.get("financing_bps", 0), "financing bps", 0, 10000) / 10000
    )
    exposure = 0.0
    equity = 1.0
    peak = 1.0
    dd = 0.0
    rows = []
    returns = []
    turnover = 0.0
    si = 0
    target = 0.0
    for j in range(1, len(prices)):
        days = (times[j] - times[j - 1]).total_seconds() / 86400
        gross = exposure * (prices[j]["close"] / prices[j - 1]["close"] - 1)
        carry = abs(exposure) * (borrow if exposure < 0 else financing) * days / 365
        while si < len(signals) and instant(signals[si]["known_at"]) <= times[j - 1]:
            target = signals[si]["target"]
            si += 1
        trade = abs(target - exposure)
        cost = trade * fee
        net = gross - carry - cost
        if net <= -1:
            raise ValueError("hypothetical equity exhausted under requested exposure")
        equity *= 1 + net
        peak = max(peak, equity)
        dd = max(dd, 1 - equity / peak)
        returns.append(net)
        turnover += trade
        rows.append(
            {
                "at": prices[j]["at"],
                "earned_exposure": exposure,
                "next_exposure": target,
                "gross_return": gross,
                "cost_return": cost + carry,
                "net_return": net,
                "equity": equity,
            }
        )
        exposure = target
    final_cost = abs(exposure) * fee
    equity *= 1 - final_cost
    dd = max(dd, 1 - equity / peak)
    return {
        "total_return": equity - 1,
        "max_drawdown": dd,
        "turnover": turnover + abs(exposure),
        "closing_cost_return": final_cost,
        "rows": rows,
        "sample_size": len(rows),
        "annualized_volatility": stdev(returns) * sqrt(252)
        if len(returns) > 1
        else None,
        "assumption": "Volatility annualization assumes daily trading observations; marks and costs are user supplied. Signals execute at the following observed close. Terminal liquidation cost included. No alpha claim.",
    }
