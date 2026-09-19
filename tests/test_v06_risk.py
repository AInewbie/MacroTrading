import unittest

from helpers import workspace, AT
from macrotrading.portfolio import stress_portfolio, validate_workspace
from macrotrading.scenarios import currency_move, validate_scenarios


class CurrencyAndRatesRisk(unittest.TestCase):
    def test_foreign_cash_has_currency_stress(self):
        w = workspace()
        w["cash"] = {"EUR": 100000}
        w["fx_rates"] = [{"from": "EUR", "to": "USD", "rate": 1.1, "as_of": AT}]
        scenario = {"id": "usd", "name": "USD down", "currency_shocks": {"EUR": 0.09}}
        result = stress_portfolio(w, AT, [scenario])[0]
        self.assertAlmostEqual(result["pnl"], 9900)
        self.assertEqual(result["rows"][0]["kind"], "cash")

    def test_local_return_and_translation_counted_once(self):
        w = workspace()
        i = w["instruments"][0]
        i["currency"] = "EUR"
        w["positions"] = [
            {"instrument_id": "asset", "quantity": 100, "average_price": 100}
        ]
        w["fx_rates"] = [{"from": "EUR", "to": "USD", "rate": 1.1, "as_of": AT}]
        scenario = {
            "id": "both",
            "name": "Both move",
            "equity": 0.1,
            "currency_shocks": {"EUR": 0.1},
        }
        self.assertAlmostEqual(stress_portfolio(w, AT, [scenario])[0]["pnl"], 2310)

    def test_cross_currency_shock_is_a_ratio(self):
        s = {"currency_shocks": {"EUR": 0.1, "JPY": -0.1}}
        self.assertAlmostEqual(currency_move("JPY", "EUR", s), 0.9 / 1.1 - 1)
        self.assertEqual(currency_move("EUR", "EUR", s), 0)

    def test_fx_underlying_and_quote_conversion_do_not_duplicate(self):
        w = workspace("fx")
        i = w["instruments"][0]
        i.update(price=1.1, fx_base="EUR", currency="USD")
        w["positions"] = [
            {"instrument_id": "asset", "quantity": 100000, "average_price": 1.1}
        ]
        s = {"id": "fx", "name": "FX", "currency_shocks": {"EUR": 0.09}}
        self.assertAlmostEqual(stress_portfolio(w, AT, [s])[0]["pnl"], 9900)

    def test_key_rate_spread_basis_and_funding_units(self):
        w = workspace("bond")
        i = w["instruments"][0]
        i.update(
            key_rate_dv01={"2Y": 2, "10Y": 3},
            dv01=5,
            spread_dv01=4,
            basis_sensitivity={"repo": -2},
            funding_notional=1000,
        )
        w["positions"] = [
            {"instrument_id": "asset", "quantity": 10, "average_price": 100}
        ]
        s = {
            "id": "stress",
            "name": "Combined",
            "curve_bp": {"2Y": -25, "10Y": 25},
            "spread_bp": 10,
            "basis_bp": {"repo": 5},
            "funding_bp": 100,
            "horizon_days": 365,
        }
        expected = (
            -10 * (2 * -25 + 3 * 25) - 10 * 4 * 10 + 10 * -2 * 5 - 10 * 1000 * 0.01
        )
        self.assertAlmostEqual(stress_portfolio(w, AT, [s])[0]["pnl"], expected)
        i["dv01"] = 6
        with self.assertRaisesRegex(ValueError, "sum"):
            validate_workspace(w)

    def test_missing_curve_inputs_are_unavailable_not_zero(self):
        w = workspace("bond")
        w["positions"] = [
            {"instrument_id": "asset", "quantity": 1, "average_price": 100}
        ]
        s = {"id": "curve", "name": "Curve", "curve_bp": {"2Y": -25, "10Y": 25}}
        result = stress_portfolio(w, AT, [s])[0]
        self.assertIsNone(result["pnl"])
        self.assertFalse(result["complete"])
        self.assertIn("key-rate", result["issues"][0])

    def test_currency_anchor_and_impossible_shocks_rejected(self):
        for extra in (
            {"currency_shocks": {"USD": 0.1}},
            {"foreign_currency_shock": -1},
        ):
            with self.assertRaises(ValueError):
                validate_scenarios([{"id": "bad", "name": "Bad", **extra}])


if __name__ == "__main__":
    unittest.main()
