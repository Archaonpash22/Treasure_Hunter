// Before/after compare overlay: clips terrainPane via CompareSlider, draggable divider in #map.
(function () {
  var state = { enabled: false, ratio: 0.5, side: 'right', ready: false };
  var el = {};

  function build() {
    var css = document.createElement('style');
    css.textContent =
      '#cmpDivider{position:absolute;top:0;bottom:0;width:4px;margin-left:-2px;background:#fff;z-index:1200;' +
      'box-shadow:0 0 4px rgba(0,0,0,.6);cursor:ew-resize;display:none;touch-action:none}' +
      '#cmpGrip{position:absolute;top:50%;left:50%;width:36px;height:36px;margin:-18px 0 0 -18px;border-radius:50%;' +
      'background:#fff;box-shadow:0 0 6px rgba(0,0,0,.7);color:#333;font:bold 14px/36px sans-serif;text-align:center}' +
      '.cmpLabel{position:absolute;top:8px;z-index:1190;display:none;padding:2px 8px;border-radius:4px;' +
      'background:rgba(0,0,0,.6);color:#fff;font:12px sans-serif;pointer-events:none}';
    document.head.appendChild(css);
    var box = map.getContainer();
    el.div = document.createElement('div'); el.div.id = 'cmpDivider';
    el.div.innerHTML = '<div id="cmpGrip">&#9664;&#9654;</div>';
    el.l = document.createElement('div'); el.l.className = 'cmpLabel'; el.l.style.left = '8px';
    el.r = document.createElement('div'); el.r.className = 'cmpLabel'; el.r.style.right = '8px';
    [el.div, el.l, el.r].forEach(function (n) { box.appendChild(n); });
    L.DomEvent.disableClickPropagation(el.div);
    L.DomEvent.disableScrollPropagation(el.div);
    bindDrag();
    map.on('move zoom resize', update);
    state.ready = true;
  }

  function bindDrag() {
    var grabbed = false;
    function pos(e) {
      var t = e.touches && e.touches[0] ? e.touches[0] : e;
      return t.clientX - map.getContainer().getBoundingClientRect().left;
    }
    function down(e) { grabbed = true; map.dragging.disable(); e.preventDefault(); }
    function move(e) {
      if (!grabbed) return;
      state.ratio = CompareSlider.clampRatio(pos(e) / map.getSize().x);
      update();
    }
    function up() { if (grabbed) { grabbed = false; map.dragging.enable(); } }
    el.div.addEventListener('mousedown', down);
    el.div.addEventListener('touchstart', down, { passive: false });
    window.addEventListener('mousemove', move);
    window.addEventListener('touchmove', move, { passive: false });
    window.addEventListener('mouseup', up);
    window.addEventListener('touchend', up);
  }

  function update() {
    if (!state.ready) return;
    var pane = map.getPane('terrainPane');
    if (!pane) return;
    var show = state.enabled;
    el.div.style.display = el.l.style.display = el.r.style.display = show ? 'block' : 'none';
    if (!show) { pane.style.clipPath = ''; return; }
    var size = map.getSize(), pp = map._getMapPanePos();
    el.div.style.left = (state.ratio * size.x) + 'px';
    pane.style.clipPath = CompareSlider.clipToCss(
      CompareSlider.computeClip(size.x, size.y, state.ratio, state.side, pp.x, pp.y));
    el.l.textContent = state.side === 'left' ? 'Mit LiDAR' : 'Ohne LiDAR';
    el.r.textContent = state.side === 'left' ? 'Ohne LiDAR' : 'Mit LiDAR';
  }

  window.setCompareMode = function (enabled) {
    state.enabled = !!enabled;
    if (!state.ready) {
      if (typeof map === 'undefined' || !map || !map.getContainer) return;
      build();
    }
    if (state.enabled && !isTerrainAutoMode) window.setTerrainAutoMode(true);
    update();
  };
  window.setCompareSide = function (side) { state.side = side === 'left' ? 'left' : 'right'; update(); };
  window.setCompareRatio = function (r) { state.ratio = CompareSlider.clampRatio(r); update(); };
})();
