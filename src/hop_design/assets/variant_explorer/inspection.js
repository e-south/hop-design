"use strict";
import { molecularNavigation } from "./grouped_navigation.js";
import { scenePoints, stopMotion, tweenScene } from "./motion.js";
import { attachCamera, zoomNeighborhood } from "./camera.js";
import { renderAtlas } from "./atlas_view.js";
import { attachLocalExploration } from "./local_choices.js";

export async function renderInspection(
  preview,
  onPick,
  onNeighborhood = () => {},
  choices = null,
  transition = null,
  svgText = null,
  isCurrent = () => true,
) {
  const text = svgText ?? (await (await fetch(preview.drawing)).text());
  if (!isCurrent()) return false;
  if (preview.atlas) {
    renderAtlas(preview, text, onPick, onNeighborhood, transition);
    renderStateChoices(preview.atlas.states[0].available_states, "all");
    return true;
  }
  document.getElementById("construction-cost").textContent = "";
  const svg = new DOMParser().parseFromString(
    text,
    "image/svg+xml",
  ).documentElement;
  const viewport = document.getElementById("viewport");
  stopMotion();
  const before = scenePoints(viewport.querySelector("svg"));
  viewport.replaceChildren(document.importNode(svg, true));
  const drawing = viewport.firstChild;
  const picks = [...drawing.querySelectorAll("[data-base-index]")];
  drawing.setAttribute("role", "group");
  drawing.setAttribute(
    "aria-label",
    "Recorded molecule; arrows move between bases, Enter opens local choices, I follows a position",
  );
  picks.forEach(base => {
    base.style.cursor = "pointer";
    base.addEventListener("dblclick", () => zoomNeighborhood(base.dataset.neighborhood));
  });
  const bases = [...drawing.querySelectorAll("[data-base-index]")];
  const bounds = bases.map((n) => n.getBBox());
  // Captions belong below this viewport. Preserve strand orientation and operation labels.
  drawing.querySelectorAll("text").forEach((t) => {
    if (
      !t.closest(
        "[data-base-index],[data-inspection-overlays],[data-correspondence-notice],[data-change-legend]",
      ) &&
      !/^[53]′$/.test(t.textContent)
    )
      t.remove();
  });
  const overlay = drawing.querySelector("[data-inspection-overlays]");
  if (overlay && overlay.children.length) bounds.push(overlay.getBBox());
  drawing
    .querySelectorAll("[data-correspondence-notice],[data-change-legend]")
    .forEach((n) => bounds.push(n.getBBox()));
  if (bounds.length) {
    const frame = drawing.getAttribute("viewBox").split(/\s+/).map(Number);
    const top = Math.min(...bounds.map((b) => b.y)) - 16,
      baseBottom = Math.max(...bounds.map((b) => b.y + b.height));
    let bottom = baseBottom + 55;
    drawing.removeAttribute("width");
    drawing.removeAttribute("height");
    // Keep letters readable; long precursors may scroll, rather than shrink to illegibility.
    drawing.style.minWidth =
      Math.min(frame[2], Math.max(960, frame[2] * 0.8)) + "px";
    if (choices) {
      const names = {
        loop: "Loop",
        closing: "Loop-side stem",
        assembly: "Open side",
        stem: "Supplied stem",
        interfaces: "Released ends",
      };
      const lanes = [];
      const anchors = Object.entries(names)
        .flatMap(([key, name]) => {
          const boxes = bases
            .filter((b) => b.dataset.neighborhood === key)
            .map((b) => b.getBBox())
            .sort((a, b) => a.x - b.x);
          if (!boxes.length) return [];
          // Anchor the first contiguous occurrence, not the mean of separated copies.
          let end = boxes[0].x + boxes[0].width;
          for (const box of boxes) {
            if (box.x > end + 22) break;
            end = Math.max(end, box.x + box.width);
          }
          return [{ key, name, x: (boxes[0].x + end) / 2 }];
        })
        .sort((a, b) => a.x - b.x);
      for (const { key, name, x: originX } of anchors) {
        const info = choices.neighborhoods?.[key],
          status = info?.status || "unavailable";
        const label = `${name} · ${status === "variable" ? info.variant_count + " variants" : status === "unavailable" ? "inspect only" : status}`;
        const width = label.length * 7.5,
          x = Math.max(
            width / 2 + 8,
            Math.min(frame[2] - width / 2 - 8, originX),
          );
        let lane = 0;
        while (lanes[lane] !== undefined && lanes[lane] > x - width / 2 - 16)
          lane++;
        lanes[lane] = x + width / 2;
        const y = baseBottom + 38 + lane * 25;
        bottom = Math.max(bottom, y + 16);
        const line = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "path",
        );
        line.setAttribute("d", `M${originX},${baseBottom + 5} L${x},${y - 16}`);
        line.setAttribute("stroke", "#b7c8c2");
        drawing.append(line);
        const anchor = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "text",
        );
        anchor.setAttribute("x", String(x));
        anchor.setAttribute("y", String(y));
        anchor.setAttribute("text-anchor", "middle");
        anchor.setAttribute("font-size", "14");
        anchor.setAttribute("fill", "#176b63");
        anchor.textContent = label;
        anchor.setAttribute("data-region-anchor", key);
        anchor.setAttribute(
          "aria-label",
          `${name}; ${status} at ${choices.query.stage}`,
        );
        if (status !== "unavailable") {
          anchor.setAttribute("role", "button");
          anchor.setAttribute("tabindex", "0");
          anchor.addEventListener("click", () => {
            const box = anchor.getBoundingClientRect();
            onNeighborhood(key, {x: box.x, y: box.y});
          });
          anchor.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onNeighborhood(key);
            }
          });
        }
        drawing.append(anchor);
      }
    }
    drawing.setAttribute(
      "viewBox",
      `${frame[0]} ${top} ${frame[2]} ${bottom - top}`,
    );
    drawing.style.aspectRatio = `${frame[2]} / ${bottom - top}`;
    drawing.dataset.wholeFrame = drawing.getAttribute("viewBox");
  }
  attachCamera(drawing);
  attachLocalExploration(drawing, onNeighborhood, onPick);
  molecularNavigation(drawing);
  tweenScene(before, drawing, transition);
  const molecular = preview.molecular_state;
  renderStateChoices(molecular.available_states, molecular.state.state_id);
  document.getElementById("molecule-stage").textContent =
    document.getElementById("inspect-state").selectedOptions[0].textContent +
    " · recorded state; requirements retain their declared stages";
  const focused = molecular.bases.filter((b) => b.focus_relation);
  document.getElementById("inspection-detail").textContent =
    molecular.focus_status === "not_requested"
      ? "Select a nucleotide to follow its recorded ancestry and contacts through processing."
      : molecular.focus_status === "removed"
        ? "The focused ancestry occurs earlier in this preparation but has been removed from the displayed state."
        : molecular.focus_status === "not_yet_present"
          ? "The focused material enters at a later recorded state; it is not present here."
          : molecular.focus_status === "not_present"
            ? "The focused material ancestry is not present in this state; no sequence-based correspondence is inferred."
            : focused
                .map(
                  (b) =>
                    `${b.base} · ${b.neighborhood || "unmapped region"} · ${b.material_role || "unassigned material"} · ${b.focus_relation.replaceAll("_", " ")}`,
                )
                .join("; ");
  return true;
}

