import { load, post } from "./api.js";
import {
  esc,
  json,
  options,
  field,
  button,
  csv,
  download,
} from "./components.js";
import { overview } from "./overview.js";
import { themes, sources, decisions, decisionForm } from "./research.js";
import {
  portfolio,
  risk,
  orders,
  ticketForm,
  proposalForm,
  checks,
} from "./portfolio.js";
import { history, dataView, settings, evaluation } from "./operations.js";

import {
  markets,
  discoveryView,
  scenarioDetails,
  portfolioEvaluation,
  draftSpec,
} from "./workflows.js";

const pages = {
  overview: "Overview",
  themes: "Research themes",
  discovery: "Theme discovery",
  markets: "Market data",
  sources: "Sources & evidence",
  portfolio: "Portfolio",
  risk: "Portfolio risk",
  orders: "Paper orders",
  decisions: "Decision journal",
  data: "All data",
  history: "Run archive",
  evaluation: "Evaluation",
  settings: "Settings",
};
let d = null,
  lastProposal = null,
  lastRebalance = [],
  fileAction = "",
  query = "";
const app = document.querySelector("#app"),
  modal = document.querySelector("#modal");
const clone = (v) => structuredClone(v),
  now = () => new Date().toISOString();
const components = (f) =>
  Object.fromEntries(
    [..."PFMCXR"]
      .filter((k) => f.get(k) !== null && f.get(k) !== "")
      .map((k) => [k, Number(f.get(k))]),
  );
