import unittest
from copy import deepcopy

from macrotrading.portfolio_evaluation import portfolio_backtest


def dataset():
    dates = ["2026-09-14T20:00:00Z", "2026-09-15T20:00:00Z", "2026-09-16T20:00:00Z"]
    return {
        "base_currency": "USD",
        "initial_capital": 100000,
        "transaction_bps": 0,
        "borrow_bps": 0,
        "series": [
            {
                "id": "stock",
                "currency": "USD",
                "basis": "total_return_index",
                "points": [
                    {"at": at, "value": v} for at, v in zip(dates, [100, 110, 121])
                ],
            }
        ],
        "signals": [{"known_at": dates[0], "weights": {"stock": 1}}],
        "benchmark_id": "stock",
    }


class PortfolioEvaluation(unittest.TestCase):
    def test_next_close_and_benchmark(self):
        r = portfolio_backtest(dataset())
        self.assertEqual(r["rows"][0]["asset_pnl"]["stock"], 0)
        self.assertAlmostEqual(r["total_return"], 0.1)
        self.assertAlmostEqual(r["benchmark"]["total_return"], 0.21)
        self.assertAlmostEqual(r["asset_pnl"]["stock"], 10000)

    def test_cost_and_attribution_reconcile_exactly(self):
        p = dataset()
        p["transaction_bps"] = 10
        r = portfolio_backtest(p)
        self.assertGreater(r["rows"][-1]["transaction_cost"], 0)
        self.assertAlmostEqual(
            r["ending_equity"] - r["initial_capital"],
            sum(r["asset_pnl"].values()) - r["transaction_cost"] - r["carry_cost"],
        )
        self.assertLess(r["total_return"], 0.1)

    def test_multi_asset_opposite_returns_offset(self):
        p = dataset()
        b = deepcopy(p["series"][0])
        b["id"] = "bond"
        for point, value in zip(b["points"], [100, 100, 90]):
            point["value"] = value
        p["series"].append(b)
        p["signals"][0]["weights"] = {"stock": 0.5, "bond": 0.5}
        self.assertAlmostEqual(portfolio_backtest(p)["total_return"], 0)

    def test_short_and_future_signals(self):
        p = dataset()
        p["signals"][0]["weights"]["stock"] = -1
        self.assertAlmostEqual(portfolio_backtest(p)["total_return"], -0.1)
        p["signals"][0]["known_at"] = "2026-09-17T20:00:00Z"
        self.assertEqual(portfolio_backtest(p)["total_return"], 0)

    def test_no_imputation_and_no_future_availability(self):
        p = dataset()
        b = deepcopy(p["series"][0])
        b["id"] = "bad"
        b["points"][1]["at"] = "2026-09-15T21:00:00Z"
        p["series"].append(b)
        with self.assertRaisesRegex(ValueError, "share all timestamps"):
            portfolio_backtest(p)
        p = dataset()
        p["data_mode"] = "point_in_time"
        p["series"][0]["source_url"] = "https://example.com/data"
        for point in p["series"][0]["points"]:
            point["known_at"] = "2026-09-19T20:00:00Z"
        with self.assertRaisesRegex(ValueError, "known"):
            portfolio_backtest(p)

    def test_ex_post_is_explicit_and_undefined_ratios_are_null(self):
        p = dataset()
        p["data_mode"] = "historical_ex_post"
        p["series"][0]["source_url"] = "https://example.com/data"
        p["signals"] = []
        r = portfolio_backtest(p)
        self.assertIsNone(r["sharpe"])
        self.assertIsNone(r["sortino"])
        self.assertIsNone(r["calmar"])
        self.assertTrue(any("Ex-post" in x for x in r["warnings"]))


if __name__ == "__main__":
    unittest.main()
