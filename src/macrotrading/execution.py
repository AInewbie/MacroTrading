"""Paper-only state transitions and accounting. No network or live routes."""

from copy import deepcopy
from math import floor, ceil, isclose
from uuid import uuid4
from .portfolio import (
    analyse_portfolio,
    stress_portfolio,
    validate_workspace,
    position_metrics,
    fx_rate,
)
from .validation import number, identifier, stamp


def create_order(workspace, input, now=None):
    i = next(
        (x for x in workspace["instruments"] if x["id"] == input.get("instrument_id")),
        None,
    )
    if i is None:
        raise ValueError("unknown instrument")
    if input.get("side") not in ("Buy", "Sell"):
        raise ValueError("side must be Buy or Sell")
    if input.get("order_type") not in ("Market", "Limit"):
        raise ValueError(
            "only Market and Limit orders are supported; Stop is unavailable"
        )
    q = number(input.get("quantity"), "quantity", 1e-12, 1e12)
    lot = i.get("lot_size", 1)
    if not isclose(q / lot, round(q / lot), abs_tol=1e-8):
        raise ValueError("quantity is not a lot-size multiple")
    limit = None
    if input["order_type"] == "Limit":
        limit = number(input.get("limit_price"), "limit price", 1e-12)
        tick = i.get("tick_size", 0.01)
        if not isclose(limit / tick, round(limit / tick), abs_tol=1e-7):
            raise ValueError("limit price is not a tick-size multiple")
    return {
        "id": identifier(input.get("id", str(uuid4()))),
        "instrument_id": i["id"],
        "side": input["side"],
        "quantity": q,
        "order_type": input["order_type"],
        "limit_price": limit,
        "status": "Staged",
        "created_at": now or stamp(),
        "theme_id": input.get("theme_id"),
        "source": input.get("source", "Trade ticket"),
    }


def _fill_price(order, i, policy):
    direction = 1 if order["side"] == "Buy" else -1
    proposed = i["price"] * (1 + direction * policy["slippage_bps"] / 10000)
    if order["order_type"] == "Limit":
        if (direction == 1 and proposed > order["limit_price"] + 1e-12) or (
            direction == -1 and proposed < order["limit_price"] - 1e-12
        ):
            return None
    return proposed


def _apply(workspace, order, fill):
    w = deepcopy(workspace)
    i = next(x for x in w["instruments"] if x["id"] == order["instrument_id"])
    ccy = i["currency"]
    mult = i["multiplier"]
    signed = fill["quantity"] * (1 if order["side"] == "Buy" else -1)
    p = next((p for p in w["positions"] if p["instrument_id"] == i["id"]), None)
    if p is None:
        p = {
            "instrument_id": i["id"],
            "quantity": 0.0,
            "average_price": fill["price"],
            "theme_id": order.get("theme_id"),
        }
        w["positions"].append(p)
    old = p["quantity"]
    old_cost = p["average_price"]
    new = old + signed
    realized = 0.0
    if old * signed < 0:
        realized = (
            min(abs(old), abs(signed))
            * (fill["price"] - old_cost)
            * (1 if old > 0 else -1)
            * mult
        )
    if old == 0 or old * signed > 0:
        p["average_price"] = (abs(old) * old_cost + abs(signed) * fill["price"]) / (
            abs(old) + abs(signed)
        )
    elif new == 0:
        p["average_price"] = 0.0
    elif old * new < 0:
        p["average_price"] = fill["price"]
    p["quantity"] = new
    if not p.get("theme_id") and order.get("theme_id"):
        p["theme_id"] = order["theme_id"]
    cash_change = realized if i["model"] == "future" else -signed * mult * fill["price"]
    w["cash"][ccy] = w["cash"].get(ccy, 0) + cash_change - fill["commission"]
    w["realized_pnl"][ccy] = (
        w["realized_pnl"].get(ccy, 0) + realized - fill["commission"]
    )
    return w


