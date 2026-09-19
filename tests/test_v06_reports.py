import unittest

from helpers import config, event, workspace, AT
from macrotrading.engine import AnalysisEngine
from macrotrading.models import EvidenceEvent
from macrotrading.html_report import render_html
from macrotrading.report import render_markdown
from macrotrading.portfolio import analyse_portfolio, stress_portfolio


class ReportContracts(unittest.TestCase):
    def result(self):
        c = config()
        c["themes"]["test"]["title"] = "<script>alert(1)</script>"
        r = AnalysisEngine(c).analyze([EvidenceEvent.from_dict(event())], [], AT)
        w = workspace()
        w["cash"] = {"EUR": 100000}
        w["fx_rates"] = [{"from": "EUR", "to": "USD", "rate": 1.1, "as_of": AT}]
        r["portfolio"] = analyse_portfolio(w, AT)
        r["scenarios"] = stress_portfolio(w, AT)
        return r

    def test_html_escapes_evidence_and_preserves_financial_result(self):
        r = self.result()
        html = render_html(r)
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("9,900.00", html)
        self.assertIn("First known", html)
        self.assertIn("missing", html)
        self.assertIn("Portfolio activation remains", html)

    def test_markdown_contains_evidence_and_unavailable_market(self):
        result = render_markdown(self.result())
        self.assertIn("A reviewed source", result)
        self.assertIn("https://example.com/evidence", result)


if __name__ == "__main__":
    unittest.main()
