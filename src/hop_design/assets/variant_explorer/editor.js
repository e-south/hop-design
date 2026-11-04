"use strict";
import { $, node } from "./common.js";
import { queryPanel } from "./query.js";
import { navigationPanel } from "./navigation.js";
import { selectionPanel } from "./selection.js";
import { comparisonPanel } from "./comparison.js";
import { choiceSpacePanel } from "./choice_space.js";
import { envelopeBrowser } from "./envelope_browser.js";
const token = document.querySelector('meta[name="hop-editor-token"]').content;
let state,
  busy = false;
const getState = () => state,
  acceptState = (value) => {
    state = value;
  };
async function api(route, payload) {
  const response = await fetch(
    route,
    payload === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-HOP-Editor-Token": token,
          },
          body: JSON.stringify(payload),
        },
  );
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || "This action failed.");
  return value;
}
async function action(fn) {
  if (busy) return;
  busy = true;
  $("error").textContent = "";
  refresh();
  try {
    await fn();
  } catch (error) {
    $("error").textContent = error.message;
    if ($("domain-dialog").open) $("domain-error").textContent = error.message;
  } finally {
    busy = false;
    refresh();
  }
}
const navigation = navigationPanel({
  prepareTeaching: (preview, axes) => choiceSpace.prepareTeaching(preview, axes),
  api,
  action,
  getState,
  acceptState,
  onRefresh: () => {
    choiceSpace.render();
    selection.render();
    comparison.render();
    refresh();
  },
  onNeighborhood: (name) => query.focus(name),
});
const query = queryPanel({
  getState,
  action,
  update,
  previewLabel: navigation.label,
});
const selection = selectionPanel({
  api,
  action,
  getState,
  acceptState,
  previewLabel: navigation.label,
});
const comparison = comparisonPanel({
  api,
  action,
  getState,
  acceptState,
  preview: navigation.show,
});
const choiceSpace = choiceSpacePanel({
  getState,
  action,
  preview: navigation.show,
  previewLabel: navigation.label,
  update,
  evaluate: async payload => {
    state = await api("/api/evaluate-parameters", payload);
    await update(state.choices.query);
  },
});
const envelope = envelopeBrowser({
  getState, api, acceptState, action, update,
  afterEvaluation: () => update(state.choices.query),
});
function refresh() {
  $("viewport").setAttribute("aria-disabled", String(busy));
  document
    .querySelectorAll("main button:not(dialog button),main select:not(dialog select),main input:not(dialog input)")
    .forEach((n) => (n.disabled = busy));
  if (!state) return;
  $("design-answer").textContent = state.explanation ? `${state.explanation.headline} ${state.explanation.guidance}` : "";
  navigation.refresh(busy);
  query.refresh(busy);
  selection.refresh(busy);
  comparison.refresh(busy);
  choiceSpace.refresh(busy);
  envelope.refresh(busy);
}
async function update(request) {
  navigation.invalidate();
  state = await api("/api/query", request);
  choiceSpace.render();
  query.render();
  navigation.renderChoices();
  selection.render();
  comparison.render();
  const label = navigation.label();
  if (label && state.choices.compatible_options.includes(label)) {
    await navigation.show(label);
  } else if (label) {
    $("choice-preview-context").textContent = "This atlas retains the previous preparation for context. It is excluded by the current constraints; choose a remaining path to preview or retrieve.";
    $("position").textContent = "Previous preview · outside current selection";
    $("svg").hidden = $("record").hidden = true;
  } else if (!navigation.hasVariant()) {
    $("viewport").replaceChildren(
      node(
        "p",
        "Choose a supported local variant to preview a complete realization.",
      ),
    );
  }
}
action(async () => {
  state = await api("/api/state");
  choiceSpace.render();
  query.render();
  navigation.renderChoices();
  selection.render();
  comparison.render();
  if (state.browsing) await navigation.restore(state.browsing);
  else if (state.choices.compatible_options.length)
    await navigation.show(state.choices.query.reference || state.choices.compatible_options[0]);
  else
    $("viewport").append(
      node(
        "p",
        "Choose a supported local variant. If several backgrounds remain, HOP will ask which complete realization to preview.",
      ),
    );
});
