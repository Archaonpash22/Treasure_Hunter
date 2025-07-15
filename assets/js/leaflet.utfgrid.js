/*
 (c) 2012, Michael Evans
 (c) 2012, Thomas J Bradley
 (c) 2012, GEOIQ
 (c) 2014, David vt.
 (c) 2018, KlokanTech.com
*/


L.Util.ajax = function (url, cb) {
	'use strict';
	// the following is from JavaScript: The Definitive Guide, 3rd Edition.
	// written by David Flanagan.  Copyright 2001 O'Reilly & Associates, Inc.
	if (window.XMLHttpRequest === undefined) {
		window.XMLHttpRequest = function () {
			try {
				return new ActiveXObject('Microsoft.XMLHTTP.6.0');
			}
			catch (e1) {
				try {
					return new ActiveXObject('Microsoft.XMLHTTP.3.0');
				}
				catch (e2) {
					throw new Error('XMLHttpRequest is not supported');
				}
			}
		};
	}
	var request = new window.XMLHttpRequest();
	request.open('GET', url);
	request.onreadystatechange = function () {
		if (request.readyState === 4 && request.status === 200) {
			if (window.JSON) {
				cb(JSON.parse(request.responseText));
			} else {
				cb(eval('(' + request.responseText + ')'));
			}
		}
	};
	request.send(null);
};


