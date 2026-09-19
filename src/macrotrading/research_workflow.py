"""Reviewed acquisition and discovery use cases, independent of HTTP and UI."""

import json
from uuid import uuid4

from . import ai, discovery
from .engine import validate_config
from .ingestion import fetch_bytes
from .market_data import acquire_ecb
from .storage import Conflict
from .validation import identifier, stamp, text, instant


class ResearchWorkflow:
    def reserve_ai_call(self, action, ids):
        if not ai.availability()["configured"]:
            raise ValueError("AI provider is not configured")
        today = stamp()[:10]
        with self.store.transaction() as db:
            usage, version = self.store.get("ai_usage", {"date": today, "calls": 0}, db)
            if usage["date"] != today:
                usage = {"date": today, "calls": 0}
            if usage["calls"] >= 5:
                raise ValueError("Daily AI limit of five attempts reached")
            usage["calls"] += 1
            self.store.put(db, "ai_usage", usage, version)
            self.store.audit(
                db, action, {"candidate_ids": ids, "model": ai.availability()["model"]}
            )

    def market_refresh(self, body, fetcher=fetch_bytes):
        config, _ = self.store.get("config")
        theme = identifier(body["theme_id"])
        if theme not in config["themes"]:
            raise ValueError("choose an existing theme")
        calendar = json.loads((self.root / "config/calendars.json").read_text())[
            "ECB_REFERENCE_2026_2028"
        ]
        raw, snapshot = acquire_ecb(
            theme,
            body["base"],
            body["quote"],
            calendar,
            body.get("sessions", 60),
            fetcher=fetcher,
        )
        snapshot["status"] = "pending"
        with self.store.transaction() as db:
            self.store.put(db, "market_snapshot", snapshot)
            self.store.put(
                db,
                "pending_fx",
                {
                    "fx_rates": snapshot["fx_rates"],
                    "content_hash": snapshot["content_hash"],
                },
            )
            db.execute(
                "INSERT INTO source_fetches(source_id,at,status,content_hash,raw,items) VALUES(?,?,?,?,?,?)",
                (
                    "ecb-history",
                    snapshot["retrieved_at"],
                    "ok",
                    snapshot["content_hash"],
                    raw,
                    len(snapshot["market_closes"]),
                ),
            )
            self.store.audit(
                db,
                "Reference history staged for review",
                {
                    k: snapshot[k]
                    for k in (
                        "id",
                        "pair",
                        "theme_id",
                        "content_hash",
                        "latest_session",
                    )
                },
            )
        return snapshot

    def market_apply(self, body):
        reason = text(body["reason"], "proxy review reason", 2000)
        with self.store.transaction() as db:
            snapshot, version = self.store.get("market_snapshot", db=db)
            if (
                not snapshot
                or snapshot["id"] != body["snapshot_id"]
                or snapshot["status"] != "pending"
            ):
                raise ValueError(
                    "refresh and review the current pending market snapshot"
                )
            if (
                instant(stamp()) - instant(snapshot["market_closes"][-1]["close_at"])
            ).total_seconds() > 5 * 86400:
                raise ValueError(
                    "reference snapshot is stale; refresh before acceptance"
                )
            config, cv = self.store.get("config", db=db)
            if cv != body["expected_version"]:
                raise Conflict("Research configuration changed; review the proxy again")
            proxy = body.get("proxy", snapshot["proxy"])
            for key in ("series_id", "calendar", "currency", "convention"):
                if proxy.get(key) != snapshot["proxy"][key]:
                    raise ValueError(
                        "reviewed proxy must retain its staged data identity"
                    )
            if not any(
                r["close_at"] == proxy.get("anchor_at")
                and r["proxy_close"] == proxy.get("anchor_proxy")
                for r in snapshot["market_closes"]
            ):
                raise ValueError("anchor must match a staged observation")
            previous = config["themes"][snapshot["theme_id"]].get("proxy")
            config.setdefault("calendars", {})[proxy["calendar"]] = json.loads(
                (self.root / "config/calendars.json").read_text()
            )[proxy["calendar"]]
            config["themes"][snapshot["theme_id"]]["proxy"] = proxy
            validate_config(config)
            self.store.put(db, "config", config, cv)
            result = self._run(
                db,
                {
                    "as_of": stamp(),
                    "market_closes": snapshot["market_closes"],
                    "label": "Reviewed ECB reference history: " + snapshot["pair"],
                    "note": snapshot["warning"] + " Analyst reason: " + reason,
                },
            )
            snapshot.update(status="accepted", run_id=result["run_id"])
            self.store.put(db, "market_snapshot", snapshot, version)
            self.store.audit(
                db,
                "Reference proxy accepted",
                {
                    "before": previous,
                    "after": proxy,
                    "reason": reason,
                    "run_id": result["run_id"],
                },
            )
        return result

    def discover_themes(self, body, transport=None):
        method = body.get("method", "offline")
        if method not in ("offline", "ai"):
            raise ValueError("choose offline or ai discovery")
        byid = {
            r["id"]: r["payload"]
            for r in self.store.inbox()
            if r["status"] == "pending"
        }
        ids = body.get("candidate_ids") or list(byid)[: 10 if method == "ai" else 100]
        limit = 10 if method == "ai" else 100
        if (
            not isinstance(ids, list)
            or not 1 <= len(ids) <= limit
            or len(set(ids)) != len(ids)
            or any(i not in byid for i in ids)
        ):
            raise ValueError("select available pending source candidates")
        candidates = [byid[i] for i in ids]
        config, _ = self.store.get("config")
        workspace, _ = self.store.get("workspace")
        if method == "ai":
            self.reserve_ai_call("AI theme discovery requested", ids)
            result = discovery.discover(
                candidates, config["themes"], workspace["instruments"], transport
            )
        else:
            result = {
                "drafts": discovery.screen(
                    candidates, config["themes"], workspace["instruments"]
                )
            }
        with self.store.transaction() as db:
            existing, version = self.store.get("theme_drafts", [], db)
            indexed = {d["id"]: d for d in existing}
            for draft in result["drafts"]:
                indexed.setdefault(draft["id"], {**draft, "created_at": stamp()})
            self.store.put(db, "theme_drafts", list(indexed.values())[-200:], version)
            self.store.audit(
                db,
                "Theme proposals generated",
                {
                    "method": method,
                    "candidate_ids": ids,
                    "draft_ids": [d["id"] for d in result["drafts"]],
                    "request_hash": result.get("request_hash"),
                },
            )
        return result

    def review_theme_draft(self, body):
        reason = text(body["reason"], "review reason", 2000)
        with self.store.transaction() as db:
            drafts, dv = self.store.get("theme_drafts", [], db)
            draft = next((d for d in drafts if d["id"] == body["draft_id"]), None)
            if not draft or draft["status"] != "pending":
                raise ValueError("proposal missing or already reviewed")
            if body.get("action") == "reject":
                draft.update(status="rejected", reason=reason)
                self.store.put(db, "theme_drafts", drafts, dv)
                self.store.audit(
                    db, "Theme proposal rejected", {"id": draft["id"], "reason": reason}
                )
                return {"rejected": True}
            if body.get("action") != "accept":
                raise ValueError("accept or reject the proposal explicitly")
            config, cv = self.store.get("config", db=db)
            if cv != body["expected_version"]:
                raise Conflict(
                    "Research configuration changed; reload before accepting"
                )
            theme_id = identifier(body["theme_id"])
            if theme_id in config["themes"]:
                raise ValueError("new theme ID already exists")
            spec = body["spec"]
            # Scoring requires a separate explicit human baseline after discovery.
            if spec.get("components") is not None or spec.get("proxy"):
                raise ValueError(
                    "accept a new theme unscored; configure scores and market proxy in subsequent reviews"
                )
            spec["discovery_id"] = draft["id"]
            spec["expression_candidates"] = draft["expressions"]
            spec["uncertainties"] = draft["uncertainties"]
            config["themes"][theme_id] = spec
            validate_config(config)
            self.store.put(db, "config", config, cv)
            events = []
            now = stamp()
            for role, ids in (
                ("support", draft["supporting_evidence_ids"]),
                ("contradict", draft["contradicting_evidence_ids"]),
            ):
                for cid in ids:
                    row = db.execute(
                        "SELECT payload FROM inbox WHERE id=?", (cid,)
                    ).fetchone()
                    if row is None:
                        raise ValueError("referenced source is no longer available")
                    c = json.loads(row["payload"])
                    events.append(
                        {
                            "id": "discovery-" + str(uuid4()),
                            "theme_id": theme_id,
                            "observed_at": now,
                            "first_known_at": now,
                            "kind": "inference",
                            "direction": role,
                            "material": True,
                            "summary": "Reviewed relevance to hypothesis: "
                            + c["summary"][:5700],
                            "sources": [
                                {
                                    k: c[k]
                                    for k in (
                                        "url",
                                        "title",
                                        "published_at",
                                        "retrieved_at",
                                        "content_hash",
                                        "source_group",
                                    )
                                }
                            ],
                            "metadata": {
                                "discovery_id": draft["id"],
                                "review_reason": reason,
                            },
                        }
                    )
            result = self._run(
                db,
                {
                    "as_of": now,
                    "evidence": events,
                    "label": "Accepted new research theme: " + spec["title"],
                },
            )
            draft.update(
                status="accepted",
                theme_id=theme_id,
                reason=reason,
                run_id=result["run_id"],
            )
            self.store.put(db, "theme_drafts", drafts, dv)
            self.store.audit(
                db,
                "New theme accepted unscored",
                {"theme_id": theme_id, "draft_id": draft["id"], "reason": reason},
            )
        return result
