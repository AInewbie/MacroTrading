"""Currency-consistent stress attribution with explicit sensitivity units.

All currency shocks are relative to one anchor (USD by default). Conversion
into the portfolio currency uses the ratio of shocked exchange rates, so a
foreign asset's local P&L and translation are counted exactly once.
"""

from copy import deepcopy

from .validation import number, identifier, text


ADDITIONAL_SCENARIOS = [
    {
        "id": "curve_steepener",
        "name": "Curve steepener",
        "curve_bp": {"2Y": -25, "10Y": 25, "30Y": 40},
    },
    {
        "id": "spread_widening",
        "name": "Credit / sovereign spread widening",
        "spread_bp": 100,
    },
    {
        "id": "funding_squeeze",
        "name": "Funding +200 bp for 30 days",
        "funding_bp": 200,
        "horizon_days": 30,
    },
    {
        "id": "basis_dislocation",
        "name": "Basis dislocation",
        "basis_bp": {"bond_repo": 25},
    },
]


def validate_scenarios(scenarios):
    if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= 30:
        raise ValueError("provide 1–30 stress scenarios")
    ids = set()
    allowed = {
        "id",
        "name",
        "equity",
        "commodity",
        "fx",
        "rates_bp",
        "vol_points",
        "currency_anchor",
        "currency_shocks",
        "foreign_currency_shock",
        "curve_bp",
        "spread_bp",
        "basis_bp",
        "funding_bp",
        "horizon_days",
    }
    for s in scenarios:
        if not isinstance(s, dict) or set(s) - allowed:
            raise ValueError("unknown stress scenario fields")
        identifier(s.get("id"))
        text(s.get("name"), "scenario name", 200)
        if s["id"] in ids:
            raise ValueError("duplicate scenario ID")
        ids.add(s["id"])
        for k in ("equity", "commodity", "fx", "foreign_currency_shock"):
            if k in s:
                number(s[k], k, -0.999999, 10)
        for k in ("rates_bp", "vol_points", "spread_bp", "funding_bp"):
            if k in s:
                number(s[k], k, -10000, 10000)
        if "horizon_days" in s:
            number(s["horizon_days"], "scenario horizon", 0, 3650)
        anchor = s.get("currency_anchor", "USD")
        if (
            not isinstance(anchor, str)
            or len(anchor) != 3
            or not anchor.isupper()
            or not anchor.isalpha()
        ):
            raise ValueError("currency anchor must be an uppercase currency code")
        for k in ("currency_shocks", "curve_bp", "basis_bp"):
            values = s.get(k, {})
            if not isinstance(values, dict) or len(values) > 100:
                raise ValueError(k + " must be a bounded mapping")
            for key, value in values.items():
                if k == "currency_shocks":
                    if len(key) != 3 or not key.isupper() or not key.isalpha():
                        raise ValueError(
                            "currency shock keys must be uppercase currency codes"
                        )
                    number(value, k, -0.999999, 10)
                else:
                    identifier(key)
                    number(value, k, -10000, 10000)
        if s.get("currency_shocks", {}).get(anchor, 0) != 0:
            raise ValueError("the currency anchor shock must be zero")
    return deepcopy(scenarios)


def currency_move(ccy, base, scenario):
    """Return the change in units of reporting currency per unit of ccy."""
    anchor = scenario.get("currency_anchor", "USD")
    shocks = scenario.get("currency_shocks", {})
    default = scenario.get("foreign_currency_shock", 0)

    def factor(currency):
        return 1 if currency == anchor else 1 + shocks.get(currency, default)

    return factor(ccy) / factor(base) - 1


