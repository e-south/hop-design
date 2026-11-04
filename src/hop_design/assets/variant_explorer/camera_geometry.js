"use strict";
// Pure camera arithmetic has no access to molecular choices or preparation state.
export function zoomFrame(frame, factor, anchor, whole) {
  const scale = Math.max(0.008, Math.min(6, frame[2] * factor / whole[2]));
  const width = whole[2] * scale, ratio = width / frame[2];
  return [frame[0] + frame[2] * anchor[0] * (1 - ratio),
          frame[1] + frame[3] * anchor[1] * (1 - ratio), width, frame[3] * ratio];
}
export function panFrame(frame, dx, dy) {
  return [frame[0] + dx, frame[1] + dy, frame[2], frame[3]];
}

// At fit scale the page owns scrolling; only deliberate magnification enables pan.
export function wheelMode(frame, whole, modifiers) {
  if (modifiers.ctrlKey || modifiers.metaKey) return "zoom";
  return frame[2] < whole[2] * 0.999 ? "pan" : "page";
}

export function cameraKey(key) {
  if (["Home", "0"].includes(key)) return "fit";
  return ["+", "="].includes(key) ? 0.8 : key === "-" ? 1.25 : null;
}
