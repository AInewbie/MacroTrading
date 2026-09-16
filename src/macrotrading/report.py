from __future__ import annotations

from typing import Any


LABELS = {
    "observed_fact": "Observed fact",
    "company_plan": "Company plan",
    "policy_plan": "Policy plan",
    "economist_forecast": "Economist forecast",
    "market_implied": "Market-implied pricing",
    "inference": "Inference",
}


def render_markdown(result: dict[str, Any]) -> str:
    alert_theme_ids = {item["theme_id"] for item in result["alerts"]}
    if not alert_theme_ids:
        return "::SKIP_COMPLETION::\n"

    lines = ["# MacroTrading theme update", ""]
    for theme_id, theme in result["themes"].items():
        if theme_id not in alert_theme_ids:
            continue
        lines.extend([f"## {theme['title']}", ""])
        for event in theme["new_evidence"]:
            lines.append(f"- **{LABELS[event['kind']]} — {event['direction']}:** {event['summary']}")
            for source in event["sources"]:
                lines.append(f"  Source: [{source['title']}]({source['url']}) ({source['published_at']})")
        lines.append("")
        if theme["score"] is None:
            lines.append(f"Status: **{theme['status']}**; no reproducible WATCH-v1 score applies.")
        else:
            lines.append(f"WATCH-v1: **{theme['score']:g}** — {theme['status']} — `{theme['components']}`")
        lines.extend(["", "Research only. No paper position or live order is activated or recommended.", ""])
    return "\n".join(lines).rstrip() + "\n"

