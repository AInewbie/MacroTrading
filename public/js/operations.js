import {
  esc,
  num,
  money,
  badge,
  button,
  metric,
  table,
  list,
  json,
  field,
  options,
} from "./components.js";
export function history(d) {
  return `<div class="section-head"><div><h2>Run archive & audit history</h2><p>Each run retains its input, configuration, portfolio snapshot, result and hashes.</p></div><a class="button" href="/api/backup">Download state backup</a></div><article class="card"><h2>Research runs (${d.runs.length})</h2>${d.runs.map((r) => `<div class="run-row"><div class="card-head"><div><b>${esc(r.manifest.label)}</b><p>As of ${esc(r.as_of)} · ${r.manifest.alerts} alerts · ${r.manifest.evidence_added} accepted events added</p></div><div class="actions"><a class="button" href="/api/runs/${esc(r.id)}/html" target="_blank" rel="noopener">HTML report ↗</a><a class="button" href="/api/runs/${esc(r.id)}/json">Input & result JSON</a></div></div><small class="code">Input ${esc(r.manifest.input_hash)}<br>Policy ${esc(r.manifest.config_hash)}</small></div>`).join("") || '<p class="muted">No committed review yet.</p>'}</article><article class="card"><h2>Audit log</h2><p>${badge(d.audit_integrity.valid ? "Hash chain intact" : "Integrity check failed", d.audit_integrity.valid ? "pass" : "fail")} ${d.audit_integrity.rows ?? 0} recorded actions. This detects accidental changes; a local administrator still controls the database.</p>${table(
    ["Time", "Action", "Details"],
    d.audit.map((a) => [
      esc(a.at),
      esc(a.action),
      `<details><summary>Inspect</summary><pre>${json(a.payload)}</pre></details>`,
    ]),
  )}</article>`;
}
export function dataView(d, query = "") {
  const r = d.research;
  const q = query.toLowerCase();
  const rows = Object.entries(r?.themes || {}).filter(([id, t]) =>
    (id + " " + t.title).toLowerCase().includes(q),
  );
  return `<div class="section-head"><div><h2>All data</h2><p>Inspect and export what the application consumed and produced.</p></div><div class="actions">${button("Export theme CSV", "export-themes")}${button("Download full current snapshot", "export-data")}</div></div><div class="table-toolbar"><input class="search" id="data-search" placeholder="Filter themes…" value="${esc(query)}" aria-label="Filter theme data"></div><article class="card"><h2>Theme dimensions</h2>${table(
    [
      "Theme",
      "WATCH",
      "P",
      "F",
      "M",
      "C",
      "X",
      "R",
      "Evidence quality",
      "Lifecycle",
      "Evidence age / days",
      "Market",
    ],
    rows.map(([id, t]) => [
      esc(t.title),
      num(t.score),
      ..."PFMCXR".split("").map((k) => num(t.components?.[k])),
      num(t.evidence_quality),
      esc(t.lifecycle),
      num(t.evidence_age_days),
      esc(t.market.coverage),
    ]),
    "min-table",
  )}</article><article class="card"><h2>Dimension rankings</h2><p class="muted">Ties share a rank. Higher R means more counterdrivers; it is ranked from lowest to highest.</p>${table(
    ["Dimension", "Ranked themes"],
    [..."PFMCXR".split(""), "score", "evidence_quality"].map((k) => {
      const values = rows
        .map(([id, t]) => ({
          title: t.title,
          value: k.length === 1 ? t.components?.[k] : t[k],
        }))
        .filter((x) => x.value != null)
        .sort((a, b) => (k === "R" ? a.value - b.value : b.value - a.value));
      return [
        esc(k),
        values
          .map((x, i) => {
            const rank = values.findIndex((y) => y.value === x.value) + 1;
            return `${rank}. ${esc(x.title)} (${num(x.value)})`;
          })
          .join("<br>"),
      ];
    }),
  )}</article><article class="card"><h2>Accepted evidence</h2>${table(
    ["Theme", "ID", "Observed", "First known", "Kind", "Direction", "Summary"],
    rows.flatMap(([id, t]) =>
      t.evidence.map((e) => [
        esc(t.title),
        esc(e.id),
        esc(e.observed_at),
        esc(e.first_known_at),
        esc(e.kind),
        esc(e.direction),
        esc(e.summary),
      ]),
    ),
    "min-table",
  )}</article><article class="card"><details><summary>Inspect current research JSON</summary><pre>${json(r)}</pre></details><details><summary>Inspect portfolio JSON</summary><pre>${json(d.workspace)}</pre></details></article>`;
}
export function settings(d) {
  const w = d.workspace;
  return `<article class="card"><h2>Workspace identity & data mode</h2><form data-form="identity"><div class="form-grid">${field("Portfolio name", "name", w.name, "text", "required")}${field("Reporting currency", "base_currency", w.base_currency, "text", 'minlength="3" maxlength="3" required')}<label class="check-label"><input type="checkbox" name="demo" ${w.demo ? "checked" : ""}> Synthetic demo input mode</label>${field("Reason", "reason", "", "text", "required")}</div><p class="muted">Demo mode relaxes mark-age and expiry checks for the bundled synthetic portfolio. Turn it off when using your own portfolio; missing or stale inputs then block paper execution.</p><button class="primary">Save workspace mode</button></form></article><article class="card"><h2>Portfolio & risk assumptions</h2><p class="muted">Changes are validated and audited. They apply to future checks immediately.</p><form data-form="policy"><div class="form-grid">${Object.entries(
    w.policy,
  )
    .map(([k, v]) =>
      typeof v === "boolean"
        ? `<label class="check-label"><input type="checkbox" name="${k}" ${v ? "checked" : ""}> ${esc(k.replaceAll("_", " "))}</label>`
        : field(
            k.replaceAll("_", " "),
            k,
            v,
            "number",
            'step="any" min="0" required',
          ),
    )
    .join(
      "",
    )}${field("Reason for changing assumptions", "reason", "", "text", "required")}</div><button class="primary">Save risk policy</button></form></article><article class="card"><h2>WATCH scoring policy</h2><p class="muted">Positive weights must sum to 100. The R weight is zero or negative. Changing weights re-evaluates accepted evidence and records a new run.</p><form data-form="weights"><div class="form-grid">${Object.entries(
    d.config.weights,
  )
    .map(([k, v]) =>
      field(
        k + " weight",
        k,
        v,
        "number",
        `min="${k === "R" ? -50 : 0}" max="${k === "R" ? 0 : 100}" step="any" required`,
      ),
    )
    .join(
      "",
    )}${field("Version label", "version", d.config.version, "text", "required")}${field("Reason", "reason", "", "text", "required")}</div><button class="primary">Save & re-evaluate</button></form><details><summary>Advanced theme and calendar configuration</summary><p>Use this editor for catalyst/test definitions, proxy anchors, close calendars, freshness limits and market thresholds. Review all changes before saving.</p><form data-form="config"><textarea class="json-editor" name="config">${json(d.config)}</textarea>${field("Change reason", "reason", "", "text", "required")}<button class="primary">Validate & save configuration</button></form></details></article><article class="card"><h2>Workspace recovery</h2><p>Workspace export contains instruments, positions, cash and paper history. State backup also includes accepted research and configuration. Copy the SQLite database with the app stopped to retain every source body, run HTML and audit entry.</p><div class="actions"><a class="button" href="/api/export">Export workspace</a><a class="button" href="/api/backup">Back up state</a>${button("Import workspace", "import-workspace")}${button("Restore state backup", "restore-state")}</div></article><article class="card"><h2>Optional AI extraction</h2><p>${d.ai.configured ? `Configured: ${esc(d.ai.model)}` : "Set OPENAI_API_KEY and OPENAI_MODEL in the server environment, then restart."} The key is never sent to the browser or stored in exports. Each explicit extraction can send up to ten headlines/summaries, with a 2,000-token output limit and five calls per day. Provider billing still applies; call limits are not a monetary spending cap.</p><p class="muted">AI proposals cannot update scores, create quantities or place orders. Review source evidence independently before acceptance.</p></article>`;
}
export const sampleBacktest = {
  prices: [
    { at: "2026-09-14T20:00:00Z", close: 100 },
    { at: "2026-09-15T20:00:00Z", close: 102 },
    { at: "2026-09-16T20:00:00Z", close: 101 },
    { at: "2026-09-17T20:00:00Z", close: 104 },
    { at: "2026-09-18T20:00:00Z", close: 103 },
  ],
  signals: [
    { known_at: "2026-09-14T20:00:00Z", target: 1 },
    { known_at: "2026-09-17T20:00:00Z", target: 0 },
  ],
  transaction_bps: 5,
  borrow_bps: 200,
  financing_bps: 300,
};
export function evaluation(d) {
  const e = d.evaluation;
  return `<div class="callout">Evaluation is an experimental tool for supplied datasets. The example below is synthetic. It does not validate the profitability of the five macro themes.</div><article class="card"><h2>Chronological replay or expression backtest</h2><p>Replay accepts chronological batches with optional expected alert labels. Backtest accepts prices and timestamped target exposures from −1 to +1; signals execute at the following observed close.</p><form data-form="evaluate"><label>Evaluation type<select name="kind"><option value="backtest">Single-expression paper backtest</option><option value="replay">Research event replay</option></select></label><label>Input JSON<textarea name="payload" class="json-editor">${json(sampleBacktest)}</textarea></label><button class="primary">Run evaluation</button></form></article>${
    e
      ? `<article class="card"><h2>Latest result · ${esc(e.kind)}</h2><p class="muted">${esc(e.as_of)}</p>${
          e.kind === "backtest"
            ? `<div class="metrics">${metric("Net return", num(e.result.total_return * 100) + "%", "Includes modeled execution and carry costs")}${metric("Maximum drawdown", num(e.result.max_drawdown * 100) + "%", "Observed hypothetical equity curve")}${metric("Observations", num(e.result.sample_size, 0), "Small samples carry no validation claim")}${metric("Turnover", num(e.result.turnover), "Absolute changes in target exposure")}</div><p>${esc(e.result.assumption)}</p>${table(
                [
                  "Time",
                  "Earned exposure",
                  "Next exposure",
                  "Net return",
                  "Equity",
                ],
                e.result.rows.map((r) => [
                  esc(r.at),
                  num(r.earned_exposure),
                  num(r.next_exposure),
                  num(r.net_return * 100) + "%",
                  num(r.equity, 6),
                ]),
              )}`
            : `<div class="metrics">${metric("Precision", e.result.precision == null ? "Unlabelled" : num(e.result.precision * 100) + "%")}${metric("Recall", e.result.recall == null ? "Unlabelled" : num(e.result.recall * 100) + "%")}${metric("False alerts", num(e.result.false_positives, 0))}${metric("Missed alerts", num(e.result.false_negatives, 0))}</div>`
        }<details><summary>Complete evaluation output</summary><pre>${json(e.result)}</pre></details></article>`
      : ""
  }`;
}
