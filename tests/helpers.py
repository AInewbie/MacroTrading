import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AT = "2026-09-18T21:00:00Z"


def config():
    c = json.loads((ROOT / "config/live_themes.json").read_text())
    c["as_of"] = "2026-01-01T00:00:00Z"
    c["themes"] = {
        "test": {
            "title": "Test thesis",
            "hypothesis": "A sourced and falsifiable test hypothesis.",
            "components": {"P": 0.5, "F": 0.5, "M": 0.5, "C": 0.5, "X": 0.5, "R": 1},
            "counterdrivers": [],
            "fundamental_tests": [],
            "catalysts": [],
            "decisions": [],
            "paper_risks": [],
            "expression": {},
            "invalidation": "Two adverse closes.",
            "proxy": {
                "anchor_proxy": 100,
                "anchor_benchmark": 100,
                "threshold_pct": 3,
                "invalidation_threshold_pct": 8,
                "hypothesis_direction": "positive",
                "calendar": "XNYS_2026",
            },
        }
    }
    return c


def event(id="one", **changes):
    e = {
        "id": id,
        "theme_id": "test",
        "observed_at": "2026-09-16T12:00:00Z",
        "first_known_at": "2026-09-16T13:00:00Z",
        "kind": "observed_fact",
        "direction": "support",
        "material": True,
        "summary": "A reviewed source supports the hypothesis.",
        "sources": [
            {
                "url": "https://example.com/evidence",
                "title": "Evidence fixture",
                "published_at": "2026-09-16T11:00:00Z",
                "retrieved_at": "2026-09-16T12:00:00Z",
            }
        ],
        "component_updates": {"F": 1},
    }
    e.update(changes)
    return e


def close(day="2026-09-17", price=104, ret=None, **changes):
    c = {
        "theme_id": "test",
        "session_date": day,
        "proxy_close": price,
        "benchmark_close": 100,
        "completed": True,
        "source_url": "https://example.com/close",
        "close_at": day + "T20:00:00Z",
        "benchmark_close_at": day + "T20:00:00Z",
        "convention": "official_close",
        "currency": "USD",
        "benchmark_currency": "USD",
    }
    if ret is not None:
        c["proxy_return_pct"] = ret
        c["benchmark_return_pct"] = 0
    c.update(changes)
    return c


def workspace(model="equity"):
    i = {
        "id": "asset",
        "symbol": "TEST",
        "name": "Synthetic test asset",
        "model": model,
        "currency": "USD",
        "price": 100.0,
        "price_at": AT,
        "multiplier": 1.0,
        "lot_size": 1,
        "tick_size": 0.01,
        "risk_factor": "equity",
        "factor_loadings": {"equity": 1},
        "adv": 1_000_000,
        "financing_bps": 300,
        "borrow_bps": 200,
        "tradable": True,
    }
    if model == "future":
        i.update(multiplier=50, margin_rate=0.1)
    if model == "option":
        i.update(
            price=5,
            multiplier=100,
            underlying_price=100,
            delta=0.5,
            gamma=0.01,
            vega=10,
            option_type="Call",
            strike=100,
            expiry="2027-01-15",
            margin_rate=0.2,
        )
    if model == "bond":
        i.update(price_convention="dirty_per_100", multiplier=10, duration=5)
    return {
        "schema_version": 3,
        "mode": "paper",
        "name": "Test portfolio",
        "base_currency": "USD",
        "demo": False,
        "cash": {"USD": 100000},
        "instruments": [i],
        "positions": [],
        "fx_rates": [],
        "orders": [],
        "fills": [],
        "realized_pnl": {},
        "policy": {"slippage_bps": 0, "commission_bps": 0},
    }
