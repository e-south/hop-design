import { drawPlot } from "./plot.js";
import { toggleValue, rangeQuery, queryCommands, preparationDescription, coverageDescription } from "./model.js";
import { coherentViews } from "./selected_views.js";
import { molecularViewport } from "./atlas.js";
import { teachingNavigation } from "./grouped_navigation.js";
import { parameterKeys, parameterSelector, highlightParameters, resolveParameterFocus } from "./parameters.js";
import { connectTeaching } from "./teaching_links.js";
const $ = (id) => document.getElementById(id),
  auth = document.querySelector("meta[name=hop-token]").content;
let state = null,
  busy = false,
  teachingUrl = null,
  focusedKeys = [];
const viewport = molecularViewport($("atlas"), $("fit"), focusKeys);
async function prepareTeaching({preview, key}) {
  if (!key || key === teachingUrl) return () => {};
  const response = await fetch(key);
  if (!response.ok) throw Error("Could not load the parameter teaching drawing.");
  const parsed = new DOMParser().parseFromString(await response.text(), "image/svg+xml");
  if (parsed.querySelector("parsererror")) throw Error("Invalid teaching SVG.");
  const drawing = parsed.documentElement;
  const identity = preview?.summary?.atlas?.materialized_realization_id;
  if (identity && drawing.getAttribute("data-preparation-id") !== identity)
    throw Error("Teaching drawing and route describe different preparations.");
  return () => {
    const host = $("teaching");
    const frame = document.createElement("div");
    frame.className = identity ? "teaching-window" : "teaching-definition";
    frame.tabIndex = 0;
    frame.setAttribute("role", "region");
    frame.setAttribute("aria-label", "Selected molecular structure and parameters");
    frame.append(drawing);
    host.replaceChildren(frame);
    teachingNavigation(drawing);
    teachingUrl = key;
  };
}
const selectedViews = coherentViews(
  ({preview}) => preview ? viewport.prepare(preview) : () => viewport.clear(),
  prepareTeaching,
  () => { viewport.clear(); $("teaching").replaceChildren(); teachingUrl = null; },
);
function focus(axis, description) {
  if (!axis) return;
  focusKeys([axis.key], description);
}
function focusKeys(keys, description) {
  if (!state) return;
  const resolved = resolveParameterFocus(state.choices.axes, keys);
  const axes = resolved.axes;
  if (!axes.length) return;
  focusedKeys = resolved.keys;
  $("parameter").textContent =
    description ||
    axes.map((axis) => `${axis.label}${axis.symbol ? ` (${axis.symbol})` : ""} · ${axis.stage.replaceAll("_", " ")}. ${axis.measurement}${axis.relationship ? ` ${axis.relationship}.` : ""}`).join(" · ");
  viewport.highlight(focusedKeys);
  highlightParameters($("teaching"), focusedKeys);
  highlightParameters($("plot"), focusedKeys);
  highlightParameters($("teaching").parentElement.querySelector(".teaching-links") || $("teaching"), focusedKeys);
}
async function act(route, payload) {
  if (busy) return;
  busy = true;
  document.body.classList.add("busy");
  $("notice").classList.remove("error");
  $("notice").textContent =
    route === "query"
      ? "Filtering complete designs…"
      : "Loading the selected preparation…";
  try {
    const response = await fetch(`/api/${route}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-HOP-Editor-Token": auth,
      },
      body: JSON.stringify({ token: state.token, ...payload }),
    });
    const result = await response.json();
    if (!response.ok) throw Error(result.error);
    state = result;
    await render();
  } catch (error) {
    $("notice").textContent = error.message;
    $("notice").classList.add("error");
  } finally {
    busy = false;
    document.body.classList.remove("busy");
  }
}
function query(next) {
  return act("query", { query: next });
}
function select(path) {
  return act("select", {
    ...path.address,
    materialized_realization_id: path.materialized_realization_id,
  });
}
function choose(members) {
  const available = members.filter((p) => p.matches),
    container = $("members");
  container.replaceChildren();
  const caption = document.createElement("p");
  caption.textContent = available.length
    ? `${members.length} preparations share these coordinates. Choose one to inspect. Material changes are compared with the first choice.`
    : "These preparations are outside the current filter. Clear or change the filter to select them.";
  container.append(caption);
  if (available.length === 1) {
    select(available[0]);
    return;
  }
  for (const p of available) {
    const button = document.createElement("button");
    button.textContent = preparationDescription(p, available[0]);
    button.title = p.materialized_realization_id;
    button.onclick = () => {
      $("member-dialog").close();
      select(p);
    };
    container.append(button);
  }
  $("member-dialog").showModal();
}
$("member-close").onclick = () => $("member-dialog").close();
function domain(axis) {
  $("domain-name").textContent = axis.label;
  $("domain-description").textContent =
    `${axis.measurement} Choose a value to pin this axis; choose the same value to clear it. Unwitnessed values remain unresolved unless all declared partner choices have a scoped exclusion.`;
  const container = $("domain-values");
  container.replaceChildren();
  container.classList.toggle(
    "wide-values",
    axis.nodes.some((n) => n.label.length > 4),
  );
  for (const node of axis.nodes) {
    const button = document.createElement("button");
    button.textContent = node.label;
    button.className = node.state;
    button.title = `${node.conditional_preparations} preparations under other predicates; ${node.supported_preparations} in the pool. ${node.state.replaceAll("_", " ")}`;
    button.onclick = () => {
      $("domain").close();
      query(toggleValue(state.choices.query, axis.key, node.value));
    };
    container.append(button);
  }
  $("domain").showModal();
}
$("domain-close").onclick = () => $("domain").close();
async function render() {
  const c = state.choices,
    coverage = c.coverage;
  const context = $("context");
  if (context) {
    context.hidden = !state.discovery;
    context.textContent = state.discovery
      ? `${state.discovery.intent.product.replaceAll('_', ' ')} · supplied stem ${state.discovery.intent.stem_arm.length} nt · ${state.discovery.context.id}. ${state.discovery.context.description}`
      : '';
  }
  $("coverage").textContent =
    coverageDescription(coverage);
  $("counts").textContent =
    `${c.matching_preparations} matching preparations · ${c.matching_products.endpoint} released products`;
  $("notice").textContent = state.explanation?.headline || (c.matching_preparations
    ? "Choose a complete path to see its molecule and preparation."
    : "No complete preparation matches this filter in the evaluated pool.");
  $("guidance").textContent = state.explanation?.guidance || "Filtering explores recorded designs. Further search and changed permissions are separate actions.";
  $("sample").disabled = !c.matching_preparations;
  $("retrieve").disabled = true;
  $("save-selection").disabled = true;
  $("download").hidden = true;
  $("clear").disabled = !c.query.parameters.length;
  $("query").value = JSON.stringify(c.query, null, 2);
  $("preview-status").textContent =
    state.preview_status === "excluded_by_query"
      ? "Inspected molecule excluded by the current query; retrieval disabled."
      : "";
  drawPlot($("plot"), c, state.plot_svg, {
    path: choose,
    value: (k, v) => query(toggleValue(c.query, k, v)),
    range: (k, a, b) => query(rangeQuery(c.query, k, a, b)),
    focus,
    domain,
    context: text => { $("plot-context").textContent = text; },
  });
  try {
    await selectedViews.show({preview: state.preview, key: state.preview?.teaching || state.parameter_key});
  } catch (error) {
    selectedViews.clear();
    $("construction-cost").textContent = "";
    $("molecule").textContent = "Molecular preview unavailable; reload to retry.";
    $("selection").textContent = "Preview failed; preparation retrieval is disabled.";
    throw error;
  }
  if (state.preview) {
    const v = state.preview.summary.projection.values;
    $("construction-cost").textContent = (state.preview.summary.atlas?.construction_cost?.summary_lines || []).join(" ");
    $("molecule").textContent =
      `${v.left_end_word} / ${v.right_end_word} · loop ${v.loop_word} · gaps ${v.left_gap}/${v.right_gap} bp`;
  } else {
    $("construction-cost").textContent = "";
  }
  $("selection").textContent = state.selection
    ? JSON.stringify(state.selection, null, 2)
    : "No exact preparation is selected under this query.";
  $("save-selection").disabled = !state.selection;
  $("retrieve").disabled = !state.selection;
  $("commands").textContent = queryCommands(state.selection, state.sample_seed, state.discovery ? state : null);
  $("download").hidden = !state.handoff;
  if (state.handoff) {
    $("download").href = state.handoff.archive;
    $("download").download = "preparation.zip";
  }
  if (focusedKeys.length) focusKeys(focusedKeys);
  connectTeaching($("teaching"), $("plot"));
}
window.addEventListener("resize", () => connectTeaching($("teaching"), $("plot")));
$("sample").onclick = () =>
  act("sample", { seed: crypto.getRandomValues(new Uint32Array(1))[0] });
$("retrieve").onclick = () => act("retrieve", { selection: state.selection });
$("clear").onclick = () =>
  query({ ...state.choices.query, parameters: [] });
$("apply").onclick = () => {
  try {
    query(JSON.parse($("query").value));
  } catch (e) {
    $("notice").textContent = e.message;
    $("notice").classList.add("error");
  }
};
$("reload").onclick = () => act("reload", {});
function downloadJson(name, value) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], {
      type: "application/json",
    }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$("save-selection").onclick = () =>
  downloadJson("selection.json", state.selection);
$("save-query").onclick = () => downloadJson("query.json", state.choices.query);
for (const event of ["pointerover", "focusin"])
  $("teaching").addEventListener(event, (e) => {
    const target = e.target.closest(parameterSelector);
    if (target) focusKeys(parameterKeys(target));
  });
try {
  const response = await fetch("/api/state");
  if (!response.ok) throw Error("Could not admit the survey.");
  state = await response.json();
  await render();
} catch (error) {
  $("notice").textContent = error.message;
  $("notice").classList.add("error");
}
