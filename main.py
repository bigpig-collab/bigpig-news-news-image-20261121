#!/usr/bin/env python3
"""news-image-20261121 v2 — 'THE WORLD IN ONE DAY' broadsheet.

Fresh build: Saturday 21 November 2026, 36 stories, 7 regions.
Pure Python 3.13 stdlib only (os, struct, zlib, math). Deterministic:
same bytes on every run. Writes /output/entry.png (1024x1024, PNG).

Design: cream broadsheet, bold navy masthead, colour-filled
illustrations, per-story sources, UTC timeline, region bar, DATE CHECK.
No pixel font, no external assets, no network.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 242, 228)
INK = (27, 42, 74)
RED = (166, 30, 34)
RED_DK = (140, 22, 26)
GOLD = (201, 162, 39)
TEAL = (31, 122, 109)
BLUE = (46, 90, 136)
BLUE_LT = (178, 205, 228)
SKY = (135, 190, 220)
NAVY = (22, 34, 64)
NAVY2 = (38, 54, 96)
GREEN = (46, 125, 62)
ORANGE = (214, 110, 30)
GREY = (120, 116, 106)
GREY_DK = (74, 70, 62)
WHITE = (255, 255, 255)
CREAM2 = (238, 231, 210)
PURPLE = (108, 72, 150)
BROWN = (122, 84, 52)
PINK = (196, 120, 130)


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def _set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, int(round(x)))
        y0 = max(0, int(round(y)))
        x1 = min(self.w, int(round(x + w)))
        y1 = min(self.h, int(round(y + h)))
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]
                i += 3

    def poly(self, pts, c):
        # filled polygon (scanline fill)
        if len(pts) < 3:
            return
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        y0 = max(0, int(math.floor(min(ys))))
        y1 = min(self.h - 1, int(math.ceil(max(ys))))
        n = len(pts)
        for y in range(y0, y1 + 1):
            nodes = []
            for i in range(n):
                x1, y1p = pts[i]
                x2, y2p = pts[(i + 1) % n]
                if (y1p <= y < y2p) or (y2p <= y < y1p):
                    t = (y - y1p) / (y2p - y1p)
                    nodes.append(x1 + t * (x2 - x1))
            nodes.sort()
            for k in range(0, len(nodes) - 1, 2):
                xa = max(0, int(math.ceil(nodes[k])))
                xb = min(self.w - 1, int(math.floor(nodes[k + 1])))
                for x in range(xa, xb + 1):
                    self._set(x, y, c)

    def disc(self, cx, cy, r, c):
        r = int(round(r))
        for dy in range(-r, r + 1):
            dx = int(round(math.sqrt(max(0, r * r - dy * dy))))
            for x in range(cx - dx, cx + dx + 1):
                self._set(x, cy + dy, c)

    def ring(self, cx, cy, r, t, c):
        steps = max(24, int(2 * math.pi * r))
        for i in range(steps):
            a = 2 * math.pi * i / steps
            x = int(round(cx + r * math.cos(a)))
            y = int(round(cy + r * math.sin(a)))
            self.disc(x, y, max(1, t // 2), c)

    def thick_line(self, x1, y1, x2, y2, w, c):
        # segment drawn as a filled quad + round caps
        dx = x2 - x1
        dy = y2 - y1
        L = math.hypot(dx, dy)
        if L < 0.01:
            self.disc(int(round(x1)), int(round(y1)), int(round(w / 2)), c)
            return
        nx = -dy / L * w / 2
        ny = dx / L * w / 2
        self.poly([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
                   (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)], c)
        self.disc(int(round(x1)), int(round(y1)), int(round(w / 2)), c)
        self.disc(int(round(x2)), int(round(y2)), int(round(w / 2)), c)

    def hline(self, x, y, w, t, c):
        self.fill_rect(x, y - t / 2, w, t, c)

    def vline(self, x, y, h, t, c):
        self.fill_rect(x - t / 2, y, t, h, c)


def png_bytes(cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(bytes(raw), 6)) +
            chunk(b"IEND", b""))


# ---------------------------------------------------------------- stroke font
# Proportional geometric sans. Each glyph: (advance, [strokes]).
# Coordinates in a 1000-unit em: baseline 0, cap 700, x-height 500,
# descender -220. Strokes are polylines drawn as thick quads.
def _ov(cx, cy, rx, ry, n=10, a0=0.0, a1=360.0):
    pts = []
    steps = max(4, int(n * (a1 - a0) / 360.0))
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return pts


G = {}
# --- uppercase
G['A'] = (640, [[(110, 0), (500, 700), (890, 0)], [(330, 250), (670, 250)]])
G['B'] = (620, [[(120, 0), (120, 700)],
                [(120, 700), (580, 700), (730, 610), (660, 470), (480, 420), (120, 420)],
                [(120, 420), (480, 420), (660, 370), (730, 240), (660, 110), (580, 0), (120, 0)]])
G['C'] = (640, [_ov(500, 350, 380, 350, 12, 45, 315)])
G['D'] = (660, [[(130, 0), (130, 700), (580, 700), (800, 560), (800, 140), (580, 0), (130, 0)]])
G['E'] = (580, [[(760, 700), (130, 700), (130, 0), (760, 0)], [(130, 350), (560, 350)]])
G['F'] = (560, [[(130, 0), (130, 700), (760, 700)], [(130, 350), (540, 350)]])
G['G'] = (660, [_ov(500, 350, 380, 350, 12, 40, 320), [(700, 350), (880, 350), (880, 120), (700, 120)]])
G['H'] = (660, [[(130, 0), (130, 700)], [(870, 0), (870, 700)], [(130, 350), (870, 350)]])
G['I'] = (340, [[(170, 0), (170, 700)]])
G['J'] = (560, [[(700, 700), (700, 140), (620, 30), (420, 0), (260, 60)]])
G['K'] = (640, [[(130, 0), (130, 700)], [(820, 700), (180, 300)], [(380, 380), (830, 0)]])
G['L'] = (560, [[(130, 700), (130, 0), (780, 0)]])
G['M'] = (760, [[(110, 0), (110, 700), (500, 180), (890, 700), (890, 0)]])
G['N'] = (680, [[(120, 0), (120, 700), (880, 0), (880, 700)]])
G['O'] = (680, [_ov(500, 350, 380, 350, 14)])
G['P'] = (620, [[(130, 0), (130, 700), (580, 700), (740, 600), (740, 460), (580, 360), (130, 360)]])
G['Q'] = (680, [_ov(500, 350, 380, 350, 14), [(620, 120), (830, -40)]])
G['R'] = (640, [[(130, 0), (130, 700), (580, 700), (740, 600), (740, 460), (580, 360), (130, 360)],
                [(480, 360), (840, 0)]])
G['S'] = (620, [[(740, 620), (620, 700), (380, 700), (240, 620), (240, 500), (360, 420), (640, 350), (760, 270), (760, 150), (640, 40), (380, 0), (240, 80)]])
G['T'] = (620, [[(120, 700), (880, 700)], [(500, 700), (500, 0)]])
G['U'] = (660, [[(130, 700), (130, 160), (240, 40), (460, 0), (680, 40), (790, 160), (790, 700)]])
G['V'] = (640, [[(110, 700), (500, 0), (890, 700)]])
G['W'] = (900, [[(80, 700), (250, 0), (450, 480), (650, 0), (820, 700)]])
G['X'] = (640, [[(140, 700), (860, 0)], [(860, 700), (140, 0)]])
G['Y'] = (620, [[(110, 700), (500, 300), (890, 700)], [(500, 300), (500, 0)]])
G['Z'] = (600, [[(130, 700), (820, 700), (130, 0), (820, 0)]])
# --- lowercase (x-height 500)
G['a'] = (580, [_ov(470, 250, 330, 250, 10), [(790, 500), (790, 0)]])
G['b'] = (580, [[(130, 700), (130, 0)], _ov(480, 250, 320, 250, 10)])
G['c'] = (560, [_ov(470, 250, 350, 250, 10, 50, 310)])
G['d'] = (580, [_ov(450, 250, 330, 250, 10), [(790, 700), (790, 0)]])
G['e'] = (580, [_ov(480, 250, 340, 250, 12, 20, 340), [(150, 250), (800, 250)]])
G['f'] = (420, [[(500, 0), (500, 560), (620, 640), (700, 640)], [(250, 380), (640, 380)]])
G['g'] = (580, [_ov(470, 250, 330, 250, 10), [(790, 500), (790, -80), (700, -200), (480, -220), (330, -160)]])
G['h'] = (580, [[(130, 700), (130, 0)], [(130, 500), (130, 330), (260, 470), (480, 500), (640, 430), (700, 300), (700, 0)]])
G['i'] = (300, [[(150, 0), (150, 500)], [(150, 640), (150, 660)]])
G['j'] = (340, [[(200, 500), (200, -80), (120, -200), (20, -220)], [(200, 640), (200, 660)]])
G['k'] = (560, [[(130, 700), (130, 0)], [(720, 500), (180, 220)], [(360, 280), (700, 0)]])
G['l'] = (300, [[(150, 700), (150, 0)]])
G['m'] = (860, [[(110, 0), (110, 500)], [(110, 500), (110, 330), (230, 470), (400, 500), (520, 430), (560, 330), (560, 0)],
                [(560, 500), (560, 330), (680, 470), (820, 500), (900, 430), (920, 300), (920, 0)]])
G['n'] = (580, [[(130, 0), (130, 500)], [(130, 500), (130, 330), (260, 470), (480, 500), (640, 430), (700, 300), (700, 0)]])
G['o'] = (580, [_ov(480, 250, 340, 250, 12)])
G['p'] = (580, [[(130, 0), (130, -220)], _ov(480, 250, 320, 250, 10)])
G['q'] = (580, [_ov(450, 250, 330, 250, 10), [(790, 0), (790, -220)]])
G['r'] = (420, [[(130, 0), (130, 500)], [(130, 500), (130, 340), (240, 460), (380, 500), (480, 460)]])
G['s'] = (540, [[(700, 440), (600, 500), (380, 500), (270, 430), (270, 330), (380, 270), (600, 230), (700, 160), (700, 70), (600, 10), (380, 0), (280, 60)]])
G['t'] = (420, [[(460, 0), (460, 600), (560, 660), (640, 660)], [(180, 380), (640, 380)]])
G['u'] = (580, [[(130, 500), (130, 160), (230, 40), (430, 0), (590, 40), (680, 160), (680, 500)]])
G['v'] = (560, [[(100, 500), (480, 0), (860, 500)]])
G['w'] = (820, [[(70, 500), (220, 0), (410, 330), (600, 0), (750, 500)]])
G['x'] = (560, [[(120, 500), (800, 0)], [(800, 500), (120, 0)]])
G['y'] = (560, [[(100, 500), (480, 60), (860, 500)], [(480, 60), (480, -160), (380, -220), (260, -220)]])
G['z'] = (540, [[(120, 500), (760, 500), (120, 0), (760, 0)]])
# --- digits
G['0'] = (640, [_ov(500, 350, 360, 350, 14)])
G['1'] = (420, [[(400, 700), (400, 0)], [(400, 700), (220, 560)], [(180, 0), (620, 0)]])
G['2'] = (620, [[(200, 560), (320, 680), (620, 680), (760, 580), (700, 420), (380, 180), (180, 0), (800, 0)]])
G['3'] = (620, [[(220, 700), (600, 700), (740, 600), (660, 460), (480, 400), (660, 330), (740, 200), (620, 60), (380, 0), (220, 80)]])
G['4'] = (620, [[(640, 700), (180, 180), (780, 180)], [(640, 700), (640, 0)]])
G['5'] = (620, [[(760, 700), (200, 700), (200, 420), (560, 420), (700, 330), (700, 150), (580, 40), (340, 0), (200, 70)]])
G['6'] = (620, [[(760, 640), (620, 700), (380, 680), (240, 540), (200, 350), (240, 140), (420, 20), (620, 40), (760, 160), (760, 300), (640, 400), (420, 400), (280, 300)]])
G['7'] = (600, [[(160, 700), (800, 700), (340, 0)]])
G['8'] = (620, [_ov(500, 520, 300, 180, 10), _ov(500, 180, 330, 180, 10)])
G['9'] = (620, [[(240, 60), (380, 0), (620, 20), (760, 160), (800, 350), (760, 560), (580, 680), (380, 660), (240, 540), (240, 400), (360, 300), (580, 300), (720, 400), (720, 700)]])
# --- punctuation
G['.'] = (300, [[(150, 0), (160, 10)]])
G[','] = (300, [[(150, 0), (160, 10)], [(150, 0), (110, -140)]])
G[':'] = (300, [[(150, 480), (160, 490)], [(150, 0), (160, 10)]])
G[';'] = (300, [[(150, 480), (160, 490)], [(150, 0), (160, 10)], [(150, 0), (110, -140)]])
G["'"] = (280, [[(200, 700), (120, 540)]])
G['"'] = (420, [[(160, 700), (90, 540)], [(360, 700), (290, 540)]])
G['-'] = (400, [[(80, 330), (720, 330)]])
G['\u2013'] = (560, [[(60, 330), (760, 330)]])
G['\u2014'] = (800, [[(60, 330), (880, 330)]])
G['\u00b7'] = (300, [[(150, 330), (160, 340)]])
G['('] = (360, [[(300, 700), (180, 540), (140, 350), (180, 160), (300, 0)]])
G[')'] = (360, [[(60, 700), (180, 540), (220, 350), (180, 160), (60, 0)]])
G['%'] = (860, [_ov(280, 520, 170, 170, 8), _ov(720, 180, 170, 170, 8), [(760, 700), (180, 0)]])
G['\u20ac'] = (640, [_ov(520, 350, 360, 350, 12, 50, 310), [(120, 250), (760, 250)], [(120, 420), (760, 420)]])
G['$'] = (620, [[(740, 620), (620, 700), (380, 700), (240, 620), (240, 500), (360, 420), (640, 350), (760, 270), (760, 150), (640, 40), (380, 0), (240, 80)],
                [(500, 780), (500, -80)]])
G['/'] = (480, [[(380, 700), (100, 0)]])
G['+'] = (620, [[(310, 140), (310, 560)], [(100, 350), (520, 350)]])
G['='] = (620, [[(100, 450), (520, 450)], [(100, 250), (520, 250)]])
G['!'] = (300, [[(150, 700), (150, 140)], [(150, 0), (160, 10)]])
G['?'] = (560, [[(180, 620), (300, 700), (480, 700), (560, 620), (560, 500), (480, 420), (330, 380), (330, 300)],
                [(330, 0), (340, 10)]])
G[' '] = (300, [])
G['\u00a0'] = (300, [])

# Effective advance: a glyph's strokes may reach past its declared
# advance, so the advance must cover the glyph's rightmost point plus a
# side bearing, or neighbouring letters (and word spaces) collide.
_ADV = {}
for _ch, (_adv, _strokes) in G.items():
    _mx = 0
    for _st in _strokes:
        for (_px, _py) in _st:
            if _px > _mx:
                _mx = _px
    _ADV[_ch] = max(_adv, _mx + 50)


def text_width(s, size, bold=False):
    sc = size / 1000.0
    w = 0.0
    for ch in s:
        w += _ADV.get(ch, 300) * sc
    return w


def draw_text(cv, x, y, s, size, color, bold=False, italic=False,
              align='l'):
    """Draw text; y is the baseline. align l/c/r relative to x."""
    sc = size / 1000.0
    w = text_width(s, size, bold)
    if align == 'c':
        x -= w / 2
    elif align == 'r':
        x -= w
    sw = size * (0.155 if bold else 0.105)
    for ch in s:
        adv = _ADV.get(ch, 300)
        strokes = G.get(ch, G[' '])[1]
        for stroke in strokes:
            pts = []
            for (px, py) in stroke:
                sx = x + px * sc
                sy = y - py * sc
                if italic:
                    sx += (y - sy) * 0.16
                pts.append((sx, sy))
            for i in range(len(pts) - 1):
                cv.thick_line(pts[i][0], pts[i][1], pts[i + 1][0],
                              pts[i + 1][1], max(1.0, sw), color)
            if len(pts) == 1:
                cv.disc(int(round(pts[0][0])), int(round(pts[0][1])),
                        int(round(sw / 2)), color)
        x += adv * sc
    return w


def wrap_text(s, size, max_w, bold=False):
    words = s.split(' ')
    lines = []
    cur = ''
    for w in words:
        trial = (cur + ' ' + w).strip()
        if text_width(trial, size, bold) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_block(cv, x, y, s, size, max_w, color, bold=False, italic=False,
               leading=None, align='l'):
    """Draw wrapped text; y is the first baseline. Returns bottom y.
    align 'c'/'r' centre/right-align each line inside the max_w box."""
    lines = wrap_text(s, size, max_w, bold)
    lh = leading if leading else size * 1.28
    for ln in lines:
        lw = text_width(ln, size, bold)
        if align == 'c':
            lx = x + (max_w - lw) / 2
        elif align == 'r':
            lx = x + max_w - lw
        else:
            lx = x
        draw_text(cv, lx, y, ln, size, color, bold, italic)
        y += lh
    return y, len(lines)


def fit_lines(s, size, max_w, max_lines, bold=False, min_size=8):
    """Shrink size until text fits in max_lines lines. Returns (size, lines)."""
    sz = size
    while sz > min_size:
        lines = wrap_text(s, sz, max_w, bold)
        if len(lines) <= max_lines:
            return sz, lines
        sz -= 0.5
    return sz, wrap_text(s, sz, max_w, bold)


# ---------------------------------------------------------------- world map
# Schematic land spans per row (col ranges, grid 54 x 22). Dotted map.
MAP_SPANS = [
    [(4, 12), (27, 30), (34, 49)],
    [(3, 13), (17, 19), (26, 31), (33, 50)],
    [(2, 14), (26, 31), (33, 51)],
    [(2, 14), (24, 24), (25, 31), (34, 51)],
    [(3, 13), (26, 30), (35, 51), (52, 52)],
    [(4, 13), (27, 30), (31, 35), (35, 48)],
    [(4, 12), (26, 32), (36, 46)],
    [(5, 11), (25, 33), (38, 45)],
    [(7, 11), (26, 33), (40, 44)],
    [(9, 11), (27, 32), (41, 43)],
    [(10, 12), (12, 17), (27, 31), (42, 46)],
    [(13, 18), (28, 31), (43, 45)],
    [(13, 17), (28, 30)],
    [(14, 17), (29, 30), (44, 49)],
    [(14, 16), (44, 49)],
    [(14, 15), (45, 48)],
    [(15, 16), (51, 52)],
    [(15, 15), (51, 51)],
    [], [], [], [], [],
]


def draw_map(cv, x, y, w, h, pins):
    """Dotted world map with numbered red pins. pins: [(fx, fy, n), ...]."""
    cols, rows = 54, 22
    cw = w / cols
    ch = h / rows
    for r, spans in enumerate(MAP_SPANS):
        for (a, b) in spans:
            for c in range(a, b + 1):
                cx = x + (c + 0.5) * cw
                cy = y + (r + 0.5) * ch
                cv.disc(int(cx), int(cy), max(1, int(min(cw, ch) * 0.42)),
                        (120, 130, 150))
    for (fx, fy, n) in pins:
        cx = int(x + fx * w)
        cy = int(y + fy * h)
        cv.disc(cx, cy, 8, RED)
        cv.ring(cx, cy, 8, 2, WHITE)
        draw_text(cv, cx, cy + 3, str(n), 10, WHITE, bold=True, align='c')


def burst(cv, cx, cy, r, c, spikes=8):
    pts = []
    for i in range(spikes * 2):
        a = math.pi * i / spikes
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    cv.poly(pts, c)


# ---------------------------------------------------------------- illustrations
def art_cop31(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (168, 214, 205))
    # globe
    gx, gy, gr = x + w * 0.38, y + h * 0.52, h * 0.36
    cv.disc(int(gx), int(gy), int(gr), BLUE)
    cv.poly([(gx - gr * 0.7, gy - gr * 0.2), (gx - gr * 0.1, gy - gr * 0.6),
             (gx + gr * 0.3, gy - gr * 0.3), (gx - gr * 0.2, gy + gr * 0.1),
             (gx - gr * 0.6, gy + gr * 0.4)], GREEN)
    cv.poly([(gx + gr * 0.2, gy + gr * 0.5), (gx + gr * 0.7, gy + gr * 0.3),
             (gx + gr * 0.6, gy + gr * 0.75), (gx + gr * 0.1, gy + gr * 0.8)], GREEN)
    # thermometer
    tx = x + w * 0.78
    cv.fill_rect(tx - 4, y + h * 0.14, 8, h * 0.62, WHITE)
    cv.disc(int(tx), int(y + h * 0.82), 11, RED)
    cv.fill_rect(tx - 2, y + h * 0.40, 4, h * 0.36, RED)
    cv.disc(int(tx), int(y + h * 0.82), 6, (255, 120, 120))
    # draft paper
    cv.fill_rect(x + w * 0.60, y + h * 0.10, w * 0.14, h * 0.22, WHITE)
    cv.hline(x + w * 0.62, y + h * 0.15, w * 0.10, 2, RED)
    cv.hline(x + w * 0.62, y + h * 0.20, w * 0.10, 2, GREY)


def art_poland(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, NAVY)
    for sx, sy in [(0.12, 0.18), (0.35, 0.10), (0.62, 0.22), (0.85, 0.12), (0.5, 0.3)]:
        cv.disc(int(x + w * sx), int(y + h * sy), 2, WHITE)
    # missile streaking down-left
    cv.thick_line(x + w * 0.82, y + h * 0.12, x + w * 0.45, y + h * 0.55, 7, WHITE)
    cv.thick_line(x + w * 0.82, y + h * 0.12, x + w * 0.74, y + h * 0.20, 7, RED)
    burst(cv, int(x + w * 0.42), int(y + h * 0.58), 16, ORANGE)
    burst(cv, int(x + w * 0.42), int(y + h * 0.58), 8, GOLD)
    # Polish flag
    fx, fy = x + w * 0.08, y + h * 0.62
    cv.fill_rect(fx, fy, w * 0.22, h * 0.10, WHITE)
    cv.fill_rect(fx, fy + h * 0.10, w * 0.22, h * 0.10, RED)
    # ground
    cv.fill_rect(x, y + h * 0.85, w, h * 0.15, (30, 48, 80))


def art_kyiv(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, NAVY)
    for sx, sy in [(0.1, 0.12), (0.3, 0.08), (0.55, 0.15), (0.8, 0.1), (0.92, 0.2)]:
        cv.disc(int(x + w * sx), int(y + h * sy), 2, WHITE)
    # skyline
    base = y + h * 0.88
    for bx, bw, bh in [(0.04, 0.10, 0.42), (0.16, 0.08, 0.55), (0.26, 0.12, 0.38),
                       (0.40, 0.09, 0.60), (0.51, 0.11, 0.44), (0.64, 0.08, 0.52),
                       (0.74, 0.12, 0.40), (0.88, 0.09, 0.48)]:
        cv.fill_rect(x + w * bx, base - h * bh, w * bw, h * bh, (16, 26, 52))
        for wy in range(3):
            cv.fill_rect(x + w * (bx + 0.02), base - h * bh + 6 + wy * 12,
                         3, 4, GOLD)
    # explosions
    burst(cv, int(x + w * 0.30), int(y + h * 0.30), 18, ORANGE)
    burst(cv, int(x + w * 0.30), int(y + h * 0.30), 9, GOLD)
    burst(cv, int(x + w * 0.72), int(y + h * 0.42), 13, ORANGE)
    burst(cv, int(x + w * 0.72), int(y + h * 0.42), 6, GOLD)
    # river + bridge arc
    cv.fill_rect(x, y + h * 0.88, w, h * 0.12, (40, 90, 140))
    cv.thick_line(x + w * 0.05, y + h * 0.88, x + w * 0.5, y + h * 0.72,
                  3, WHITE)
    cv.thick_line(x + w * 0.5, y + h * 0.72, x + w * 0.95, y + h * 0.88,
                  3, WHITE)


def art_riyadh(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (58, 32, 96))
    cv.disc(int(x + w * 0.85), int(y + h * 0.18), 10, (250, 240, 200))
    base = y + h * 0.88
    for bx, bw, bh in [(0.05, 0.09, 0.40), (0.16, 0.07, 0.52), (0.25, 0.10, 0.36),
                       (0.37, 0.08, 0.58), (0.47, 0.12, 0.42), (0.61, 0.07, 0.50),
                       (0.70, 0.11, 0.38), (0.83, 0.10, 0.46)]:
        cv.fill_rect(x + w * bx, base - h * bh, w * bw, h * bh, (28, 18, 52))
        for wy in range(3):
            cv.fill_rect(x + w * (bx + 0.02), base - h * bh + 6 + wy * 11,
                         3, 4, GOLD)
    # three intercept trails
    for tx, ty in [(0.22, 0.10), (0.50, 0.06), (0.74, 0.12)]:
        ex, ey = x + w * tx, y + h * ty
        bx, by = x + w * (tx + 0.08), y + h * 0.42
        for i in range(6):
            t = i / 5
            px = ex + (bx - ex) * t
            py = ey + (by - ey) * t + 14 * math.sin(t * math.pi)
            cv.disc(int(px), int(py), 3, ORANGE)
        burst(cv, int(bx), int(by), 10, GOLD)
        burst(cv, int(bx), int(by), 5, WHITE)


def art_denmark(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (232, 226, 208))
    cx, cy = x + w * 0.32, y + h * 0.5
    cv.ring(int(cx), int(cy), 20, 4, RED)
    cv.ring(int(cx), int(cy), 12, 4, RED)
    cv.disc(int(cx), int(cy), 4, RED)
    # Danish flag
    fx, fy = x + w * 0.62, y + h * 0.22
    cv.fill_rect(fx, fy, w * 0.30, h * 0.56, RED)
    cv.fill_rect(fx + w * 0.09, fy, w * 0.05, h * 0.56, WHITE)
    cv.fill_rect(fx, fy + h * 0.24, w * 0.30, h * 0.08, WHITE)


def art_bepi(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (12, 14, 24))
    mx, my = x + w * 0.34, y + h * 0.52
    cv.disc(int(mx), int(my), 18, (168, 164, 152))
    cv.disc(int(mx - 6), int(my - 4), 4, (130, 126, 116))
    cv.disc(int(mx + 7), int(my + 6), 3, (130, 126, 116))
    cv.disc(int(mx + 2), int(my - 9), 2, (130, 126, 116))
    # spacecraft
    sx, sy = x + w * 0.68, y + h * 0.40
    cv.fill_rect(sx - 8, sy - 5, 16, 10, GOLD)
    cv.fill_rect(sx - 24, sy - 3, 14, 6, BLUE_LT)
    cv.fill_rect(sx + 10, sy - 3, 14, 6, BLUE_LT)
    cv.thick_line(sx, sy + 6, sx - 4, sy + 16, 3, ORANGE)
    cv.ring(int(mx), int(my), 30, 2, (120, 130, 150))


def art_hormuz(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, SKY)
    cv.fill_rect(x, y + h * 0.62, w, h * 0.38, (30, 80, 130))
    # tanker
    hx = x + w * 0.12
    cv.fill_rect(hx, y + h * 0.48, w * 0.70, h * 0.16, (40, 40, 44))
    cv.fill_rect(hx + w * 0.56, y + h * 0.34, w * 0.10, h * 0.14, (40, 40, 44))
    cv.fill_rect(hx + w * 0.18, y + h * 0.40, w * 0.10, h * 0.08, (200, 60, 50))
    cv.fill_rect(hx + w * 0.32, y + h * 0.40, w * 0.10, h * 0.08, (60, 160, 90))
    # flame + smoke
    burst(cv, int(hx + w * 0.62), int(y + h * 0.30), 12, ORANGE)
    burst(cv, int(hx + w * 0.62), int(y + h * 0.30), 6, GOLD)
    cv.disc(int(hx + w * 0.70), int(y + h * 0.16), 7, (120, 120, 120))
    cv.disc(int(hx + w * 0.78), int(y + h * 0.10), 5, (150, 150, 150))


def art_wallst(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, WHITE)
    cv.fill_rect(x + 3, y + 3, w - 6, h - 6, (250, 248, 242))
    bars = [(0.12, 0.30, 0.55, GREEN), (0.26, 0.42, 0.45, RED),
            (0.40, 0.36, 0.60, RED), (0.54, 0.55, 0.38, GREEN),
            (0.68, 0.50, 0.62, RED), (0.82, 0.66, 0.30, RED)]
    for fx, fy, fh, c in bars:
        cv.fill_rect(x + w * fx, y + h * fy, w * 0.09, h * fh, c)
        cv.vline(x + w * (fx + 0.045), y + h * (fy - 0.08), h * (fh + 0.16), 2, c)
    cv.thick_line(x + w * 0.10, y + h * 0.28, x + w * 0.90, y + h * 0.72, 2, RED)


def art_eu(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (30, 60, 130))
    cx, cy = x + w * 0.5, y + h * 0.5
    for i in range(12):
        a = 2 * math.pi * i / 12 - math.pi / 2
        cv.disc(int(cx + 20 * math.cos(a)), int(cy + 20 * math.sin(a)), 2, GOLD)
    draw_text(cv, cx, cy + 8, "\u20ac", 22, GOLD, bold=True, align='c')


def art_n0n(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (24, 28, 40))
    cx, cy = x + w * 0.5, y + h * 0.56
    cv.ring(int(cx), int(cy - 8), 9, 3, GOLD)
    cv.fill_rect(cx - 13, cy - 6, 26, 18, GOLD)
    cv.disc(int(cx), int(cy + 1), 3, (24, 28, 40))
    draw_text(cv, cx, y + h * 0.16, "n0n", 11, (255, 120, 120), bold=True, align='c')


def art_akvan(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (168, 205, 225))
    cx, cy = x + w * 0.42, y + h * 0.52
    for r in (18, 13, 8):
        cv.ring(int(cx), int(cy), r, 3, WHITE)
    cv.disc(int(cx), int(cy), 3, WHITE)
    for rx, ry in [(0.75, 0.2), (0.85, 0.45), (0.7, 0.7)]:
        cv.thick_line(x + w * rx, y + h * ry, x + w * (rx - 0.04), y + h * (ry + 0.12), 2, (90, 130, 170))
    cv.disc(int(x + w * 0.82), int(y + h * 0.78), 4, RED)


def art_anthropic(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (250, 248, 242))
    cv.fill_rect(x + w * 0.14, y + h * 0.18, w * 0.72, h * 0.34, (30, 60, 130))
    draw_text(cv, x + w * 0.5, y + h * 0.42, "$93.5bn", 13, WHITE, bold=True, align='c')
    cv.fill_rect(x + w * 0.16, y + h * 0.62, w * 0.68, h * 0.24, WHITE)
    cv.hline(x + w * 0.16, y + h * 0.62, w * 0.68, 2, RED)
    cv.hline(x + w * 0.16, y + h * 0.86, w * 0.68, 2, RED)
    draw_text(cv, x + w * 0.5, y + h * 0.80, "CLAIM ONLY", 10, RED, bold=True, align='c')


def art_irancost(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (250, 248, 242))
    vals = [0.25, 0.45, 0.38, 0.62, 0.85]
    for i, v in enumerate(vals):
        cv.fill_rect(x + w * (0.10 + i * 0.18), y + h * (0.85 - v), w * 0.11,
                     h * v, BLUE)
    draw_text(cv, x + w * 0.5, y + h * 0.16, "$48.3bn", 12, INK, bold=True, align='c')


# ---------------------------------------------------------------- data
NUMBERS = [
    ("0", "climate deal agreed"),
    ("400+", "drones fired at Ukraine"),
    ("3", "missiles downed over Riyadh"),
    ("-5.28%", "Nasdaq, Friday close"),
    ("\u20ac7.9bn", "EU's largest-ever payment"),
    ("300,000+", "evacuated before Akvan"),
]

REGIONS = [
    ("EUROPE", 9, BLUE), ("AMERICAS", 14, RED), ("ASIA", 4, GOLD),
    ("MIDEAST", 3, TEAL), ("AFRICA", 2, GREEN), ("OCEANIA", 2, PURPLE),
    ("WORLD", 2, GREY_DK),
]

UTC_SLOTS = [
    ("23:00 UTC", "Riyadh: 3 missiles downed"),
    ("01:56 UTC", "COP31 no deal; draft due Sat"),
    ("MORNING", "COP31 draft due in Antalya"),
    ("MIDDAY", "Rutte due in Warsaw"),
    ("19:24 CET", "BepiColombo burn for Mercury"),
    ("EVENING", "Wall Street: Nasdaq -5.28%"),
]

LEADS = [
    ("1", "ANTALYA \u00b7 CLIMATE", "COP31 runs into overtime with no deal",
     "No deal as talks pass their close; a third draft is due Saturday "
     "morning. Fossil fuels and the $120bn target are out. (AP, Reuters)",
     art_cop31),
    ("2", "WARSAW \u00b7 SECURITY", "Russian missiles land in Poland",
     "Two missiles and a drone crash in the south-east; no injuries. Tusk "
     "calls it 'an intentional provocation'; Rutte is due in Warsaw on "
     "Saturday. (AP, Reuters)", art_poland),
    ("3", "KYIV \u00b7 WAR", "Russia's biggest strike hits Kyiv",
     "400+ drones and 110+ missiles overnight; 12 killed, 82 hurt. Three "
     "Dnipro bridges are damaged; outages in 11 regions. (CNN, Reuters)",
     art_kyiv),
    ("4", "RIYADH \u00b7 CONFLICT", "Three missiles downed over Riyadh",
     "Saudi defences intercept three ballistic missiles fired at the "
     "capital early on Saturday; no damage or casualties. Third straight "
     "night of alerts. (Reuters, AFP)", art_riyadh),
]

CARDS = [
    ("5", "COPENHAGEN \u00b7 SECURITY",
     "Denmark foils 'Russian plot' to kill rapper Kyivstoner",
     "3 arrested; 2 charged Friday. Denmark orders Russia's attache out in "
     "7 days. (Reuters)", art_denmark),
    ("6", "MERCURY \u00b7 SPACE",
     "BepiColombo reaches Mercury after eight years",
     "Planned capture burn 19:24 CET; first mission with two orbiters "
     "around Mercury. (ESA)", art_bepi),
    ("7", "STRAIT OF HORMUZ \u00b7 SHIPPING",
     "Tanker hit by projectile catches fire",
     "UKMTO 214-26: fire on board, no casualties. Hormuz transits down 15% "
     "in a week. (Reuters)", art_hormuz),
    ("8", "NEW YORK \u00b7 MARKETS",
     "Wall Street enters correction; Nasdaq -5.28%",
     "S&P -3.70%, 7th straight fall. Gold -4.62%; Bitcoin below $60,000. "
     "(Reuters)", art_wallst),
    ("9", "BRUSSELS \u00b7 AID",
     "EU approves \u20ac1bn more military aid for Ukraine",
     "Joint procurement of drones and air defence, delivered by end-2027. "
     "(European Council)", art_eu),
    ("10", "NEW YORK \u00b7 CYBER",
     "Hackers leak JPMorgan, Visa, Mastercard data",
     "Group 'n0n' claims the theft; ~16,000 JPMorgan emails found. No card "
     "numbers. (Reuters)", art_n0n),
    ("11", "GOPALPUR \u00b7 WEATHER",
     "Cyclone Akvan weakens after landfall; 300,000+ moved",
     "Winds gust to 110 km/h; 300,000+ evacuated to relief camps. No deaths "
     "reported. (IMD, PTI)", art_akvan),
    ("12", "SAN FRANCISCO \u00b7 TECH",
     "Anthropic IPO closes at $93.5bn; Riemann claim",
     "Largest IPO on record. A Riemann proof is claimed, with Claude. "
     "CLAIM ONLY. (Sci. Am.)", art_anthropic),
    ("13", "WASHINGTON \u00b7 WAR COSTS",
     "US war against Iran has cost $48.3bn",
     "Pentagon: the campaign cost $48.3bn as of 13 Nov, excluding base "
     "damage. (AP)", art_irancost),
]

BRIEFS = [
    (14, "BRUSSELS", "EU pays Ukraine \u20ac7.9bn, largest ever (European Commission)"),
    (15, "NEW YORK", "Gupta jailed 235 months in Sikh plot (US DOJ)"),
    (16, "JOHANNESBURG", "581 women killed in three months (SAPS)"),
    (17, "PERTH", "Starc 7/58 as England fold for 172 (ANI)"),
    (18, "WELLINGTON", "India fight back 159/1 after NZ 368 (Cricbuzz)"),
    (19, "KUALA LUMPUR", "India U17 draw 0-0, qualify (AFC)"),
    (20, "VIRGINIA", "First US measles death of 2026 (VDH)"),
    (21, "TOKYO", "Japan to buy 8M barrels of Saudi oil (Bloomberg)"),
    (22, "SANAA", "Coalition says it hit 6 Houthi workshops (Coalition claim)"),
    (23, "NEW YORK", "GTA VI makes $3.79bn in day one (Take-Two)"),
    (24, "WASHINGTON", "Trump: 'tremendous tax' on AI data centres abroad (Reuters)"),
    (25, "BRUSSELS", "UK-EU reset deal sealed (Reuters)"),
    (26, "NEW ORLEANS", "5th Circuit voids $1.7tn spending bill; Pete Rose pardoned (Reuters)"),
    (27, "NEW YORK", "Mamdani unveils plan to close Rikers by 2032 (BBC)"),
    (28, "WASHINGTON", "US declassifies more UFO footage (BBC)"),
    (29, "LONDON", "Lauren Price undisputed welterweight champion (BBC)"),
    (30, "NEW YORK", "1,144 children killed or injured in Ukraine in 2026 (UNICEF)"),
    (31, "TALLINN", "Estonia to close road borders with Russia (Kyiv Independent)"),
    (32, "WASHINGTON", "US adds 4 Iranians to sanctions list (US Treasury)"),
    (33, "BRASILIA", "Lula strengthens Indigenous land protection (Wire)"),
    (34, "KATHMANDU", "Nepal PM Shah to meet India's PM Modi (BBC)"),
    (35, "JOHANNESBURG", "South Africa local elections; ANC fights to hold cities (BBC)"),
    (36, "WASHINGTON", "US cleared ~900,000 AI chips for China (House committee)"),
]

PINS = [
    (0.62, 0.33, 1), (0.57, 0.17, 2), (0.61, 0.24, 3), (0.66, 0.42, 4),
    (0.52, 0.13, 5), (0.70, 0.40, 7), (0.15, 0.27, 8), (0.49, 0.22, 9),
    (0.23, 0.28, 10), (0.78, 0.50, 11), (0.08, 0.32, 12), (0.20, 0.32, 13),
]


# ---------------------------------------------------------------- layout
def draw_page(cv):
    # top rule + bar
    cv.fill_rect(0, 0, W, 4, RED)
    draw_text(cv, 10, 22, "THE WORLD IN ONE DAY", 13, RED, bold=True)
    draw_text(cv, 1014, 21, "36 STORIES \u00b7 7 REGIONS \u00b7 EVERY ONE DATED "
              "SATURDAY 21 NOVEMBER 2026", 11, INK, align='r')
    cv.hline(10, 28, 1004, 1, INK)
    # masthead
    draw_text(cv, 512, 86, "Saturday 21 November 2026", 50, INK, bold=True,
              align='c')
    draw_text(cv, 512, 106,
              "COP31 runs into overtime \u00b7 Russian missiles land in Poland "
              "\u00b7 Kyiv hit in overnight barrage \u00b7 Riyadh downs three missiles",
              13, INK, italic=True, align='c')
    cv.fill_rect(10, 114, 1004, 2, INK)
    cv.hline(10, 119, 1004, 1, INK)
    # numbers strip
    cw = 1004 / 6
    for i, (num, cap) in enumerate(NUMBERS):
        x = 10 + i * cw
        draw_text(cv, x + cw / 2, 146, num, 26, INK, bold=True, align='c')
        draw_text(cv, x + cw / 2, 162, cap, 9.5, GREY_DK, align='c')
        if i:
            cv.vline(x, 126, 42, 1, (200, 192, 172))
    cv.hline(10, 174, 1004, 1, (200, 192, 172))
    # region bar
    total = sum(n for _, n, _ in REGIONS)
    rx = 10.0
    for name, n, col in REGIONS:
        wseg = 1004 * n / total
        cv.fill_rect(rx, 178, wseg, 18, col)
        draw_text(cv, rx + wseg / 2, 191, "%s %d" % (name, n), 10, WHITE,
                  bold=True, align='c')
        rx += wseg
    # by field
    draw_text(cv, 512, 208,
              "BY FIELD: War & security 10 \u00b7 Politics & diplomacy 7 "
              "\u00b7 Economy & markets 6 \u00b7 Science & health 4 \u00b7 Courts "
              "& justice 3 \u00b7 Sport 4 \u00b7 Climate & disasters 2",
              11, INK, align='c')
    # UTC strip
    cv.fill_rect(10, 214, 1004, 36, NAVY)
    sw = 1004 / 6
    for i, (t, ev) in enumerate(UTC_SLOTS):
        x = 10 + i * sw
        draw_text(cv, x + 6, 227, t, 8.5, GOLD, bold=True)
        draw_text(cv, x + 6, 241, ev, 8.5, WHITE)
        if i:
            cv.vline(x, 218, 28, 1, (90, 100, 130))
    # leads
    lw = 242
    for i, (num, kick, head, body, art) in enumerate(LEADS):
        x = 10 + i * (lw + 12)
        y = 256
        art(cv, x, y, lw, 84)
        cv.fill_rect(x, y + 84, lw, 19, RED)
        draw_text(cv, x + 6, y + 98, "%s  %s" % (num, kick), 11, WHITE,
                  bold=True)
        sz, lines = fit_lines(head, 18, lw - 10, 2, bold=True)
        yy = y + 103 + sz
        for ln in lines:
            draw_text(cv, x + 5, yy, ln, sz, INK, bold=True)
            yy += sz * 1.22
        yy += 2
        bsz, blines = fit_lines(body, 11, lw - 10, 3, min_size=9.5)
        for ln in blines:
            draw_text(cv, x + 5, yy, ln, bsz, GREY_DK)
            yy += bsz * 1.28
    # medium cards 5-13 (3 rows x 3 cols)
    card_w, card_h = 330, 68
    for i, (num, kick, head, body, art) in enumerate(CARDS):
        r, c = divmod(i, 3)
        x = 10 + c * (card_w + 7)
        y = 452 + r * (card_h + 4)
        cv.fill_rect(x, y, card_w, card_h, WHITE)
        cv.hline(x, y, card_w, 1, (210, 202, 182))
        cv.hline(x, y + card_h, card_w, 1, (210, 202, 182))
        art(cv, x + 4, y + 6, 58, card_h - 12)
        tx = x + 68
        draw_text(cv, tx, y + 13, "%s  %s" % (num, kick), 9.5, RED, bold=True)
        sz, lines = fit_lines(head, 13, card_w - 74, 2, bold=True)
        yy = y + 13 + sz + 3
        for ln in lines:
            draw_text(cv, tx, yy, ln, sz, INK, bold=True)
            yy += sz * 1.18
        bsz, blines = fit_lines(body, 9.5, card_w - 74, 2, min_size=9)
        for ln in blines:
            draw_text(cv, tx, yy + 1, ln, bsz, GREY_DK)
            yy += bsz * 1.25
    # bottom band: map + briefs
    y0 = 672
    draw_text(cv, 10, y0 + 14, "WHERE IT HAPPENED", 12, INK, bold=True)
    draw_text(cv, 340, y0 + 14, "ALSO ON SATURDAY 21 NOVEMBER \u2014 23 MORE "
              "STORIES", 12, INK, bold=True)
    cv.hline(10, y0 + 20, 320, 1, INK)
    cv.hline(340, y0 + 20, 674, 1, INK)
    draw_map(cv, 14, y0 + 28, 312, 150, PINS)
    draw_text(cv, 14, y0 + 188, "Pins 1-13 mark the drawn stories.", 9, GREY_DK)
    draw_text(cv, 14, y0 + 200, "No. 6 is in space: Mercury.", 9, GREY_DK)
    cols = [BRIEFS[:12], BRIEFS[12:]]
    for ci, col in enumerate(cols):
        x = 340 + ci * 342
        yy = y0 + 32
        for (n, city, txt) in col:
            line = "%d %s \u2014 %s" % (n, city, txt)
            sz, lines = fit_lines(line, 9, 330, 2, min_size=8.5)
            for ln in lines:
                draw_text(cv, x, yy, ln, sz, INK)
                yy += sz * 1.28
            yy += 1.5
    # date check
    dy = 900
    cv.fill_rect(10, dy, 1004, 50, (255, 246, 240))
    cv.hline(10, dy, 1004, 2, RED)
    cv.hline(10, dy + 50, 1004, 2, RED)
    cv.vline(10, dy, 50, 2, RED)
    cv.vline(1014, dy, 50, 2, RED)
    draw_text(cv, 20, dy + 16, "DATE CHECK \u2014 WHAT WE LEFT OUT:", 11, RED,
              bold=True)
    draw_text(cv, 20, dy + 33,
              "ICJ Myanmar ruling (19 Nov) \u00b7 Shenzhen trilateral (19 Nov) "
              "\u00b7 Mongolia president resigns (19 Nov) \u00b7 Kerch Bridge "
              "strikes (16-19 Nov)", 10, INK)
    draw_text(cv, 20, dy + 46,
              "NOT YET HAPPENED: the COP31 final deal \u00b7 BepiColombo capture "
              "confirmation \u00b7 the outcome of Rutte's Warsaw visit.",
              10, INK)
    # footer
    draw_text(cv, 512, 960,
              "Every story here happened, or was first reported, on Saturday "
              "21 November 2026 in at least one time zone. Claims are "
              "attributed, not stated as fact. Original drawings.",
              9.5, GREY_DK, align='c')
    draw_text(cv, 512, 974,
              "Sources: Reuters \u00b7 AP \u00b7 BBC \u00b7 AFP \u00b7 European "
              "Commission \u00b7 US DOJ \u00b7 UKMTO \u00b7 ESA \u00b7 IMD \u00b7 VDH "
              "\u00b7 House Foreign Affairs Committee",
              9.5, GREY_DK, align='c')
    cv.fill_rect(10, 984, 1004, 3, RED)


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "output")
    os.makedirs(outdir, exist_ok=True)
    cv = Canvas(W, H, PAPER)
    draw_page(cv)
    data = png_bytes(cv)
    with open(os.path.join(outdir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
