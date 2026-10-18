"""Archaeological LiDAR visualisations computed from height tiles (no AI, no network beyond the heights).

  combo  All of the below in one picture (VAT-like): shading, sky-view factor and slope as grey base,
         coloured by the local relief. The default view.
  lrm    Local Relief Model: terrain minus its smoothed surface. Mounds, banks and ditches of a few
         decimetres stand out, the large-scale topography disappears. Red = raised, blue = lowered.
  multi  Hillshade from 8 light directions averaged: no feature hides because it runs parallel to the light.
  svf    Sky-View Factor: how much of the sky is visible from each point. Ditches, hollow ways and pits
         are dark, ridges and banks bright; independent of any light direction.
  slope  Slope: steep edges (banks, terrace and ditch edges) are dark.

Heights come from Terrarium tiles (Mapterhorn: the official 1 m DTMs of many countries). Each output tile
is computed on the 3 x 3 block of height tiles around it, so filters see across tile edges.
"""
import io
import math
import os
import threading

try:
    import numpy as np
    from PIL import Image
except ImportError:
    np = None
    Image = None

ORIGIN_SHIFT = 20037508.342789244
ANALYSES = ('combo', 'lrm', 'multi', 'svf', 'slope')


def available():
    return np is not None


class HeightSource:
    """Terrarium height tiles from a URL template, kept on disk (they are reused by all analyses
    and by the neighbouring output tiles)."""

    def __init__(self, url_template, cache_dir, session, max_zoom=16):
        self.url = url_template
        self.dir = cache_dir
        self.session = session
        self.max_zoom = max_zoom
        self._locks = {}
        self._lock = threading.Lock()

    def tile(self, z, x, y):
        """512 x 512 float heights, or None outside the world / when the service has nothing."""
        n = 2 ** z
        if not (0 <= y < n):
            return None
        x %= n
        path = os.path.join(self.dir, str(z), str(x), f'{y}.webp')
        with self._lock:
            lock = self._locks.setdefault(path, threading.Lock())
        with lock:
            if not os.path.isfile(path):
                r = self.session.get(self.url.format(z=z, x=x, y=y), timeout=(10, 60))
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                os.makedirs(os.path.dirname(path), exist_ok=True)
                tmp = f'{path}.{threading.get_ident()}.tmp'
                with open(tmp, 'wb') as f:
                    f.write(r.content)
                os.replace(tmp, path)
            with open(path, 'rb') as f:
                data = f.read()
        rgb = np.asarray(Image.open(io.BytesIO(data)).convert('RGB'), dtype=np.float32)
        return rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768

    def block(self, z, x, y):
        """3 x 3 tiles around (x, y) as one 1536 x 1536 array (missing neighbours: edge copy)."""
        centre = self.tile(z, x, y)
        if centre is None:
            return None
        size = centre.shape[0]
        out = np.empty((3 * size, 3 * size), dtype=np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                t = centre if dx == dy == 0 else self.tile(z, x + dx, y + dy)
                if t is None:
                    t = centre  # a crude fill; only ever at the edge of the data
                out[(dy + 1) * size:(dy + 2) * size, (dx + 1) * size:(dx + 2) * size] = t
        return out


def _box_mean(a, r):
    """Mean over a (2r+1)^2 window via summed-area tables (same shape, edges use smaller windows)."""
    if r < 1:
        return a.copy()
    p = np.pad(a, r + 1, mode='edge').astype(np.float64)
    s = p.cumsum(0).cumsum(1)
    k = 2 * r + 1
    total = s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]
    return (total / (k * k))[:a.shape[0], :a.shape[1]].astype(np.float32)


def _hillshade(z, ground, azimuth, altitude=45.0, zf=1.0):
    dzdx = np.gradient(z, axis=1) / ground * zf
    dzdn = -np.gradient(z, axis=0) / ground * zf
    az, alt = math.radians(azimuth), math.radians(altitude)
    lx, ly, lz = math.sin(az) * math.cos(alt), math.cos(az) * math.cos(alt), math.sin(alt)
    return (-dzdx * lx - dzdn * ly + lz) / np.sqrt(dzdx * dzdx + dzdn * dzdn + 1)


def _ramp(values, stops):
    """Map values in [0, 1] to RGB through colour stops [(pos, (r, g, b)), ...]."""
    v = np.clip(values, 0, 1)
    out = np.zeros(v.shape + (3,), dtype=np.float32)
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        m = (v >= p0) & (v <= p1)
        t = ((v - p0) / (p1 - p0))[m][:, None]
        out[m] = np.array(c0) * (1 - t) + np.array(c1) * t
    return out.astype(np.uint8)


# blue (lower) - white - red/brown (raised), like the usual LRM colouring
LRM_STOPS = [(0.0, (33, 82, 160)), (0.35, (140, 178, 222)), (0.5, (246, 244, 238)),
             (0.65, (228, 160, 120)), (1.0, (150, 45, 25))]


