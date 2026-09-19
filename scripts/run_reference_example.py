"""Reproduce a reviewed public-data example without a network or paid API call.

Exchange-rate observations are official-page transcriptions. Holdings and the
proposed quantity are illustrative assumptions, never the user's portfolio.
"""

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from macrotrading.service import Service
from macrotrading.validation import stamp, digest
from macrotrading.calendars import expected_close
from macrotrading.execution import proposal
from macrotrading.portfolio import validate_workspace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "var/reference-example"))
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads((ROOT / "examples/ecb_eurusd_2026-09-18.json").read_text())
    known = data["retrieved_at"]
    at = known
    calendar = json.loads((ROOT / "config/calendars.json").read_text())[
        "ECB_REFERENCE_2026_2028"
    ]
    closes = [
        {
            "theme_id": "eurusd_watch",
            "session_date": r["session_date"],
            "proxy_close": r["rate"],
            "source_url": data["source_url"],
            "completed": True,
            "convention": "reference_rate",
            "currency": "USD",
            "known_at": known,
            "series_id": "ECB-EURUSD",
            "close_at": stamp(
                expected_close(date.fromisoformat(r["session_date"]), calendar)
            ),
        }
        for r in data["observations"]
    ]
    note = "Official ECB reference observations; illustrative EUR 100,000 and USD 100,000 cash balances, not user holdings. Data transcribed from the published page because direct XML acquisition was unavailable in the build environment. No executable prices or investment recommendation."
    theme = {
        "title": "EUR/USD weakness — monitored research",
        "hypothesis": "Investigate whether the observed September EUR/USD weakness persists.",
        "components": {"P": 1, "F": 0, "M": 0, "C": 0, "X": 0.5, "R": 1},
        "counterdrivers": [
            "A short price trend does not establish a macro cause or forward edge.",
            "Policy surprises and positioning can reverse the observed move.",
        ],
        "fundamental_tests": [
            "Obtain independently sourced policy-rate expectations and growth/inflation surprises before raising F."
        ],
        "catalysts": [
            "Future ECB/Fed decisions: dates and expectations not established in this example."
        ],
        "invalidation": "Two adjacent reference observations above the adverse anchor threshold suspend the directional research.",
        "decisions": [
            "Review source freshness and whether this price pattern merits fundamental research.",
            "Assess an illustrative EUR 25,000 hedge only after obtaining executable quotes and a reviewed mandate.",
        ],
        "paper_risks": [
            "Reference observations cannot justify an executable order.",
            "Portfolio balances and proposed size are illustrative.",
        ],
        "expression": {
            "proxy": "EUR/USD reference series",
            "limits": "Reference-only instrument is explicitly non-tradable.",
        },
        "proxy": {
            "symbol": "EURUSD",
            "series_id": "ECB-EURUSD",
            "calendar": "ECB_REFERENCE_2026_2028",
            "convention": "reference_rate",
            "currency": "USD",
            "anchor_proxy": closes[0]["proxy_close"],
            "anchor_at": closes[0]["close_at"],
            "threshold_pct": 3,
            "invalidation_threshold_pct": 3,
            "daily_threshold_pct": 0.1,
            "hypothesis_direction": "negative",
        },
    }
    config = {
        "version": "reference-example-v0.6",
        "as_of": "2026-09-01T00:00:00Z",
        "weights": {"P": 25, "F": 25, "M": 20, "C": 20, "X": 10, "R": -10},
        "calendars": {"ECB_REFERENCE_2026_2028": calendar},
        "themes": {"eurusd_watch": theme},
    }
    instrument = {
        "id": "eurusd-reference",
        "name": "ECB EUR/USD reference (not executable)",
        "symbol": "EURUSD",
        "model": "fx",
        "currency": "USD",
        "fx_base": "EUR",
        "price": closes[-1]["proxy_close"],
        "price_at": closes[-1]["close_at"],
        "multiplier": 1,
        "lot_size": 1,
        "tick_size": 0.0001,
        "adv": 1e8,
        "financing_bps": 0,
        "borrow_bps": 0,
        "tradable": False,
        "basis_sensitivity": {},
        "funding_notional": 0,
    }
    workspace = validate_workspace(
        {
            "schema_version": 3,
            "mode": "paper",
            "demo": False,
            "name": "Illustrative currency balances — not user holdings",
            "base_currency": "USD",
            "cash": {"EUR": 100000, "USD": 100000},
            "instruments": [instrument],
            "positions": [],
            "fx_rates": [
                {
                    "from": "EUR",
                    "to": "USD",
                    "rate": closes[-1]["proxy_close"],
                    "as_of": closes[-1]["close_at"],
                }
            ],
            "policy": {"slippage_bps": 0, "commission_bps": 0},
        }
    )
    evidence = {
        "id": "ecb-eurusd-observation-2026-09-18",
        "theme_id": "eurusd_watch",
        "observed_at": known,
        "first_known_at": known,
        "kind": "observed_fact",
        "direction": "support",
        "material": True,
        "summary": "ECB EUR/USD reference rates decreased from 1.1551 on 14 September to 1.1460 on 18 September 2026. This establishes an observed move, not its cause or persistence.",
        "sources": [
            {
                "url": data["source_url"],
                "title": "ECB daily EUR/USD reference table",
                "published_at": known,
                "retrieved_at": known,
                "source_group": "ECB",
            }
        ],
        "metadata": {
            "source_date_precision": "day; conservative publication timestamp equals retrieval",
            "normalized_dataset_hash": digest(data),
        },
    }
    with TemporaryDirectory(prefix="macrotrading-reference-") as directory:
        service = Service(ROOT, directory)
        with service.store.transaction() as db:
            service.store.put(db, "config", config)
            service.store.put(db, "workspace", workspace)
        result = service.run(
            {
                "as_of": at,
                "label": "Verified public references and illustrative portfolio impact",
                "note": note,
                "evidence": [evidence],
                "market_closes": closes,
            }
        )
        assessment = proposal(
            workspace,
            {
                "instrument_id": "eurusd-reference",
                "theme_id": "eurusd_watch",
                "side": "Sell",
                "quantity": 25000,
            },
            result,
            at,
        )
        saved = service.store.run(result["run_id"])
        (out / "reference-workflow.html").write_text(saved["html"])
        (out / "reference-workflow.json").write_text(
            json.dumps(
                {
                    "run": {k: v for k, v in saved.items() if k != "html"},
                    "illustrative_proposal": assessment,
                    "data_note": note,
                },
                indent=2,
            )
            + "\n"
        )
        print(
            json.dumps(
                {
                    "run_id": result["run_id"],
                    "score": result["themes"]["eurusd_watch"]["score"],
                    "market_coverage": result["themes"]["eurusd_watch"]["market"][
                        "coverage"
                    ],
                    "nav": result["portfolio"]["nav"],
                    "usd_down_pnl": next(
                        s["pnl"] for s in result["scenarios"] if s["id"] == "usd_down"
                    ),
                    "proposal_eligible": assessment["eligible_for_review"],
                    "output": str(out),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
