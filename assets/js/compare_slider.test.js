const test = require('node:test');
const assert = require('node:assert/strict');
const CS = require('./compare_slider.js');

const O = -5000;

test('ratio 0.5, lidar left', () => {
  assert.deepEqual(CS.computeClip(240, 100, 0.5, 'left', 0, 0), { left: O, top: O, right: -120, bottom: O });
});

test('ratio 0.5, lidar right', () => {
  assert.deepEqual(CS.computeClip(240, 100, 0.5, 'right', 0, 0), { left: 120, top: O, right: O, bottom: O });
});

test('ratio 0 and 1 edge cases', () => {
  assert.equal(CS.computeClip(200, 100, 0, 'left', 0, 0).right, 0);
  assert.equal(CS.computeClip(200, 100, 0, 'right', 0, 0).left, 0);
  assert.equal(CS.computeClip(200, 100, 1, 'left', 0, 0).right, -200);
  assert.equal(CS.computeClip(200, 100, 1, 'right', 0, 0).left, 200);
});

test('clampRatio clamps and handles NaN', () => {
  assert.equal(CS.clampRatio(-1), 0);
  assert.equal(CS.clampRatio(2), 1);
  assert.equal(CS.clampRatio(0.3), 0.3);
  assert.equal(CS.clampRatio(NaN), 0.5);
  assert.equal(CS.clampRatio(undefined), 0.5);
  assert.equal(CS.computeClip(200, 100, 5, 'right', 0, 0).left, 200);
});

test('pane offset compensation', () => {
  // pane translated by (-30, 40): container x 100 is pane-local 130
  const l = CS.computeClip(200, 100, 0.5, 'left', -30, 40);
  assert.equal(l.right, -130);
  assert.equal(l.left, O);
  const r = CS.computeClip(200, 100, 0.5, 'right', -30, 40);
  assert.equal(r.left, 130);
  assert.equal(r.right, O);
});

test('left side w=1000: right inset is negative localX', () => {
  assert.equal(CS.computeClip(1000, 100, 0.5, 'left', 0, 0).right, -500);
  assert.equal(CS.computeClip(1000, 100, 0.5, 'left', 100, 0).right, -400);
  assert.equal(CS.computeClip(1000, 100, 0, 'left', 0, 0).right, 0);
  assert.equal(CS.computeClip(1000, 100, 1, 'left', 0, 0).right, -1000);
});

test('visible range against a 0-width reference box is the expected half', () => {
  const w = 1000, pp = 100;
  for (const side of ['left', 'right']) {
    const c = CS.computeClip(w, 100, 0.5, side, pp, 0);
    // inset on a 0-wide box at pane origin: visible x in [left, 0 - right]
    const x0 = c.left, x1 = 0 - c.right;
    // convert pane-local to container coords
    const lo = x0 + pp, hi = x1 + pp;
    if (side === 'right') { assert.equal(lo, 500); assert.ok(hi >= w); }
    else { assert.ok(lo <= 0); assert.equal(hi, 500); }
  }
});

test('clipToCss', () => {
  assert.equal(CS.clipToCss({ left: O, top: O, right: 120, bottom: O }), 'inset(-5000px 120px -5000px -5000px)');
});
