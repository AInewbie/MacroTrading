import {
  esc,
  num,
  badge,
  button,
  table,
  list,
  json,
  link,
  options,
  field,
} from "./components.js";
export function themes(d) {
  const rows = Object.entries(d.config.themes);
  return `<div class="section-head"><div><h2>Research themes</h2><p>Accepted evidence, score changes and persistent decisions.</p></div><div class="actions">${button("Add theme", "add-theme")}${button("Add evidence", "add-evidence")}${button("Import research JSON", "import-research")}</div></div><div class="theme-grid">${rows
    .map(([id, s]) => {
      const t = d.research?.themes[id];
      return `<article class="theme-card"><div class="card-head"><div><div class="tags">${badge(t?.status || "Not run", t?.lifecycle || "")}${badge(t?.coverage || "missing")}</div><h2>${esc(s.title)}</h2></div><div class="theme-score">${num(t?.score, 1)}<small>WATCH / 100</small></div></div><p>${esc(s.hypothesis)}</p><div class="components">${Object.entries(
        t?.components || s.components || {},
      )
        .map(([k, v]) => `<span><b>${k}</b>${v}</span>`)
        .join(
          "",
        )}</div><p class="muted">Evidence quality: ${num(t?.evidence_quality, 1)} / 100 · ${t?.source_groups ?? 0} source groups · Market ${esc(t?.market.coverage || "missing")}</p>${t?.component_changes?.length ? `<div class="callout">${t.component_changes.map((c) => `${c.component}: ${c.before} → ${c.after}`).join(" · ")}</div>` : ""}${t?.lifecycle_reason ? `<div class="callout warn">${esc(t.lifecycle_reason)}</div>` : ""}<details><summary>Evidence and contradictions (${t?.evidence.length ?? 0})</summary>${(t?.evidence || []).map((e) => `<div class="evidence ${esc(e.direction)}"><small>${esc(e.kind.replaceAll("_", " "))} · ${esc(e.direction)} · ${esc(e.first_known_at)}</small><p>${esc(e.summary)}</p>${e.sources.map((s) => link(s.title, s.url)).join(" · ")}${t.active_evidence_ids.includes(e.id) ? "" : badge("Superseded")}</div>`).join("") || '<p class="muted">No accepted evidence. Baseline scores are assumptions.</p>'}</details><details><summary>Tests, catalysts and invalidation</summary><h3>Fundamental tests</h3>${list(s.fundamental_tests)}<h3>Counterdrivers</h3>${list(s.counterdrivers)}<h3>Catalysts</h3>${list(s.catalysts)}<h3>Invalidation</h3><p>${esc(s.invalidation)}</p></details><details><summary>Expression and portfolio decisions</summary><p>${esc(s.expression?.proxy)} — ${esc(s.expression?.limits)}</p>${list(s.decisions)}</details><div class="lifecycle"><div class="actions">${button("Record decision", "decision", id)}${button("Edit thesis", "edit-theme", id)}${button("Assess portfolio impact", "proposal-theme", id)}</div></div></article>`;
    })
    .join("")}</div>`;
}
export function sources(d) {
  const pending = d.inbox.filter((r) => r.status === "pending");
  return `<div class="section-head"><div><h2>Sources & evidence inbox</h2><p>Retrieved headlines require review before affecting a theme.</p></div><div class="actions">${button("Refresh enabled sources", "fetch-sources", "", "primary")}${button("Configure sources", "edit-sources")}</div></div><div class="callout">The bundled connectors cover Fed communications, ECB communications and ECB reference FX. Add approved RSS/Atom or market CSV endpoints for other themes. A headline’s theme suggestion is not a verified claim.</div><article class="card">${table(
    ["Source", "Enabled", "Latest result", "Observations", "Detail"],
    d.sources.map((s) => {
      const h = d.source_health.find((x) => x.source_id === s.id);
      return [
        link(s.name, s.url),
        s.enabled ? "Yes" : "No",
        badge(h?.status || "Not fetched"),
        num(h?.items ?? 0, 0),
        esc(h?.error || h?.at || ""),
      ];
    }),
  )}<div class="actions">${d.pending_fx ? button("Apply latest reference FX", "apply-fx") : ""}${d.pending_market ? button("Review fetched market input", "review-pending-market") : ""}${button("Import market CSV", "import-market")}</div></article><div class="section-head"><div><h2>Pending evidence (${pending.length})</h2><p>Select up to 10 entries for optional AI extraction. Review and accept each source separately.</p></div><button data-action="extract-ai" ${d.ai.configured ? "" : "disabled"}>Propose claims with AI</button></div><p class="muted">${d.ai.configured ? `Configured model: ${esc(d.ai.model)}. Clicking sends selected titles and summaries to OpenAI. Limit: five calls/day; no claims are automatically accepted.` : "Optional AI is unconfigured. Manual review works without an API key."}</p>${
    d.ai_result
      ? `<article class="card"><h2>Latest AI proposals · review required</h2>${table(
          [
            "Theme",
            "Proposed claim",
            "Classification",
            "Cited candidates",
            "Uncertainty",
          ],
          d.ai_result.claims.map((c) => [
            esc(d.config.themes[c.theme_id]?.title),
            esc(c.summary),
            esc(c.kind + " / " + c.direction),
            esc(c.evidence_ids.join(", ")),
            esc(c.uncertainties),
          ]),
        )}</article>`
      : ""
  }<div class="grid">${
    pending
      .map((r) => {
        const c = r.payload;
        return `<article class="card"><label class="check-label"><input type="checkbox" class="candidate-select" value="${esc(r.id)}"> Select for AI</label><h2>${esc(c.title)}</h2><p>${esc(c.summary)}</p><small>Published ${esc(c.published_at)}<br>First retrieved ${esc(r.first_known_at)}</small><p>${link("Original source", c.url)}</p><div class="actions">${button("Review & accept", "review-candidate", r.id, "primary")}${button("Dismiss", "dismiss-candidate", r.id)}</div></article>`;
      })
      .join("") ||
    '<div class="empty">Refresh sources or add evidence manually to populate the research ledger.</div>'
  }</div>`;
}
export function decisions(d) {
  return `<div class="section-head"><div><h2>Decision journal</h2><p>Suspension and invalidation persist until an explicit reviewed transition.</p></div>${button("Record decision", "decision", Object.keys(d.config.themes)[0])}</div><article class="card">${table(
    ["Time", "Theme", "Action", "Reason", "Run"],
    d.decisions.map((x) => [
      esc(x.at),
      esc(d.config.themes[x.theme_id]?.title || x.theme_id),
      badge(x.action),
      esc(x.reason),
      x.payload.run_id
        ? `<a href="/api/runs/${esc(x.payload.run_id)}/html" target="_blank" rel="noopener">Report ↗</a>`
        : "—",
    ]),
  )}</article><div class="callout">“Review” records an analyst decision. It does not approve quantities or activate a portfolio position. Paper orders are staged and executed separately.</div>`;
}
export function decisionForm(d, tid) {
  return `<form data-form="decision"><div class="form-grid"><label>Theme<select name="theme_id">${options(
    Object.entries(d.config.themes).map(([k, v]) => [k, v.title]),
    tid,
  )}</select></label><label>Action<select name="action">${options([
    ["review", "Record review"],
    ["defer", "Defer"],
    ["suspend", "Suspend"],
    ["invalidate", "Invalidate"],
    ["resume", "Resume after review"],
    ["archive", "Archive"],
  ])}</select></label><label class="full">Reason / evidence<textarea name="reason" required placeholder="Explain the decision and what would change it."></textarea></label><div class="full"><h3>Optional score component updates</h3><p class="muted">Leave blank to retain the accepted value. P/F/M/C/X: 0, 0.5 or 1. R: 0, 1 or 2.</p></div>${"PFMCXR"
    .split("")
    .map((k) =>
      field(
        k,
        k,
        "",
        "number",
        `step="${k === "R" ? 1 : 0.5}" min="0" max="${k === "R" ? 2 : 1}"`,
      ),
    )
    .join(
      "",
    )}</div><div class="actions"><button class="primary">Save decision & run review</button></div></form>`;
}
