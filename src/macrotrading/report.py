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


def render_markdown(result: dict[str, Any], full_review: bool = False) -> str:
    selected = (
        set(result["themes"])
        if full_review
        else {item["theme_id"] for item in result["alerts"]}
    )
    if not selected:
        return "::SKIP_COMPLETION::\n"

    title = (
        "# MacroTrading five-theme review"
        if full_review
        else "# MacroTrading theme update"
    )
    lines = [title, ""]
    for theme_id, theme in result["themes"].items():
        if theme_id not in selected:
            continue
        lines.extend(
            [f"## {theme['title']}", "", f"**Thesis:** {theme['hypothesis']}", ""]
        )
        for event in theme["new_evidence"]:
            lines.append(
                f"- **{LABELS[event['kind']]} — {event['direction']}:** {event['summary']}"
            )
            for source in event["sources"]:
                lines.append(
                    f"  Source: [{source['title']}]({source['url']}) ({source['published_at']})"
                )
        if not theme["new_evidence"]:
            lines.append(
                "- No newly supplied evidence in this run; baseline state carried without treating missing data as stability."
            )
        lines.append("")
        if theme["score"] is None:
            lines.append(
                f"Status: **{theme['status']}**; no reproducible WATCH-v1 score applies."
            )
        else:
            lines.append(
                f"WATCH-v1: **{theme['score']:g}** — {theme['status']} — `{theme['components']}`"
            )
        if theme["counterdrivers"]:
            lines.extend(
                [
                    "",
                    "**Counterdrivers**",
                    *[f"- {item}" for item in theme["counterdrivers"]],
                ]
            )
        expression = theme["expression"]
        if expression:
            lines.extend(
                [
                    "",
                    f"**Expression:** {expression.get('proxy', 'Unpriced research proxy')}. {expression.get('limits', '')}".rstrip(),
                ]
            )
        if theme["fundamental_tests"]:
            lines.extend(
                [
                    "",
                    "**Fundamental tests**",
                    *[f"- {item}" for item in theme["fundamental_tests"]],
                ]
            )
        if theme["catalysts"]:
            lines.extend(
                ["", "**Catalysts**", *[f"- {item}" for item in theme["catalysts"]]]
            )
        lines.extend(["", f"**Invalidation:** {theme['invalidation']}"])
        if theme["paper_risks"]:
            lines.extend(
                [
                    "",
                    "**Paper/implementation risks**",
                    *[f"- {item}" for item in theme["paper_risks"]],
                ]
            )
        lines.extend(
            [
                "",
                "Research only. No paper position or live order is activated or recommended.",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
