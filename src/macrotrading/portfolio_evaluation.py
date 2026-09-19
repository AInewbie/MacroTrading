"""Self-financing multi-series research portfolios, with next-close decisions.

Each series is a positive base-currency price or total-return index, not a raw
option premium or leveraged futures contract. This deliberately avoids giving
an asset-allocation diagnostic the appearance of a derivative execution model.
"""

from math import sqrt, log, exp
from statistics import mean, stdev

from .validation import collection, number, instant, digest, identifier, url
from .portfolio import currency


def performance(equities, times, periods_per_year=252, risk_free_bps=0):
    returns = [b / a - 1 for a, b in zip(equities, equities[1:])]
    peak = equities[0]
    drawdown = 0
    for value in equities:
        peak = max(peak, value)
        drawdown = max(drawdown, 1 - value / peak)
    years = (times[-1] - times[0]).total_seconds() / (365.25 * 86400)
    annual_log = (
        log(equities[-1] / equities[0]) / years if years >= 1 / 365.25 else None
    )
    cagr = (
        exp(annual_log) - 1
        if annual_log is not None and -745 < annual_log < log(1e12 + 1)
        else None
    )
    rf = (1 + risk_free_bps / 10000) ** (1 / periods_per_year) - 1
    excess = [r - rf for r in returns]
    deviation = stdev(returns) if len(returns) > 1 else 0
    downside = sqrt(mean(min(0, r) ** 2 for r in excess)) if excess else 0
    return {
        "total_return": equities[-1] / equities[0] - 1,
        "annualized_return": cagr,
        "annualized_volatility": deviation * sqrt(periods_per_year),
        "max_drawdown": drawdown,
        "sharpe": mean(excess) / deviation * sqrt(periods_per_year)
        if deviation > 1e-14
        else None,
        "sortino": mean(excess) / downside * sqrt(periods_per_year)
        if downside > 1e-14
        else None,
        "calmar": cagr / drawdown if cagr is not None and drawdown > 1e-14 else None,
        "sample_size": len(returns),
        "elapsed_years": years,
    }