export function renderStateChoices(states, selected) {
  const control = document.getElementById("inspect-state");
  control.replaceChildren(
    new Option("All processing steps", "all"),
    ...states.map((s) => {
      const peers = states.filter((v) => v.phase === s.phase);
      const name =
        (s.phase === "clone_ready_duplex"
          ? "Released duplex insert"
          : s.phase.replaceAll("_", " ")) +
        (s.roles?.includes("endpoint") ? " · endpoint" : "") +
        (peers.length > 1
          ? ` · state ${peers.indexOf(s) + 1} of ${peers.length}`
          : "");
      const option = new Option(
        name,
        peers.length === 1 ? s.phase : s.state_id,
      );
      option.title = s.state_id;
      return option;
    }),
  );
  if (selected === "all") { control.value = "all"; return; }
  const exact = states.find((s) => s.state_id === selected);
  const matches = states.filter((s) => s.phase === selected);
  const match = exact || (matches.length === 1 ? matches[0] : null);
  if (match)
    control.value =
      states.filter((s) => s.phase === match.phase).length === 1
        ? match.phase
        : match.state_id;
  else {
    control.prepend(
      new Option(
        matches.length > 1
          ? "Choose an exact recorded state"
          : "Requested phase unavailable",
        selected,
      ),
    );
    control.value = selected;
  }
}
