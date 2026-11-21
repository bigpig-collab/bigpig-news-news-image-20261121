#!/usr/bin/env python3
"""news-image-20261121 v3 -- 'THE WORLD IN ONE DAY' broadsheet, 42 stories.

Fresh build. Stdlib only (math, os, struct, zlib). One 1024x1024 PNG.
Font: stroke-based vector faces drawn from scratch in this file -- a refined
sans (arc bowls, correct t/w/f) and a serif display face (thick verticals,
thin horizontals, serif ticks) built from the same glyph geometry. Set
FONT_TEST=1 to render a font test sheet instead of the page.
"""
import math
import os
import struct
import zlib

W, H = 1024, 1024
PAPER = (247, 242, 228)
INK = (28, 32, 48)
NAVY = (31, 52, 96)
RED = (178, 34, 34)
DRED = (139, 0, 0)
GREY = (110, 108, 96)
LGREY = (226, 220, 204)
BLUE = (47, 85, 151)
TEAL = (0, 128, 128)
GOLD = (184, 134, 11)
GREEN = (46, 125, 50)
PURP = (103, 58, 140)
BROWN = (121, 85, 72)
ORANGE = (214, 106, 0)

# ---------------------------------------------------------------- PNG writer
def _chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)


def write_png(path, px, w, h):
    raw = b"".join(b"\x00" + bytes(px[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    data = b"\x89PNG\r\n\x1a\n"
    data += _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    data += _chunk(b"IDAT", zlib.compress(raw, 9))
    data += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)


# ------------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        self.rect(0, 0, w, h, bg)

    def _set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(self.w, int(x + w)), min(self.h, int(y + h))
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                self.px[i], self.px[i + 1], self.px[i + 2] = c
                i += 3

    def circle(self, cx, cy, r, c):
        r = int(r)
        for yy in range(int(cy) - r, int(cy) + r + 1):
            for xx in range(int(cx) - r, int(cx) + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self._set(xx, yy, c)

    def tri(self, ax, ay, bx, by, cx, cy, c):
        x0 = max(0, int(min(ax, bx, cx)))
        x1 = min(self.w - 1, int(max(ax, bx, cx)) + 1)
        y0 = max(0, int(min(ay, by, cy)))
        y1 = min(self.h - 1, int(max(ay, by, cy)) + 1)
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if d == 0:
            return
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                w0 = ((by - cy) * (xx - cx) + (cx - bx) * (yy - cy)) / d
                w1 = ((cy - ay) * (xx - cx) + (ax - cx) * (yy - cy)) / d
                w2 = 1 - w0 - w1
                if w0 >= 0 and w1 >= 0 and w2 >= 0:
                    self._set(xx, yy, c)

    def poly(self, pts, c):
        """Even-odd scanline fill for a simple polygon (list of (x, y))."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0, y1 = max(0, int(min(ys))), min(self.h - 1, int(max(ys)))
        n = len(pts)
        for yy in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, y0p = pts[i]
                x1, y1p = pts[(i + 1) % n]
                if (y0p <= yy < y1p) or (y1p <= yy < y0p):
                    xs.append(x0 + (yy - y0p) * (x1 - x0) / (y1p - y0p))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for xx in range(max(0, int(xs[k])), min(self.w - 1, int(xs[k + 1])) + 1):
                    self._set(xx, yy, c)

    def thick_line(self, x0, y0, x1, y1, w, c):
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        if ln < 0.001:
            self.circle(int(x0), int(y0), max(1, int(w / 2)), c)
            return
        nx, ny = -dy / ln * w / 2, dx / ln * w / 2
        self.poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                   (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], c)
        self.circle(int(x0), int(y0), max(1, int(w / 2)), c)
        self.circle(int(x1), int(y1), max(1, int(w / 2)), c)

    def polyline(self, pts, w, c):
        for i in range(len(pts) - 1):
            self.thick_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], w, c)


# ------------------------------------------------------------- font geometry
# Glyph space: 1000-unit em, baseline y=0, x-height 500, cap height 700,
# ascender 750, descender -250. Angles in font space: 0=east, 90=north(up),
# 180=west, 270=south(down). Strokes: ('l',x0,y0,x1,y1) line, ('a',cx,cy,rx,ry,a0,a1)
# arc, ('d',x,y,r) filled dot. Widths are applied by the renderer per face.
G = {}

# --- lowercase -------------------------------------------------------------
G['a'] = [('a', 280, 250, 220, 250, 0, 360), ('l', 500, 500, 500, 0)]
G['b'] = [('l', 180, 750, 180, 0), ('a', 360, 250, 180, 250, 0, 360)]
G['c'] = [('a', 300, 250, 220, 250, 60, 300)]
G['d'] = [('a', 340, 250, 180, 250, 0, 360), ('l', 520, 750, 520, 0)]
G['e'] = [('a', 300, 250, 220, 250, 45, 315), ('l', 80, 250, 520, 250)]
G['f'] = [('l', 300, 540, 300, 0), ('a', 300, 620, 130, 80, 270, 360),
          ('l', 200, 500, 440, 500)]
G['g'] = [('a', 300, 250, 220, 250, 0, 360), ('l', 520, 250, 520, -100),
          ('a', 300, -100, 220, 150, 0, -180)]
G['h'] = [('l', 180, 750, 180, 0), ('a', 360, 250, 180, 250, 180, 0),
          ('l', 540, 250, 540, 0)]
G['i'] = [('l', 300, 500, 300, 0), ('d', 300, 640, 45)]
G['j'] = [('l', 300, 500, 300, -100), ('a', 300, -100, 120, 80, 270, 180),
          ('d', 300, 640, 45)]
G['k'] = [('l', 180, 750, 180, 0), ('l', 480, 500, 200, 250), ('l', 240, 250, 480, 0)]
G['l'] = [('l', 300, 750, 300, 0)]
G['m'] = [('l', 180, 500, 180, 0), ('a', 330, 250, 150, 250, 180, 0),
          ('l', 480, 250, 480, 0), ('a', 630, 250, 150, 250, 180, 0),
          ('l', 780, 250, 780, 0)]
G['n'] = [('l', 180, 500, 180, 0), ('a', 360, 250, 180, 250, 180, 0),
          ('l', 540, 250, 540, 0)]
G['o'] = [('a', 300, 250, 220, 250, 0, 360)]
G['p'] = [('l', 180, 250, 180, -250), ('a', 360, 250, 180, 250, 0, 360)]
G['q'] = [('a', 340, 250, 180, 250, 0, 360), ('l', 520, 250, 520, -250)]
G['r'] = [('l', 180, 500, 180, 0), ('a', 360, 400, 180, 100, 90, 0)]
G['s'] = [('a', 300, 375, 220, 125, 90, 270), ('a', 300, 125, 220, 125, 270, 450)]
G['t'] = [('l', 300, 600, 300, 80), ('a', 300, 80, 130, 80, 270, 360),
          ('l', 140, 480, 460, 480)]
G['u'] = [('l', 180, 500, 180, 80), ('a', 360, 80, 180, 80, 180, 360),
          ('l', 540, 500, 540, 80)]
G['v'] = [('l', 120, 500, 300, 0), ('l', 300, 0, 480, 500)]
G['w'] = [('l', 80, 500, 200, 0), ('l', 200, 0, 320, 500),
          ('l', 320, 500, 440, 0), ('l', 440, 0, 560, 500)]
G['x'] = [('l', 120, 500, 480, 0), ('l', 480, 500, 120, 0)]
G['y'] = [('l', 120, 500, 300, 150), ('l', 480, 500, 300, 150),
          ('l', 300, 150, 180, -250)]
G['z'] = [('l', 120, 500, 480, 500), ('l', 480, 500, 120, 0), ('l', 120, 0, 480, 0)]

# --- uppercase -------------------------------------------------------------
G['A'] = [('l', 100, 0, 300, 700), ('l', 300, 700, 500, 0), ('l', 180, 280, 420, 280)]
G['B'] = [('l', 150, 700, 150, 0), ('a', 330, 525, 180, 175, 0, 360),
          ('a', 350, 175, 200, 175, 0, 360)]
G['C'] = [('a', 320, 350, 240, 350, 60, 300)]
G['D'] = [('l', 150, 700, 150, 0), ('a', 330, 350, 200, 350, 0, 360)]
G['E'] = [('l', 150, 700, 150, 0), ('l', 150, 700, 500, 700),
          ('l', 150, 350, 450, 350), ('l', 150, 0, 500, 0)]
G['F'] = [('l', 150, 700, 150, 0), ('l', 150, 700, 500, 700), ('l', 150, 350, 450, 350)]
G['G'] = [('a', 330, 350, 240, 350, 60, 300), ('l', 430, 350, 570, 350),
          ('l', 570, 350, 570, 200)]
G['H'] = [('l', 150, 700, 150, 0), ('l', 550, 700, 550, 0), ('l', 150, 350, 550, 350)]
G['I'] = [('l', 300, 700, 300, 0), ('l', 200, 700, 400, 700), ('l', 200, 0, 400, 0)]
G['J'] = [('l', 200, 700, 500, 700), ('l', 420, 700, 420, 120),
          ('a', 300, 120, 120, 120, 0, -180)]
G['K'] = [('l', 150, 700, 150, 0), ('l', 520, 700, 220, 350), ('l', 260, 350, 520, 0)]
G['L'] = [('l', 150, 700, 150, 0), ('l', 150, 0, 520, 0)]
G['M'] = [('l', 120, 700, 120, 0), ('l', 120, 700, 350, 250),
          ('l', 350, 250, 580, 700), ('l', 580, 700, 580, 0)]
G['N'] = [('l', 120, 700, 120, 0), ('l', 120, 700, 580, 0), ('l', 580, 700, 580, 0)]
G['O'] = [('a', 350, 350, 240, 350, 0, 360)]
G['P'] = [('l', 150, 700, 150, 0), ('a', 330, 525, 200, 175, 0, 360)]
G['Q'] = [('a', 350, 350, 240, 350, 0, 360), ('l', 480, 150, 620, -50)]
G['R'] = [('l', 150, 700, 150, 0), ('a', 330, 525, 200, 175, 0, 360),
          ('l', 300, 350, 560, 0)]
G['S'] = [('a', 350, 525, 220, 175, 90, 270), ('a', 350, 175, 220, 175, 270, 450)]
G['T'] = [('l', 100, 700, 600, 700), ('l', 350, 700, 350, 0)]
G['U'] = [('l', 150, 700, 150, 80), ('a', 350, 80, 200, 80, 180, 360),
          ('l', 550, 700, 550, 80)]
G['V'] = [('l', 120, 700, 350, 0), ('l', 350, 0, 580, 700)]
G['W'] = [('l', 80, 700, 200, 0), ('l', 200, 0, 320, 700),
          ('l', 320, 700, 440, 0), ('l', 440, 0, 560, 700)]
G['X'] = [('l', 120, 700, 580, 0), ('l', 580, 700, 120, 0)]
G['Y'] = [('l', 120, 700, 350, 350), ('l', 580, 700, 350, 350), ('l', 350, 350, 350, 0)]
G['Z'] = [('l', 120, 700, 580, 700), ('l', 580, 700, 120, 0), ('l', 120, 0, 580, 0)]

# --- digits ----------------------------------------------------------------
G['0'] = [('a', 275, 350, 210, 350, 0, 360)]
G['1'] = [('l', 180, 560, 300, 700), ('l', 300, 700, 300, 0), ('l', 180, 0, 420, 0)]
G['2'] = [('a', 300, 500, 220, 200, 90, -45), ('l', 455, 360, 80, 0),
          ('l', 80, 0, 520, 0)]
G['3'] = [('a', 300, 525, 200, 175, 90, -90), ('a', 300, 175, 200, 175, 90, -90)]
G['4'] = [('l', 400, 700, 120, 200), ('l', 120, 200, 520, 200), ('l', 400, 700, 400, 0)]
G['5'] = [('l', 120, 700, 480, 700), ('l', 120, 700, 120, 400),
          ('a', 300, 200, 200, 200, 90, -90)]
G['6'] = [('a', 300, 350, 200, 350, 45, 315), ('a', 300, 175, 200, 175, 0, 360)]
G['7'] = [('l', 120, 700, 520, 700), ('l', 520, 700, 200, 0)]
G['8'] = [('a', 300, 500, 190, 200, 0, 360), ('a', 300, 175, 210, 175, 0, 360)]
G['9'] = [('a', 300, 525, 200, 175, 0, 360), ('l', 500, 525, 500, 50),
          ('a', 300, 200, 200, 150, 0, -90)]

# --- punctuation -----------------------------------------------------------
G['.'] = [('d', 300, 0, 50)]
G[','] = [('d', 300, 0, 50), ('l', 300, 0, 220, -200)]
G[':'] = [('d', 300, 150, 50), ('d', 300, 450, 50)]
G[';'] = [('d', 300, 150, 50), ('d', 300, 450, 50), ('l', 300, 150, 220, -50)]
G['!'] = [('l', 300, 700, 300, 150), ('d', 300, 0, 50)]
G['?'] = [('a', 300, 500, 200, 200, 90, -45), ('l', 300, 300, 300, 150),
          ('d', 300, 0, 50)]
G["'"] = [('l', 280, 700, 340, 500)]
G['"'] = [('l', 220, 700, 280, 500), ('l', 380, 700, 440, 500)]
G['('] = [('a', 420, 350, 180, 350, 60, 300)]
G[')'] = [('a', 180, 350, 180, 350, 240, 480)]
G['-'] = [('l', 120, 250, 480, 250)]
G['–'] = [('l', 100, 250, 500, 250)]
G['—'] = [('l', 60, 250, 540, 250)]
G['&'] = [('a', 300, 500, 200, 150, 90, 270), ('a', 300, 175, 200, 175, 270, 90),
          ('l', 120, 0, 480, 700)]
G['%'] = [('a', 200, 550, 130, 150, 0, 360), ('a', 400, 150, 130, 150, 0, 360),
          ('l', 100, 100, 500, 600)]
G['$'] = [('a', 300, 525, 220, 175, 90, 270), ('a', 300, 175, 220, 175, 270, 90),
          ('l', 300, 750, 300, -50)]
G['€'] = [('a', 340, 350, 240, 350, 60, 300), ('l', 100, 450, 500, 450),
          ('l', 100, 250, 500, 250)]
G['£'] = [('l', 320, 540, 320, 0), ('a', 320, 620, 130, 80, 270, 360),
          ('l', 140, 250, 500, 250), ('l', 160, 0, 480, 0)]
G['/'] = [('l', 200, -50, 400, 750)]
G['·'] = [('d', 300, 250, 45)]
G['+'] = [('l', 120, 350, 480, 350), ('l', 300, 530, 300, 170)]
G['='] = [('l', 120, 450, 480, 450), ('l', 120, 250, 480, 250)]
G['~'] = [('a', 200, 350, 120, 100, 180, 360), ('a', 400, 350, 120, 100, 0, 180)]
G['×'] = [('l', 150, 500, 450, 200), ('l', 450, 500, 150, 200)]
G['°'] = [('a', 300, 550, 90, 90, 0, 360)]
G['’'] = [('l', 280, 700, 340, 500)]
G['‘'] = [('l', 320, 700, 260, 500)]
G['“'] = [('l', 220, 700, 280, 500), ('l', 380, 700, 440, 500)]
G['”'] = [('l', 220, 700, 280, 500), ('l', 380, 700, 440, 500)]
G[' '] = []


def _glyph_right(ch):
    mx = 0
    for s in G.get(ch, []):
        if s[0] == 'l':
            mx = max(mx, s[1], s[3])
        elif s[0] == 'a':
            mx = max(mx, s[1] + s[3])
        elif s[0] == 'd':
            mx = max(mx, s[1] + s[3])
    return mx


_ADV = {}
for _ch, _st in G.items():
    if _ch == ' ':
        _ADV[_ch] = 300
    else:
        _ADV[_ch] = max(560, _glyph_right(_ch) + 70)
_ADV[' '] = 300
_ADV['i'] = 400
_ADV['j'] = 400
_ADV['l'] = 400
_ADV['I'] = 420
_ADV['.'] = 380
_ADV[','] = 380
_ADV[':'] = 380
_ADV[';'] = 380
_ADV['!'] = 420
_ADV['?'] = 620
_ADV["'"] = 300
_ADV['’'] = 300
_ADV['‘'] = 300
_ADV['"'] = 560
_ADV['“'] = 560
_ADV['”'] = 560
_ADV['('] = 480
_ADV[')'] = 480
_ADV['-'] = 620
_ADV['–'] = 620
_ADV['—'] = 620
_ADV['/'] = 620
_ADV['·'] = 380
_ADV['+'] = 620
_ADV['='] = 620
_ADV['%'] = 760
_ADV['$'] = 640
_ADV['€'] = 700
_ADV['£'] = 640
_ADV['&'] = 700
_ADV['~'] = 620
_ADV['×'] = 620
_ADV['°'] = 360

# ------------------------------------------------------------- font rendering
def _arc_pts(cx, cy, rx, ry, a0, a1):
    n = max(4, int(abs(a1 - a0) / 12) + 1)
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def _stroke_width(kind, stroke, face):
    if face == 'sans':
        return 72
    if face == 'sans-bold':
        return 118
    if face == 'serif':
        if kind == 'l':
            dx = abs(stroke[3] - stroke[1])
            dy = abs(stroke[4] - stroke[2])
            if dx < dy * 0.3:
                return 132
            if dy < dx * 0.3:
                return 46
            return 88
        return 92
    if face == 'serif-bold':
        if kind == 'l':
            dx = abs(stroke[3] - stroke[1])
            dy = abs(stroke[4] - stroke[2])
            if dx < dy * 0.3:
                return 150
            if dy < dx * 0.3:
                return 58
            return 104
        return 108
    return 72


def _draw_glyph(cv, ch, ox, oy, size, face, color, shear=0.0):
    """Draw one glyph; ox,oy = origin in px (baseline point). y is up in font
    space, down on screen. shear shifts x by shear*(font y) for italics."""
    s = size / 1000.0
    strokes = G.get(ch)
    if not strokes:
        return
    for st in strokes:
        kind = st[0]
        w = _stroke_width(kind, st, face) * s
        if kind == 'l':
            _, x0, y0, x1, y1 = st
            p0 = (ox + (x0 + shear * y0) * s, oy - y0 * s)
            p1 = (ox + (x1 + shear * y1) * s, oy - y1 * s)
            cv.thick_line(p0[0], p0[1], p1[0], p1[1], max(1.0, w), color)
            if face.startswith('serif') and abs(x1 - x0) < abs(y1 - y0) * 0.3:
                # serif ticks at both ends of a near-vertical stem
                for (ex, ey) in ((x0, y0), (x1, y1)):
                    cxp = ox + (ex + shear * ey) * s
                    cyp = oy - ey * s
                    cv.thick_line(cxp - 46 * s, cyp, cxp + 46 * s, cyp,
                                  max(1.0, 40 * s), color)
        elif kind == 'a':
            _, cx, cy, rx, ry, a0, a1 = st
            pts = _arc_pts(cx, cy, rx, ry, a0, a1)
            sp = [(ox + (px + shear * py) * s, oy - py * s) for (px, py) in pts]
            cv.polyline(sp, max(1.0, w), color)
        elif kind == 'd':
            _, dx, dy, r = st
            cv.circle(ox + (dx + shear * dy) * s, oy - dy * s, max(1.0, r * s), color)


def text_width(s, size, face='sans'):
    sc = size / 1000.0
    return sum(_ADV.get(ch, 600) * sc for ch in s)


def draw_text(cv, s, x, y, size, face='sans', color=INK, shear=0.0):
    """Draw s with baseline at y (screen coords, y down)."""
    sc = size / 1000.0
    cx = x
    for ch in s:
        _draw_glyph(cv, ch, cx, y, size, face, color, shear)
        cx += _ADV.get(ch, 600) * sc
    return cx


def wrap_words(cv, text, size, max_w, face='sans'):
    words = text.split(' ')
    lines, cur = [], ''
    for wd in words:
        trial = wd if not cur else cur + ' ' + wd
        if text_width(trial, size, face) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_block(cv, text, x, y, max_w, size, face='sans', color=INK,
               align='l', leading=None, shear=0.0):
    """Draw wrapped text; returns y just below the last line."""
    if leading is None:
        leading = size * 1.28
    for ln in wrap_words(cv, text, size, max_w, face):
        w = text_width(ln, size, face)
        lx = x + (max_w - w) / 2 if align == 'c' else (
            x + max_w - w if align == 'r' else x)
        draw_text(cv, ln, lx, y, size, face, color, shear)
        y += leading
    return y

# ------------------------------------------------------------- font test sheet
def render_test(cv):
    y = 60
    draw_text(cv, "SERIF 50", 30, y, 16, 'sans-bold', RED)
    y += 30
    draw_text(cv, "Saturday 21 November 2026", 30, y, 50, 'serif', INK)
    y += 70
    draw_text(cv, "THE WORLD IN ONE DAY", 30, y, 34, 'serif', NAVY)
    y += 60
    draw_text(cv, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", 30, y, 26, 'serif', INK)
    y += 40
    draw_text(cv, "abcdefghijklmnopqrstuvwxyz", 30, y, 26, 'serif', INK)
    y += 40
    draw_text(cv, "0123456789 . , : ; ! ? ' \" ( ) - $ % /", 30, y, 26, 'serif', INK)
    y += 70
    draw_text(cv, "SANS-BOLD 20 — headline check", 30, y, 14, 'sans-bold', RED)
    y += 26
    draw_text(cv, "Three missiles downed over Riyadh", 30, y, 20, 'sans-bold', INK)
    y += 34
    draw_text(cv, "COP31 runs into overtime with no deal", 30, y, 20, 'sans-bold', INK)
    y += 34
    draw_text(cv, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", 30, y, 20, 'sans-bold', INK)
    y += 34
    draw_text(cv, "abcdefghijklmnopqrstuvwxyz", 30, y, 20, 'sans-bold', INK)
    y += 34
    draw_text(cv, "0123456789 . , : ; ! ? $ % & / -", 30, y, 20, 'sans-bold', INK)
    y += 60
    draw_text(cv, "SANS 12 — body check", 30, y, 14, 'sans-bold', RED)
    y += 24
    draw_text(cv, "Saudi defences intercept three ballistic missiles fired", 30, y, 12, 'sans', INK)
    y += 22
    draw_text(cv, "towards Riyadh early on Saturday; no damage or casualties.", 30, y, 12, 'sans', INK)
    y += 22
    draw_text(cv, "abcdefghijklmnopqrstuvwxyz 0123456789", 30, y, 12, 'sans', INK)
    y += 22
    draw_text(cv, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", 30, y, 12, 'sans', INK)
    y += 22
    draw_text(cv, "The quick brown fox jumps over the lazy dog. 1234567890", 30, y, 12, 'sans', INK)
    y += 40
    draw_text(cv, "ITALIC 13 — sub-headline check", 30, y, 14, 'sans-bold', RED)
    y += 26
    draw_text(cv, "Riyadh intercepts three missiles - COP31 into overtime -", 30, y, 13, 'sans', INK, shear=0.18)
    y += 24
    draw_text(cv, "BepiColombo at Mercury - Rutte in Warsaw", 30, y, 13, 'sans', INK, shear=0.18)
    return y

# ------------------------------------------------------------- illustrations
def _skyline(cv, x, y, w, h, base, cols, seed=0):
    import random as _r
    rnd = _r.Random(seed)
    bx = x
    while bx < x + w - 8:
        bw = rnd.randint(14, 30)
        bh = rnd.randint(int(h * 0.35), int(h * 0.95))
        cv.rect(bx, y + h - bh, bw, bh, cols[rnd.randrange(len(cols))])
        for wy in range(int(y + h - bh + 4), int(y + h - 4), 9):
            for wx in range(int(bx + 3), int(bx + bw - 3), 7):
                if rnd.random() < 0.45:
                    cv.rect(wx, wy, 3, 4, GOLD)
        bx += bw + 2


def _burst(cv, cx, cy, r, col):
    for a in range(0, 360, 30):
        ar = math.radians(a)
        cv.thick_line(cx, cy, cx + r * math.cos(ar), cy + r * math.sin(ar), 2.5, col)
    cv.circle(cx, cy, max(2, int(r * 0.28)), col)


def art(cv, kind, x, y, w, h):
    if kind == 'riyadh':
        cv.rect(x, y, w, h, (16, 22, 48))
        cv.circle(x + w - 28, y + 22, 13, (240, 230, 190))
        _skyline(cv, x, y + h - 62, w, 62, y + h, [(38, 44, 74), (52, 58, 92)], 7)
        for (tx, ty, ang) in ((x + 60, y + 78, -32), (x + 150, y + 62, -18), (x + 240, y + 84, -40)):
            ex = tx + 55 * math.cos(math.radians(ang))
            ey = ty + 55 * math.sin(math.radians(ang))
            cv.thick_line(tx, ty, ex, ey, 2.5, (255, 220, 120))
            _burst(cv, tx, ty, 9, (255, 210, 90))
    elif kind == 'cop31':
        cv.rect(x, y, w, h, (14, 90, 96))
        cv.circle(x + 62, y + h // 2, 40, (38, 110, 180))
        cv.poly([(x + 42, y + 34), (x + 58, y + 30), (x + 70, y + 44), (x + 52, y + 62),
                 (x + 40, y + 52)], (46, 160, 90))
        cv.poly([(x + 74, y + 58), (x + 92, y + 54), (x + 96, y + 70), (x + 80, y + 78)], (46, 160, 90))
        cv.rect(x + w - 46, y + 14, 10, h - 28, (240, 240, 230))
        cv.rect(x + w - 46, y + h - 40, 10, 26, RED)
        cv.circle(x + w - 41, y + h - 14, 9, RED)
        for i, col in enumerate((RED, (240, 240, 230), BLUE)):
            cv.rect(x + 130 + i * 26, y + 16, 20, 12, col)
    elif kind == 'mercury':
        cv.rect(x, y, w, h, (10, 14, 34))
        for (sx, sy) in ((30, 20), (90, 44), (150, 16), (210, 36), (270, 22), (60, 90), (250, 84)):
            cv.circle(x + sx, y + sy, 1.5, (255, 255, 255))
        cv.circle(x + 22, y + 20, 10, (250, 200, 80))
        cv.circle(x + 120, y + h // 2 + 6, 44, (150, 138, 122))
        for (cx, cy, cr) in ((100, 52, 7), (138, 78, 5), (112, 96, 9), (150, 58, 4)):
            cv.circle(x + cx, y + cy, cr, (120, 110, 96))
        cv.rect(x + 205, y + 30, 46, 20, (210, 210, 200))
        cv.rect(x + 195, y + 34, 10, 12, (120, 140, 200))
        cv.rect(x + 251, y + 34, 10, 12, (120, 140, 200))
        cv.thick_line(x + 205, y + 40, x + 168, y + 58, 2.5, (255, 210, 90))
    elif kind == 'poland':
        cv.rect(x, y, w, h, (24, 30, 64))
        cv.rect(x + 12, y + 10, 34, 10, (245, 245, 245))
        cv.rect(x + 12, y + 20, 34, 10, RED)
        cv.thick_line(x + 60, y + 34, x + w - 30, y + 12, 2.5, (255, 220, 120))
        _burst(cv, x + w - 28, y + 12, 8, (255, 210, 90))
        _skyline(cv, x, y + h - 16, w, 16, y + h, [(40, 44, 70)], 3)
    elif kind == 'kyiv':
        cv.rect(x, y, w, h, (14, 18, 44))
        _skyline(cv, x, y + h - 30, w, 30, y + h, [(36, 40, 68), (50, 54, 84)], 11)
        _burst(cv, x + w // 2, y + 16, 11, (255, 190, 60))
        cv.thick_line(x + 20, y + h - 8, x + w - 20, y + h - 8, 3, (200, 200, 190))
    elif kind == 'denmark':
        cv.rect(x, y, w, h, (240, 235, 220))
        cv.circle(x + w // 2, y + h // 2, 18, RED)
        cv.circle(x + w // 2, y + h // 2, 11, (240, 235, 220))
        cv.circle(x + w // 2, y + h // 2, 4, RED)
        cv.rect(x + 12, y + 8, 26, 8, RED)
        cv.rect(x + 12, y + 16, 26, 8, (245, 245, 245))
    elif kind == 'hormuz':
        cv.rect(x, y, w, h, (16, 60, 110))
        cv.rect(x + 8, y + h - 18, w - 16, 10, (30, 30, 30))
        cv.rect(x + w // 2 - 14, y + h - 30, 28, 12, (200, 200, 190))
        cv.poly([(x + w // 2 - 6, y + 8), (x + w // 2 + 6, y + 8), (x + w // 2 + 2, y + 22),
                 (x + w // 2 - 2, y + 22)], (255, 170, 40))
        cv.poly([(x + w // 2 - 3, y + 14), (x + w // 2 + 3, y + 14), (x + w // 2, y + 24)], RED)
    elif kind == 'markets':
        cv.rect(x, y, w, h, (245, 243, 235))
        base = y + h - 8
        vals = [0.5, 0.72, 0.6, 0.85, 0.62, 0.4, 0.28]
        bw = w // 8
        for i, v in enumerate(vals):
            cx = x + 8 + i * bw
            col = GREEN if i in (0, 2) else RED
            cv.rect(cx, base - int(v * (h - 16)), 5, int(v * (h - 16)), col)
            cv.thick_line(cx + 2, base - int(v * (h - 16)) - 4, cx + 2, base + 2, 1.5, col)
    elif kind == 'eu':
        cv.rect(x, y, w, h, (24, 48, 120))
        for i in range(12):
            a = math.radians(i * 30)
            cv.circle(x + w // 2 + int(15 * math.cos(a)), y + h // 2 + int(15 * math.sin(a)),
                      2, GOLD)
        cv.circle(x + w // 2, y + h // 2, 4, GOLD)
    elif kind == 'n0n':
        cv.rect(x, y, w, h, (20, 20, 26))
        cv.rect(x + w // 2 - 12, y + h // 2 - 4, 24, 18, GOLD)
        cv.poly([(x + w // 2 - 8, y + h // 2 - 4), (x + w // 2 - 8, y + h // 2 - 14),
                 (x + w // 2 + 8, y + h // 2 - 14), (x + w // 2 + 8, y + h // 2 - 4)], GOLD)
        cv.circle(x + w // 2, y + h // 2 + 5, 3, (20, 20, 26))
    elif kind == 'akvan':
        cv.rect(x, y, w, h, (190, 220, 235))
        cx, cy = x + w // 2, y + h // 2
        for i in range(0, 540, 18):
            a = math.radians(i)
            r = 3 + i * 0.035
            cv.circle(cx + int(r * math.cos(a)), cy + int(r * math.sin(a)), 2.5, (20, 90, 140))
        cv.circle(cx, cy, 4, (20, 90, 140))
    elif kind == 'anthropic':
        cv.rect(x, y, w, h, (245, 240, 225))
        draw_text(cv, "$93.5bn", x + 8, y + 26, 15, 'sans-bold', (150, 90, 20))
        cv.rect(x + 8, y + h - 16, 78, 11, RED)
        draw_text(cv, "CLAIM ONLY", x + 11, y + h - 7, 7.5, 'sans-bold', (255, 255, 255))
    elif kind == 'irancost':
        cv.rect(x, y, w, h, (245, 243, 235))
        vals = [0.25, 0.45, 0.7, 1.0]
        bw = w // 5
        for i, v in enumerate(vals):
            cv.rect(x + 10 + i * bw, y + h - 6 - int(v * (h - 14)), 12,
                    int(v * (h - 14)), NAVY if i < 3 else RED)

# ------------------------------------------------------------- page content
LEADS = [
    ('riyadh', '1 RIYADH · CONFLICT',
     'Three missiles downed over Riyadh',
     'Saudi defences intercept three ballistic missiles fired towards Riyadh '
     'early on Saturday; two explosions heard in the capital. No damage or '
     'casualties.',
     'Reuters · AFP'),
    ('cop31', '2 ANTALYA · CLIMATE',
     'COP31 runs into overtime with no deal',
     'Talks pass their Friday close with no deal; a third draft is due '
     'Saturday morning. It cuts 144 paragraphs to 80, dropping the $120bn '
     'target.',
     'AP · Reuters · AFP'),
    ('mercury', '3 MERCURY · SPACE',
     'BepiColombo reaches Mercury after eight years',
     'The ESA-JAXA craft fires four thrusters for 37 minutes at 19:24 CET to '
     'be captured by Mercury. First mission to put two orbiters around '
     'Mercury.',
     'ESA · Sky & Telescope'),
]

CARDS = [
    ('poland', '4 WARSAW · SECURITY', 'Russian missiles land in Poland',
     'Two missiles and a drone crash in the south-east; no injuries.',
     'AP · Reuters'),
    ('kyiv', '5 KYIV · WAR', 'Russia\u2019s biggest strike hits Kyiv',
     '400+ drones, 110+ missiles; 12 killed, 82 hurt. Three bridges hit.',
     'Reuters'),
    ('denmark', '6 COPENHAGEN · SECURITY', 'Denmark foils \u2018Russian plot\u2019 to kill rapper',
     '3 arrested, 2 charged Friday; Russia\u2019s defence attach\u00e9 ordered out '
     'in 7 days.', 'Reuters'),
    ('hormuz', '7 STRAIT OF HORMUZ · SHIPPING', 'Tanker hit by projectile catches fire',
     'Fire on board, no casualties. Transits down 15% on the week.', 'UKMTO'),
    ('markets', '8 NEW YORK · MARKETS', 'Wall Street enters correction; Nasdaq -5.28%',
     'S&P -3.70%, 7th straight fall. Gold -4.62% (futures); Bitcoin below '
     '$60,000.', 'Reuters'),
    ('eu', '9 BRUSSELS · AID', 'EU approves \u20ac1bn more military aid',
     'Joint procurement of drones, air defence and ammunition, delivered by '
     'end-2027.', 'European Council'),
    ('n0n', '10 NEW YORK · CYBER', 'Hackers leak JPMorgan, Visa, Mastercard data',
     '\u2018n0n\u2019 claims the theft; 16,000 JPMorgan emails found. No card '
     'numbers.', 'Reuters'),
    ('akvan', '11 GOPALPUR · WEATHER', 'Cyclone Akvan weakens after landfall',
     'Winds gust to 110 km/h; 300,000+ evacuated. No deaths reported.', 'IMD'),
    ('anthropic', '12 SAN FRANCISCO · TECH', 'Anthropic IPO closes at $93.5bn',
     'Largest IPO on record; shares closed $88.30, down ~9%. Riemann: CLAIM '
     'ONLY.', 'The Big Ant'),
    ('irancost', '13 WASHINGTON · WAR COSTS', 'US war against Iran has cost $48.3bn',
     'Pentagon: the campaign cost $48.3bn as of 13 Nov, excluding base damage.',
     'AP'),
]

BRIEFS = [
    ('14 BRUSSELS', 'EU pays Ukraine \u20ac7.9bn, largest ever', 'European Commission'),
    ('15 NEW YORK', 'Gupta jailed 235 months in Sikh plot case', 'US DOJ'),
    ('16 JOHANNESBURG', '581 women killed in three months', 'SAPS'),
    ('17 PERTH', 'Starc takes 7/58 as England fold for 172', 'ANI'),
    ('18 WELLINGTON', 'India fight back 159/1 after NZ 368', 'Cricbuzz'),
    ('19 KUALA LUMPUR', 'India U17 draw 0-0, qualify for Asian Cup', 'AFC'),
    ('20 VIRGINIA', 'First US measles death of 2026, a child aged 0-4', 'VDH'),
    ('21 TOKYO', 'Japan to buy up to 8M barrels of Saudi oil', 'Bloomberg'),
    ('22 SANAA', 'Coalition says it hit 6 Houthi workshops', 'Coalition claim'),
    ('23 NEW YORK', 'GTA VI makes $3.79bn in day one, a record', 'Take-Two'),
    ('24 WASHINGTON', 'Trump: \u201ctremendous tax\u201d on AI centres abroad', 'Reuters'),
    ('25 BRUSSELS', 'UK-EU reset deal sealed; youth scheme, 100,000 visas', 'Reuters'),
    ('26 NEW ORLEANS', '5th Circuit voids $1.7tn spending bill; Trump pardons Pete Rose', 'Reuters'),
    ('27 NEW YORK', 'Mamdani unveils plan to close Rikers by 2032', 'BBC'),
    ('28 WASHINGTON', 'US declassifies more UFO footage', 'BBC'),
    ('29 LONDON', 'Lauren Price becomes undisputed welterweight champion', 'BBC'),
    ('30 NEW YORK', 'UNICEF: 1,144 children killed or injured in Ukraine', 'UNICEF'),
    ('31 TALLINN', 'Estonia to close road borders with Russia', 'Kyiv Independent'),
    ('32 WASHINGTON', 'US adds 4 Iranians to sanctions list', 'US Treasury'),
    ('33 BRASILIA', 'Lula strengthens Indigenous land protection', 'Wire'),
    ('34 KATHMANDU', 'Nepal PM Shah to meet India\u2019s Modi', 'BBC'),
    ('35 JOHANNESBURG', 'South Africa local elections; ANC fights for cities', 'BBC'),
    ('36 WASHINGTON', 'US cleared ~900,000 AI chips for China', 'House committee'),
    ('37 MUMBAI', 'IndusInd Bank sacks ex-CEO, seeks pay clawback', 'Reuters'),
    ('38 WASHINGTON', 'Senate rejects Iran war-powers resolution 48-51', 'Reuters'),
    ('39 FRANKFURT', 'Eurozone consumer confidence -16.9 in November', 'Reuters'),
    ('40 FRANKFURT', 'Deutsche Bank accidentally forwards Trump\u2019s tax return', 'Reuters'),
    ('41 LUANDA', 'Angola to pay ~$180m for 10% of De Beers', 'Reuters'),
    ('42 PARIS', 'French police sentenced over 2020 Zecler beating', 'Wire'),
]

NUMBERS = [
    ('3', 'missiles downed over Riyadh'),
    ('400+', 'drones fired at Ukraine'),
    ('92,000', 'people at COP31'),
    ('-5.28%', 'Nasdaq, Friday close'),
    ('\u20ac7.9bn', 'EU\u2019s largest-ever payment'),
    ('300,000+', 'evacuated before Akvan'),
]

REGIONS = [
    ('EUROPE', 12, BLUE), ('AMERICAS', 15, RED), ('ASIA', 5, GOLD),
    ('MIDEAST', 3, TEAL), ('AFRICA', 3, GREEN), ('OCEANIA', 2, PURP),
    ('WORLD', 2, BROWN),
]

CONTINENTS = [
    [(30, 8), (95, 4), (140, 10), (155, 28), (130, 42), (105, 38), (95, 52),
     (70, 48), (48, 28), (28, 18)],
    [(125, 56), (155, 52), (175, 62), (160, 74), (140, 76), (126, 64)],
    [(255, 10), (285, 6), (300, 16), (282, 28), (258, 24)],
    [(262, 34), (300, 32), (315, 48), (295, 68), (268, 66), (256, 50)],
    [(305, 8), (400, 4), (440, 14), (425, 38), (375, 48), (330, 38), (308, 22)],
    [(395, 60), (425, 56), (435, 66), (410, 72), (392, 68)],
]

PINS = [
    (1, 330, 42), (2, 290, 20), (4, 272, 14), (5, 292, 17), (6, 262, 8),
    (7, 338, 40), (8, 84, 24), (9, 258, 20), (10, 102, 34), (11, 375, 42),
    (12, 72, 36), (13, 94, 40),
]

# ------------------------------------------------------------- page assembly
def render_page(cv):
    # ---- v4 content: 36 stories (3 leads + 10 cards + 23 briefs) ----
    _nums = [
        ('0', 'climate deal agreed at COP31'),
        ('12', 'killed in Ukraine strikes'),
        ('42', 'injured in Kryvyi Rih strike'),
        ('3', 'missiles downed over Riyadh'),
        ('92,000', 'people at COP31, the largest'),
        ('300,000+', 'evacuated before Akvan'),
    ]
    _regs = [('EUROPE', 9, BLUE), ('AMERICAS', 14, RED), ('ASIA', 4, GOLD),
             ('MIDEAST', 3, TEAL), ('AFRICA', 2, GREEN), ('OCEANIA', 2, PURP),
             ('WORLD', 2, BROWN)]

    def _renum(kick, n):
        return str(n) + ' ' + kick.split(' ', 1)[1]

    _cop31 = LEADS[1]
    _riyadh = LEADS[0]
    _kyivc = CARDS[1]
    _bep = LEADS[2]
    _leads = [
        (_cop31[0], _renum(_cop31[1], 1), _cop31[2], _cop31[3], _cop31[4]),
        (_kyivc[0], _renum(_kyivc[1], 2), _kyivc[2],
         'Russia\u2019s biggest strike of the war: 400+ drones and 110+ missiles '
         'overnight; 12 killed, 82 hurt in Kyiv. Three bridges over the Dnipro '
         'damaged.', _kyivc[4]),
        (_riyadh[0], _renum(_riyadh[1], 3), _riyadh[2], _riyadh[3], _riyadh[4]),
    ]
    _cards = [
        (CARDS[0][0], _renum(CARDS[0][1], 4), CARDS[0][2], CARDS[0][3], CARDS[0][4]),
        (CARDS[2][0], _renum(CARDS[2][1], 5), CARDS[2][2], CARDS[2][3], CARDS[2][4]),
        (_bep[0], _renum(_bep[1], 6), _bep[2],
         'Capture burn 19:24 CET: four thrusters, 37 min. First two orbiters '
         'at Mercury.', _bep[4]),
        (CARDS[3][0], _renum(CARDS[3][1], 7), CARDS[3][2], CARDS[3][3], CARDS[3][4]),
        (CARDS[4][0], _renum(CARDS[4][1], 8), CARDS[4][2], CARDS[4][3], CARDS[4][4]),
        (CARDS[5][0], _renum(CARDS[5][1], 9), CARDS[5][2], CARDS[5][3], CARDS[5][4]),
        (CARDS[6][0], _renum(CARDS[6][1], 10), CARDS[6][2], CARDS[6][3], CARDS[6][4]),
        (CARDS[7][0], _renum(CARDS[7][1], 11), CARDS[7][2], CARDS[7][3], CARDS[7][4]),
        (CARDS[8][0], _renum(CARDS[8][1], 12), CARDS[8][2], CARDS[8][3], CARDS[8][4]),
        (CARDS[9][0], _renum(CARDS[9][1], 13), CARDS[9][2], CARDS[9][3], CARDS[9][4]),
    ]
    _briefs = BRIEFS[:23]
    _continents = [
        [(15, 12), (60, 6), (110, 10), (125, 22), (115, 36), (95, 48), (70, 44), (40, 40), (15, 26)],
        [(120, 50), (150, 46), (165, 58), (155, 76), (130, 76), (118, 62)],
        [(245, 8), (280, 6), (295, 15), (285, 26), (260, 28), (245, 18)],
        [(255, 33), (295, 30), (310, 44), (300, 66), (275, 70), (258, 52)],
        [(300, 6), (380, 4), (450, 10), (470, 22), (440, 35), (400, 40), (350, 35), (315, 26), (300, 15)],
        [(420, 58), (460, 55), (470, 66), (435, 70)],
    ]
    _pins = [(1, 290, 18), (2, 292, 15), (3, 330, 42), (4, 272, 12), (5, 262, 7),
             (7, 338, 40), (8, 84, 22), (9, 258, 18), (10, 102, 33), (11, 375, 42),
             (12, 72, 34), (13, 94, 38)]
    _dc = ['Kyiv bridges hit \u2014 Fri 20 Nov',
           'Cyclone Akvan landfall \u2014 Fri 20 Nov',
           'ICJ Myanmar ruling \u2014 Thu 19 Nov',
           'Shenzhen trilateral \u2014 Thu 19 Nov',
           'Anthropic $93.5bn IPO \u2014 Thu 19 Nov',
           'Wall Street correction \u2014 Fri 20 Nov']
    # top bar
    cv.rect(0, 0, W, 22, RED)
    draw_text(cv, 'THE WORLD IN ONE DAY', 10, 15, 11, 'sans-bold', (255, 255, 255))
    _tr = '36 STORIES \u00b7 7 REGIONS \u00b7 SATURDAY 21 NOVEMBER 2026'
    draw_text(cv, _tr, W - 10 - text_width(_tr, 11, 'sans-bold'), 15, 11, 'sans-bold', (255, 255, 255))
    # masthead (68px serif-bold, shrink to fit)
    _mt = 'Saturday 21 November 2026'
    _ms = 68
    while text_width(_mt, _ms, 'serif-bold') > 1004 and _ms > 40:
        _ms -= 1
    draw_text(cv, _mt, (W - text_width(_mt, _ms, 'serif-bold')) / 2, 92, _ms, 'serif-bold', NAVY)
    cv.rect(10, 100, 1004, 2, NAVY)
    cv.rect(10, 104, 1004, 1, NAVY)
    # sub-headline
    _sh = ('COP31 into overtime \u00b7 Russia\u2019s biggest strike hits Kyiv \u00b7 '
           'Riyadh intercepts three missiles \u00b7 BepiColombo at Mercury')
    draw_text(cv, _sh, (W - text_width(_sh, 13, 'sans')) / 2, 124, 13, 'sans', INK)
    # numbers strip
    _cw = (W - 20) / 6
    for i, (num, cap) in enumerate(_nums):
        _cx = 10 + i * _cw
        draw_text(cv, num, _cx + (_cw - text_width(num, 32, 'sans-bold')) / 2, 164, 32, 'sans-bold', NAVY)
        draw_text(cv, cap, _cx + (_cw - text_width(cap, 10, 'sans')) / 2, 180, 10, 'sans', GREY)
        if i:
            cv.rect(_cx, 134, 1, 48, LGREY)
    # region bar
    _tot = sum(c for _, c, _ in _regs)
    _rx = 10
    for name, cnt, col in _regs:
        _w = (W - 20) * cnt / _tot
        cv.rect(_rx, 186, _w, 16, col)
        _lab = name + ' ' + str(cnt)
        _ls = 9
        while text_width(_lab, _ls, 'sans-bold') > _w - 6 and _ls > 7:
            _ls -= 0.5
        draw_text(cv, _lab, _rx + (_w - text_width(_lab, _ls, 'sans-bold')) / 2, 198, _ls, 'sans-bold', (255, 255, 255))
        _rx += _w
    # leads
    _lw = (W - 20 - 2 * 12) / 3
    for i, (kind, kick, head, body, src) in enumerate(_leads):
        _x = 10 + i * (_lw + 12)
        _y = 208
        art(cv, kind, _x, _y, _lw, 150)
        if kind == 'cop31':
            cv.rect(_x + 128, _y + 18, 74, 18, RED)
            draw_text(cv, 'NO DEAL', _x + 145, _y + 31, 10, 'sans-bold', (255, 255, 255))
            cv.circle(_x + 175, _y + 95, 12, (255, 255, 255))
            cv.circle(_x + 195, _y + 90, 15, (255, 255, 255))
            cv.circle(_x + 215, _y + 97, 11, (255, 255, 255))
        if kind == 'kyiv':
            cv.circle(_x + 290, _y + 30, 12, (240, 235, 210))
            for _sx, _sy in [(30, 30), (70, 60), (110, 25), (210, 40), (250, 80), (300, 60), (60, 90), (190, 80)]:
                cv.circle(_x + _sx, _y + _sy, 2, (255, 210, 90))
        cv.rect(_x, _y + 150, _lw, 16, RED)
        draw_text(cv, kick, _x + 6, _y + 162, 10, 'sans-bold', (255, 255, 255))
        draw_block(cv, head, _x, _y + 186, _lw, 19, 'serif-bold', INK, leading=22)
        draw_block(cv, body, _x, _y + 232, _lw, 10.5, 'sans', INK, leading=13)
        draw_text(cv, src, _x, _y + 276, 9, 'sans', GREY)
    # cards
    _cw2 = (W - 20 - 4 * 6) / 5
    _cg = 6
    for i, (kind, kick, head, body, src) in enumerate(_cards):
        _row, _col = divmod(i, 5)
        _x = 10 + _col * (_cw2 + _cg)
        _y = 494 + _row * 148
        art(cv, kind, _x, _y, _cw2, 58)
        if kind == 'anthropic':
            cv.rect(_x, _y, _cw2, 58, PAPER)
            _big = '$93.5bn'
            draw_text(cv, _big, _x + (_cw2 - text_width(_big, 18, 'sans-bold')) / 2, _y + 26, 18, 'sans-bold', (150, 100, 20))
            _st = 'CLAIM ONLY'
            _sw = text_width(_st, 9, 'sans-bold') + 14
            cv.rect(_x + (_cw2 - _sw) / 2, _y + 36, _sw, 14, RED)
            draw_text(cv, _st, _x + (_cw2 - text_width(_st, 9, 'sans-bold')) / 2, _y + 46, 9, 'sans-bold', (255, 255, 255))
        draw_text(cv, kick, _x, _y + 70, 8.5, 'sans-bold', RED)
        draw_block(cv, head, _x, _y + 86, _cw2, 12, 'sans-bold', INK, leading=14)
        draw_block(cv, body, _x, _y + 112, _cw2, 8.5, 'sans', INK, leading=11.5)
        draw_text(cv, src, _x, _y + 140, 8, 'sans', GREY)
    # dotted map + date check
    _my = 800

    def _inside(px, py, poly):
        _ins = False
        _j = len(poly) - 1
        for _i in range(len(poly)):
            _xi, _yi = poly[_i]
            _xj, _yj = poly[_j]
            if ((_yi > py) != (_yj > py)) and (px < (_xj - _xi) * (py - _yi) / (_yj - _yi) + _xi):
                _ins = not _ins
            _j = _i
        return _ins

    draw_text(cv, 'WHERE IT HAPPENED', 10, _my + 12, 9, 'sans-bold', NAVY)
    for _gy in range(0, 68, 5):
        for _gx in range(0, 490, 5):
            for _poly in _continents:
                if _inside(_gx, _gy, _poly):
                    cv.circle(10 + _gx, _my + 14 + _gy, 1.5, BLUE)
                    break
    for _n, _px, _py in _pins:
        cv.circle(10 + _px, _my + 14 + _py, 6, RED)
        _ns = str(_n)
        draw_text(cv, _ns, 10 + _px - text_width(_ns, 7, 'sans-bold') / 2, _my + 14 + _py + 2.5, 7, 'sans-bold', (255, 255, 255))
    cv.rect(510, _my, 504, 2, RED)
    cv.rect(510, _my + 78, 504, 2, RED)
    cv.rect(510, _my, 2, 80, RED)
    cv.rect(1012, _my, 2, 80, RED)
    draw_text(cv, 'DATE CHECK \u2014 WHAT WE LEFT OUT', 520, _my + 14, 10, 'sans-bold', RED)
    for i, _item in enumerate(_dc):
        _col = 0 if i < 3 else 1
        _ix = 520 if _col == 0 else 772
        _iy = _my + 30 + (i % 3) * 16
        draw_text(cv, 'x', _ix, _iy, 9, 'sans-bold', RED)
        draw_text(cv, _item, _ix + 12, _iy, 8.5, 'sans', INK)
    draw_text(cv, 'NOT YET: COP31 deal \u00b7 BepiColombo confirmation \u00b7 Rutte outcome', 520, _my + 74, 8, 'sans', GREY)
    # briefs
    draw_text(cv, 'ALSO ON SATURDAY 21 NOVEMBER \u2014 23 MORE STORIES', 10, 890, 11, 'sans-bold', NAVY)
    cv.rect(10, 894, 1004, 1, NAVY)
    for i, (city, text, src) in enumerate(_briefs):
        _col = 0 if i < 12 else 1
        _bx = 10 if _col == 0 else 519
        _by = 904 + (i % 12) * 9.5
        _pre = city + ' \u2013 '
        draw_text(cv, _pre, _bx, _by, 9, 'sans-bold', INK)
        _tx = text + ' (' + src + ')'
        draw_text(cv, _tx, _bx + text_width(_pre, 9, 'sans-bold'), _by, 9, 'sans', INK)
    # footer (one line)
    cv.rect(10, 1012, 1004, 1, RED)
    _f1 = ('Every story here happened, or was first reported, on Saturday 21 '
           'November 2026. Sources named beside each story. Original drawings, '
           'not photographs.')
    draw_text(cv, _f1, (W - text_width(_f1, 8, 'sans')) / 2, 1021, 8, 'sans', GREY)


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/tmp/v3out")
    os.makedirs(out, exist_ok=True)
    cv = Canvas(W, H, PAPER)
    if os.environ.get("FONT_TEST"):
        render_test(cv)
    else:
        render_page(cv)
    write_png(os.path.join(out, "entry.png"), cv.px, W, H)


if __name__ == "__main__":
    main()