def portfolio_backtest(payload):
    base = currency(payload.get("base_currency", "USD"))
    mode = payload.get("data_mode", "synthetic")
    if mode not in ("synthetic", "historical_ex_post", "point_in_time"):
        raise ValueError("declare synthetic, historical_ex_post or point_in_time data")
    series = collection(payload.get("series"), "return series", 100)
    if not series:
        raise ValueError("at least one return series is required")
    prices = {}
    dates = None
    provenance = []
    for asset in series:
        key = identifier(asset["id"])
        if key in prices:
            raise ValueError("duplicate series ID")
        if asset.get("basis") not in (
            "price_index",
            "total_return_index",
            "reference_rate",
        ):
            raise ValueError(
                "declare series basis: price_index, total_return_index or reference_rate"
            )
        if currency(asset.get("currency")) != base:
            raise ValueError(
                "all evaluation series must already be expressed in reporting currency"
            )
        if mode != "synthetic":
            url(asset.get("source_url", ""))
        points = collection(asset.get("points"), "series points", 20000)
        times = [instant(p["at"]) for p in points]
        if len(times) < 3 or times != sorted(set(times)):
            raise ValueError(
                "each series needs at least three unique ascending observations"
            )
        if dates is not None and times != dates:
            raise ValueError(
                "series must share all timestamps; no silent fill or missing-date interpolation"
            )
        dates = times
        prices[key] = [number(p["value"], "index value", 1e-12, 1e12) for p in points]
        if mode == "point_in_time":
            if any(
                not p.get("known_at") or instant(p["known_at"]) > at
                for p, at in zip(points, times)
            ):
                raise ValueError(
                    "point-in-time observations must be known by their valuation timestamp"
                )
        provenance.append(
            {
                k: asset.get(k)
                for k in ("id", "source_url", "basis", "currency", "retrieved_at")
            }
        )
    signals = collection(payload.get("signals", []), "signals", 10000)
    maximum = number(payload.get("max_gross", 2), "maximum gross weight", 0.01, 10)
    last = None
    for signal in signals:
        at = instant(signal["known_at"])
        if last is not None and at <= last:
            raise ValueError("signals must have unique ascending known_at timestamps")
        last = at
        weights = signal.get("weights")
        if not isinstance(weights, dict) or set(weights) - set(prices):
            raise ValueError("signals must map known series IDs to target weights")
        for weight in weights.values():
            number(weight, "target weight", -10, 10)
        if sum(abs(w) for w in weights.values()) > maximum + 1e-12:
            raise ValueError("target exceeds maximum gross exposure")
    initial = number(payload.get("initial_capital", 100000), "initial capital", 1, 1e15)
    fee = (
        number(payload.get("transaction_bps", 5), "transaction cost bps", 0, 1000)
        / 10000
    )
    financing = (
        number(payload.get("financing_bps", 300), "financing bps", 0, 10000) / 10000
    )
    borrow = number(payload.get("borrow_bps", 200), "borrow bps", 0, 10000) / 10000
    cash_rate = (
        number(payload.get("cash_rate_bps", 0), "cash interest bps", -1000, 10000)
        / 10000
    )
    annualization = number(
        payload.get("periods_per_year", 252), "periods per year", 1, 100000
    )
    risk_free = number(payload.get("risk_free_bps", 0), "risk free bps", -9999, 10000)
    units = {key: 0.0 for key in prices}
    attribution = dict(units)
    cash = initial
    previous_nav = initial
    equities = [initial]
    rows = []
    si = 0
    turnover = total_cost = total_carry = 0.0
    for j in range(1, len(dates)):
        days = (dates[j] - dates[j - 1]).total_seconds() / 86400
        gains = {
            key: units[key] * (values[j] - values[j - 1])
            for key, values in prices.items()
        }
        short_value = sum(
            max(0, -units[key] * values[j - 1]) for key, values in prices.items()
        )
        carry = (
            (
                max(0, -cash) * financing
                + short_value * borrow
                - max(0, cash) * cash_rate
            )
            * days
            / 365
        )
        cash -= carry
        total_carry += carry
        nav_before_trade = cash + sum(
            units[key] * values[j] for key, values in prices.items()
        )
        if nav_before_trade <= 0:
            raise ValueError("hypothetical portfolio exhausted")
        target = None
        while si < len(signals) and instant(signals[si]["known_at"]) <= dates[j - 1]:
            target = signals[si]
            si += 1
        traded = cost = 0.0
        if target is not None:
            for key, values in prices.items():
                desired = target["weights"].get(key, 0) * nav_before_trade / values[j]
                notional = (desired - units[key]) * values[j]
                cash -= notional
                traded += abs(notional)
                units[key] = desired
            cost = traded * fee
            cash -= cost
            turnover += traded / nav_before_trade
        nav = cash + sum(units[key] * values[j] for key, values in prices.items())
        if j == len(dates) - 1:
            closing = sum(abs(units[key] * values[j]) for key, values in prices.items())
            cost += closing * fee
            nav -= closing * fee
            turnover += closing / max(nav + closing * fee, 1e-12)
        if nav <= 0:
            raise ValueError("hypothetical equity exhausted after costs")
        total_cost += cost
        for key, pnl in gains.items():
            attribution[key] += pnl
        rows.append(
            {
                "at": dates[j].isoformat(),
                "equity": nav,
                "net_return": nav / previous_nav - 1,
                "transaction_cost": cost,
                "carry_cost": carry,
                "asset_pnl": gains,
                "executed_signal_known_at": target["known_at"] if target else None,
                "gross_weight": sum(
                    abs(units[key] * values[j]) for key, values in prices.items()
                )
                / nav,
            }
        )
        equities.append(nav)
        previous_nav = nav
    metrics = performance(equities, dates, annualization, risk_free)
    benchmark = payload.get("benchmark_id")
    comparison = None
    if benchmark is not None:
        if benchmark not in prices:
            raise ValueError("benchmark must reference an included series")
        benchmark_values = [
            initial * p / prices[benchmark][0] for p in prices[benchmark]
        ]
        bm = performance(benchmark_values, dates, annualization, risk_free)
        active = [
            row["net_return"] - (b / a - 1)
            for row, a, b in zip(rows, benchmark_values, benchmark_values[1:])
        ]
        active_std = stdev(active) if len(active) > 1 else 0
        comparison = {
            "id": benchmark,
            **bm,
            "excess_total_return": metrics["total_return"] - bm["total_return"],
            "tracking_error": active_std * sqrt(annualization),
            "information_ratio": mean(active) / active_std * sqrt(annualization)
            if active_std > 1e-14
            else None,
            "costs": "unfunded benchmark index; no transaction or carry costs",
        }
    return {
        **metrics,
        "base_currency": base,
        "data_mode": mode,
        "initial_capital": initial,
        "ending_equity": equities[-1],
        "turnover": turnover,
        "transaction_cost": total_cost,
        "carry_cost": total_carry,
        "asset_pnl": attribution,
        "benchmark": comparison,
        "rows": rows,
        "input_hash": digest(payload),
        "provenance": provenance,
        "warnings": (
            ["Fewer than 60 intervals; annualized ratios are unstable."]
            if len(rows) < 60
            else []
        )
        + (
            [
                "Ex-post history; this does not establish what was available at each historical decision."
            ]
            if mode == "historical_ex_post"
            else []
        ),
        "assumption": "Base-currency index portfolio. Signals known by t execute at t+1 close, after that interval's return. Holdings drift between signals. Costs and terminal liquidation are included. No derivative settlement, corporate-action processing or alpha claim.",
        "annualization": {
            "periods_per_year": annualization,
            "risk_free_bps": risk_free,
            "cagr_basis": "actual elapsed time",
            "sortino_basis": "RMS downside across all periods",
        },
    }
