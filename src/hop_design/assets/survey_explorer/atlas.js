import { zoomFrame, panFrame, wheelMode, cameraKey } from "./camera_geometry.js";
import { molecularNavigation } from "./grouped_navigation.js";
import { parameterKeys, parameterSelector, highlightParameters } from "./parameters.js";
import { addressKey, transferAtlasView } from "./atlas_position.js";

function positions(drawing) {
  const points = new Map(), rows = new Map();
  for (const row of drawing.querySelectorAll("[data-atlas-state]"))
    rows.set(row.dataset.atlasState, [+row.dataset.atlasX, +row.dataset.atlasY]);
  for (const base of drawing.querySelectorAll("[data-base-index]")) {
    const row = base.closest("[data-atlas-state]").dataset, box = base.getBBox();
    points.set(addressKey(baseAddress(base)), [
      +row.atlasX + box.x + box.width / 2, +row.atlasY + +(base.closest("[data-scene-y]")?.dataset.sceneY || 0) + box.y + box.height / 2,
    ]);
  }
  return {points, rows};
}

function baseAddress(base) {
  return {state_id: base.dataset.stateId, strand_id: base.dataset.strandId, index: +base.dataset.baseIndex};
}

export function molecularViewport(host, fitButton, onFocus) {
  let svg = null,
    whole = null,
    frame = null,
    url = null,
    drag = null,
    summary = null,
    focus = null,
    serial = 0;
  function paint() {
    svg?.setAttribute("viewBox", frame.join(" "));
  }
  function markFocus() {
    for (const base of svg?.querySelectorAll("[data-base-index]") || []) {
      if (focus && addressKey(baseAddress(base)) === addressKey(focus))
        base.setAttribute("data-inspected", "true");
      else base.removeAttribute("data-inspected");
    }
  }
  function fit() {
    if (whole) {
      frame = [...whole];
      paint();
    }
  }
  fitButton.addEventListener("click", fit);
  host.parentElement.addEventListener("keydown", (e) => {
    if (e.defaultPrevented || e.target.closest("select,input,textarea")) return;
    const action = cameraKey(e.key);
    if (action === "fit") {
      e.preventDefault();
      fit();
    }
    else if (frame && action !== null) {
      e.preventDefault();
      frame = zoomFrame(frame, action, [0.5, 0.5], whole);
      paint();
    }
  });
  host.addEventListener(
    "wheel",
    (e) => {
      if (!svg) return;
      const mode = wheelMode(frame, whole, e);
      if (mode === "page") return;
      e.preventDefault();
      const rect = svg.getBoundingClientRect();
      if (mode === "zoom") {
        const p = svg.createSVGPoint();
        p.x = e.clientX;
        p.y = e.clientY;
        const q = p.matrixTransform(svg.getScreenCTM().inverse());
        frame = zoomFrame(
          frame,
          Math.exp(e.deltaY * 0.003),
          [(q.x - frame[0]) / frame[2], (q.y - frame[1]) / frame[3]],
          whole,
        );
      } else {
        const scale = Math.max(frame[2] / rect.width, frame[3] / rect.height);
        frame = panFrame(frame, e.deltaX * scale, e.deltaY * scale);
      }
      paint();
    },
    { passive: false },
  );
  host.addEventListener("pointerdown", (e) => {
    if (!svg || e.button !== 0) return;
    if (wheelMode(frame, whole, {}) === "page" || e.target.closest("[data-base-index],[data-site-id]")) return;
    drag = [e.clientX, e.clientY, ...frame];
    host.setPointerCapture(e.pointerId);
  });
  host.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const rect = svg.getBoundingClientRect(),
      scale = Math.max(drag[4] / rect.width, drag[5] / rect.height);
    frame = panFrame(
      drag.slice(2),
      (drag[0] - e.clientX) * scale,
      (drag[1] - e.clientY) * scale,
    );
    paint();
  });
  host.addEventListener("pointerup", () => (drag = null));
  host.addEventListener("pointercancel", () => (drag = null));
  host.addEventListener("focusin", (e) => {
    const base = e.target.closest("[data-base-index]");
    if (base) {
      focus = baseAddress(base);
      markFocus();
    }
  });
  for (const event of ["pointerover", "focusin"])
    host.addEventListener(event, (e) => {
      const marked = e.target.closest(parameterSelector);
      if (marked) onFocus(parameterKeys(marked));
    });
  return {
    clear() {
      serial++;
      host.replaceChildren();
      svg = whole = frame = url = drag = summary = focus = null;
    },
    async prepare(preview) {
      const ticket = ++serial;
      if (!preview || preview.drawing === url) return () => {};
      let text;
      try {
        const response = await fetch(preview.drawing);
        if (ticket !== serial) return;
        if (!response.ok)
          throw Error("The selected molecular drawing could not be loaded.");
        text = await response.text();
      } catch (error) {
        if (ticket !== serial) return;
        throw error;
      }
      if (ticket !== serial) return;
      const document = new DOMParser().parseFromString(text, "image/svg+xml");
      if (document.querySelector("parsererror"))
        throw Error("Invalid molecular SVG.");
      const next = document.documentElement,
        box = next.getAttribute("viewBox").split(/\s+/).map(Number);
      return () => {
      if (ticket !== serial) return;
      const previous = svg ? positions(svg) : null;
      // getBBox needs a rendered SVG. Keep the old camera until both layouts exist.
      host.replaceChildren(next);
      if (whole && frame && summary && previous) {
        const target = positions(next);
        const transferred = transferAtlasView(summary, preview.summary, {
          frame, whole, nextWhole: box, beforePoints: previous.points,
          afterPoints: target.points, beforeRows: previous.rows, afterRows: target.rows, focus,
        });
        frame = transferred.frame;
        focus = transferred.focus;
        next.dataset.focusStatus = transferred.focusStatus;
      } else frame = [...box];
      whole = box;
      svg = next;
      molecularNavigation(svg);
      url = preview.drawing;
      summary = preview.summary;
      markFocus();
      paint();
      };
    },
    async show(preview) {
      const commit = await this.prepare(preview);
      commit?.();
    },
    camera() { return frame ? [...frame] : null; },
    restoreCamera(value) {
      if (value && value.length === 4 && value.every(Number.isFinite) && value[2]>0 && value[3]>0) {
        frame=[...value]; paint();
      }
    },
    stage(state) {
      if (state === 'all') return fit();
      const row=[...svg?.querySelectorAll('[data-atlas-state]') || []].find(e=>e.dataset.atlasState===state);
      if (!row) return;
      const box=row.getBBox();
      frame=[+row.dataset.atlasX+box.x-24,+row.dataset.atlasY+box.y-24,box.width+48,box.height+48];
      paint();
    },
    highlight(keys) {
      highlightParameters(host, keys);
    },
  };
}
