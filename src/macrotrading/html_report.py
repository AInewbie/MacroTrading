from __future__ import annotations

from html import escape
from typing import Any

from .report import LABELS


def _list(items: list[str], class_name: str = "") -> str:
    if not items:
        return '<p class="muted">None recorded.</p>'
    cls = f' class="{class_name}"' if class_name else ""
    return f"<ul{cls}>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def render_html(result: dict[str, Any], generated_at: str, title: str = "MacroTrading Five-Theme Review") -> str:
    themes = result["themes"]
    cards = []
    for theme_id, theme in themes.items():
        score = theme["score"]
        score_text = "N/A" if score is None else f"{score:g}"
        width = 0 if score is None else max(0, min(100, score))
        band = "unscored" if score is None else "priority" if score >= 70 else "research" if score >= 45 else "exploratory"
        evidence = []
        for event in theme["new_evidence"]:
            links = " ".join(
                f'<a href="{escape(src["url"], quote=True)}" target="_blank" rel="noreferrer">{escape(src["title"])}</a>'
                for src in event["sources"]
            )
            evidence.append(
                f'<div class="evidence {escape(event["direction"])}">'
                f'<span class="tag">{escape(LABELS[event["kind"]])}</span>'
                f'<strong>{escape(event["direction"].title())}</strong>'
                f'<p>{escape(event["summary"])}</p><small>{links}</small></div>'
            )
        expression = theme["expression"]
        decisions = theme.get("decisions", [])
        cards.append(f"""
        <article class="theme-card" id="{escape(theme_id)}">
          <header><div><p class="eyebrow">{escape(theme["status"])}</p><h2>{escape(theme["title"])}</h2></div>
            <div class="score {band}"><span>{score_text}</span><small>WATCH-v1</small></div></header>
          <div class="score-track"><i style="width:{width}%"></i></div>
          <p class="thesis"><b>Thesis</b> {escape(theme["hypothesis"])}</p>
          <section><h3>Evidence & contradiction</h3>{''.join(evidence) or '<p class="muted">No new evidence supplied.</p>'}</section>
          <div class="two-col">
            <section><h3>Counterdrivers</h3>{_list(theme["counterdrivers"])}</section>
            <section><h3>Expression</h3><p><b>{escape(expression.get("proxy", "Unpriced"))}</b><br>{escape(expression.get("limits", ""))}</p></section>
            <section><h3>Catalysts</h3>{_list(theme["catalysts"])}</section>
            <section><h3>Invalidation</h3><p>{escape(theme["invalidation"])}</p></section>
          </div>
          <section class="decision"><h3>Portfolio decisions required</h3>{_list(decisions, "checklist")}</section>
          <details><summary>Implementation risks and fundamental tests</summary>
            <div class="two-col"><div><h4>Risks</h4>{_list(theme["paper_risks"])}</div><div><h4>Tests</h4>{_list(theme["fundamental_tests"])}</div></div>
          </details>
        </article>""")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><style>
:root{{--ink:#14213d;--muted:#64748b;--bg:#f4f7fb;--card:#fff;--line:#dce4ef;--blue:#2364d2;--amber:#f59e0b;--green:#14804a;--red:#be3455}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.5}}
.wrap{{max-width:1180px;margin:auto;padding:36px 22px 64px}} .hero{{background:linear-gradient(135deg,#14213d,#274c77);color:white;padding:34px;border-radius:22px;box-shadow:0 15px 35px #14213d24}}
.hero h1{{margin:4px 0 8px;font-size:clamp(28px,5vw,46px);line-height:1.06}} .hero p{{margin:0;color:#dbeafe}} .eyebrow{{margin:0;text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:800;color:var(--blue)}}
.gate{{display:grid;grid-template-columns:1.2fr 2fr;gap:22px;margin:22px 0;background:#fff7ed;border:1px solid #fed7aa;border-radius:18px;padding:22px}} .gate h2{{margin:0 0 8px;color:#9a3412}} .gate ul{{margin:0;padding-left:20px}}
.dashboard{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:22px 0}} .mini{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}} .mini strong{{display:block;font-size:25px}} .mini span{{font-size:12px;color:var(--muted)}}
.theme-card{{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:24px;margin:18px 0;box-shadow:0 8px 24px #14213d0a}} .theme-card header{{display:flex;justify-content:space-between;gap:18px;align-items:center}} h2{{margin:3px 0;font-size:24px}} h3{{font-size:14px;text-transform:uppercase;letter-spacing:.06em;margin:22px 0 9px}} h4{{margin-bottom:6px}}
.score{{width:88px;height:70px;border-radius:14px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:white;background:var(--muted);flex:none}} .score span{{font-size:25px;font-weight:800;line-height:1}} .score small{{font-size:10px;margin-top:5px}} .score.exploratory{{background:#64748b}} .score.research{{background:var(--amber)}} .score.priority{{background:var(--green)}}
.score-track{{height:5px;background:#e9eef5;border-radius:10px;margin:15px 0 20px;overflow:hidden}} .score-track i{{height:100%;display:block;background:linear-gradient(90deg,var(--blue),#7c3aed)}} .thesis{{font-size:17px;background:#f8fafc;padding:14px;border-radius:12px}}
.evidence{{border-left:4px solid var(--muted);padding:10px 14px;margin:9px 0;background:#f8fafc;border-radius:0 10px 10px 0}} .evidence.support{{border-color:var(--green)}} .evidence.contradict{{border-color:var(--red)}} .evidence p{{margin:5px 0}} .evidence small a{{color:var(--blue);margin-right:10px}} .tag{{font-size:11px;background:#e2e8f0;padding:3px 7px;border-radius:99px;margin-right:8px}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:8px 30px}} ul{{padding-left:20px}} li{{margin:5px 0}} .decision{{background:#eff6ff;border:1px solid #bfdbfe;padding:2px 18px 13px;border-radius:14px}} .checklist{{list-style:'□  '}} details{{margin-top:16px;border-top:1px solid var(--line);padding-top:14px}} summary{{cursor:pointer;font-weight:700}} .muted{{color:var(--muted)}} footer{{text-align:center;color:var(--muted);font-size:12px;margin-top:26px}}
@media(max-width:850px){{.dashboard{{grid-template-columns:1fr 1fr}}.gate,.two-col{{grid-template-columns:1fr}}}} @media print{{body{{background:white}}.theme-card{{break-inside:avoid;box-shadow:none}}}}
</style></head><body><main class="wrap">
<section class="hero"><p class="eyebrow" style="color:#93c5fd">Research decision dashboard · {escape(generated_at)}</p><h1>{escape(title)}</h1><p>Evidence, contradictions, catalysts and portfolio approval gates. Research only—no orders or active paper positions.</p></section>
<section class="gate"><div><p class="eyebrow" style="color:#c2410c">Portfolio activation gate</p><h2>Blocked pending implementation inputs</h2><p>No theme should become a portfolio position from these scores alone.</p></div><ul><li>Provide current holdings and overlapping factor exposures.</li><li>Set risk budget, horizon and acceptable drawdown.</li><li>Confirm permitted instruments, derivatives and shorting.</li><li>Verify liquidity, spreads, financing, borrow and option surfaces.</li></ul></section>
<section class="dashboard">{''.join(f'<div class="mini"><span>{escape(t["title"])}</span><strong>{"N/A" if t["score"] is None else f"{t["score"]:g}"}</strong><span>{escape(t["status"])}</span></div>' for t in themes.values())}</section>
{''.join(cards)}
<footer>Generated by MacroTrading. Scores are deterministic classifications, not probabilities or investment recommendations.</footer>
</main></body></html>"""

