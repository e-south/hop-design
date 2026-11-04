import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const load = async () => import("data:text/javascript;base64," + Buffer.from(await readFile(
  new URL("../../src/hop_design/assets/variant_explorer/camera_geometry.js", import.meta.url)
)).toString("base64"));

test("camera zoom keeps the pointed molecular coordinate fixed and does not mutate its input", async () => {
  const { zoomFrame, panFrame } = await load();
  const frame = [10, 20, 1000, 2000];
  const next = zoomFrame(frame, 0.5, [0.25, 0.75], [0, 0, 1000, 2000]);
  assert.deepEqual(next, [135, 770, 500, 1000]);
  assert.deepEqual(frame, [10, 20, 1000, 2000]);
  assert.deepEqual(panFrame(frame, 50, -20), [60, 0, 1000, 2000]);
});

test("ordinary scrolling belongs to the page at fit scale and pans only after zoom", async () => {
  const { wheelMode, cameraKey } = await load();
  const whole = [0, 0, 1000, 800];
  assert.equal(wheelMode(whole, whole, {}), "page");
  assert.equal(wheelMode([0, 0, 1200, 960], whole, {}), "page");
  assert.equal(wheelMode([10, 20, 500, 400], whole, {}), "pan");
  assert.equal(wheelMode(whole, whole, {ctrlKey:true}), "zoom");
  assert.equal(wheelMode(whole, whole, {metaKey:true}), "zoom");
  assert.equal(cameraKey("Home"), "fit");
  assert.equal(cameraKey("0"), "fit");
  assert.equal(cameraKey("="), 0.8);
  assert.equal(cameraKey("-"), 1.25);
  assert.equal(cameraKey("ArrowRight"), null);
});
