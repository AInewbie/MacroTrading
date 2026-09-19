import json
import unittest
from unittest.mock import patch
from macrotrading import ai
from macrotrading.ingestion import (
    parse_feed,
    parse_fx,
    parse_market_csv,
    validate_public_url,
    xml_root,
    validate_sources,
)
from macrotrading.evaluation import backtest, replay
from macrotrading.migration import migrate_document
from helpers import config, event, ROOT, AT

FEED = b"""<rss><channel><item><title>Policy update</title><link>https://example.com/news</link><pubDate>Wed, 16 Sep 2026 12:00:00 GMT</pubDate><description>&lt;p&gt;A policy plan, not a completed outcome.&lt;/p&gt;</description></item></channel></rss>"""
SOURCE = {
    "id": "test-feed",
    "name": "Test feed",
    "kind": "rss",
    "url": "https://example.com/rss",
    "allowed_hosts": ["example.com"],
    "enabled": True,
    "theme_ids": ["test"],
}


class IngestionTests(unittest.TestCase):
    def test_feed_quarantine_stable_ids_and_raw_hash(self):
        first = parse_feed(FEED, SOURCE, AT)
        again = parse_feed(FEED, SOURCE, "2026-09-19T21:00:00Z")
        c = first["candidates"][0]
        self.assertEqual(c["id"], again["candidates"][0]["id"])
        self.assertTrue(c["review_required"])
        self.assertEqual(c["kind"], "unclassified")
        self.assertEqual(len(c["content_hash"]), 64)
        self.assertNotIn("<p>", c["summary"])

    def test_future_feed_and_xml_entities_are_rejected(self):
        self.assertEqual(parse_feed(FEED, SOURCE, "2026-01-01")["candidates"], [])
        with self.assertRaisesRegex(ValueError, "entities"):
            xml_root(b'<!DOCTYPE rss [<!ENTITY foo "bar">]><rss/>')

    def test_private_source_and_unapproved_host_are_blocked(self):
        with patch(
            "macrotrading.ingestion.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("127.0.0.1", 443))],
        ):
            with self.assertRaisesRegex(ValueError, "public"):
                validate_public_url("https://example.com/rss", ["example.com"])
        with self.assertRaises(ValueError):
            validate_sources([{**SOURCE, "url": "http://example.com/rss"}])

    def test_ecb_fx_has_date_and_explicit_conversion(self):
        r = parse_fx(
            b'<Envelope><Cube><Cube time="2026-09-17"><Cube currency="USD" rate="1.1"/><Cube currency="JPY" rate="160"/></Cube></Cube></Envelope>',
            AT,
        )
        self.assertEqual(r["fx_rates"][0]["from"], "EUR")
        self.assertEqual(r["fx_rates"][0]["rate"], 1.1)
        self.assertEqual(r["fx_rates"][0]["as_of"], "2026-09-17T00:00:00Z")

    def test_csv_does_not_turn_false_string_into_completed_session(self):
        r = parse_market_csv(
            "theme_id,session_date,proxy_close,completed\ntest,2026-09-17,100,false\n"
        )
        self.assertFalse(r["market_closes"][0]["completed"])
        with self.assertRaises(ValueError):
            parse_market_csv(
                "theme_id,session_date,proxy_close,completed\ntest,2026-09-17,100,yes\n"
            )

    def test_legacy_import_never_replays_original_broken_fills(self):
        doc = {
            "format": "macrotrading-workspace",
            "schemaVersion": 2,
            "executionMode": "paper-only",
            "workspace": json.loads((ROOT / "config/legacy_demo.json").read_text()),
        }
        w, warnings = migrate_document(doc)
        self.assertFalse(w["demo"])
        self.assertEqual(w["orders"], [])
        self.assertEqual(w["fills"], [])
        self.assertTrue(warnings)
        self.assertIn("legacy_history", w)


class EvaluationTests(unittest.TestCase):
    def test_signals_cannot_earn_the_return_at_the_decision_close(self):
        p = {
            "prices": [
                {"at": "2026-09-14", "close": 100},
                {"at": "2026-09-15", "close": 200},
                {"at": "2026-09-16", "close": 220},
            ],
            "signals": [{"known_at": "2026-09-14", "target": 1}],
            "transaction_bps": 0,
            "financing_bps": 0,
        }
        r = backtest(p)
        self.assertEqual(r["rows"][0]["earned_exposure"], 0)
        self.assertEqual(r["rows"][1]["earned_exposure"], 1)
        self.assertAlmostEqual(r["total_return"], 0.1)
        p["transaction_bps"] = 10
        self.assertLess(backtest(p)["total_return"], 0.1)

    def test_future_signal_does_not_leak_backwards(self):
        p = {
            "prices": [
                {"at": "2026-09-14", "close": 100},
                {"at": "2026-09-15", "close": 200},
                {"at": "2026-09-16", "close": 220},
            ],
            "signals": [{"known_at": "2026-09-17", "target": 1}],
        }
        self.assertEqual(backtest(p)["total_return"], 0)

    def test_replay_deduplication_precision_and_chronology(self):
        batches = [
            {
                "as_of": "2026-09-16T21:00:00Z",
                "evidence": [event()],
                "expected_alerts": ["material_evidence:test", "score_change:test"],
            },
            {"as_of": AT, "evidence": [event()], "expected_alerts": []},
        ]
        r = replay(config(), batches)
        self.assertEqual(r["precision"], 1)
        self.assertEqual(r["recall"], 1)
        self.assertEqual(r["runs"][1]["alerts"], [])
        with self.assertRaises(ValueError):
            replay(config(), list(reversed(batches)))


class AiTests(unittest.TestCase):
    def candidate(self):
        return parse_feed(FEED, SOURCE, AT)["candidates"][0]

    def claim(self):
        return {
            "theme_id": "test",
            "summary": "A tentative policy claim.",
            "kind": "policy_plan",
            "direction": "support",
            "evidence_ids": [self.candidate()["id"]],
            "uncertainties": "Only a headline and summary were supplied.",
        }

    def test_ai_is_optional_and_unknown_citations_are_rejected(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(ai.availability()["configured"])
            with self.assertRaises(ValueError):
                ai.extract([self.candidate()], config()["themes"])
        bad = self.claim()
        bad["evidence_ids"] = ["invented"]
        with self.assertRaises(ValueError):
            ai.validate_claims(
                {"claims": [bad]}, [self.candidate()], config()["themes"]
            )

    def test_mocked_structured_output_is_proposal_only(self):
        def transport(payload):
            self.assertTrue(payload["text"]["format"]["strict"])
            self.assertFalse(payload["store"])
            self.assertEqual(payload["max_output_tokens"], 2000)
            return {
                "status": "completed",
                "output": [
                    {
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps({"claims": [self.claim()]}),
                            }
                        ]
                    }
                ],
                "usage": {"output_tokens": 100},
            }

        with patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-only", "OPENAI_MODEL": "mock-model"}
        ):
            r = ai.extract([self.candidate()], config()["themes"], transport)
        self.assertTrue(r["review_required"])
        self.assertNotIn("orders", r)
        self.assertEqual(r["model"], "mock-model")
