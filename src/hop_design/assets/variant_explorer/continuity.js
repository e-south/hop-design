"use strict";
// These keys locate drawn bases; they never establish molecular correspondence.
export const addressKey = (a) => JSON.stringify([a.state_id, a.strand_id, a.index]);

export function motionPlan(before, after, transition) {
  const candidates = new Map(),
    used = new Set(),
    mapped = new Map();
  for (const link of transition?.links || []) {
    const from = addressKey(link.reference),
      to = addressKey(link.target);
    if (!before.has(from) || !after.has(to)) continue;
    if (!candidates.has(to)) candidates.set(to, new Set());
    candidates.get(to).add(from);
  }
  for (const [to, from] of candidates) {
    if (from.size !== 1) continue;
    const key = [...from][0];
    mapped.set(to, { ...before.get(key), sourceKey: key });
    used.add(key);
  }
  return {
    mapped,
    entering: [...after.keys()].filter((k) => !mapped.has(k)),
    departing: [...before.keys()].filter((k) => !used.has(k)),
  };
}

export function latestOnly(produce, consume) {
  let revision = 0;
  const run = async (...args) => {
    const current = ++revision;
    try {
      const result = await produce(...args);
      if (current !== revision) return;
      return await consume(result, () => current === revision);
    } catch (error) {
      if (current === revision) throw error;
    }
  };
  run.invalidate = () => {
    revision++;
  };
  return run;
}