def pre_trade_checks(workspace, order, as_of=None):
    w = validate_workspace(workspace)
    as_of = as_of or stamp()
    policy = w["policy"]
    i = next(x for x in w["instruments"] if x["id"] == order["instrument_id"])
    # Revalidate order shape on every submission, not just staging.
    create_order(w, order, order["created_at"])
    price = _fill_price(order, i, policy)
    price = i["price"] if price is None else price
    reference = i.get("underlying_price") if i["model"] == "option" else i["price"]
    checks = []

    def check(name, passed, value=None, limit=None):
        checks.append(
            {"name": name, "pass": bool(passed), "value": value, "limit": limit}
        )

    try:
        conversion = fx_rate(w, i["currency"], as_of)
    except ValueError:
        conversion = None
    notional = (
        order["quantity"] * reference * i["multiplier"] * conversion
        if reference is not None and conversion is not None
        else None
    )
    check("Instrument tradable", i.get("tradable", True))
    check("Known notional", notional is not None)
    check(
        "Order notional",
        notional is not None and notional <= policy["max_order_notional"],
        notional,
        policy["max_order_notional"],
    )
    if i["model"] == "option":
        check(
            "Option contracts",
            order["quantity"] <= policy["max_option_contracts"],
            order["quantity"],
            policy["max_option_contracts"],
        )
        check(
            "Option limit order",
            not policy["require_limit_options"] or order["order_type"] == "Limit",
        )
    if i["model"] == "future":
        check(
            "Future contracts",
            order["quantity"] <= policy["max_future_contracts"],
            order["quantity"],
            policy["max_future_contracts"],
        )
    fee = order["quantity"] * price * i["multiplier"] * policy["commission_bps"] / 10000
    after = _apply(
        w, order, {"quantity": order["quantity"], "price": price, "commission": fee}
    )
    metrics = analyse_portfolio(after, as_of)
    check(
        "Complete current economics", metrics["complete"], "; ".join(metrics["issues"])
    )
    check(
        "Gross exposure",
        metrics["gross"] is not None
        and metrics["gross"] <= policy["max_gross_exposure"],
        metrics["gross"],
        policy["max_gross_exposure"],
    )
    check(
        "Net exposure",
        metrics["net"] is not None
        and abs(metrics["net"]) <= policy["max_net_exposure"],
        metrics["net"],
        policy["max_net_exposure"],
    )
    check(
        "Cash available",
        policy["allow_cash_overdraft"]
        or all(v >= -1e-8 for v in after["cash"].values()),
    )
    check(
        "Margin available",
        metrics["cash"] is not None
        and metrics["margin"] is not None
        and metrics["cash"] >= metrics["margin"],
        metrics["margin"],
        metrics["cash"],
    )
    pos = next(p for p in after["positions"] if p["instrument_id"] == i["id"])
    check("Shorting permitted", policy["allow_short"] or pos["quantity"] >= 0)
    if i.get("adv") is None:
        check("Liquidity supplied", w["demo"])
    else:
        check(
            "ADV participation",
            order["quantity"] <= i["adv"] * policy["max_adv_fraction"],
            order["quantity"],
            i["adv"] * policy["max_adv_fraction"],
        )
    losses = stress_portfolio(after, as_of)
    worst = (
        None
        if any(s["pnl"] is None for s in losses)
        else max(0.0, -min(s["pnl"] for s in losses))
    )
    check(
        "Scenario loss",
        worst is not None and worst <= policy["max_scenario_loss"],
        worst,
        policy["max_scenario_loss"],
    )
    return {
        "pass": all(c["pass"] for c in checks),
        "checks": checks,
        "notional": notional,
        "after": metrics,
        "worst_scenario_loss": worst,
        "commission": fee,
    }


def execute_paper(workspace, order_id, as_of=None):
    w = validate_workspace(workspace)
    order = next((o for o in w["orders"] if o["id"] == order_id), None)
    if order is None:
        raise ValueError("unknown order")
    if order["status"] == "Filled":
        return w, {
            "status": "Already filled",
            "fill": next((f for f in w["fills"] if f["order_id"] == order_id), None),
        }
    if order["status"] not in ("Staged", "Unfilled"):
        raise ValueError("order must be freshly staged before execution")
    controls = pre_trade_checks(w, order, as_of)
    if not controls["pass"]:
        order["status"] = "Blocked"
        order["checks"] = controls["checks"]
        return w, {"status": "Blocked", "controls": controls}
    i = next(x for x in w["instruments"] if x["id"] == order["instrument_id"])
    price = _fill_price(order, i, w["policy"])
    if price is None:
        order["status"] = "Unfilled"
        return w, {
            "status": "Unfilled",
            "reason": "Current simulated execution price is outside the limit",
        }
    fill = {
        "id": "fill-" + order_id,
        "order_id": order_id,
        "instrument_id": i["id"],
        "quantity": order["quantity"],
        "price": price,
        "commission": controls["commission"],
        "filled_at": as_of or stamp(),
        "mode": "paper",
    }
    w = _apply(w, order, fill)
    next(o for o in w["orders"] if o["id"] == order_id)["status"] = "Filled"
    w["fills"].append(fill)
    return w, {"status": "Filled", "fill": fill}