def local_stress(position, instrument, scenario, metrics):
    q = position["quantity"]
    if not q:
        return 0.0, []
    i = instrument
    s = scenario
    m = i["multiplier"]
    price = i["price"]
    model = i["model"]
    issues = []
    pnl = 0.0
    if model == "bond" or (model == "future" and i.get("risk_factor") == "rates"):
        keys = i.get("key_rate_dv01")
        if s.get("curve_bp"):
            if not keys:
                issues.append("key-rate DV01 required for non-parallel curve stress")
            else:
                pnl -= q * sum(
                    v * (s.get("rates_bp", 0) + s["curve_bp"].get(k, 0))
                    for k, v in keys.items()
                )
        elif s.get("rates_bp", 0):
            if metrics["dv01"] is None:
                issues.append("DV01 required for rates stress")
            else:
                pnl -= metrics["dv01"] * s["rates_bp"]
        if s.get("spread_bp", 0):
            if i.get("spread_dv01") is None:
                issues.append(
                    "spread DV01 required; supply explicit zero for no spread risk"
                )
            else:
                pnl -= q * i["spread_dv01"] * s["spread_bp"]
    elif model == "option":
        if any(
            i.get(k) is None for k in ("underlying_price", "delta", "gamma", "vega")
        ):
            issues.append("option sensitivities missing")
        else:
            ds = i["underlying_price"] * s.get(i.get("risk_factor", "equity"), 0)
            pnl = q * m * (i["delta"] * ds + 0.5 * i["gamma"] * ds * ds) + q * i[
                "vega"
            ] * s.get("vol_points", 0)
    elif model == "fx" and i.get("fx_base"):
        pnl = q * m * price * currency_move(i["fx_base"], i["currency"], s)
    else:
        factor = "fx" if model == "fx" else i.get("risk_factor", "equity")
        pnl = q * m * price * s.get(factor, 0) * i.get("beta", 1)
        if model == "fx" and (
            s.get("currency_shocks") or s.get("foreign_currency_shock")
        ):
            issues.append("FX base currency required for currency stress")
    if s.get("basis_bp"):
        sensitivities = i.get("basis_sensitivity")
        if sensitivities is None:
            issues.append(
                "basis sensitivity mapping required; use empty map for no basis risk"
            )
        else:
            pnl += q * sum(
                v * s["basis_bp"].get(k, 0) for k, v in sensitivities.items()
            )
    if s.get("funding_bp", 0):
        if i.get("funding_notional") is None:
            issues.append(
                "funding notional per contract required; explicit zero is permitted"
            )
        else:
            pnl -= (
                abs(q)
                * i["funding_notional"]
                * s["funding_bp"]
                / 10000
                * s.get("horizon_days", 30)
                / 365
            )
    return (None if issues else pnl), issues


def portfolio_stress(workspace, as_of, scenarios):
    # Local import keeps valuation independent from the scenario implementation.
    from .portfolio import validate_workspace, fx_rate, position_metrics

    w = validate_workspace(workspace)
    base = w["base_currency"]
    instruments = {i["id"]: i for i in w["instruments"]}
    results = []
    for s in validate_scenarios(scenarios):
        rows = []
        issues = []
        for ccy, balance in w["cash"].items():
            try:
                value = balance * fx_rate(w, ccy, as_of) * currency_move(ccy, base, s)
                row_issues = []
            except ValueError as exc:
                value = None
                row_issues = [str(exc)]
            rows.append(
                {
                    "instrument_id": "cash-" + ccy,
                    "symbol": ccy + " cash",
                    "theme_id": None,
                    "pnl": value,
                    "local_pnl": 0,
                    "translation_pnl": value,
                    "issues": row_issues,
                    "kind": "cash",
                }
            )
        for p in w["positions"]:
            i = instruments[p["instrument_id"]]
            metrics = position_metrics(p, i)
            local, row_issues = local_stress(p, i, s, metrics)
            translation = None
            value = None
            try:
                conversion = fx_rate(w, i["currency"], as_of)
                change = currency_move(i["currency"], base, s)
                translation = metrics["market_value"] * conversion * change
                if local is not None:
                    value = local * conversion * (1 + change) + translation
            except ValueError as exc:
                row_issues.append(str(exc))
            rows.append(
                {
                    "instrument_id": i["id"],
                    "symbol": i["symbol"],
                    "theme_id": p.get("theme_id"),
                    "pnl": value,
                    "local_pnl": local,
                    "translation_pnl": translation,
                    "issues": row_issues,
                    "kind": "position",
                }
            )
        for row in rows:
            issues.extend(row["symbol"] + ": " + issue for issue in row["issues"])
        total = (
            None if any(r["pnl"] is None for r in rows) else sum(r["pnl"] for r in rows)
        )
        results.append(
            {
                **s,
                "pnl": total,
                "rows": rows,
                "issues": issues,
                "complete": not issues,
                "method": "Local sensitivities plus currency translation, including cash; no full repricing",
            }
        )
    return results
