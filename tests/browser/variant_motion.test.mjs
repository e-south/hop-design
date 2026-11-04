import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const source = new URL(
  "../../src/hop_design/assets/variant_explorer/continuity.js",
  import.meta.url,
);
const { motionPlan, latestOnly } = await import(
  "data:text/javascript;base64," +
    Buffer.from(await readFile(source)).toString("base64")
);
const a = (s, i) => ({ state_id: "s", strand_id: s, index: i });

test("copying is one-to-many; ambiguous targets are not given an arbitrary anchor", () => {
  const before = new Map([
    ['["s","a",0]', { x: 10, y: 20 }],
    ['["s","a",1]', { x: 30, y: 20 }],
  ]);
  const after = new Map([
    ['["s","b",0]', { x: 10, y: 40 }],
    ['["s","b",1]', { x: 30, y: 40 }],
  ]);
  const links = [0, 1].map((i) => ({
    reference: a("a", 0),
    target: a("b", i),
    relation: "copied",
  }));
  const plan = motionPlan(before, after, { links });
  assert.equal(plan.mapped.size, 2);
  assert.equal(plan.mapped.get('["s","b",1]').x, 10);
  const ambiguous = motionPlan(before, after, {
    links: [
      ...links,
      { reference: a("a", 1), target: a("b", 1), relation: "comparison" },
    ],
  });
  assert.equal(ambiguous.mapped.has('["s","b",1]'), false);
  assert.deepEqual(ambiguous.entering, ['["s","b",1]']);
});

test("rapid reversal accepts only the latest requested target", async () => {
  const pending = [],
    accepted = [];
  const run = latestOnly(
    (value) => new Promise((resolve) => pending.push(() => resolve(value))),
    (value) => accepted.push(value),
  );
  const p1 = run("AAAC"),
    p2 = run("AACA"),
    p3 = run("AAAC");
  pending[2]();
  await p3;
  pending[1]();
  await p2;
  pending[0]();
  await p1;
  assert.deepEqual(accepted, ["AAAC"]);
});

const motionSource = await readFile(
  new URL(
    "../../src/hop_design/assets/variant_explorer/motion.js",
    import.meta.url,
  ),
  "utf8",
);
const strandCurveURL = "data:text/javascript;base64," + Buffer.from(await readFile(
  new URL("../../src/hop_design/assets/variant_explorer/strand_curve.js", import.meta.url),
)).toString("base64");
const motionModule = await import(
  "data:text/javascript;base64," +
    Buffer.from(
      motionSource.replace(
        '"./continuity.js"',
        JSON.stringify(
          "data:text/javascript;base64," +
            Buffer.from(await readFile(source)).toString("base64"),
        ),
      ).replace('"./strand_curve.js"', JSON.stringify(strandCurveURL)),
    ).toString("base64")
);

test("colored neighborhoods meet on a continuous curve through exact bases", async () => {
  const { bandSegments } = await import(strandCurveURL);
  const points = [[0, 0], [16, 0], [27, 11], [32, 22], [27, 33], [16, 44]];
  const left = bandSegments(points, 0, 2), right = bandSegments(points, 3, 5);
  assert.deepEqual(left.at(-1).at(-1), right[0][0]);
  const [a, b] = left.at(-1).slice(-2), [c, d] = right[0];
  assert.ok(b.every((v, i) => Math.abs((v - a[i]) - (d[i] - c[i])) < 1e-10));
  const singleton = bandSegments([[20, 30]], 0, 0);
  assert.deepEqual(singleton[0][0], [14, 30]);
  assert.deepEqual(singleton[0].at(-1), [26, 30]);
});

test("recognition footprints retain band width around a moving handle bend", () => {
  const points = motionModule.ribbonPoints([[0, 0], [32, 0], [64, 32]], 15);
  assert.ok(points.length > 6);
  const n = points.length/2;
  assert.ok(Math.abs(Math.hypot(points[n-1][0] - points[n][0], points[n-1][1] - points[n][1]) - 30) < 1e-8);
  assert.deepEqual(motionModule.ribbonPoints([[20, 30]], 15)[0], [12, 45]);
});