L.UtfGrid = (L.Layer || L.Class).extend({
	options: {
		subdomains: 'abc',

		minZoom: 0,
		maxZoom: 18,
		tileSize: 256,

		resolution: 4,
		useJsonP: true,
		pointerCursor: true
	},

	//The thing the mouse is currently on
	_mouseOn: null,

	initialize: function (url, options) {
		L.Util.setOptions(this, options);

		this._url = url;
		this._cache = {};

		//Find a unique id in window for holding the PJSON data
		if (this.options.useJsonP) {
			this._windowKey = '_l_utfgrid_' + (L.stamp(this));
			window[this._windowKey] = {};
		}
	},

	onAdd: function (map) {
		this._map = map;
		this._container = this._map._container;

		this._update();

		var zoom = this._map.getZoom();

		if (this.options.minZoom < zoom && this.options.maxZoom > zoom) {
			this._addEvents();
		}
	},

	onRemove: function () {
		this._removeEvents();
		this._mouseOn = null;

		if (this.options.useJsonP) {
			delete window[this._windowKey];
		}
	},

	createTile: function(coords) {
		this._loadTile(coords);
		return document.createElement('div');
	},

	_loadTile: function(coords) {
		var url = this.getTileUrl(coords);
		var key = this._tileCoordsToKey(coords);
		if (this._cache[key]) {
			return;
		}

		if (this.options.useJsonP) {
			this._loadJsonP(url, key);
		} else {
			L.Util.ajax(url, L.bind(function(data) {
				this._cache[key] = data;
				this._update();
			}, this));
		}
	},

	_loadJsonP: function(url, key) {
		var head = document.getElementsByTagName('head')[0];
		var script = document.createElement('script');

		window[this._windowKey][key] = L.bind(function (data) {
			this._cache[key] = data;
			delete window[this._windowKey][key];
			head.removeChild(script);
			this._update();
		}, this);

		script.type = 'text/javascript';
		script.src = url;
		head.appendChild(script);
	},

	_addEvents: function () {
		L.DomEvent.on(this._container, 'mousemove', this._onMouseMove, this);
		L.DomEvent.on(this._map, 'click', this._onClick, this);
		L.DomEvent.on(this._map, 'zoomend', this._onZoom, this);
		L.DomEvent.on(this._map, 'moveend', this._onMove, this);
	},

	_removeEvents: function () {
		L.DomEvent.off(this._container, 'mousemove', this._onMouseMove, this);
		L.DomEvent.off(this._map, 'click', this._onClick, this);
		L.DomEvent.off(this._map, 'zoomend', this._onZoom, this);
		L.DomEvent.off(this._map, 'moveend', this._onMove, this);
	},

	_onZoom: function() {
		this._cache = {};
		this._update();
	},

	_onMove: function() {
		this._update();
	},

	_onMouseMove: function (e) {
		var on = this._objectForEvent(e);

		if (on && on.id !== (this._mouseOn && this._mouseOn.id)) {
			this._fire('mouseover', this._mouseOn = on);
			if (this.options.pointerCursor) {
				this._container.style.cursor = 'pointer';
			}
		} else if (!on && this._mouseOn) {
			this._fire('mouseout', this._mouseOn);
			this._mouseOn = null;
			if (this.options.pointerCursor) {
				this._container.style.cursor = '';
			}
		}
	},

	_onClick: function (e) {
		var on = this._objectForEvent(e);
		if (on) {
			this._fire('click', on);
		}
	},

	_objectForEvent: function (e) {
		var point = this._map.project(e.latlng);
		var_tile = this._getTile(point);
		if (!tile) {
			return null;
		}

		var gridX = Math.floor((point.x - tile.x) / this.options.resolution);
		var gridY = Math.floor((point.y - tile.y) / this.options.resolution);
		var max = tile.grid.length - 1;

		if (gridX < 0 || gridX > max || gridY < 0 || gridY > max) {
			return null;
		}

		var key = this._utfDecode(tile.grid[gridY].charCodeAt(gridX));
		var data = tile.data[key];

		if (data) {
			return L.Util.extend({
				latlng: e.latlng,
				id: key
			}, data);
		}

		return null;
	},

	_getTile: function(point) {
		var coords = this._getTileCoords(point);
		var key = this._tileCoordsToKey(coords);
		var tile = this._cache[key];
		if (tile) {
			var tilePoint = this._getTilePoint(coords);
			tile.x = tilePoint.x;
			tile.y = tilePoint.y;
		} else {
			this._loadTile(coords);
		}
		return tile;
	},

	_getTileCoords: function(point) {
		return {
			x: Math.floor(point.x / this.options.tileSize),
			y: Math.floor(point.y / this.options.tileSize),
			z: this._map.getZoom()
		};
	},

	_getTilePoint: function(coords) {
		return {
			x: coords.x * this.options.tileSize,
			y: coords.y * this.options.tileSize
		};
	},

	_tileCoordsToKey: function(coords) {
		return coords.z + '/' + coords.x + '/' + coords.y;
	},

	_update: function () {
		var bounds = this._map.getPixelBounds();
		var zoom = this._map.getZoom();

		if (zoom > this.options.maxZoom || zoom < this.options.minZoom) {
			return;
		}

		var nw = this._getTileCoords(bounds.min);
		var se = this._getTileCoords(bounds.max);

		for (var x = nw.x; x <= se.x; x++) {
			for (var y = nw.y; y <= se.y; y++) {
				this._loadTile({
					x: x,
					y: y,
					z: zoom
				});
			}
		}
	},

	//The following function is based on the UTF-8 Decoder from Google's V3 API
	_utfDecode: function (c) {
		if (c >= 93) {
			c--;
		}
		if (c >= 35) {
			c--;
		}
		return c - 32;
	},

	getTileUrl: function (coords) {
		var url = L.Util.template(this._url, L.Util.extend({
			s: L.TileLayer.prototype._getSubdomain.call(this, coords),
			z: coords.z,
			x: coords.x,
			y: coords.y
		}, this.options));

		if (this.options.useJsonP) {
			return url + '?callback=' + this._windowKey + '.' + this._tileCoordsToKey(coords);
		}
		return url;
	},

	//This is for compatibility with L.LayerGroup
	addLayer: function () { },
	removeLayer: function () { },
	
	//This is for compatibility with Leaflet v1.0
	_fire: L.Evented.prototype.fire

});

L.utfGrid = function (url, options) {
	return new L.UtfGrid(url, options);
};