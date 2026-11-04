"use strict";
import {
  $,
  node,
  neighborhoods,
  properties,
  variantName,
  preparationName,
} from "./common.js";
import { exclusionSummaries } from "./local_choice_model.js";
export function queryPanel({ getState, update, action, previewLabel }) {
  const query = () => structuredClone(getState().choices.query);
  function render() {
    const state = getState(),
      q = state.choices.query,
      pin = q.pins.find((p) => p.neighborhood === q.focus);
    $("stage").value = q.stage;
    $("neighborhood").replaceChildren(
      ...Object.entries(neighborhoods).map(
        ([id, name]) => new Option(name, id),
      ),
    );
    $("neighborhood").value = q.focus;
    $("allowed-variants").replaceChildren(
      ...state.choices.variants.map((v) => {
        const label = node("label", ""),
          input = document.createElement("input");
        input.type = "checkbox";
        input.value = v.variant_id;
        input.checked = !pin || pin.variant_ids.includes(v.variant_id);
        label.append(input, document.createTextNode(variantName(v)));
        return label;
      }),
    );
    $("pins").textContent =
      `Choices assessed at ${q.stage === "hairpin" ? "hairpin" : "preparation endpoint"}. ` +
      (q.pins.length
        ? "Allowed: " +
          q.pins
            .map(
              (p) =>
                `${neighborhoods[p.neighborhood]} (${p.variant_ids.length})`,
            )
            .join("; ")
        : "All observed variants allowed.");
    $("reference").replaceChildren(
      new Option("No reference", ""),
      ...state.pool.options.map(
        (o) => new Option(preparationName(state, o.label), o.label),
      ),
    );
    $("reference").value = q.reference || "";
    $("control-options").replaceChildren(
      ...Object.entries(properties).map(([key, name]) => {
        const label = node("label", ""),
          input = document.createElement("input");
        input.type = "checkbox";
        input.checked = q.controls.some(
          (c) => c.stage === q.stage && c.property === key,
        );
        input.onchange = () =>
          action(async () => {
            const request = query();
            request.controls = request.controls.filter(
              (c) => !(c.stage === q.stage && c.property === key),
            );
            if (input.checked)
              request.controls.push({ stage: q.stage, property: key });
            await update(request);
          });
        label.append(input, document.createTextNode(name));
        return label;
      }),
    );
    const surroundings = q.surroundings || [];
    $("surroundings-context").textContent = surroundings.length
      ? "Preserved surroundings: " +
        surroundings
          .map(
            (c) => `${c.stage}, except ${neighborhoods[c.except_neighborhood]}`,
          )
          .join("; ") +
        ". Changing the explored region does not move these controls."
      : "Use the current preview as a reference and keep every assessed region outside this neighborhood unchanged.";
    $("clear-surroundings").hidden = !surroundings.length;
    $("active-controls").textContent = q.controls.length
      ? "Preserved: " +
        q.controls
          .map((c) => `${c.stage}: ${properties[c.property]}`)
          .join("; ")
      : surroundings.length
        ? "Regional preservation applies to the fixed reference."
        : "No reference-based preservation requirements.";
    $("status").textContent =
      `${state.choices.products.length} complete ${q.stage} products · ${state.choices.compatible_options.length} preparations. Previewing does not select a preparation.`;
    const counts = node(
      "p",
      `${state.choices.excluded_options.length} options excluded; ${state.choices.examined_failures.length} examined failures. Absence from this pool is not impossibility.`,
    );
    const detail = node(
      "pre",
      JSON.stringify(
        {
          excluded: state.choices.excluded_options,
          failures: state.choices.examined_failures,
          coverage: state.choices.coverage,
          interfaces: state.choices.interface_coverage,
        },
        null,
        2,
      ),
    );
    const reasons = node("ul", "");
    for (const {text, count} of exclusionSummaries(state.choices, {neighborhoods, properties}))
      reasons.append(node("li", `${count} preparation${count === 1 ? "" : "s"}: ${text}`));
    $("diagnostics").replaceChildren(counts, reasons, detail);
  }
  async function focus(value) {
    const q = query();
    q.focus = value;
    await update(q);
  }
  $("neighborhood").onchange = () =>
    action(() => focus($("neighborhood").value));
  $("apply-allowed").onclick = () =>
    action(async () => {
      const q = query(),
        ids = [...$("allowed-variants").querySelectorAll("input:checked")].map(
          (n) => n.value,
        );
      if (!ids.length)
        throw new Error(
          "Choose at least one allowed variant; ‘Allow all here’ clears this pin explicitly.",
        );
      q.pins = q.pins.filter((p) => p.neighborhood !== q.focus);
      q.pins.push({ neighborhood: q.focus, variant_ids: ids });
      await update(q);
    });
  $("allow-all").onclick = () =>
    action(() => {
      const q = query();
      q.pins = q.pins.filter((p) => p.neighborhood !== q.focus);
      return update(q);
    });
  $("stage").onchange = () =>
    action(async () => {
      const q = query();
      if (q.pins.length) {
        $("stage").value = q.stage;
        throw new Error(
          "Pins name an assessment stage. Clear them explicitly before changing that stage; preserved properties retain their declared stages.",
        );
      }
      q.stage = $("stage").value;
      await update(q);
    });
  $("reference").onchange = () =>
    action(() => {
      const q = query();
      if (
        !$("reference").value &&
        (q.controls.length || q.surroundings?.length)
      ) {
        $("reference").value = q.reference;
        throw new Error(
          "Remove preserved properties explicitly before removing their reference.",
        );
      }
      q.reference = $("reference").value || null;
      return update(q);
    });
  $("use-reference").onclick = () =>
    action(() => update({ ...query(), reference: previewLabel() }));
  $("keep-surroundings").onclick = () =>
    action(async () => {
      const q = query();
      if (q.reference && q.reference !== previewLabel())
        throw new Error(
          "A different reference is already fixed. Change it explicitly before preserving this preview's surroundings.",
        );
      q.reference = previewLabel();
      const control = { stage: q.stage, except_neighborhood: q.focus };
      q.surroundings = [
        ...(q.surroundings || []).filter(
          (c) => c.stage !== q.stage || c.except_neighborhood !== q.focus,
        ),
        control,
      ];
      await update(q);
    });
  $("clear-surroundings").onclick = () =>
    action(() => update({ ...query(), surroundings: [] }));
  function refresh(busy) {
    $("keep-surroundings").disabled = busy || !previewLabel();
    $("use-reference").disabled = busy || !previewLabel();
    document
      .querySelectorAll("#control-options input")
      .forEach(
        (n) => (n.disabled = busy || !getState()?.choices.query.reference),
      );
  }
  return { render, refresh, focus };
}
