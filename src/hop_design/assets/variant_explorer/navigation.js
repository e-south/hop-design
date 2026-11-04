"use strict";
import {
  $,
  node,
  neighborhoods,
  variantName,
  preparationName,
} from "./common.js";
import { renderInspection, renderStateChoices } from "./inspection.js";
import { realizationName, inspectionNotices } from "./inspection_labels.js";
import { latestOnly } from "./continuity.js";
import { showLocalChoices } from "./local_choices.js";
import { renderEnvelope } from "./envelope.js";
export function navigationPanel({
  getState,
  acceptState,
  api,
  action,
  onRefresh,
  onNeighborhood,
  prepareTeaching,
}) {
  let phase = "all",
    variantId = null,
    label = null,
    focus = null,
    focusLabel = null,
    displayed = null;
  function request(option = null) {
    const state = getState();
    return {
      result_digest: state.pool.result_digest,
      query_digest: state.choices.query_digest,
      variant_id: variantId,
      state: phase,
      option_label: option,
      focus,
      focus_option_label: focusLabel,
      focus_mode: "comparison",
      view_from: displayed,
    };
  }
  function renderChoices() {
    const state = getState(),
      q = state.choices.query;
    $("variant-label").textContent =
      `Preview ${neighborhoods[q.focus].toLowerCase()}`;
    const variants = state.choices.variants.filter(
      (v) =>
        v.sequences.length &&
        v.option_labels.some((l) =>
          state.choices.compatible_options.includes(l),
        ),
    );
    $("variant-choice").replaceChildren(
      new Option("Choose a supported variant", ""),
      ...variants.map((v) => new Option(variantName(v), v.variant_id)),
    );
    if (!variants.some((v) => v.variant_id === variantId)) variantId = null;
    $("variant-choice").value = variantId || "";
    $("variant-choice").disabled = !variants.length;
    $("variant-choice").hidden = variants.length === 1;
    $("fixed-variant").hidden = variants.length !== 1;
    $("fixed-variant").textContent =
      variants.length === 1 ? `Preview ${variantName(variants[0])}` : "";
    $("neighborhood-facts").textContent =
      Object.entries(state.choices.neighborhoods || {})
        .map(
          ([k, v]) =>
            `${neighborhoods[k]}: ${v.status}${v.variant_count > 1 ? ` (${v.variant_count})` : ""}`,
        )
        .join(" · ") + `. Assessed at ${q.stage}.`;
  }
  async function localChoice(name, anchor, picked = null) {
    if (!neighborhoods[name]) return;
    const pickedOwner = displayed?.option_label || label;
    const point = anchor || {x: $("viewport").getBoundingClientRect().x + 40,
                            y: $("viewport").getBoundingClientRect().y + 40};
    if (getState().choices.query.focus !== name) await action(() => onNeighborhood(name));
    function open() {
      const browsing = getState().browsing;
      showLocalChoices(getState().choices, point, async id => {
        variantId = id;
        const same = getState().choices.variants.find(v => v.variant_id === id)?.option_labels.includes(label);
        renderChoices();
        try { await browse(same ? label : null); if (variantId === id) open(); }
        catch (error) { $("error").textContent = error.message; }
      }, picked && picked.address.state_id ? () => {
        focus = picked.address; focusLabel = pickedOwner; browseSafely(label);
      } : null, browsing?.status === "preparation_choice_required" ? {
        candidates: browsing.candidates, choose: async option => {
          try { await browse(option); open(); } catch(error) { $("error").textContent = error.message; }
        },
      } : null, label, picked?.parameterKeys || []);
    }
    open();
  }
  // Serialize HTTP mutations but reject superseded views. Controls remain usable during motion.
  let pending = Promise.resolve();
  const perform = latestOnly(
    async (payload) => {
      const response = pending.then(() => api("/api/browse", payload));
      pending = response.catch(() => {});
      const state = await response;
      const inspection = state.browsing.inspection;
      const [text, teaching] = inspection ? await Promise.all([
        fetch(inspection.drawing).then(response => {
          if (!response.ok) throw new Error(`Molecular drawing unavailable (${response.status}).`);
          return response.text();
        }),
        prepareTeaching(state.preview, state.choices.choice_space.axes),
      ]) : [null, null];
      if (text && new DOMParser().parseFromString(text, "image/svg+xml").querySelector("parsererror"))
        throw new Error("Molecular drawing is not valid SVG.");
      return { state, text, teaching };
    },
    async ({ state, text, teaching }, isCurrent) => {
      if (state.choices.query_digest !== getState().choices.query_digest)
        return;
      acceptState(state);
      const result = state.browsing;
      label = result.inspection?.option_label || result.option_label || null;
      $("realization-label").hidden = result.candidates.length < 2;
      $("realization").replaceChildren(
        new Option("Choose a complete realization", ""),
        ...result.candidates.map((c) => {
          const option = new Option(
            realizationName(c, result.candidates, state.choices.query.focus),
            c.label,
          );
          option.title = c.label;
          return option;
        }),
      );
      $("realization").value = label || "";
      $("svg").hidden = $("record").hidden = !result.inspection;
      if (!result.inspection) {
        const message = {
          preparation_choice_required:
            "This variant occurs in several complete preparations. Choose a realization; no route has been selected.",
          excluded_by_constraints:
            "This variant is outside the active permissions. Edit allowed choices explicitly to consider it.",
          state_unavailable:
            "This preparation has no recorded state for the requested phase. Choose another processing state explicitly.",
          state_ambiguous:
            "Several recorded states have this phase. Choose an exact state explicitly.",
        }[result.status];
        if (!displayed) $("viewport").replaceChildren(node("p", message));
        $("viewport").dataset.pending = "true";
        $("position").textContent = displayed
          ? message + " Previous molecule retained for context only."
          : "";
        $("molecule-stage").textContent = "";
        $("inspection-detail").textContent = "";
        $("molecular-changes").textContent = "";
        $("material-changes").textContent = "";
        $("interface-facts").textContent = "";
        $("inspection-notices").textContent = "";
        if (label) {
          const candidate = result.candidates.find((c) => c.label === label);
          renderStateChoices(candidate.available_states, phase);
        }
      } else {
        $("viewport").dataset.pending = "false";
        document.querySelector("main").classList.add("has-molecular-view");
        renderEnvelope(result.inspection);
        const rendered = await renderInspection(
          result.inspection,
          (picked) => {
            focus = picked.address;
            focusLabel = label;
            browseSafely(label);
          },
          (name, anchor, picked) => localChoice(name, anchor, picked).catch(e => { $("error").textContent = e.message; }),
          state.choices,
          result.atlas_transitions?.length ? {
            mode: result.atlas_transitions[0].mode,
            links: result.atlas_transitions.flatMap(t => t.links),
            notices: result.atlas_transitions.flatMap(t => t.notices),
          } : result.transition,
          text,
          isCurrent,
        );
        if (!rendered || !isCurrent()) return;
        teaching();
        displayed = {
          option_label: label,
          state: result.inspection.atlas ? "all" : result.inspection.molecular_state.state.state_id,
        };
        if (result.focus_transfer === "comparison_position") {
          focus = (result.inspection.request || result.inspection.inspection).focus;
          focusLabel = label;
        }
        $("inspection-notices").textContent = inspectionNotices(
          result.inspection,
          result.atlas_transitions?.length ? {notices: result.atlas_transitions.flatMap(t => t.notices)} : result.transition,
        );
        phase = $("inspect-state").value;
        if (result.focus_transfer === "cleared_no_verified_correspondence") {
          focus = null;
          ((focusLabel = null), (displayed = null));
          $("inspection-detail").textContent =
            "Position correspondence is unresolved for this change. Choose a base explicitly; no inferred alignment is shown.";
        }
        $("svg").href = result.inspection.drawing;
        $("record").href = result.inspection.record;
        $("position").textContent =
          preparationName(state, label) + " · preview only";
        const change = state.choices.changes.find((c) => c.label === label);
        $("molecular-changes").textContent =
          change.status === "no_reference"
            ? "No comparison reference is fixed."
            : "Molecule changes: " +
              (change.molecular_neighborhoods
                .map((n) => neighborhoods[n])
                .join(", ") || "none assessed") +
              ".";
        if (
          change.status !== "no_reference" &&
          $("viewport").querySelector(
            '[data-change="substitution"],[data-change="added"]',
          )
        ) {
          $("molecular-changes").textContent +=
            " Filled bases: purple substitutions; green additions.";
        }
        $("material-changes").textContent =
          change.status === "no_reference"
            ? ""
            : "Preparation changes: " +
              (change.material_roles
                .map((r) => r.replaceAll("_", " "))
                .join(", ") || "none") +
              ".";
        const face = state.choices.preparations.find(
          (p) => p.label === label,
        ).interface;
        $("interface-facts").textContent = face
          ? `Released-insert gaps: ${face.achieved_distances_bp.left}/${face.achieved_distances_bp.right} bp. These ends belong to the released product, not its hairpin intermediate.`
          : "This endpoint has no released-insert interface.";
      }
      onRefresh();
    },
  );
  async function browse(option = null) {
    if (!variantId) return;
    const started = performance.now();
    await perform(request(option));
    $("viewport").dataset.responseMs = (performance.now() - started).toFixed(1);
  }
  function browseSafely(option = null) {
    $("error").textContent = "";
    browse(option).catch((error) => {
      $("error").textContent = error.message;
    });
  }
  function retainPhase() {
    // phase is a semantic processing choice, independent of query/preview changes.
  }
  async function show(option) {
    if (option !== label) retainPhase();
    const s = getState(),
      v = s.choices.variants.find((v) => v.option_labels.includes(option));
    if (!v)
      throw new Error(
        "Preparation is outside the current neighborhood choices.",
      );
    variantId = v.variant_id;
    renderChoices();
    await browse(option);
  }
  function refresh(busy) {
    $("inspect-state").disabled =
      busy || !label || !getState().choices.compatible_options.includes(label);
    $("variant-choice").disabled =
      busy || $("variant-choice").options.length < 2;
    $("clear-focus").hidden = !focus;
    $("clear-focus").disabled = busy || !focus;
  }
  $("fixed-variant").onclick = () => {
    variantId = $("variant-choice").options[1].value;
    browseSafely();
  };
  $("variant-choice").onchange = () => {
    variantId = $("variant-choice").value || null;
    browseSafely();
  };
  $("realization").onchange = () =>
    browseSafely($("realization").value || null);
  $("inspect-state").onchange = () => {
    phase = $("inspect-state").value;
    browseSafely(label);
  };
  $("clear-focus").onclick = () => {
    focus = null;
    focusLabel = null;
    browseSafely(label);
  };
  async function restore(result) {
    phase = result.request.state;
    variantId = result.request.variant_id;
    focus = result.request.focus;
    focusLabel = result.request.focus_option_label;
    renderChoices();
    await browse(result.option_label);
  }
  return {
    renderChoices,
    refresh,
    show,
    browse,
    restore,
    label: () => label,
    hasVariant: () => !!variantId,
    invalidate: () => perform.invalidate(),
  };
}
