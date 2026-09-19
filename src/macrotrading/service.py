"""Application orchestration. All durable transitions occur inside SQLite transactions."""

from __future__ import annotations
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from uuid import uuid4
import json
from . import __version__
from .storage import Store, Conflict
from .validation import canonical, digest, stamp, instant, text, identifier
from .engine import AnalysisEngine, validate_config
from .models import EvidenceEvent, MarketClose
from .portfolio import (
    validate_workspace,
    analyse_portfolio,
    stress_portfolio,
    reconcile,
)
from .execution import (
    create_order,
    pre_trade_checks,
    execute_paper,
    rebalance_orders,
    proposal,
)
from .migration import migrate_document
from .ingestion import validate_sources, acquire
from .evaluation import replay, backtest
from .portfolio_evaluation import portfolio_backtest
from .research_workflow import ResearchWorkflow
from .portfolio import SCENARIOS
from .scenarios import ADDITIONAL_SCENARIOS
from . import ai
from .html_report import render_html


class Service(ResearchWorkflow):
    def __init__(self, root, data_dir):
        self.root = Path(root)
        self.store = Store(Path(data_dir) / "macrotrading.sqlite3")
        self.code_hash = digest(
            {
                str(p.relative_to(root)): p.read_text()
                for p in sorted((self.root / "src" / "macrotrading").glob("*.py"))
            }
        )
        with self.store.transaction() as db:
            for key, file in [
                ("config", "live_themes.json"),
                ("workspace", "demo_workspace.json"),
                ("sources", "sources.json"),
            ]:
                if self.store.get(key, None, db)[0] is None:
                    value = json.loads((self.root / "config" / file).read_text())
                    if key == "workspace":
                        value = validate_workspace(value)
                    elif key == "config":
                        validate_config(value)
                    else:
                        validate_sources(value)
                    self.store.put(db, key, value)
                    self.store.audit(
                        db,
                        "Initialized " + key,
                        {"version": __version__, "demo": key == "workspace"},
                    )

    def snapshot(self):
        w, wv = self.store.get("workspace")
        c, cv = self.store.get("config")
        sources, sv = self.store.get("sources")
        latest, _ = self.store.get("latest_result")
        state, rv = self.store.get("research_state")
        return {
            "version": __version__,
            "market_snapshot": self.store.get("market_snapshot")[0],
            "theme_drafts": self.store.get("theme_drafts", [])[0],
            "scenario_definitions": w.get("scenarios", SCENARIOS),
            "scenario_templates": ADDITIONAL_SCENARIOS,
            "workspace": w,
            "workspace_version": wv,
            "config": c,
            "config_version": cv,
            "sources": sources,
            "sources_version": sv,
            "research": latest,
            "research_version": rv,
            "portfolio": analyse_portfolio(w),
            "scenarios": stress_portfolio(w),
            "source_health": self.store.source_health(),
            "inbox": self.store.inbox(),
            "runs": self.store.runs(),
            "decisions": self.store.decisions(),
            "audit": self.store.audit_rows(),
            "audit_integrity": self.store.verify_audit(),
            "ai": ai.availability(),
            "ai_result": self.store.get("ai_result")[0],
            "pending_fx": self.store.get("pending_fx")[0],
            "pending_market": self.store.get("pending_market")[0],
            "evaluation": self.store.get("evaluation")[0],
            "reconciliation": self.store.get("reconciliation")[0],
        }

    def _run(self, db, payload, now=None):
        c, _ = self.store.get("config", db=db)
        state, _ = self.store.get("research_state", db=db)
        w, _ = self.store.get("workspace", db=db)
        at = payload.get("as_of") or now or stamp()
        instant(at)
        events = [EvidenceEvent.from_dict(e) for e in payload.get("evidence", [])]
        closes = [MarketClose.from_dict(r) for r in payload.get("market_closes", [])]
        if len(events) > 5000 or len(closes) > 5000:
            raise ValueError("run input exceeds 5000 records")
        result = AnalysisEngine(c, state).analyze(events, closes, at)
        state_after = result.pop("state")
        result["input_note"] = payload.get("note", "")
        result["portfolio"] = analyse_portfolio(w, at)
        result["scenarios"] = stress_portfolio(w, at)
        run_id = str(uuid4())
        result["run_id"] = run_id
        manifest = {
            "run_id": run_id,
            "app_version": __version__,
            "created_at": stamp(),
            "as_of": result["as_of"],
            "label": payload.get("label", "Manual research run"),
            "code_hash": self.code_hash,
            "config_hash": digest(c),
            "input_hash": digest(payload),
            "state_before_hash": digest(state),
            "state_after_hash": digest(state_after),
            "portfolio_hash": digest(w),
            "alerts": len(result["alerts"]),
            "evidence_added": result["new_evidence_count"],
            "themes": {
                k: {
                    "score": t["score"],
                    "coverage": t["coverage"],
                    "lifecycle": t["lifecycle"],
                }
                for k, t in result["themes"].items()
            },
        }
        result["manifest"] = manifest
        html = render_html(result, result["as_of"])
        db.execute(
            "INSERT INTO runs VALUES(?,?,?,?,?,?,?)",
            (
                run_id,
                result["as_of"],
                manifest["created_at"],
                canonical(manifest),
                canonical(
                    {
                        "payload": payload,
                        "config": c,
                        "state_before": state,
                        "portfolio": w,
                    }
                ),
                canonical(result),
                html,
            ),
        )
        self.store.put(db, "research_state", state_after)
        self.store.put(db, "latest_result", result)
        self.store.audit(db, "Research run committed", manifest)
        return result

    def run(self, payload):
        with self.store.transaction() as db:
            return self._run(db, payload)

    def save_workspace(self, body):
        w = validate_workspace(body["workspace"])
        with self.store.transaction() as db:
            previous, _ = self.store.get("workspace", db=db)
            if w["orders"] != previous["orders"] or w["fills"] != previous["fills"]:
                raise ValueError(
                    "Use order actions or explicit workspace import to change execution history"
                )
            v = self.store.put(db, "workspace", w, body["expected_version"])
            self.store.audit(
                db,
                "Workspace updated",
                {
                    "before_hash": digest(previous),
                    "after_hash": digest(w),
                    "version": v,
                    "reason": text(
                        body.get("reason", "Manual portfolio or assumption edit"),
                        "reason",
                    ),
                },
            )
        return {"version": v}

    def import_workspace(self, body):
        w, warnings = migrate_document(body["document"])
        with self.store.transaction() as db:
            version = self.store.put(db, "workspace", w, body["expected_version"])
            self.store.audit(
                db,
                "Workspace imported",
                {"hash": digest(w), "warnings": warnings, "version": version},
            )
        return {"version": version, "warnings": warnings}

    def save_config(self, body):
        c = validate_config(body["config"])
        with self.store.transaction() as db:
            self.store.put(db, "config", c, body["expected_version"])
            self.store.audit(
                db,
                "Research policy updated",
                {"hash": digest(c), "reason": text(body["reason"], "change reason")},
            )
            # Atomic re-evaluation ensures the dashboard never displays stale policy scores.
            state, _ = self.store.get("research_state", db=db)
            if state:
                self._run(
                    db,
                    {
                        "as_of": max(stamp(), state["last_as_of"]),
                        "label": "Policy change re-evaluation",
                    },
                )
        return {"saved": True}

    def decision(self, body):
        tid = identifier(body["theme_id"])
        reason = text(body["reason"], "decision reason", 6000)
        action = body["action"]
        now = stamp()
        if action not in (
            "review",
            "defer",
            "suspend",
            "resume",
            "invalidate",
            "archive",
        ):
            raise ValueError("invalid decision action")
        meta = {"decision_action": action}
        if action in ("suspend", "resume", "archive"):
            meta["lifecycle_action"] = action
        if action == "invalidate":
            meta["invalidation_met"] = True
        event = {
            "id": "decision-" + str(uuid4()),
            "theme_id": tid,
            "observed_at": now,
            "first_known_at": now,
            "kind": "inference",
            "direction": "neutral",
            "material": True,
            "summary": reason,
            "sources": [],
            "metadata": meta,
            "component_updates": body.get("component_updates", {}),
        }
        with self.store.transaction() as db:
            result = self._run(
                db, {"evidence": [event], "label": "Decision: " + action}, now
            )
            db.execute(
                "INSERT INTO decisions VALUES(?,?,?,?,?,?)",
                (
                    event["id"],
                    now,
                    tid,
                    action,
                    reason,
                    canonical(
                        {
                            "run_id": result["run_id"],
                            "component_updates": event["component_updates"],
                        }
                    ),
                ),
            )
            self.store.audit(
                db,
                "Decision recorded",
                {
                    "theme_id": tid,
                    "action": action,
                    "reason": reason,
                    "run_id": result["run_id"],
                },
            )
        return result

    def stage(self, body):
        with self.store.transaction() as db:
            w, v = self.store.get("workspace", db=db)
            if v != body["expected_version"]:
                raise Conflict("Reload the changed portfolio before staging")
            o = create_order(w, body["order"])
            controls = pre_trade_checks(w, o)
            o["checks"] = controls["checks"]
            if any(x["id"] == o["id"] for x in w["orders"]):
                raise ValueError("order id already exists")
            o["status"] = "Staged" if controls["pass"] else "Blocked"
            w["orders"].append(o)
            self.store.put(db, "workspace", w, v)
            self.store.audit(
                db, "Paper order staged", {"order": o, "pass": controls["pass"]}
            )
        return {"order": o, "controls": controls}

    def execute(self, body):
        with self.store.transaction() as db:
            w, v = self.store.get("workspace", db=db)
            # An already-filled retry is harmless even if the supplied version is old.
            old = next((x for x in w["orders"] if x["id"] == body["order_id"]), None)
            if old is None:
                raise ValueError("unknown order")
            if old["status"] != "Filled" and v != body["expected_version"]:
                raise Conflict("Reload before executing against a changed portfolio")
            updated, result = execute_paper(w, body["order_id"])
            if result["status"] != "Already filled":
                self.store.put(db, "workspace", updated, v)
                self.store.audit(db, "Paper execution", result)
        return result

    def cancel_order(self, body):
        with self.store.transaction() as db:
            w, v = self.store.get("workspace", db=db)
            if v != body["expected_version"]:
                raise Conflict("Reload before cancelling")
            order = next((x for x in w["orders"] if x["id"] == body["order_id"]), None)
            if order is None or order["status"] == "Filled":
                raise ValueError("filled or unknown order cannot be cancelled")
            order["status"] = "Cancelled"
            self.store.put(db, "workspace", w, v)
            self.store.audit(db, "Order cancelled", {"order_id": order["id"]})
        return {"cancelled": True}

    def propose(self, body):
        return proposal(
            self.store.get("workspace")[0], body, self.store.get("latest_result")[0]
        )

    def rebalance(self):
        return {"orders": rebalance_orders(self.store.get("workspace")[0])}

    def save_sources(self, body):
        sources = validate_sources(body["sources"])
        with self.store.transaction() as db:
            self.store.put(db, "sources", sources, body["expected_version"])
            self.store.audit(db, "Sources updated", {"hash": digest(sources)})
        return {"saved": True}

    def refresh_sources(self, fetcher=None):
        sources = self.store.get("sources")[0]
        enabled = [s for s in sources if s["enabled"]]
        results = []

        def task(s):
            return acquire(s, **({"fetcher": fetcher} if fetcher else {}))

        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs = {pool.submit(task, s): s for s in enabled}
            for future in as_completed(jobs):
                s = jobs[future]
                at = stamp()
                try:
                    raw, parsed = future.result()
                    count = len(
                        parsed.get(
                            "candidates",
                            parsed.get("fx_rates", parsed.get("market_closes", [])),
                        )
                    )
                    with self.store.transaction() as db:
                        db.execute(
                            "INSERT INTO source_fetches(source_id,at,status,content_hash,raw,items) VALUES(?,?,?,?,?,?)",
                            (
                                s["id"],
                                at,
                                "warning" if parsed.get("warnings") else "ok",
                                parsed["content_hash"],
                                raw,
                                count,
                            ),
                        )
                        for c in parsed.get("candidates", []):
                            db.execute(
                                "INSERT OR IGNORE INTO inbox(id,source_id,first_known_at,payload) VALUES(?,?,?,?)",
                                (c["id"], s["id"], at, canonical(c)),
                            )
                        if "fx_rates" in parsed:
                            self.store.put(db, "pending_fx", parsed)
                        if "market_closes" in parsed:
                            self.store.put(db, "pending_market", parsed)
                        self.store.audit(
                            db,
                            "Source fetched",
                            {
                                "source_id": s["id"],
                                "hash": parsed["content_hash"],
                                "items": count,
                                "warnings": parsed.get("warnings", []),
                            },
                        )
                    results.append(
                        {
                            "source_id": s["id"],
                            "status": "ok",
                            "items": count,
                            "warnings": parsed.get("warnings", []),
                        }
                    )
                except Exception as exc:
                    message = str(exc)[:600]
                    with self.store.transaction() as db:
                        db.execute(
                            "INSERT INTO source_fetches(source_id,at,status,error) VALUES(?,?,?,?)",
                            (s["id"], at, "error", message),
                        )
                        self.store.audit(
                            db,
                            "Source fetch failed",
                            {"source_id": s["id"], "error": message},
                        )
                    results.append(
                        {"source_id": s["id"], "status": "error", "error": message}
                    )
        return {"sources": results}

    def accept_candidate(self, body):
        with self.store.transaction() as db:
            row = db.execute(
                "SELECT * FROM inbox WHERE id=?", (body["candidate_id"],)
            ).fetchone()
            if row is None or row["status"] != "pending":
                raise ValueError("candidate missing or already reviewed")
            c = json.loads(row["payload"])
            now = stamp()
            event = {
                "id": "accepted-" + str(uuid4()),
                "theme_id": body["theme_id"],
                "observed_at": c["published_at"],
                "first_known_at": now,
                "kind": body["kind"],
                "direction": body["direction"],
                "material": body.get("material", False),
                "summary": body.get("summary") or c["summary"],
                "sources": [
                    {
                        "url": c["url"],
                        "title": c["title"],
                        "published_at": c["published_at"],
                        "retrieved_at": c["retrieved_at"],
                        "content_hash": c["content_hash"],
                        "source_group": c["source_group"],
                    }
                ],
                "component_updates": body.get("component_updates", {}),
                "metadata": {"candidate_id": c["id"], "reviewed_at": now},
            }
            result = self._run(
                db, {"evidence": [event], "label": "Accepted source evidence"}
            )
            db.execute("UPDATE inbox SET status='accepted' WHERE id=?", (c["id"],))
            self.store.audit(
                db,
                "Evidence accepted",
                {"candidate_id": c["id"], "event_id": event["id"]},
            )
        return result

    def reject_candidate(self, body):
        with self.store.transaction() as db:
            changed = db.execute(
                "UPDATE inbox SET status='rejected' WHERE id=? AND status='pending'",
                (body["candidate_id"],),
            ).rowcount
            if not changed:
                raise ValueError("candidate missing or reviewed")
            self.store.audit(
                db,
                "Evidence candidate rejected",
                {
                    "id": body["candidate_id"],
                    "reason": text(body.get("reason", "Not relevant"), "reason"),
                },
            )
        return {"rejected": True}

    def apply_fx(self, body):
        with self.store.transaction() as db:
            pending, _ = self.store.get("pending_fx", db=db)
            if not pending:
                raise ValueError("No pending FX snapshot; refresh sources first")
            w, v = self.store.get("workspace", db=db)
            if v != body["expected_version"]:
                raise Conflict("Reload before applying FX")
            new = pending["fx_rates"]
            keys = {(r["from"], r["to"]) for r in new}
            w["fx_rates"] = [
                r for r in w["fx_rates"] if (r["from"], r["to"]) not in keys
            ] + new
            validate_workspace(w)
            self.store.put(db, "workspace", w, v)
            self.store.audit(
                db, "Reference FX snapshot applied", {"hash": pending["content_hash"]}
            )
        return {"applied": len(new)}

    def extract(self, body):
        ids = body.get("candidate_ids", [])
        byid = {
            r["id"]: r["payload"]
            for r in self.store.inbox()
            if r["status"] == "pending"
        }
        if (
            not ids
            or len(ids) > 10
            or len(set(ids)) != len(ids)
            or any(i not in byid for i in ids)
        ):
            raise ValueError("Select 1–10 distinct pending candidates")
        if not ai.availability()["configured"]:
            raise ValueError("AI provider is not configured")
        self.reserve_ai_call("AI extraction requested", ids)
        result = ai.extract(
            [byid[i] for i in ids], self.store.get("config")[0]["themes"]
        )
        with self.store.transaction() as db:
            self.store.put(db, "ai_result", result)
            self.store.audit(
                db,
                "AI proposals returned",
                {
                    "model": result["model"],
                    "usage": result["usage"],
                    "request_hash": result["request_hash"],
                },
            )
        return result

    def evaluate(self, body):
        handlers = {
            "backtest": backtest,
            "portfolio": portfolio_backtest,
            "replay": lambda payload: replay(
                self.store.get("config")[0], payload["batches"]
            ),
        }
        if body["kind"] not in handlers:
            raise ValueError("unknown evaluation kind")
        result = handlers[body["kind"]](body["payload"])
        if result is None:
            raise ValueError("unknown evaluation kind")
        with self.store.transaction() as db:
            self.store.put(
                db,
                "evaluation",
                {"kind": body["kind"], "as_of": stamp(), "result": result},
            )
            self.store.audit(
                db,
                "Evaluation completed",
                {"kind": body["kind"], "input_hash": digest(body["payload"])},
            )
        return result

    def reconcile(self, body):
        result = reconcile(self.store.get("workspace")[0], body["snapshot"])
        with self.store.transaction() as db:
            self.store.put(db, "reconciliation", result)
            self.store.audit(
                db,
                "Read-only reconciliation",
                {"pass": result["pass"], "as_of": result["as_of"]},
            )
        return result

    def export(self):
        return {
            "format": "macrotrading-workspace",
            "schemaVersion": 3,
            "exportedAt": stamp(),
            "executionMode": "paper-only",
            "workspace": self.store.get("workspace")[0],
        }

    def backup(self):
        with closing(self.store.connect()) as db:
            return {
                "format": "macrotrading-backup",
                "schema_version": 1,
                "exported_at": stamp(),
                "objects": {
                    r["key"]: json.loads(r["payload"])
                    for r in db.execute("SELECT key,payload FROM objects")
                    if r["key"] != "ai_usage"
                },
                "note": "State backup. Immutable run reports, source bodies and audit history remain in the SQLite database; copy the database for a complete archive.",
            }

    def restore(self, body):
        backup = body["backup"]
        if (
            backup.get("format") != "macrotrading-backup"
            or backup.get("schema_version") != 1
        ):
            raise ValueError("invalid state backup")
        objects = json.loads(canonical(backup["objects"]))
        objects["workspace"] = validate_workspace(objects["workspace"])
        validate_config(objects["config"])
        validate_sources(objects["sources"])
        state = objects.get("research_state")
        if state:
            # Validate and rebuild imported research from its complete accepted ledger.
            events = [EvidenceEvent.from_dict(e) for e in state["events"].values()]
            closes = [MarketClose.from_dict(c) for c in state["closes"].values()]
            AnalysisEngine(objects["config"]).analyze(
                events, closes, state["last_as_of"]
            )
            # Preserve validated snapshot memory (e.g. suspension after a market
            # recovery, or the last known M after observations become stale).
            for snapshot in state.get("theme_snapshots", {}).values():
                if snapshot.get("lifecycle") not in (
                    "watch",
                    "suspended",
                    "invalidated",
                    "archived",
                ):
                    raise ValueError("invalid restored lifecycle")
                if snapshot.get("components") is not None:
                    from .scoring import validate_components

                    validate_components(snapshot["components"])
                instant(snapshot["as_of"])
            objects["research_state"] = AnalysisEngine(
                objects["config"], state
            ).analyze([], [], state["last_as_of"])["state"]
        with self.store.transaction() as db:
            current, v = self.store.get("workspace", db=db)
            if v != body["expected_version"]:
                raise Conflict("Reload before restoring")
            for o in objects["workspace"]["orders"]:
                if o["status"] != "Filled":
                    o["status"] = "Imported"
            for key in ("workspace", "config", "sources"):
                self.store.put(db, key, objects[key])
            for key in (
                "research_state",
                "latest_result",
                "pending_fx",
                "pending_market",
                "market_snapshot",
                "theme_drafts",
                "ai_result",
                "evaluation",
                "reconciliation",
            ):
                db.execute("DELETE FROM objects WHERE key=?", (key,))
            db.execute("DELETE FROM inbox")
            if state:
                self.store.put(db, "research_state", objects["research_state"])
                self._run(
                    db,
                    {
                        "as_of": state["last_as_of"],
                        "label": "Restored accepted research",
                        "note": "Rebuilt from an imported state backup; source archives remain in the originating database.",
                    },
                )
            self.store.audit(
                db,
                "State backup restored",
                {
                    "exported_at": backup.get("exported_at"),
                    "before_workspace_hash": digest(current),
                    "after_workspace_hash": digest(objects["workspace"]),
                },
            )
        return {"restored": True}