PAD = 24  # context pixels around the centre tile for the neighbourhood filters


def _lrm(block, s, ground):
    """Local relief of the centre tile in metres (terrain minus a ~20 m smoothed surface)."""
    r = max(3, int(round(20.0 / ground / 2)))   # two box passes ~ Gaussian; at least 3 px
    trend = _box_mean(_box_mean(block, r), r)
    return (block - trend)[s:2 * s, s:2 * s]


def _lrm_span(ground):
    return 1.0 if ground < 3 else 2.0 if ground < 10 else 5.0   # metres shown as full colour


def _multi(sub, ground):
    """Mean of 8 hillshades, 0..1, stretched around the flat-ground value (fixed, so tiles match)."""
    zf = min(max(ground, 1.0) ** 0.3, 4.0)
    hs = np.mean([_hillshade(sub, ground, az, 45, zf) for az in range(0, 360, 45)], axis=0)
    return np.clip((hs - math.sin(math.radians(45))) * 4.0 + 0.62, 0, 1)


def _slope(sub, ground):
    """1 = flat, 0 = steep (40 deg at 1-3 m pixels, 25 deg when coarser)."""
    dzdx = np.gradient(sub, axis=1) / ground
    dzdy = np.gradient(sub, axis=0) / ground
    deg = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    return 1 - np.clip(deg / (40.0 if ground < 3 else 25.0), 0, 1) ** 0.8


def _svf(sub, ground):
    """Sky-view factor, 0..1 on a fixed scale (open flat ground = 1); 8 directions, ~10 m radius."""
    steps = max(3, min(PAD, int(round(10.0 / ground))))
    svf = np.zeros_like(sub)
    for dx, dy in ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)):
        dist = math.hypot(dx, dy) * ground
        best = np.full_like(sub, -np.pi / 2)
        for k in range(1, steps + 1):
            shifted = np.roll(np.roll(sub, -dy * k, axis=0), -dx * k, axis=1)
            best = np.maximum(best, np.arctan((shifted - sub) / (dist * k)))
        svf += np.sin(np.maximum(best, 0))
    return np.clip((1 - svf / 8 - 0.78) / 0.22, 0, 1) ** 1.5


def render(kind, block, size, ground):
    """RGB or grey uint8 array (size x size) for the centre tile of a 3 x 3 height block."""
    s = size
    sub = block[s - PAD:2 * s + PAD, s - PAD:2 * s + PAD]
    crop = (slice(PAD, -PAD), slice(PAD, -PAD))
    if kind == 'lrm':
        rgb = _ramp(_lrm(block, s, ground) / (2 * _lrm_span(ground)) + 0.5, LRM_STOPS)
        shade = np.clip(_hillshade(block, ground, 315)[s:2 * s, s:2 * s], 0, 1)
        return (rgb * (0.55 + 0.45 * shade[..., None])).astype(np.uint8)
    if kind == 'multi':
        return (_multi(sub, ground)[crop] * 255).astype(np.uint8)
    if kind == 'slope':
        return (_slope(sub, ground)[crop] * 255).astype(np.uint8)
    if kind == 'svf':
        return (_svf(sub, ground)[crop] * 255).astype(np.uint8)
    if kind == 'combo':
        # Like the VAT composite (Kokalj & Somrak 2019): the grey base mixes multi-direction shading
        # (form), sky-view factor (ditches, pits) and slope (edges); the local relief colours it, so
        # raised features turn red and sunken ones blue without hiding the shading.
        grey = (0.45 * _multi(sub, ground) + 0.35 * _svf(sub, ground) + 0.20 * _slope(sub, ground))[crop]
        grey = np.clip((grey - 0.5) * 1.25 + 0.55, 0, 1)
        colour = _ramp(_lrm(block, s, ground) / (2 * _lrm_span(ground)) + 0.5, LRM_STOPS).astype(np.float32) / 255
        tint = 0.35 + 0.65 * colour            # white stays neutral, red/blue tint the grey
        return np.clip(grey[..., None] * tint * 255 * 1.08, 0, 255).astype(np.uint8)
    raise ValueError(kind)


def tile_jpeg(kind, source, gz, x, y, size=512):
    """JPEG of analysis `kind` for the 512 px tile (gz, x, y) of the height source, or None (no data)."""
    block = source.block(gz, x, y)
    if block is None:
        return None
    span = 2 * ORIGIN_SHIFT / (2 ** gz)
    lat = math.degrees(2 * math.atan(math.exp((ORIGIN_SHIFT - (y + 0.5) * span) / 6378137.0)) - math.pi / 2)
    ground = span / size * math.cos(math.radians(lat))
    img = render(kind, block, size, ground)
    buf = io.BytesIO()
    Image.fromarray(img, 'RGB' if img.ndim == 3 else 'L').save(buf, 'JPEG', quality=88)
    return buf.getvalue()
