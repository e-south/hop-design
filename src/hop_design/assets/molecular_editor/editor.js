"use strict";
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="hop-editor-token"]').content;
let state, dirty = true, draftVersion = 0, renderedDigest = null, requesting = false;
const choices = new Map();
const words = () => $("words").value.split(/\s+/).filter(Boolean).map(w => w.toUpperCase());
function focusLoop(event) {
  if (!event || event.type === "click" || ["Enter", " "].includes(event.key)) {
    if (event) event.preventDefault();
    $("words").focus();
  }
}
$("initial-loop").addEventListener("click", focusLoop);
$("initial-loop").addEventListener("keydown", focusLoop);
async function api(route, payload) {
  const response = await fetch(route, payload === undefined ? {} : {
    method: "POST", headers: {"Content-Type": "application/json", "X-HOP-Editor-Token": token},
    body: JSON.stringify(payload)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "The action failed.");
  return result;
}
function stale() {
  return dirty || !state?.result || state.result.edit_digest !== state.preview?.edit_digest;
}
function updateControls() {
  $("preview").disabled = requesting || !!state?.busy;
  $("evaluate").disabled = requesting || dirty || !!state?.busy || state?.preview?.status !== "ready" || !stale();
  $("select").disabled = requesting || stale() || !!state?.busy || !$("baseline").value || choices.size === 0;
  $("molecules").classList.toggle("stale", !!state?.result && stale());
  $("result-status").className = stale() && state?.result ? "notice" : "";
  if (state?.busy) $("result-status").textContent = "Evaluating complete constructions under the recorded bounds…";
  else if (state?.result && stale()) $("result-status").textContent = "Earlier result — this request has changed. Preview and evaluate before selecting.";
  else if (state?.result) $("result-status").textContent = state.result.options.length
    ? `${state.result.options.length} complete preparations examined. Select explicitly below.`
    : "No complete preparation found in the examined choices. Inspect failures and unexamined coverage below.";
}
for (const id of ["words", "placements", "left-end", "right-end", "edit-ends", "nicks", "releases"]) $(id).addEventListener("input", () => {
  dirty = true; draftVersion++; $("handoff").replaceChildren(); updateControls();
});
function link(label, href) {
  const a = document.createElement("a"); a.textContent = label; a.href = href; a.target = "_blank"; a.rel = "noopener"; return a;
}
function updateMembers() {
  const before = $("baseline").value;
  $("baseline").replaceChildren(new Option("Choose a selected member", ""));
  for (const [label, name] of choices) $("baseline").append(new Option(name, label));
  if (choices.has(before)) $("baseline").value = before;
  updateControls();
}
$("baseline").addEventListener("change", updateControls);
async function renderOptions(result) {
  choices.clear(); updateMembers(); $("molecules").replaceChildren();
  $("initial").hidden = result.options.length > 0;
  $("retrieval").hidden = result.options.length === 0;
  $("pdf").hidden = false; $("pdf").href = result.files_prefix + "report.pdf";
  for (const [index, option] of result.options.entries()) {
    const section = document.createElement("article"); section.className = "option";
    const head = document.createElement("div"); head.className = "option-head";
    const title = document.createElement("h3"); title.textContent = `Loop ${option.loop_sequence} · preparation ${index + 1}`;
    head.append(title); section.append(head);
    const scroll = document.createElement("div"); scroll.className = "molecule-scroll";
    scroll.tabIndex = 0; scroll.setAttribute("aria-label", "Folded primary sequence; scroll horizontally if needed");
    const source = await (await fetch(result.files_prefix + option.sequence_drawing)).text();
    const svg = new DOMParser().parseFromString(source, "image/svg+xml").documentElement;
    svg.setAttribute("role", "group");
    svg.querySelectorAll("[data-base-index]").forEach(base => base.setAttribute("aria-hidden", "true"));
    scroll.append(document.importNode(svg, true)); section.append(scroll);
    const zoom = document.createElement("button"); zoom.textContent = "Read bases";
    zoom.setAttribute("aria-pressed", "false");
    zoom.addEventListener("click", () => {
      const enlarged = scroll.classList.toggle("enlarged");
      zoom.textContent = enlarged ? "Fit molecule" : "Read bases";
      zoom.setAttribute("aria-pressed", String(enlarged));
      const drawing = scroll.querySelector("svg");
      drawing.dataset.fullViewBox ||= drawing.getAttribute("viewBox");
      if (enlarged) {
        const boxes = [...drawing.querySelectorAll("[data-base-index]")].map(base => base.getBBox());
        const [x, , width] = drawing.dataset.fullViewBox.split(/\s+/).map(Number);
        const top = Math.min(...boxes.map(box => box.y)) - 20;
        const bottom = Math.max(...boxes.map(box => box.y + box.height)) + 20;
        drawing.setAttribute("viewBox", `${x} ${top} ${width} ${bottom - top}`);
        drawing.style.aspectRatio = `${width} / ${bottom - top}`;
        const loop = scroll.querySelector('[data-region="loop"]');
        if (loop) scroll.scrollLeft += loop.getBoundingClientRect().left - scroll.getBoundingClientRect().left - scroll.clientWidth / 2;
      } else {
        drawing.setAttribute("viewBox", drawing.dataset.fullViewBox);
        drawing.style.aspectRatio = "";
      }
    });
    head.append(zoom);
    const row = document.createElement("div"); row.className = "selection-row";
    const choose = document.createElement("input"); choose.type = "checkbox"; choose.id = `choose-${index}`;
    const label = document.createElement("label"); label.htmlFor = choose.id; label.textContent = "Include this preparation";
    const name = document.createElement("input"); name.type = "text"; name.value = `loop-${option.loop_sequence.toLowerCase()}-${index + 1}`;
    name.id = `member-name-${index}`;
    name.setAttribute("aria-label", `Name for preparation ${index + 1}`);
    const changed = () => {if (choose.checked) choices.set(option.label, name.value); else choices.delete(option.label); updateMembers();};
    choose.addEventListener("change", changed); name.addEventListener("input", changed);
    row.append(choose, label, name); section.append(row);
    const links = document.createElement("p"); links.className = "option-links";
    links.append(link("Export SVG", result.files_prefix + option.sequence_drawing),
                 link("Exact sequence & pairing", result.files_prefix + option.sequence_view),
                 link("Product stages", result.files_prefix + option.product_stages),
                 link("Preparation & conditions", result.files_prefix + option.preparation));
    section.append(links); $("molecules").append(section);
    if (option.target_facts?.end_placement) {
      const ends = document.createElement("p"), p = option.target_facts.end_placement;
      ends.textContent = `Released insert: ${p.left_bp}/${p.right_bp} bp left/right gaps from the supplied stem. These are not exposed ends on the hairpin.`;
      section.insertBefore(ends, scroll);
    }
    const loopBases = [...scroll.querySelectorAll('[data-region="loop"]')];
    if (loopBases.length) {
      const box = loopBases.map(n => n.getBBox());
      const x = Math.min(...box.map(b => b.x)) - 8, y = Math.min(...box.map(b => b.y)) - 10;
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("role", "button"); g.setAttribute("tabindex", "0"); g.setAttribute("aria-label", "Edit loop sequence");
      const rect = document.createElementNS(g.namespaceURI, "rect");
      const attributes = {x, y, width: Math.max(...box.map(b => b.x + b.width)) - x + 8,
        height: Math.max(...box.map(b => b.y + b.height)) - y + 10, fill: "transparent", stroke: "#258365", rx: 8};
      Object.entries(attributes).forEach(([k,v]) => rect.setAttribute(k, v));
      g.append(rect); g.addEventListener("click", focusLoop); g.addEventListener("keydown", focusLoop);
      scroll.querySelector("svg").append(g);
    }
  }
  $("diagnostics").hidden = false;
  $("diagnostic-content").replaceChildren();
  const coverage = document.createElement("p");
  coverage.textContent = `${result.coverage.evaluated_branches} branches examined; ${result.coverage.unexamined_branches} branches and ${result.coverage.unexamined_pairs} continuations unexamined. `
    + (result.coverage.exploration_complete === false ? "Declared search coverage remains incomplete; inspect local enumeration below. " : "")
    + "This is not a global feasibility or minimum-distance claim.";
  const details = document.createElement("pre"); details.textContent = JSON.stringify(result.branches.map(b => ({branch: b.label, failures: b.failures, local: b.local_coverage})), null, 2);
  $("diagnostic-content").append(coverage, link("Recorded request and failures", result.files_prefix + "options/report.md"), details);
}
async function render() {
  $("error").textContent = state.error || "";
  if (state.preview) {
    const p = document.createElement("p");
    p.textContent = state.preview.status === "ready" ? "Request previewed. Unedited requirements remain active." : "The edit conflicts with inherited requirements.";
    $("preview-result").replaceChildren(p);
    for (const c of state.preview.conflicts) {
      const issue = document.createElement("p"); issue.textContent = `${c.inherited_field}: ${c.explicit_edit}`; $("preview-result").append(issue);
    }
  }
  if (state.result && state.result.edit_digest !== renderedDigest) {
    renderedDigest = state.result.edit_digest; await renderOptions(state.result);
  }
  if (state.selection && !stale()) {
    $("handoff").replaceChildren(link("Download verified preparations & oligo specifications", state.selection.archive));
  }
  updateControls();
}
async function action(fn) {
  $("error").textContent = "";
  requesting = true; updateControls();
  try {await fn();} catch (error) {
    $("error").textContent = error.message; $("handoff").replaceChildren();
  } finally {requesting = false; updateControls();}
}
$("preview").addEventListener("click", () => action(async () => {
  const version = draftVersion;
  const payload = {};
  if (words().length) payload.loop_sequences = words();
  if ($("edit-ends").checked) {
    const placements = $("placements").value.trim().split(/\s+/).map(p => p.split(":").map(Number));
    if (!placements.every(p => p.length === 2 && p.every(n => Number.isInteger(n) && n >= 0))) throw new Error("Use nonnegative LEFT:RIGHT gap pairs, for example 0:0, 3:3 and 6:6 on separate lines.");
    payload.end_placements = placements;
    payload.end_words = [$("left-end").value.trim().toUpperCase(), $("right-end").value.trim().toUpperCase()];
    payload.basal_nick_enzyme_ids = [...$("nicks").selectedOptions].map(o => o.value);
    payload.release_enzyme_ids = [...$("releases").selectedOptions].map(o => o.value);
  }
  state = await api("/api/preview", payload);
  dirty = version !== draftVersion; await render();
}));
$("evaluate").addEventListener("click", () => action(async () => {
  state = await api("/api/evaluate", {edit_digest: state.preview.edit_digest}); await render();
  while (state.busy) {
    await new Promise(resolve => setTimeout(resolve, 600));
    state = await api("/api/state"); await render();
  }
}));
$("select").addEventListener("click", () => action(async () => {
  const members = Object.fromEntries([...choices].map(([label,name]) => [name,label]));
  if (Object.keys(members).length !== choices.size) throw new Error("Give each selected member a distinct name.");
  $("select").disabled = true;
  $("handoff").textContent = "Verifying the selected molecular authorities and preparing the download…";
  state = await api("/api/select", {edit_digest: state.preview.edit_digest, members,
    baseline: choices.get($("baseline").value), shared_properties: $("shared").checked ? ["non_loop_sequences"] : []});
  await render();
}));
action(async () => {
  state = await api("/api/state");
  $("words").value = (state.original_request.product.foldback.geometry.loop_sequences || []).join("\n");
  const product = state.original_request.product;
  $("end-controls").hidden = !product.ends;
  if (product.ends) {
    $("placements").value = `${product.ends.left.payload_end_offset_bp}:${product.ends.right.payload_end_offset_bp}`;
    $("left-end").value = product.ends.left.cohesive_end_sequence;
    $("right-end").value = product.ends.right.cohesive_end_sequence;
    const permitted = (job, role) => job.enzymes.role_restrictions.find(r => r.role === role)?.allowed_enzyme_ids || job.enzymes.allowed_enzyme_ids;
    for (const e of product.enzyme_catalog.enzymes) {
      const select = e.enzyme_class === "nickase" ? $("nicks") : $("releases");
      const allowed = e.enzyme_class === "nickase" ? permitted(product.basal, "basal_nick") : permitted(product.release, "end_generation");
      select.append(new Option(e.canonical_name, e.enzyme_id, false, allowed.includes(e.enzyme_id)));
    }
  }
  $("stage").textContent = state.original_request.product.endpoint === "clone_ready_duplex"
    ? "Compare the hairpin intermediate; retrieve a preparation ending in a released duplex insert."
    : "Compare the modeled hairpin endpoint and retrieve its preparation.";
  await render();
});
