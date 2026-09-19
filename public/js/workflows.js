import {
  esc,
  num,
  pct,
  money,
  badge,
  button,
  metric,
  table,
  list,
  json,
  options,
  field,
  link,
} from "./components.js";

export function valueChart(values, label, first = "", last = "") {
  const clean = values.filter(Number.isFinite);
  if (clean.length < 2)
    return '<p class="muted">At least two observations are needed.</p>';
  const low = Math.min(...clean),
    high = Math.max(...clean),
    range = high - low || 1;
  const points = clean
    .map(
      (v, i) =>
        `${65 + (i * 590) / (clean.length - 1)},${185 - ((v - low) * 155) / range}`,
    )
    .join(" ");
  return `<svg class="chart" viewBox="0 0 700 225" role="img" aria-label="${esc(label)}"><line class="axis" x1="65" y1="185" x2="655" y2="185"/><polyline class="series" stroke="#147f87" points="${points}"/><text x="2" y="34">${num(high, 4)}</text><text x="2" y="186">${num(low, 4)}</text><text x="65" y="214">${esc(first)}</text><text x="530" y="214">${esc(last)}</text></svg>`;
}

export function markets(d) {
  const m = d.market_snapshot;
  return `<div class="section-head"><div><h2>Market observations</h2><p>Acquire official daily reference history, review its meaning, then attach it to a research theme.</p></div>${button("Import market CSV", "import-market")}</div>
  <article class="card"><h2>ECB reference FX</h2><p>Use currency codes such as EUR, USD, GBP or JPY. These daily reference rates support research and reporting; they are not executable quotes.</p>
  <form data-form="market-refresh"><div class="form-grid"><label>Research theme<select name="theme_id">${options(Object.entries(d.config.themes).map(([k, v]) => [k, v.title]))}</select></label>${field("Base currency", "base", "EUR", "text", 'minlength="3" maxlength="3" required')}${field("Quote currency", "quote", "USD", "text", 'minlength="3" maxlength="3" required')}${field("History / sessions", "sessions", 60, "number", 'min="3" max="65" required')}</div><button class="primary">Fetch reference history</button></form></article>
  ${
    m
      ? `<div class="metrics">${metric("Pair", esc(m.pair), "Quote currency per unit of base")}${metric("Latest reference", num(m.market_closes.at(-1).proxy_close, 5), m.latest_session)}${metric("Age", num(m.age_days) + " days", m.stale ? "Refresh before acceptance" : "At retrieval")}${metric("Observations", m.market_closes.length, m.status)}</div><article class="card"><h2>Review the data and proxy</h2><p>${link("ECB source", m.source_url)} · Retrieved ${esc(m.retrieved_at)}</p>${valueChart(
          m.market_closes.map((c) => c.proxy_close),
          m.pair + " reference history",
          m.market_closes[0].session_date,
          m.latest_session,
        )}<p class="callout ${m.stale ? "warn" : ""}">${esc(m.warning)}</p>${list(m.issues)}<p>Historical rows are first-known at retrieval. This download cannot establish what the application knew at earlier decision times.</p>${m.status === "pending" ? button("Review proxy & accept history", "market-review", "", "primary") : badge("History accepted", "pass")}<details><summary>Inspect observations and provenance</summary><pre>${json(m)}</pre></details></article>`
      : '<div class="callout">Acquisition does not change scores or portfolio holdings. You will review the proxy, anchor and hypothesis direction before acceptance.</div>'
  }`;
}

export function discoveryView(d) {
  const drafts = d.theme_drafts || [];
  return `<div class="section-head"><div><h2>Discover and challenge themes</h2><p>Review new hypotheses before adding them to the research ledger.</p></div><div class="actions">${button("Screen source headlines", "discovery-offline")}${button("Propose themes with AI", "discovery-ai", "", "primary")}</div></div>
  <div class="callout">Start with pending items in Sources & evidence. Offline screening groups shared headline words into research questions. Optional AI proposes hypotheses, counterarguments and configured instrument expressions. Neither method sets scores or trade sizes.</div>
  ${
    drafts.length
      ? drafts
          .slice()
          .reverse()
          .map(
            (t) =>
              `<article class="card"><div class="card-head"><div><small>${esc(t.method)} · ${t.source_groups} source groups</small><h2>${esc(t.title)}</h2></div>${badge(t.status)}</div><p>${esc(t.hypothesis)}</p><div class="grid"><div><h3>Counterdrivers</h3>${list(t.counterdrivers)}<h3>Invalidation</h3><p>${esc(t.invalidation)}</p></div><div><h3>Catalysts</h3>${list(t.catalysts)}<h3>Uncertainty</h3><p>${esc(t.uncertainties)}</p></div></div><p class="muted">Text novelty ${num(t.text_novelty * 100)}% · ${esc(t.note)}</p><details><summary>Source evidence and expression candidates</summary>${table(
                ["Role", "Source"],
                [
                  ["Supporting", t.supporting_evidence_ids],
                  ["Contradicting", t.contradicting_evidence_ids],
                ].flatMap(([role, ids]) =>
                  ids.map((id) => {
                    const c = d.inbox.find((r) => r.id === id)?.payload;
                    return [role, c ? link(c.title, c.url) : esc(id)];
                  }),
                ),
              )}${table(
                ["Instrument", "Stance", "Rationale"],
                t.expressions.map((e) => [
                  esc(e.instrument_id),
                  esc(e.side),
                  esc(e.rationale),
                ]),
              )}</details>${t.status === "pending" ? `<div class="actions">${button("Review & accept unscored", "discovery-review", t.id, "primary")}${button("Reject proposal", "discovery-reject", t.id)}</div>` : ""}</article>`,
          )
          .join("")
      : '<article class="card"><h2>No theme proposals yet</h2><p>Refresh sources, select evidence, then screen for emerging research questions.</p></article>'
  }`;
}