function notice(message, error = false) {
  const n = document.querySelector("#notice");
  n.hidden = false;
  n.className = error ? "notice error" : "notice";
  n.textContent = message;
}
function open(title, body) {
  document.querySelector("#modal-title").textContent = title;
  document.querySelector("#modal-body").innerHTML = body;
  if (!modal.open) modal.showModal();
}
function render() {
  if (!d) return;
  const v = pages[location.hash.slice(1)] ? location.hash.slice(1) : "overview";
  document.querySelector("#page-title").textContent = pages[v];
  document.querySelector("#nav").innerHTML = Object.entries(pages)
    .map(
      ([id, title]) =>
        `<a href="#${id}" class="nav-link ${id === v ? "active" : ""}" ${id === v ? 'aria-current="page"' : ""}>${title}</a>`,
    )
    .join("");
  const views = {
    overview,
    themes,
    sources,
    portfolio,
    risk: (x) => risk(x, lastProposal) + scenarioDetails(x),
    discovery: discoveryView,
    markets,
    orders: (x) => orders(x, lastRebalance),
    decisions,
    data: (x) => dataView(x, query),
    history,
    evaluation: (x) => portfolioEvaluation(x, evaluation),
    settings,
  };
  app.innerHTML = views[v](d);
  document.querySelector(".environment small").textContent =
    (d.workspace.demo ? "Synthetic demo inputs" : "User-supplied inputs") +
    " · v" +
    d.version;
}
async function reload() {
  d = await load();
  render();
}
function go(view) {
  if (location.hash === "#" + view) render();
  else location.hash = view;
  modal.close();
  document.querySelector("#sidebar").classList.remove("open");
}
function editor(title, form, name, value, extra = "") {
  open(
    title,
    `<form data-form="${form}"><label>${esc(name)}<textarea class="json-editor" name="${name}" required>${json(value)}</textarea></label>${extra}<button class="primary">Validate & save</button></form>`,
  );
}
function researchInput(
  payload = {
    as_of: now(),
    label: "Manual research run",
    evidence: [],
    market_closes: [],
  },
) {
  editor(
    "Review research input",
    "run",
    "payload",
    payload,
    '<p class="muted">Only include information known by the cutoff. Duplicate evidence IDs must have identical content. Runs cannot rewind the current ledger; use Evaluation for historical replay.</p>',
  );
}
function evidenceForm(candidate = null) {
  const first = Object.keys(d.config.themes)[0];
  open(
    candidate ? "Review source evidence" : "Add accepted evidence",
    `<form data-form="evidence"><input type="hidden" name="candidate_id" value="${esc(candidate?.id || "")}"><div class="form-grid"><label>Theme<select name="theme_id">${options(
      Object.entries(d.config.themes).map(([k, v]) => [k, v.title]),
      candidate?.suggested_themes?.[0] || first,
    )}</select></label><label>Classification<select name="kind">${options(
      [
        "observed_fact",
        "company_plan",
        "policy_plan",
        "economist_forecast",
        "market_implied",
        "inference",
      ].map((x) => [x, x.replaceAll("_", " ")]),
      candidate ? "observed_fact" : "inference",
    )}</select></label><label>Direction<select name="direction">${options(["support", "contradict", "neutral"].map((x) => [x, x]))}</select></label><label class="check-label"><input type="checkbox" name="material"> Material change</label><label class="full">Reviewed summary<textarea name="summary" required>${esc(candidate?.summary || "")}</textarea></label>${candidate ? `<p class="full">Source: ${esc(candidate.title)}. The original publication time and retrieval hash are retained.</p>` : `${field("Observation time (UTC ISO)", "observed_at", now(), "text", "required")}${field("Source URL (required for facts)", "url", "", "url")}${field("Source title", "title")}${field("Source publication time (UTC ISO)", "published_at", now())}${field("Source group (e.g. federalreserve.gov)", "source_group")}`}<p class="full muted">Optional accepted component updates. Leave blank to retain current values.</p>${[..."PFMCXR"].map((k) => field(k, k, "", "number", `step="${k === "R" ? 1 : 0.5}" min="0" max="${k === "R" ? 2 : 1}"`)).join("")}</div><button class="primary">Accept evidence & run review</button></form>`,
  );
}
async function saveWorkspace(w, reason) {
  await post("workspace/save", {
    workspace: w,
    expected_version: d.workspace_version,
    reason,
  });
  lastProposal = null;
  lastRebalance = [];
}
const actions = {
  "market-review": async () =>
    editor(
      "Review reference proxy",
      "market-apply",
      "proxy",
      d.market_snapshot.proxy,
      `<input type="hidden" name="snapshot_id" value="${esc(d.market_snapshot.id)}"><p>Review the anchor and positive/negative hypothesis direction. This changes the selected theme's market proxy; it does not change portfolio prices.</p>${field("Review reason", "reason", "", "text", "required")}`,
    ),
  "discovery-offline": async () => {
    const r = await post("discovery/run", { method: "offline" });
    await reload();
    go("discovery");
    notice(
      `${r.drafts.length} research questions proposed. Review sources before acceptance.`,
    );
  },
  "discovery-ai": async () => {
    const r = await post("discovery/run", { method: "ai" });
    await reload();
    go("discovery");
    notice(`${r.drafts.length} AI theme proposals returned for review.`);
  },
  "discovery-review": async (id) => {
    const t = d.theme_drafts.find((x) => x.id === id);
    editor(
      "Review a new research theme",
      "discovery-review",
      "spec",
      draftSpec(t),
      `<input type="hidden" name="draft_id" value="${esc(id)}">${field("New stable theme ID", "theme_id", id.replace("draft-", "theme-"), "text", "required")}${field("Review reason", "reason", "", "text", "required")}<p>Acceptance records cited relevance as inference. Scores and proxy require separate review.</p>`,
    );
  },
  "discovery-reject": async (id) =>
    open(
      "Reject theme proposal",
      `<form data-form="discovery-reject"><input type="hidden" name="draft_id" value="${esc(id)}">${field("Rejection reason", "reason", "", "text", "required")}<button class="primary">Reject proposal</button></form>`,
    ),
  "scenario-edit": async () =>
    editor(
      "Review scenario assumptions",
      "scenarios",
      "scenarios",
      d.scenario_definitions,
      field("Change reason", "reason", "", "text", "required"),
    ),
  "scenario-templates": async () =>
    editor(
      "Review extended macro scenarios",
      "scenarios",
      "scenarios",
      [
        ...d.scenario_definitions,
        ...d.scenario_templates.filter(
          (x) => !d.scenario_definitions.some((y) => y.id === x.id),
        ),
      ],
      `<p>These scenarios can expose missing curve, spread, basis or funding sensitivities. Explicit zero means no exposure; absent data means unknown.</p>${field("Change reason", "reason", "", "text", "required")}`,
    ),
  "portfolio-evaluation-example": async () => {
    const r = await fetch("/api/evaluation-example");
    if (!r.ok) throw new Error("Example could not be loaded");
    editor(
      "Run portfolio evaluation",
      "evaluate",
      "payload",
      await r.json(),
      '<input type="hidden" name="kind" value="portfolio"><p>The example is synthetic. Replace its series and provenance with your own aligned dataset.</p>',
    );
  },
  "evaluation-download": async () => {
    if (!d.evaluation) throw new Error("Run an evaluation first");
    download("macrotrading-evaluation.json", d.evaluation);
  },

  refresh: async () => {
    await reload();
    notice("Workspace reloaded.");
  },
  navigate: async (id) => go(id),
  "close-modal": async () => modal.close(),
  run: async () => researchInput(),
  example: async () => {
    await post("run/example");
    await reload();
    notice("Historical example committed. It is not live market data.");
  },
  "add-evidence": async () => evidenceForm(),
  decision: async (id) =>
    open("Record a research decision", decisionForm(d, id)),
  "proposal-theme": async (id) =>
    open("Assess portfolio impact", proposalForm(d, id)),
  "add-theme": async () => editTheme(""),
  "edit-theme": async (id) => editTheme(id),
  "review-candidate": async (id) =>
    evidenceForm(d.inbox.find((r) => r.id === id).payload),
  "dismiss-candidate": async (id) => {
    await post("inbox/reject", {
      candidate_id: id,
      reason: "Dismissed after manual review",
    });
    await reload();
    notice("Candidate dismissed.");
  },
  "edit-sources": async () =>
    editor(
      "Configure approved sources",
      "sources",
      "sources",
      d.sources,
      '<p class="muted">HTTPS only. List every permitted redirect host in allowed_hosts. Keep credentials out of URLs. Changes take effect on your next explicit refresh.</p>',
    ),
  "fetch-sources": async () => {
    notice("Fetching enabled sources…");
    const r = await post("sources/refresh");
    await reload();
    const failed = r.sources.filter((s) => s.status === "error");
    notice(
      `${r.sources.length - failed.length} sources fetched; ${failed.length} failed. Review source health and pending evidence.`,
      failed.length > 0,
    );
  },
  "apply-fx": async () => {
    await post("fx/apply", { expected_version: d.workspace_version });
    await reload();
    notice(
      "Reference FX applied. Review its date before using it for portfolio checks.",
    );
  },
  "review-pending-market": async () =>
    researchInput({
      as_of: now(),
      label: "Reviewed fetched market closes",
      market_closes: d.pending_market.market_closes,
      evidence: [],
    }),
  "extract-ai": async () => {
    const ids = [...document.querySelectorAll(".candidate-select:checked")].map(
      (x) => x.value,
    );
    notice("Requesting AI proposals for your selected sources…");
    await post("ai/extract", { candidate_ids: ids });
    await reload();
    notice("AI proposals returned. They require independent source review.");
  },
  ticket: async () => open("Stage a paper order", ticketForm(d)),
  restage: async (id) =>
    open(
      "Create a fresh paper order",
      ticketForm(
        d,
        d.workspace.orders.find((o) => o.id === id),
      ),
    ),
  execute: async (id) => {
    const r = await post("orders/execute", {
      order_id: id,
      expected_version: d.workspace_version,
    });
    await reload();
    notice(
      `Paper order: ${r.status}${r.reason ? " — " + r.reason : ""}.`,
      r.status === "Blocked",
    );
    if (r.controls) open("Execution controls", checks(r.controls));
  },
  "cancel-order": async (id) => {
    await post("orders/cancel", {
      order_id: id,
      expected_version: d.workspace_version,
    });
    await reload();
    notice("Paper order cancelled.");
  },
  rebalance: async () => {
    lastRebalance = (await post("rebalance")).orders;
    render();
    notice(
      `${lastRebalance.length} target adjustments proposed. Review each before staging.`,
    );
  },
  "stage-rebalance": async (index) => stage(lastRebalance[Number(index)]),
  "stage-proposal": async () => {
    if (!lastProposal?.eligible_for_review)
      throw new Error("Calculate and review an eligible proposal first.");
    await stage(lastProposal.order);
    lastProposal = null;
  },
  position: async (id) => {
    const p = d.workspace.positions.find((p) => p.instrument_id === id) || {};
    open(
      p.instrument_id ? "Edit position" : "Add position",
      `<form data-form="position"><input type="hidden" name="original_id" value="${esc(id || "")}"><div class="form-grid"><label>Instrument<select name="instrument_id" ${id ? "disabled" : ""}>${options(
        d.workspace.instruments.map((i) => [i.id, i.symbol]),
        p.instrument_id,
      )}</select></label>${field("Quantity (zero keeps a target row)", "quantity", p.quantity ?? 0, "number", 'step="any" required')}${field("Average entry price", "average_price", p.average_price ?? 0, "number", 'min="0" step="any" required')}${field("Target delta weight (%) — optional", "target_weight", p.target_weight == null ? "" : p.target_weight * 100, "number", 'step="any"')}<label>Theme<select name="theme_id">${options([["", "Unassigned"], ...Object.entries(d.config.themes).map(([k, v]) => [k, v.title])], p.theme_id || "")}</select></label>${field("Reason for manual position edit", "reason", "", "text", "required")}</div><p class="muted">This edits your starting holdings. Use paper orders when you want cash, average cost and realized P&L to update together.</p><button class="primary">Save position</button></form>`,
    );
  },
  instrument: async (id) => {
    const i = d.workspace.instruments.find((i) => i.id === id) || {
      id: "new-instrument",
      symbol: "NEW",
      name: "New instrument",
      model: "equity",
      currency: d.workspace.base_currency,
      price: 100,
      price_at: now(),
      multiplier: 1,
      lot_size: 1,
      tick_size: 0.01,
      risk_factor: "equity",
      beta: 1,
      factor_loadings: { equity: 1 },
      adv: null,
      financing_bps: null,
      borrow_bps: null,
      tradable: true,
    };
    editor(
      "Instrument economics",
      "instrument",
      "instrument",
      i,
      `<input type="hidden" name="original_id" value="${esc(id || "")}"><p class="muted">Models: equity, bond, fx, option, future. Supply actual liquidity, timestamps and financing assumptions. Derivatives need explicit margin and sensitivities; see the guide.</p>${field("Reason", "reason", "", "text", "required")}`,
    );
  },
  "cash-fx": async () =>
    editor(
      "Cash balances and FX conversion",
      "cash",
      "balances",
      { cash: d.workspace.cash, fx_rates: d.workspace.fx_rates },
      field("Reason", "reason", "", "text", "required"),
    ),
  "export-themes": async () => {
    const ts = Object.values(d.research?.themes || {});
    download(
      "macrotrading-themes.csv",
      csv(
        [
          "Theme",
          "Score",
          ..."PFMCXR",
          "Evidence quality",
          "Evidence coverage",
          "Market coverage",
          "Lifecycle",
        ],
        ts.map((t) => [
          t.title,
          t.score,
          ...[..."PFMCXR"].map((k) => t.components?.[k]),
          t.evidence_quality,
          t.coverage,
          t.market.coverage,
          t.lifecycle,
        ]),
      ),
      "text/csv",
    );
  },
  "export-data": async () => {
    const data = clone(d);
    delete data.csrf_token;
    download(
      "macrotrading-current-snapshot.json",
      JSON.stringify(data, null, 2),
      "application/json",
    );
  },
};
function editTheme(id) {
  const spec = id
    ? d.config.themes[id]
    : {
        title: "New research theme",
        hypothesis: "Define a testable hypothesis.",
        components: { P: 0, F: 0, M: 0, C: 0, X: 0, R: 0 },
        fundamental_tests: [],
        counterdrivers: [],
        catalysts: [],
        decisions: [],
        expression: { proxy: "", limits: "" },
        invalidation: "Define observations that disprove the thesis.",
        evidence_max_age_days: 30,
        market_max_age_days: 5,
      };
  editor(
    id ? "Edit research theme" : "Add research theme",
    "theme",
    "spec",
    spec,
    `${field("Stable theme ID", "theme_id", id || "new-theme", "text", id ? "readonly" : "required")}${field("Change reason", "reason", "", "text", "required")}`,
  );
}
async function stage(order) {
  const r = await post("orders/stage", {
    order,
    expected_version: d.workspace_version,
  });
  await reload();
  go("orders");
  open(`Paper order ${r.order.status.toLowerCase()}`, checks(r.controls));
  notice("Order recorded. Execution remains a separate action.");
}
const forms = {
  "market-refresh": async (f) => {
    await post("market/refresh", {
      theme_id: f.get("theme_id"),
      base: f.get("base").toUpperCase(),
      quote: f.get("quote").toUpperCase(),
      sessions: Number(f.get("sessions")),
    });
    await reload();
    go("markets");
    notice("Reference history acquired. Review before accepting.");
  },
  "market-apply": async (f) => {
    await post("market/apply", {
      snapshot_id: f.get("snapshot_id"),
      proxy: JSON.parse(f.get("proxy")),
      expected_version: d.config_version,
      reason: f.get("reason"),
    });
    await reload();
    go("markets");
    notice("Reviewed market history accepted and report saved.");
  },
  "discovery-review": async (f) => {
    await post("discovery/review", {
      action: "accept",
      draft_id: f.get("draft_id"),
      theme_id: f.get("theme_id"),
      spec: JSON.parse(f.get("spec")),
      expected_version: d.config_version,
      reason: f.get("reason"),
    });
    await reload();
    go("themes");
    notice(
      "New theme accepted unscored. Review its scoring baseline and market proxy.",
    );
  },
  "discovery-reject": async (f) => {
    await post("discovery/review", {
      action: "reject",
      draft_id: f.get("draft_id"),
      reason: f.get("reason"),
    });
    await reload();
    go("discovery");
    notice("Theme proposal rejected with reason.");
  },
  scenarios: async (f) => {
    const w = clone(d.workspace);
    w.scenarios = JSON.parse(f.get("scenarios"));
    await saveWorkspace(w, f.get("reason"));
    await reload();
    go("risk");
    notice("Scenario assumptions saved. Review any missing sensitivities.");
  },

  run: async (f) => {
    await post("run", JSON.parse(f.get("payload")));
    await reload();
    go("overview");
    notice("Research run committed with an immutable HTML report.");
  },
  decision: async (f) => {
    await post("decision", {
      theme_id: f.get("theme_id"),
      action: f.get("action"),
      reason: f.get("reason"),
      component_updates: components(f),
    });
    await reload();
    go("decisions");
    notice("Decision and resulting research state saved.");
  },
  evidence: async (f) => {
    const e = {
      theme_id: f.get("theme_id"),
      kind: f.get("kind"),
      direction: f.get("direction"),
      summary: f.get("summary"),
      material: f.has("material"),
      component_updates: components(f),
    };
    if (f.get("candidate_id"))
      await post("inbox/accept", { ...e, candidate_id: f.get("candidate_id") });
    else {
      const known = now();
      const sources = f.get("url")
        ? [
            {
              url: f.get("url"),
              title: f.get("title"),
              published_at: f.get("published_at"),
              retrieved_at: known,
              source_group: f.get("source_group") || undefined,
            },
          ]
        : [];
      await post("run", {
        as_of: known,
        label: "Manually accepted evidence",
        evidence: [
          {
            ...e,
            id: "manual-" + crypto.randomUUID(),
            observed_at: f.get("observed_at"),
            first_known_at: known,
            sources,
          },
        ],
      });
    }
    await reload();
    go("themes");
    notice("Accepted evidence saved and scores re-evaluated.");
  },
  sources: async (f) => {
    await post("sources/save", {
      sources: JSON.parse(f.get("sources")),
      expected_version: d.sources_version,
    });
    await reload();
    modal.close();
    notice("Source configuration saved.");
  },
  theme: async (f) => {
    const c = clone(d.config);
    c.themes[f.get("theme_id")] = JSON.parse(f.get("spec"));
    await post("config/save", {
      config: c,
      expected_version: d.config_version,
      reason: f.get("reason"),
    });
    await reload();
    modal.close();
    notice("Theme saved.");
  },
  order: async (f) =>
    stage({
      instrument_id: f.get("instrument_id"),
      side: f.get("side"),
      quantity: Number(f.get("quantity")),
      order_type: f.get("order_type"),
      limit_price:
        f.get("limit_price") === "" ? null : Number(f.get("limit_price")),
      theme_id: f.get("theme_id") || null,
    }),
  proposal: async (f) => {
    lastProposal = await post("proposal", {
      instrument_id: f.get("instrument_id"),
      theme_id: f.get("theme_id") || null,
      side: f.get("side"),
      quantity: Number(f.get("quantity")),
      risk_budget: Number(f.get("risk_budget")),
      holding_days: Number(f.get("holding_days")),
    });
    go("risk");
    render();
  },
  position: async (f) => {
    const w = clone(d.workspace),
      id = f.get("original_id") || f.get("instrument_id");
    const p = {
      instrument_id: id,
      quantity: Number(f.get("quantity")),
      average_price: Number(f.get("average_price")),
      target_weight:
        f.get("target_weight") === ""
          ? null
          : Number(f.get("target_weight")) / 100,
      theme_id: f.get("theme_id") || null,
    };
    const old = w.positions.findIndex((p) => p.instrument_id === id);
    if (old < 0) w.positions.push(p);
    else w.positions[old] = p;
    await saveWorkspace(w, f.get("reason"));
    await reload();
    modal.close();
    notice("Starting position updated.");
  },
  instrument: async (f) => {
    const w = clone(d.workspace),
      i = JSON.parse(f.get("instrument")),
      old = f.get("original_id");
    if (old && i.id !== old)
      throw new Error("Keep an existing instrument’s stable ID.");
    const ix = w.instruments.findIndex((x) => x.id === i.id);
    if (!old && ix >= 0) throw new Error("Instrument ID already exists.");
    if (ix < 0) w.instruments.push(i);
    else w.instruments[ix] = i;
    await saveWorkspace(w, f.get("reason"));
    await reload();
    modal.close();
    notice("Instrument economics saved.");
  },
  cash: async (f) => {
    const w = clone(d.workspace),
      v = JSON.parse(f.get("balances"));
    w.cash = v.cash;
    w.fx_rates = v.fx_rates;
    await saveWorkspace(w, f.get("reason"));
    await reload();
    modal.close();
    notice("Cash and FX saved.");
  },
  identity: async (f) => {
    const w = clone(d.workspace);
    w.name = f.get("name");
    w.base_currency = f.get("base_currency").toUpperCase();
    w.demo = f.has("demo");
    await saveWorkspace(w, f.get("reason"));
    await reload();
    notice(
      "Workspace data mode saved. Review any newly surfaced input issues.",
    );
  },
  policy: async (f) => {
    const w = clone(d.workspace);
    for (const [k, v] of Object.entries(w.policy))
      w.policy[k] = typeof v === "boolean" ? f.has(k) : Number(f.get(k));
    await saveWorkspace(w, f.get("reason"));
    await reload();
    notice("Risk assumptions saved.");
  },
  weights: async (f) => {
    const c = clone(d.config);
    c.weights = Object.fromEntries(
      [..."PFMCXR"].map((k) => [k, Number(f.get(k))]),
    );
    c.version = f.get("version");
    await post("config/save", {
      config: c,
      expected_version: d.config_version,
      reason: f.get("reason"),
    });
    await reload();
    notice("Scoring policy saved and accepted evidence re-evaluated.");
  },
  config: async (f) => {
    await post("config/save", {
      config: JSON.parse(f.get("config")),
      expected_version: d.config_version,
      reason: f.get("reason"),
    });
    await reload();
    notice("Configuration saved.");
  },
  evaluate: async (f) => {
    await post("evaluate", {
      kind: f.get("kind"),
      payload: JSON.parse(f.get("payload")),
    });
    await reload();
    go("evaluation");
    notice("Evaluation completed; current research state was not rewound.");
  },
  "workspace-import": async (f) => {
    const r = await post("workspace/import", {
      document: JSON.parse(f.get("document")),
      expected_version: d.workspace_version,
    });
    await reload();
    modal.close();
    notice(
      ["Workspace imported.", ...r.warnings].join(" "),
      r.warnings.length > 0,
    );
  },
  restore: async (f) => {
    await post("restore", {
      backup: JSON.parse(f.get("backup")),
      expected_version: d.workspace_version,
    });
    lastProposal = null;
    lastRebalance = [];
    await reload();
    go("overview");
    notice("State restored. Imported unfilled orders need fresh staging.");
  },
};
async function guarded(fn, control) {
  if (control?.disabled) return;
  if (control) control.disabled = true;
  try {
    await fn();
  } catch (error) {
    notice(error.message, true);
  } finally {
    if (control) control.disabled = false;
  }
}
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-action]");
  if (!b) return;
  const action = b.dataset.action;
  if (action.startsWith("import-") || action === "restore-state") {
    fileAction = action;
    const f = document.querySelector("#file-input");
    f.accept = action === "import-market" ? ".csv" : ".json";
    f.value = "";
    f.click();
    return;
  }
  if (actions[action]) guarded(() => actions[action](b.dataset.id || ""), b);
});
document.addEventListener("submit", (e) => {
  const form = e.target.closest("form[data-form]");
  if (!form) return;
  e.preventDefault();
  const f = new FormData(form);
  guarded(
    () => forms[form.dataset.form](f),
    form.querySelector('button[type="submit"],button.primary'),
  );
});
document.querySelector("#file-input").addEventListener("change", (e) =>
  guarded(async () => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 7_900_000)
      throw new Error("File exceeds the 8 MB request limit.");
    const value = await file.text();
    if (fileAction === "import-market") {
      const r = await post("market/csv", { csv: value });
      researchInput({
        as_of: now(),
        label: "Reviewed CSV import",
        evidence: [],
        market_closes: r.market_closes,
      });
    } else {
      const data = JSON.parse(value);
      if (fileAction === "import-research") researchInput(data);
      else if (fileAction === "import-broker") {
        await post("reconcile", { snapshot: data });
        await reload();
        go("portfolio");
        notice("Read-only reconciliation completed.");
      } else if (fileAction === "restore-state")
        editor(
          "Review and replace current state",
          "restore",
          "backup",
          data,
          '<p class="callout warn">This replaces current research, portfolio and configuration. Download a state backup first if you want to retain the current state. Existing run archives remain in this database.</p>',
        );
      else
        editor(
          "Review and replace current workspace",
          "workspace-import",
          "document",
          data,
          '<p class="callout warn">This replaces current portfolio holdings and paper history. Legacy imports retain their original records separately and need reconciliation. Imported unfilled orders cannot execute until freshly staged.</p>',
        );
    }
  }),
);
document.addEventListener("input", (e) => {
  if (e.target.id === "data-search") {
    query = e.target.value;
    const pos = e.target.selectionStart;
    render();
    const search = document.querySelector("#data-search");
    search.focus();
    search.setSelectionRange(pos, pos);
  }
});
document
  .querySelector("#menu")
  .addEventListener("click", () =>
    document.querySelector("#sidebar").classList.toggle("open"),
  );
window.addEventListener("hashchange", () => {
  render();
  document.querySelector("#sidebar").classList.remove("open");
});
guarded(reload);
