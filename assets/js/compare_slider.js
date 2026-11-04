(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.CompareSlider = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  var OVERSCAN = -5000;

  function clampRatio(r) {
    r = Number(r);
    if (r !== r) return 0.5;
    return Math.min(1, Math.max(0, r));
  }

  // Clip for a pane translated by (panePosX, panePosY) in the map container,
  // in pane-local coordinates. Non-clipped edges get generous overscan.
  function computeClip(w, h, ratio, lidarSide, panePosX, panePosY) {
    var localX = clampRatio(ratio) * w - (panePosX || 0);
    var clip = { left: OVERSCAN, top: OVERSCAN, right: OVERSCAN, bottom: OVERSCAN };
    if (lidarSide === 'right') clip.left = localX;
    else clip.right = 0 - localX; // pane is 0x0: visible x <= localX needs a negative right inset
    return clip;
  }

  function clipToCss(c) {
    return 'inset(' + [c.top, c.right, c.bottom, c.left].map(function (v) { return v + 'px'; }).join(' ') + ')';
  }

  return { clampRatio: clampRatio, computeClip: computeClip, clipToCss: clipToCss };
}));
