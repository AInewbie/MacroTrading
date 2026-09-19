from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import AnalysisEngine
from .models import EvidenceEvent, MarketClose
from .report import render_markdown
from .html_report import render_html


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze MacroTrading research themes")
    parser.add_argument("--config", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--state")
    parser.add_argument("--state-out")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument(
        "--full-review",
        action="store_true",
        help="render every configured theme, not only alerts",
    )
    parser.add_argument("--html-out", help="write a portable full-review HTML file")
    parser.add_argument(
        "--generated-at", default=None, help="timestamp shown in HTML output"
    )
    args = parser.parse_args()

    payload = _load(args.input)
    state = _load(args.state) if args.state and Path(args.state).exists() else None
    engine = AnalysisEngine(_load(args.config), state)
    result = engine.analyze(
        [EvidenceEvent.from_dict(item) for item in payload.get("evidence", [])],
        [MarketClose.from_dict(item) for item in payload.get("market_closes", [])],
        as_of=payload.get("as_of"),
    )
    result["input_note"] = payload.get("note", "")
    if args.state_out:
        Path(args.state_out).write_text(
            json.dumps(result["state"], indent=2) + "\n", encoding="utf-8"
        )
    if args.html_out:
        Path(args.html_out).write_text(
            render_html(result, generated_at=args.generated_at), encoding="utf-8"
        )
    print(
        json.dumps(result, indent=2)
        if args.as_json
        else render_markdown(result, full_review=args.full_review),
        end="",
    )


if __name__ == "__main__":
    main()
