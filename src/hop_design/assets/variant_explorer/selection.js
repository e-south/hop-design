"use strict";
import { $, node, preparationName } from "./common.js";
export function selectionPanel({
  getState,
  acceptState,
  api,
  action,
  previewLabel,
}) {
  const members = new Map();
  let serial = 0,
    retrievedKey = null;
  const key = () =>
    JSON.stringify([
      getState().choices.query_digest,
      [...members],
      $("baseline").value,
    ]);
  function refresh(busy = false) {
    const state = getState(),
      label = previewLabel();
    $("include").disabled =
      busy ||
      !label ||
      !state.choices.compatible_options.includes(label) ||
      members.has(label);
    $("retrieve").disabled =
      busy ||
      !members.size ||
      !$("baseline").value ||
      [...members.keys()].some(
        (k) => !state.choices.compatible_options.includes(k),
      );
  }
  function render() {
    const state = getState(),
      baseline = $("baseline").value;
    $("members").replaceChildren();
    $("baseline").replaceChildren(new Option("Choose a member", ""));
    for (const [label, name] of members) {
      const valid = state.choices.compatible_options.includes(label),
        li = node(
          "li",
          `${name}: ${preparationName(state, label)}${valid ? "" : " · outside current choices"}`,
        ),
        remove = node("button", "Remove");
      remove.onclick = () =>
        action(async () => {
          members.delete(label);
          render();
        });
      li.append(remove);
      $("members").append(li);
      $("baseline").append(new Option(name, name));
    }
    $("baseline").value = baseline;
    $("handoff").replaceChildren();
    if (state.selection && retrievedKey === key()) {
      const link = node("a", "Download verified preparations and oligos");
      link.href = state.selection.archive;
      $("handoff").append(link);
    }
    refresh();
  }
  $("include").onclick = () =>
    action(async () => {
      members.set(previewLabel(), `member-${++serial}`);
      render();
    });
  $("baseline").onchange = render;
  $("retrieve").onclick = () =>
    action(async () => {
      $("handoff").textContent = "Rechecking source records and requirements…";
      const state = await api("/api/select", {
        query_digest: getState().choices.query_digest,
        members: Object.fromEntries(
          [...members].map(([label, name]) => [name, label]),
        ),
        baseline: $("baseline").value,
      });
      acceptState(state);
      retrievedKey = key();
      render();
    });
  return { render, refresh };
}