test("molecular picking waits for motion; reduced motion preserves a ready static scene", (t) => {
  let frame;
  globalThis.matchMedia = () => ({ matches: false });
  globalThis.requestAnimationFrame = (fn) => {
    frame = fn;
    return 1;
  };
  globalThis.cancelAnimationFrame = () => {};
  t.after(() => {
    delete globalThis.matchMedia;
    delete globalThis.requestAnimationFrame;
    delete globalThis.cancelAnimationFrame;
  });
  const attrs = new Map();
  const drawing = {
    dataset: {},
    style: {},
    querySelectorAll: () => [],
    setAttribute: (k, v) => attrs.set(k, v),
    removeAttribute: (k) => {
      attrs.delete(k);
      if (k === "data-transition-mode") delete drawing.dataset.transitionMode;
    },
  };
  motionModule.tweenScene(
    new Map([
      [
        "unused",
        {
          element: {
            closest: () => null,
            cloneNode: () => ({
              removeAttribute() {},
              setAttribute() {},
              style: {},
              remove() {},
            }),
          },
        },
      ],
    ]),
    { ...drawing, append() {} },
    { mode: "processing", links: [] },
  );
  assert.equal(attrs.get("aria-disabled"), "true");
  frame(performance.now() + 400);
  assert.equal(attrs.has("aria-disabled"), false);
  globalThis.matchMedia = () => ({ matches: true });
  motionModule.tweenScene(new Map([["unused", {}]]), drawing, {
    mode: "variant",
    links: [],
  });
  assert.equal(attrs.has("aria-disabled"), false);
  assert.equal(drawing.dataset.transitionMode, undefined);
});

test("an obsolete failure cannot replace the latest successful view", async () => {
  let rejectOld;
  const seen = [];
  const run = latestOnly(
    (value) =>
      value === "old"
        ? new Promise((_, reject) => {
            rejectOld = reject;
          })
        : Promise.resolve(value),
    (value) => seen.push(value),
  );
  const old = run("old");
  await run("current");
  rejectOld(new Error("stale query"));
  await assert.doesNotReject(old);
  assert.deepEqual(seen, ["current"]);
  const failing = latestOnly(
    () => Promise.reject(new Error("current failure")),
    () => {},
  );
  await assert.rejects(failing(), /current failure/);
});

test("repeated strand names in different atlas stages cannot collide", () => {
  const before = new Map([
    ['["source","strand",0]', { x: 10, y: 20 }],
    ['["duplex","strand",0]', { x: 10, y: 400 }],
  ]);
  const after = new Map([['["target","strand",0]', { x: 20, y: 500 }]]);
  const plan = motionPlan(before, after, { links: [{
    reference: { state_id: "duplex", strand_id: "strand", index: 0 },
    target: { state_id: "target", strand_id: "strand", index: 0 },
    relation: "comparison",
  }] });
  assert.equal(plan.mapped.get('["target","strand",0]')?.y, 400);
});

test("rounded molecular bands retain terminal extents during motion", async () => {
  const { ribbonPath } = await import(strandCurveURL);
  const d = ribbonPath([[0,0],[16,0],[32,0]], 13, 0, 2, 6);
  assert.ok(d.includes('Q'));
  const points = [...d.matchAll(/(-?\d+\.\d+),(-?\d+\.\d+)/g)].map(m=>[+m[1],+m[2]]);
  assert.equal(Math.min(...points.map(p=>p[0])), -6);
  assert.equal(Math.max(...points.map(p=>p[0])), 38);
  assert.equal(Math.max(...points.map(p=>p[1])), 13);
});

test("scene normalization preserves the displayed molecular address during motion", () => {
  const element = {
    dataset: { stateId: "s", strandId: "strand", baseIndex: "0" },
    transform: { baseVal: { consolidate: () => null } },
    querySelector: name => ({ getAttribute: key => name === "rect" ? ({x:"8",width:"14"})[key] : "45" }),
    closest: selector => ({dataset: selector === "[data-scene-y]" ? {sceneY:"-50"} : selector === "[data-atlas-x]" ? {atlasX:"100"} : {atlasY:"300"}}),
  };
  const points = motionModule.scenePoints({querySelectorAll: () => [element]});
  const actual = points.get('["s","strand",0]');
  assert.equal(actual.x, 115);
  assert.equal(actual.y, 290);
});
