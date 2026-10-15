"""Ring-gauge tray icon rendering (ARGB32, network byte order)."""
import base64
import math
import zlib

from .fmt import color_for

ICON_SIZE = 48

# Claude logo burst (claude.ai app icon, orange mark only) as a 20x20 alpha mask.
LOGO_SIZE = 20
LOGO_COLOR = (217, 119, 87)
_LOGO_ALPHA = zlib.decompress(base64.b64decode(
    "eNo9kE9I02EYx7/v++5PmBdBEVM3ZBAoCB6sIAZLaBhYsKEoaRcPJYJoBTsIUcc6NGJE7DBIR8gQG9WhbUzCEPWygwRSGDTEeXA46iD5Z9vv9+3dlj6Xh+fL8/D58AAK1w7TQkJF+iCVEACEDYOkW+AKX8CG/yXqvzMODJdHJQJrTkhcvK5wh8fdYppX8Yj0waLbZweSjCFI1U+uXpBCdP1kztNyWm5f2Lr029xvQwXTECUngwynEmnSrzUgrRJjeW4Zf3Jl8rVGNjVXySpEk6SR9z1J5rj3ZTn25vnMUNQwdKo3dz4F3I8ji4mvmZWUTkxzLzTgOtd2poomy0Zy7YT8+05ZrGgNcyNVLNH45rp8/+12Rss8OOKUvxj8lS1tF1yVKyk+cr2zkbP3Nj2ce8UbOhHi6QSQ3cR8Bu/pnSqNCFVFLJ06xI+4aCkc2G99qHzQrmboRt3JS+Aun9U8JG7fhOjlQ1gx3qPUmZ8FHbte/ZHa9A/62aFY"))


def _ring_cover(x, y, cx, cy, rmid, half, pct):
    """Coverage (0..1) of the filled arc and of the full track at one sample point."""
    dx, dy = x - cx, y - cy
    d = math.hypot(dx, dy)
    track = max(0.0, min(1.0, half - abs(d - rmid) + 0.5))
    if track <= 0 or pct is None:
        return track, 0.0
    pct = max(0.0, min(100.0, pct))
    ang = (math.degrees(math.atan2(dx, -dy)) + 360) % 360  # 0 = top, clockwise
    fill = track if ang <= pct * 3.6 else 0.0
    if pct > 0:  # round caps at both ends of the arc
        for a in (0.0, math.radians(pct * 3.6)):
            ex, ey = cx + rmid * math.sin(a), cy - rmid * math.cos(a)
            fill = max(fill, max(0.0, min(1.0, half - math.hypot(x - ex, y - ey) + 0.5)))
    return track, fill


def render_icon(session, weekly=None, size=ICON_SIZE):
    """Two concentric ring gauges (outer = session, inner = weekly) as ARGB32 bytes."""
    c = (size - 1) / 2
    th = size * 0.105
    rings = [(size / 2 - 0.5 - th / 2, session), (size / 2 - 0.5 - th * 1.5 - size * 0.045, weekly)]
    ls = round(size * 0.42)  # logo box, centered
    lo = (size - ls) // 2
    out = bytearray()
    for y in range(size):
        for x in range(size):
            best = (0.0, (0, 0, 0))
            for rmid, pct in rings:
                track, fill = _ring_cover(x, y, c, c, rmid, th / 2, pct)
                if fill > 0:
                    best = (fill, color_for(pct))
                elif track > 0 and best[0] == 0:
                    best = (track * 0.35, (200, 200, 200))
            cov, (r, g, b) = best
            a = int(255 * cov)
            lx, ly = x - lo, y - lo
            if 0 <= lx < ls and 0 <= ly < ls:  # logo on top, resampled to fit the inner ring
                la = _LOGO_ALPHA[int(ly * LOGO_SIZE / ls) * LOGO_SIZE + int(lx * LOGO_SIZE / ls)]
                if la:
                    r, g, b = (round((c1 * la + c0 * (255 - la) * a / 255) / max(1e-9, la + (255 - la) * a / 255))
                               for c1, c0 in zip(LOGO_COLOR, (r, g, b)))
                    a = a + la * (255 - a) // 255
            out += bytes((a, r, g, b))
    return bytes(out)
