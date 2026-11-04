// View continuity consumes recorded correspondence; it never aligns DNA letters.
export const addressKey = (a) => JSON.stringify([a.state_id, a.strand_id, a.index]);
const address = (key) => {
  const [state_id, strand_id, index] = JSON.parse(key);
  return {state_id, strand_id, index};
};

function corresponding(before, after, value) {
  if (before.atlas.materialized_realization_id === after.atlas.materialized_realization_id)
    return value;
  if (after.comparison?.reference !== before.atlas.materialized_realization_id) return null;
  const targets = new Map();
  for (const transition of after.comparison.transitions)
    for (const link of transition.links)
      if (addressKey(link.reference) === addressKey(value))
        targets.set(addressKey(link.target), link.target);
  return targets.size === 1 ? [...targets.values()][0] : null;
}

function nearest(points, frame) {
  const [x, y, width, height] = frame, center = [x + width / 2, y + height / 2];
  let best = null, distance = Infinity;
  for (const [key, [px, py]] of points) {
    if (px < x || px > x + width || py < y || py > y + height) continue;
    const d = (px - center[0]) ** 2 + (py - center[1]) ** 2;
    if (d < distance) { best = address(key); distance = d; }
  }
  return best;
}

export function transferAtlasView(before, after, geometry) {
  const {frame, whole, nextWhole, beforePoints, afterPoints, beforeRows, afterRows, focus} = geometry;
  const target = focus ? corresponding(before, after, focus) : null;
  const mapped = target && afterPoints.has(addressKey(target)) ? target : null;
  const result = {
    frame: [...frame], focus: mapped,
    focusStatus: focus ? (mapped ? "mapped" : "unresolved") : "not_requested",
  };
  if (frame.every((v, i) => Math.abs(v - whole[i]) < 0.01)) {
    result.frame = [...nextWhole];
    return result;
  }
  const anchor = focus || nearest(beforePoints, frame);
  if (!anchor) return result;
  const next = corresponding(before, after, anchor);
  let a = beforePoints.get(addressKey(anchor)), b = next && afterPoints.get(addressKey(next));
  if (!a || !b) {
    // A unique recorded phase preserves context, but is not base correspondence.
    const state = before.atlas.states.find(s => s.state.state_id === anchor.state_id)?.state;
    const oldPhases = before.atlas.states.filter(s => s.state.phase === state?.phase);
    const newPhases = after.atlas.states.filter(s => s.state.phase === state?.phase);
    if (oldPhases.length !== 1 || newPhases.length !== 1) return result;
    a = beforeRows.get(state.state_id);
    b = afterRows.get(newPhases[0].state.state_id);
  }
  if (a && b) result.frame = [frame[0] + b[0] - a[0], frame[1] + b[1] - a[1], frame[2], frame[3]];
  return result;
}
