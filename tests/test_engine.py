import json
import unittest
from pathlib import Path

from macrotrading.engine import AnalysisEngine
from macrotrading.models import EvidenceEvent, MarketClose
from macrotrading.report import render_markdown
from macrotrading.html_report import render_html
from macrotrading.scoring import watch_v1_score

ROOT = Path(__file__).resolve().parents[1]


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "config/live_themes.json").read_text())

    def test_known_corrected_scores(self):
        themes = self.config["themes"]
        self.assertEqual(watch_v1_score(themes["ai_capex_repricing"]["components"]), 7.5)
        self.assertEqual(watch_v1_score(themes["japan_normalization"]["components"]), 42.5)
        self.assertEqual(watch_v1_score(themes["china_domestic_demand"]["components"]), 55.0)
        self.assertEqual(watch_v1_score(themes["europe_defense"]["components"]), 65.0)

    def test_material_event_alerts_once(self):
        raw = json.loads((ROOT / "examples/live_evidence_2026-09-16.json").read_text())
        events = [EvidenceEvent.from_dict(item) for item in raw["evidence"]]
        first = AnalysisEngine(self.config).analyze(events)
        self.assertEqual(len(first["alerts"]), 2)
        second = AnalysisEngine(self.config, first["state"]).analyze(events)
        self.assertEqual(second["alerts"], [])
        self.assertEqual(render_markdown(second), "::SKIP_COMPLETION::\n")

    def test_full_review_renders_all_themes_without_alerts(self):
        raw = json.loads((ROOT / "examples/five_theme_review_2026-09-16.json").read_text())
        events = [EvidenceEvent.from_dict(item) for item in raw["evidence"]]
        result = AnalysisEngine(self.config).analyze(events)
        self.assertEqual(result["alerts"], [])
        report = render_markdown(result, full_review=True)
        self.assertEqual(report.count("\n## "), 5)
        self.assertIn("Paper/implementation risks", report)
        html = render_html(result, "2026-09-16T16:55:00Z")
        self.assertEqual(html.count('class="theme-card"'), 5)
        self.assertIn("Portfolio decisions required", html)
        self.assertIn("Blocked pending implementation inputs", html)

    def test_market_threshold_requires_two_completed_closes(self):
        one = MarketClose.from_dict({"theme_id": "japan_normalization", "session_date": "2026-09-16", "proxy_close": 57.80, "proxy_return_pct": -1.0})
        first = AnalysisEngine(self.config).analyze([], [one])
        self.assertFalse(first["themes"]["japan_normalization"]["market"]["new_breach"])
        two = MarketClose.from_dict({"theme_id": "japan_normalization", "session_date": "2026-09-17", "proxy_close": 57.70, "proxy_return_pct": -0.2})
        second = AnalysisEngine(self.config).analyze([], [one, two])
        market = second["themes"]["japan_normalization"]["market"]
        self.assertTrue(market["new_breach"])
        self.assertEqual(market["breach_side"], "down")

    def test_m_component_uses_completed_session_direction(self):
        closes = [
            MarketClose.from_dict({"theme_id": "ai_capex_repricing", "session_date": "2026-09-16", "proxy_close": 530, "benchmark_close": 755, "proxy_return_pct": -2.0, "benchmark_return_pct": -0.5}),
            MarketClose.from_dict({"theme_id": "ai_capex_repricing", "session_date": "2026-09-17", "proxy_close": 520, "benchmark_close": 750, "proxy_return_pct": -1.8, "benchmark_return_pct": -0.2})
        ]
        result = AnalysisEngine(self.config).analyze([], closes)
        self.assertEqual(result["themes"]["ai_capex_repricing"]["components"]["M"], 1.0)


if __name__ == "__main__":
    unittest.main()