def rebalance_orders(workspace, as_of=None):
    w = validate_workspace(workspace)
    a = analyse_portfolio(w, as_of)
    if not a["complete"] or a["nav"] is None or a["nav"] <= 0:
        raise ValueError("rebalance needs a positive NAV and complete economics")
    instruments = {i["id"]: i for i in w["instruments"]}
    proposals = []
    for p in w["positions"]:
        if p.get("target_weight") is None:
            continue
        i = instruments[p["instrument_id"]]
        unit = position_metrics({"quantity": 1, "average_price": i["price"]}, i)[
            "delta_exposure"
        ]
        if unit is None or unit == 0:
            raise ValueError("target cannot be converted to quantity for " + i["id"])
        unit *= fx_rate(w, i["currency"], as_of or stamp())
        desired = a["nav"] * p["target_weight"]
        lot = i.get("lot_size", 1)
        qty = round((desired / unit - p["quantity"]) / lot) * lot
        if qty:
            direction = 1 if qty > 0 else -1
            tick = i.get("tick_size", 0.01)
            limit = (ceil if direction == 1 else floor)(
                i["price"]
                * (1 + direction * w["policy"]["slippage_bps"] / 10000)
                / tick
            ) * tick
            proposals.append(
                create_order(
                    w,
                    {
                        "instrument_id": i["id"],
                        "side": "Buy" if qty > 0 else "Sell",
                        "quantity": abs(qty),
                        "order_type": "Limit",
                        "limit_price": max(tick, limit),
                        "theme_id": p.get("theme_id"),
                        "source": "Target rebalance",
                    },
                    as_of,
                )
            )
    return proposals


def proposal(workspace, input, research=None, as_of=None):
    w = validate_workspace(workspace)
    as_of = as_of or stamp()
    i = next(
        (i for i in w["instruments"] if i["id"] == input.get("instrument_id")), None
    )
    if i is None:
        raise ValueError("unknown instrument")
    side = input.get("side")
    direction = 1 if side == "Buy" else -1
    tick = i.get("tick_size", 0.01)
    limit = (ceil if direction == 1 else floor)(
        i["price"] * (1 + direction * w["policy"]["slippage_bps"] / 10000) / tick
    ) * tick
    o = create_order(
        w, {**input, "order_type": "Limit", "limit_price": max(tick, limit)}, as_of
    )
    before = analyse_portfolio(w, as_of)
    controls = pre_trade_checks(w, o, as_of)
    fee = controls["commission"]
    after = _apply(
        w,
        o,
        {
            "quantity": o["quantity"],
            "price": _fill_price(o, i, w["policy"]),
            "commission": fee,
        },
    )
    pre = stress_portfolio(w, as_of)
    post = stress_portfolio(after, as_of)
    scenarios = [
        {
            "name": a["name"],
            "before": a["pnl"],
            "after": b["pnl"],
            "incremental": b["pnl"] - a["pnl"]
            if a["pnl"] is not None and b["pnl"] is not None
            else None,
        }
        for a, b in zip(pre, post)
    ]
    reasons = []
    tid = input.get("theme_id")
    if tid:
        t = (research or {}).get("themes", {}).get(tid)
        if not t:
            reasons.append("Theme has no accepted research run")
        elif t["lifecycle"] != "watch":
            reasons.append("Theme is " + t["lifecycle"])
        elif t["coverage"] != "current":
            reasons.append("Theme evidence is " + t["coverage"])
        elif t.get("market_required") and t["market"]["coverage"] != "current":
            reasons.append("Theme market confirmation is " + t["market"]["coverage"])
    if not before["complete"]:
        reasons += before["issues"]
    incremental = max(
        (
            max(0.0, -s["incremental"])
            for s in scenarios
            if s["incremental"] is not None
        ),
        default=None,
    )
    budget = number(
        input.get("risk_budget", w["policy"]["risk_budget"]), "risk budget", 1e-12
    )
    holding = number(
        input.get("holding_days", w["policy"]["holding_days"]), "holding days", 1, 3650
    )
    notional = controls["notional"]
    annual = (
        i.get("borrow_bps")
        if o["side"] == "Sell" and i["model"] == "equity"
        else i.get("financing_bps")
    )
    premium_or_notional = (
        None
        if notional is None
        else o["quantity"]
        * i["price"]
        * i["multiplier"]
        * fx_rate(w, i["currency"], as_of)
    )
    cost = (
        None
        if annual is None or premium_or_notional is None
        else premium_or_notional * annual / 10000 * holding / 365
        + 2 * fee * fx_rate(w, i["currency"], as_of)
        + 2 * premium_or_notional * w["policy"]["slippage_bps"] / 10000
    )
    if cost is None:
        reasons.append("Carry/borrow inputs are missing")
    if incremental is None:
        reasons.append("Scenario risk is unavailable")
    elif incremental > budget:
        reasons.append("Incremental scenario loss exceeds theme risk budget")
    return {
        "order": o,
        "before": before,
        "after": controls["after"],
        "scenarios": scenarios,
        "incremental_worst_loss": incremental,
        "risk_budget": budget,
        "estimated_round_trip_cost": cost,
        "holding_days": holding,
        "controls": controls,
        "eligible_for_review": controls["pass"] and not reasons,
        "blockers": reasons,
        "research_only": True,
        "method": "User-specified quantity; deterministic scenario and constraint checks, not an optimizer",
    }