export function scenarioDetails(d) {
  return `<article class="card"><div class="card-head"><div><h2>Scenario assumptions & attribution</h2><p>Currency translation includes cash. Curve, spread, basis and funding scenarios require explicit sensitivities; missing inputs stay unavailable.</p></div><div class="actions">${button("Edit scenarios", "scenario-edit")}${button("Add macro stress templates", "scenario-templates")}</div></div>${d.scenarios
    .map(
      (s) =>
        `<details><summary>${esc(s.name)} · ${money(s.pnl, d.workspace.base_currency)}</summary>${list(s.issues)}${table(
          ["Exposure", "Total P&L", "Currency translation"],
          s.rows.map((r) => [
            esc(r.symbol),
            money(r.pnl, d.workspace.base_currency),
            money(r.translation_pnl, d.workspace.base_currency),
          ]),
        )}</details>`,
    )
    .join("")}</article>`;
}

export function portfolioEvaluation(d, legacy) {
  const result =
    d.evaluation?.kind === "portfolio" ? d.evaluation.result : null;
  return `<article class="card"><h2>Portfolio evaluation</h2><p>Compare allocations across aligned base-currency price or total-return series, with benchmark, trading costs and financing. Load the example to inspect the input contract.</p><div class="actions">${button("Load portfolio example", "portfolio-evaluation-example", "", "primary")}${button("Download latest evaluation", "evaluation-download")}</div></article>${
    result
      ? `<article class="card"><h2>Portfolio results</h2><p>${badge(result.data_mode)} · ${esc(result.base_currency)} · ${result.sample_size} intervals</p><div class="metrics">${metric("Net return", pct(result.total_return))}${metric("Maximum drawdown", pct(result.max_drawdown))}${metric("Sharpe", num(result.sharpe))}${metric("Sortino", num(result.sortino))}${metric("Calmar", num(result.calmar))}${metric("Trading costs", money(result.transaction_cost, result.base_currency))}</div>${valueChart([result.initial_capital, ...result.rows.map((r) => r.equity)], "Portfolio equity curve", result.rows[0].at.slice(0, 10), result.rows.at(-1).at.slice(0, 10))}${list(result.warnings)}<p>${esc(result.assumption)}</p>${result.benchmark ? table(["Benchmark", "Return", "Excess return", "Tracking error", "Information ratio"], [[esc(result.benchmark.id), pct(result.benchmark.total_return), pct(result.benchmark.excess_total_return), pct(result.benchmark.tracking_error), num(result.benchmark.information_ratio)]]) : ""}${table(
          ["Asset", "Attributed P&L"],
          Object.entries(result.asset_pnl).map(([k, v]) => [
            esc(k),
            money(v, result.base_currency),
          ]),
        )}<details><summary>Full result and provenance</summary><pre>${json(result)}</pre></details></article>`
      : ""
  }${legacy(result ? { ...d, evaluation: null } : d)}`;
}

export function draftSpec(t) {
  return {
    title: t.title,
    hypothesis: t.hypothesis,
    components: null,
    counterdrivers: t.counterdrivers,
    catalysts: t.catalysts,
    invalidation: t.invalidation,
    fundamental_tests: [
      "Review independent sources and specify a measurable transmission mechanism.",
    ],
    decisions: [
      "Assign a reviewed score baseline and market proxy before considering an expression.",
    ],
    paper_risks: [t.uncertainties],
    expression: {
      proxy: "Review expression candidates",
      limits: "No automatic sizing or execution",
    },
    evidence_max_age_days: 30,
    market_max_age_days: 5,
  };
}
