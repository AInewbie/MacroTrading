import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from helpers import config, ROOT, AT
from macrotrading import discovery
from macrotrading.market_data import parse_ecb_history, build_snapshot
from macrotrading.service import Service
from macrotrading.engine import AnalysisEngine
from macrotrading.models import MarketClose
from macrotrading.calendars import consecutive
from datetime import date
from macrotrading.validation import canonical, stamp as real_stamp

XML = b'<Envelope><Cube><Cube time="2026-09-16"><Cube currency="USD" rate="1.15"/></Cube><Cube time="2026-09-17"><Cube currency="USD" rate="1.16"/></Cube><Cube time="2026-09-18"><Cube currency="USD" rate="1.17"/></Cube></Cube></Envelope>'


class ReviewedWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.service = Service(ROOT, Path(self.temp.name))
        self.cal = json.loads((ROOT / "config/calendars.json").read_text())[
            "ECB_REFERENCE_2026_2028"
        ]
        with self.service.store.transaction() as db:
            self.service.store.put(db, "config", config())

    def candidates(self):
        candidates = []
        for n in range(2):
            c = {
                "id": "candidate-" + str(n),
                "title": "Inflation expectations " + str(n),
                "summary": "Synthetic source for testing inflation research triage.",
                "url": "https://example.com/" + str(n),
                "published_at": "2026-09-16T12:00:00Z",
                "retrieved_at": AT,
                "content_hash": "a" * 64,
                "source_group": "source-" + str(n),
            }
            candidates.append(c)
            with self.service.store.transaction() as db:
                db.execute(
                    "INSERT INTO inbox(id,source_id,first_known_at,payload) VALUES(?,?,?,?)",
                    (c["id"], "fixture", AT, canonical(c)),
                )
        return candidates

    def test_ecb_pair_units_first_known_and_calendar(self):
        p = parse_ecb_history(XML, AT)
        s = build_snapshot(p, "test", "USD", "EUR", self.cal)
        self.assertAlmostEqual(s["market_closes"][-1]["proxy_close"], 1 / 1.17)
        self.assertEqual(s["market_closes"][0]["known_at"], AT)
        self.assertEqual(s["market_closes"][0]["convention"], "reference_rate")
        self.assertTrue(consecutive(date(2026, 4, 2), date(2026, 4, 7), self.cal))
        c = config()
        c["calendars"]["ECB_REFERENCE_2026_2028"] = self.cal
        c["themes"]["test"]["proxy"] = s["proxy"]
        with self.assertRaisesRegex(ValueError, "not yet known"):
            AnalysisEngine(c).analyze(
                [],
                [MarketClose.from_dict(s["market_closes"][0])],
                "2026-09-17T21:00:00Z",
            )

    def test_market_fetch_requires_explicit_acceptance_and_is_repeatable(self):
        with patch(
            "macrotrading.market_data.stamp",
            side_effect=lambda value=None: real_stamp(value) if value else AT,
        ):
            s = self.service.market_refresh(
                {"theme_id": "test", "base": "EUR", "quote": "USD"},
                fetcher=lambda source: XML,
            )
        self.assertIsNone(self.service.snapshot()["research"])
        with patch("macrotrading.research_workflow.stamp", return_value=AT):
            r = self.service.market_apply(
                {
                    "snapshot_id": s["id"],
                    "expected_version": self.service.snapshot()["config_version"],
                    "reason": "Review fixture proxy",
                }
            )
        self.assertEqual(r["themes"]["test"]["market"]["coverage"], "current")
        self.assertTrue(self.service.store.verify_audit()["valid"])
        # Reacquisition keeps the existing economic observation and first-known time.
        with patch(
            "macrotrading.market_data.stamp",
            side_effect=lambda value=None: (
                real_stamp(value) if value else "2026-09-19T12:00:00Z"
            ),
        ):
            s = self.service.market_refresh(
                {"theme_id": "test", "base": "EUR", "quote": "USD"},
                fetcher=lambda source: XML,
            )
        with patch(
            "macrotrading.research_workflow.stamp", return_value="2026-09-19T12:00:00Z"
        ):
            self.service.market_apply(
                {
                    "snapshot_id": s["id"],
                    "expected_version": self.service.snapshot()["config_version"],
                    "reason": "Review again",
                }
            )

    def test_discovery_acceptance_preserves_citations_and_stays_unscored(self):
        self.candidates()
        draft = self.service.discover_themes({"method": "offline"})["drafts"][0]
        self.assertNotIn("new-theme", self.service.snapshot()["config"]["themes"])
        spec = {
            "title": draft["title"],
            "hypothesis": draft["hypothesis"],
            "components": None,
            "counterdrivers": draft["counterdrivers"],
            "catalysts": draft["catalysts"],
            "invalidation": draft["invalidation"],
            "expression": {},
        }
        body = {
            "draft_id": draft["id"],
            "action": "accept",
            "theme_id": "new-theme",
            "reason": "Reviewed synthetic fixture",
            "expected_version": self.service.snapshot()["config_version"],
            "spec": spec,
        }
        with patch(
            "macrotrading.research_workflow.stamp", return_value="2026-09-19T12:00:00Z"
        ):
            r = self.service.review_theme_draft(body)
        t = r["themes"]["new-theme"]
        self.assertIsNone(t["score"])
        self.assertEqual(len(t["evidence"]), 2)
        self.assertTrue(all(e["kind"] == "inference" for e in t["evidence"]))
        self.assertEqual(self.service.snapshot()["workspace"]["orders"], [])
        with self.assertRaises(ValueError):
            self.service.review_theme_draft(body)

    def test_discovery_rejects_unknown_sources_and_instruments(self):
        candidates = self.candidates()
        d = discovery.screen(candidates, config()["themes"], [])[0]
        keys = [
            "title",
            "hypothesis",
            "supporting_evidence_ids",
            "contradicting_evidence_ids",
            "catalysts",
            "counterdrivers",
            "invalidation",
            "uncertainties",
            "expressions",
        ]
        proposal = {k: d[k] for k in keys}
        proposal["supporting_evidence_ids"] = ["invented"]
        with self.assertRaises(ValueError):
            discovery.normalize(
                {"themes": [proposal]}, candidates, config()["themes"], [], "test"
            )
        proposal["supporting_evidence_ids"] = [candidates[0]["id"]]
        proposal["expressions"] = [
            {"instrument_id": "invented", "side": "Buy", "rationale": "No"}
        ]
        with self.assertRaises(ValueError):
            discovery.normalize(
                {"themes": [proposal]}, candidates, config()["themes"], [], "test"
            )

    def test_mock_ai_discovery_creates_only_pending_drafts(self):
        candidates = self.candidates()
        draft = discovery.screen(candidates, config()["themes"], [])[0]
        fields = (
            "title",
            "hypothesis",
            "supporting_evidence_ids",
            "contradicting_evidence_ids",
            "catalysts",
            "counterdrivers",
            "invalidation",
            "uncertainties",
            "expressions",
        )
        value = {"themes": [{k: draft[k] for k in fields}]}

        def transport(payload):
            self.assertEqual(payload["text"]["format"]["name"], "macro_theme_discovery")
            self.assertEqual(payload["max_output_tokens"], 4000)
            return {
                "status": "completed",
                "output": [
                    {"content": [{"type": "output_text", "text": json.dumps(value)}]}
                ],
            }

        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "synthetic-test-key", "OPENAI_MODEL": "mock-model"},
        ):
            result = self.service.discover_themes({"method": "ai"}, transport=transport)
        self.assertEqual(result["drafts"][0]["status"], "pending")
        self.assertEqual(len(self.service.snapshot()["config"]["themes"]), 1)
        self.assertIsNone(self.service.snapshot()["research"])
        self.assertEqual(self.service.snapshot()["workspace"]["orders"], [])


if __name__ == "__main__":
    unittest.main()
