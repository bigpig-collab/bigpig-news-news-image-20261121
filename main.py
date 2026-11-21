#!/usr/bin/env python3
"""news-image-20261121: one image summing up Saturday 21 November 2026.

Pure Python 3.13 stdlib. Draws a 1024x1024 broadsheet front page with a
hand-built 5x7 pixel font (all caps, no serif), three illustrated lead
panels, a figures band, a schematic world map with numbered pins, ten
story cards, a 23-item world-in-brief, a day-in-order strip and a
date-check box. Writes /output/entry.png (MAKEFUN_OUTPUT_DIR override).
Deterministic: same bytes on every run.
"""
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- font
# 5x7 pixel glyphs, written fresh for this entry. "#" = ink, "." = blank.
GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
}
BLANK = ("00000", "00000", "00000", "00000", "00000", "00000", "00000")


def text_w(s, scale):
    return len(s) * 6 * scale - scale


def wrap(s, max_chars):
    """Greedy word wrap to at most max_chars per line."""
    words = s.split(" ")
    lines, cur = [], ""
    for wd in words:
        if not cur:
            cur = wd
        elif len(cur) + 1 + len(wd) <= max_chars:
            cur += " " + wd
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- sheet
class Sheet:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = c

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + (x1 - x0) * 3] = c * (x1 - x0)

    def hline(self, x, y, w, c, t=1):
        self.rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)

    def border(self, x, y, w, h, c, t=1):
        self.hline(x, y, w, c, t)
        self.hline(x, y + h - t, w, c, t)
        self.vline(x, y, h, c, t)
        self.vline(x + w - t, y, h, c, t)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill:
                    if d <= r * r:
                        self.set(xx, yy, c)
                else:
                    if abs(d - r * r) <= r:
                        self.set(xx, yy, c)

    def poly(self, pts, c):
        """Scanline fill of a simple polygon."""
        if not pts:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for x in range(int(xs[k]), int(xs[k + 1]) + 1):
                    self.set(x, y, c)

    def glyph(self, x, y, ch, scale, c):
        g = GLYPHS.get(ch, BLANK)
        for r, row in enumerate(g):
            for col, bit in enumerate(row):
                if bit == "1":
                    self.rect(x + col * scale, y + r * scale, scale, scale, c)

    def text(self, x, y, s, scale, c, align="l"):
        s = s.upper()
        if align == "c":
            x -= text_w(s, scale) // 2
        elif align == "r":
            x -= text_w(s, scale)
        for ch in s:
            self.glyph(x, y, ch, scale, c)
            x += 6 * scale
        return x

    def para(self, x, y, s, scale, c, max_w, lh=None):
        """Wrapped paragraph; returns y just below last line."""
        if lh is None:
            lh = 9 * scale
        max_chars = max(1, (max_w + scale) // (6 * scale))
        for ln in wrap(s, max_chars):
            self.text(x, y, ln, scale, c)
            y += lh
        return y

    def png_bytes(self):
        raw = bytearray()
        stride = self.w * 3
        for y in range(self.h):
            raw.append(0)
            raw += self.px[y * stride:(y + 1) * stride]
        comp = zlib.compress(bytes(raw), 9)

        def chunk(tag, data):
            out = struct.pack(">I", len(data)) + tag + data
            out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
            return out

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- palette
PAPER = bytes((247, 243, 232))
INK = bytes((20, 20, 20))
NAVY = bytes((17, 24, 39))
NAVY2 = bytes((31, 41, 55))
RED = bytes((185, 28, 28))
RED_LT = bytes((254, 226, 226))
BLUE = bytes((29, 78, 216))
SKY = bytes((186, 220, 245))
SKY_DK = bytes((147, 197, 253))
LAND = bytes((210, 196, 160))
LAND2 = bytes((188, 172, 128))
GOLD = bytes((180, 83, 9))
GREEN = bytes((21, 128, 61))
GREY = bytes((107, 114, 128))
LINE = bytes((180, 175, 160))
WHITE = bytes((255, 255, 255))
YELLOW = bytes((250, 204, 21))
DUSK = bytes((55, 48, 84))
DUSK2 = bytes((76, 29, 149))


# ---------------------------------------------------------------- scenes
def scene_kyiv(s, x, y, w, h):
    """Night over the Dnipro: missile streaks, bridges, city blocks."""
    s.rect(x, y, w, h, DUSK)
    # stars
    for sx, sy in [(18, 14), (52, 30), (96, 10), (140, 26), (190, 12),
                   (238, 30), (282, 16), (310, 34), (70, 44), (160, 46),
                   (220, 48), (30, 58), (120, 60), (265, 56)]:
        s.rect(x + sx, y + sy, 3, 3, WHITE)
    # missile streaks with bright heads
    for (mx0, my0, mx1, my1) in [(40, 8, 90, 70), (150, 4, 185, 62),
                                 (240, 10, 275, 66), (300, 2, 318, 44),
                                 (90, 16, 120, 58), (200, 20, 225, 60)]:
        s.line(x + mx0, y + my0, x + mx1, y + my1, YELLOW)
        s.line(x + mx0, y + my0 + 1, x + mx1, y + my1 + 1, YELLOW)
        s.circle(x + mx1, y + my1, 4, YELLOW)
        s.circle(x + mx1, y + my1, 2, WHITE)
    # explosion glow over the far bank
    s.circle(x + 250, y + 84, 16, RED)
    s.circle(x + 250, y + 84, 9, YELLOW)
    s.circle(x + 250, y + 84, 4, WHITE)
    # river
    s.rect(x, y + h - 34, w, 34, BLUE)
    s.hline(x, y + h - 34, w, SKY_DK, 2)
    # city blocks on the far bank
    for bx, bw, bh in [(10, 26, 22), (44, 18, 30), (70, 30, 18),
                       (108, 22, 28), (138, 16, 20), (160, 28, 26),
                       (196, 20, 18), (222, 24, 26), (280, 30, 20)]:
        s.rect(x + bx, y + h - 34 - bh, bw, bh, NAVY2)
        for wy in range(0, bh - 6, 8):
            for wx in range(4, bw - 4, 8):
                s.rect(x + bx + wx, y + h - 34 - bh + 4 + wy, 3, 3, YELLOW)
    # three bridges across the river
    for bx in (60, 150, 240):
        s.rect(x + bx, y + h - 44, 64, 4, WHITE)
        s.line(x + bx + 6, y + h - 44, x + bx + 32, y + h - 62, WHITE)
        s.line(x + bx + 58, y + h - 44, x + bx + 32, y + h - 62, WHITE)
        s.rect(x + bx + 30, y + h - 64, 4, 20, WHITE)
    # smoke over the damaged middle bridge
    s.circle(x + 182, y + h - 56, 7, GREY)
    s.circle(x + 176, y + h - 64, 5, GREY)


def scene_riyadh(s, x, y, w, h):
    """02:00 over Riyadh: towers, three intercept bursts."""
    s.rect(x, y, w, h, DUSK2)
    for sx, sy in [(22, 12), (80, 24), (150, 10), (210, 20), (280, 14),
                   (120, 34), (250, 36), (40, 40)]:
        s.rect(x + sx, y + sy, 3, 3, WHITE)
    # skyline: PIF tower tallest, centre
    for bx, bw, bh in [(8, 22, 60), (38, 18, 84), (64, 24, 48),
                       (96, 20, 70), (124, 26, 96), (158, 22, 62),
                       (188, 18, 80), (214, 26, 54), (248, 20, 72),
                       (276, 24, 58), (306, 16, 40)]:
        s.rect(x + bx, y + h - bh, bw, bh, NAVY)
        for wy in range(6, bh - 6, 10):
            for wx in range(4, bw - 4, 9):
                s.rect(x + bx + wx, y + h - bh + wy, 3, 4, YELLOW)
    # three intercept bursts in the sky
    for cx, cy in [(70, 42), (165, 30), (262, 44)]:
        s.circle(x + cx, y + cy, 13, YELLOW)
        s.circle(x + cx, y + cy, 8, WHITE)
        s.circle(x + cx, y + cy, 4, RED)
        for ang in range(0, 360, 45):
            import math
            dx = int(20 * math.cos(math.radians(ang)))
            dy = int(20 * math.sin(math.radians(ang)))
            s.line(x + cx, y + cy, x + cx + dx, y + cy + dy, YELLOW)
    # falling debris dots
    for dx, dy in [(90, 62), (185, 56), (240, 66), (110, 74), (280, 62)]:
        s.rect(x + dx, y + dy, 3, 3, YELLOW)


def scene_markets(s, x, y, w, h):
    """Red boards: descending bars and a plunging line."""
    s.rect(x, y, w, h, WHITE)
    s.rect(x, y, w, 26, RED)
    s.text(x + 10, y + 6, "NASDAQ -5.28%", 2, WHITE)
    s.text(x + w - 10, y + 6, "S&P -3.70%", 2, WHITE, align="r")
    # descending bars
    bars = [96, 88, 92, 76, 80, 64, 68, 52, 44, 30]
    bw = (w - 40) // len(bars)
    for i, bh in enumerate(bars):
        bx = x + 20 + i * bw
        s.rect(bx, y + h - 14 - bh, bw - 6, bh, RED)
    # plunging line over the bars
    pts = [(x + 20 + i * bw, y + h - 20 - bh) for i, bh in enumerate(bars)]
    for a, b in zip(pts, pts[1:]):
        s.line(a[0], a[1], b[0], b[1], INK)
        s.line(a[0], a[1] + 1, b[0], b[1] + 1, INK)
    # big down arrow
    ax, ay = x + w - 52, y + 40
    s.rect(ax + 10, ay, 12, 34, RED)
    s.poly([(ax, ay + 34), (ax + 32, ay + 34), (ax + 16, ay + 62)], RED)


# ---------------------------------------------------------------- map
def lonlat(lon, lat, mx, my, mw, mh):
    px = mx + int((lon + 170.0) / 360.0 * mw)
    py = my + int((75.0 - lat) / 135.0 * mh)
    return px, py


CONTINENTS = {
    "NA": [(-168, 66), (-140, 70), (-120, 72), (-95, 80), (-80, 73),
           (-70, 62), (-75, 45), (-80, 32), (-90, 20), (-97, 16),
           (-105, 20), (-115, 30), (-125, 40), (-125, 49), (-140, 60),
           (-165, 60)],
    "SA": [(-80, 10), (-60, 5), (-50, -5), (-35, -8), (-40, -20),
           (-48, -28), (-58, -35), (-65, -45), (-70, -55), (-73, -40),
           (-75, -20), (-80, -5)],
    "EU": [(-10, 36), (-9, 43), (0, 46), (-2, 50), (5, 53), (8, 57),
           (18, 56), (21, 60), (28, 60), (30, 68), (40, 68), (45, 60),
           (40, 55), (35, 50), (30, 45), (28, 40), (22, 36), (15, 38),
           (10, 38), (3, 42)],
    "AF": [(-6, 35), (10, 37), (20, 32), (32, 31), (35, 28), (43, 12),
           (51, 11), (48, 0), (40, -10), (35, -20), (32, -29), (25, -34),
           (18, -35), (12, -18), (8, 4), (-8, 5), (-15, 12)],
    "AS": [(40, 68), (60, 70), (90, 75), (120, 73), (150, 70), (170, 66),
           (178, 65), (170, 60), (160, 55), (142, 50), (135, 43),
           (128, 38), (122, 30), (115, 22), (108, 12), (103, 8),
           (100, 8), (95, 15), (90, 22), (85, 20), (80, 13), (77, 8),
           (72, 20), (66, 25), (60, 25), (55, 26), (50, 29), (48, 30),
           (44, 29), (40, 35), (38, 36), (40, 45), (42, 55)],
    "OC": [(113, -22), (125, -15), (135, -12), (142, -11), (147, -19),
           (153, -27), (150, -37), (140, -38), (130, -32), (120, -34),
           (113, -26)],
}

PINS = [  # (num, lon, lat)
    (1, 30.5, 50.0), (2, 46.7, 24.6), (3, -74.0, 40.7), (4, 12.6, 55.7),
    (5, -77.0, 38.9), (6, 4.35, 50.8), (7, 10.0, 51.0), (8, 56.5, 26.5),
    (9, -74.0, 40.7), (10, -122.4, 37.8), (11, 28.0, -26.2),
    (12, -90.0, 30.0), (13, -0.1, 51.5),
]


def draw_map(s, x, y, w, h):
    s.rect(x, y, w, h, SKY)
    for pts in CONTINENTS.values():
        s.poly([lonlat(lo, la, x, y, w, h) for lo, la in pts], LAND)
    # graticule
    for gx in range(x + w // 6, x + w, w // 6):
        s.vline(gx, y, h, bytes((160, 200, 230)), 1)
    # pins 1-13; spread the Europe cluster so none hides another
    offsets = {4: (16, -8), 6: (4, 10), 7: (26, 0), 9: (16, 12)}
    placed = []
    for num, lo, la in PINS:
        px, py = lonlat(lo, la, x, y, w, h)
        dx, dy = offsets.get(num, (0, 0))
        px += dx
        py += dy
        placed.append((num, px, py))
        s.circle(px, py, 11, RED)
        s.circle(px, py, 11, WHITE, fill=False)
        s.circle(px, py, 9, RED)
        lbl = str(num)
        s.text(px - text_w(lbl, 1) // 2, py - 4, lbl, 1, WHITE)
    return placed


# ---------------------------------------------------------------- content
LEADS = [
    ("1", "KYIV", "FRI 20 NOV",
     "RUSSIA HITS KYIV BRIDGES",
     "MISSILES SPILL INTO POLAND",
     "400+ DRONES AND 110+ MISSILES OVERNIGHT. 3 DNIPRO BRIDGES "
     "DAMAGED. 2 MISSILES LAND IN POLAND."),
    ("2", "RIYADH", "SAT 21 NOV",
     "3 MISSILES DOWNED",
     "OVER RIYADH AT 02:00",
     "HOUTHI BALLISTIC MISSILES INTERCEPTED OVER THE CAPITAL. NO "
     "CASUALTIES. 13 ALERTS SINCE THURSDAY."),
    ("3", "WALL STREET", "FRI 20 NOV",
     "WALL STREET IN",
     "CORRECTION",
     "NASDAQ -5.28% IN A DAY. S AND P -3.70%, 7TH STRAIGHT FALL. "
     "BITCOIN BELOW $60,000."),
]

FIGURES = [
    ("400+", "DRONES", "110+ MISSILES AT UKRAINE"),
    ("3", "BRIDGES", "HIT IN KYIV"),
    ("3", "MISSILES", "DOWNED OVER RIYADH"),
    ("-5.28%", "NASDAQ", "FRIDAY CLOSE"),
    ("EUR 7.9BN", "EU AID", "LARGEST PAYMENT TO UKRAINE"),
    ("235", "MONTHS", "GUPTA SENTENCE, NEW YORK"),
]

CARDS = [
    ("4", "COPENHAGEN", "FRI 20 NOV",
     "DENMARK FOILS PLOT TO KILL RAPPER KYIVSTONER",
     "3 ARRESTED. RUSSIAN DEFENCE ATTACHE EXPELLED IN 7 DAYS."),
    ("5", "WASHINGTON", "FRI 20 NOV",
     "TRUMP: BIG TAX ON AI DATA CENTRES BUILT ABROAD",
     "IRAN DECISION DEFERRED TO 2027. WANTS A REAL DEAL."),
    ("6", "BRUSSELS", "FRI 20 NOV",
     "UK-EU RESET DEAL SEALED",
     "FOOD CHECKS END 2028. 100,000 YOUTH VISAS A YEAR."),
    ("7", "BRUSSELS", "FRI 20 NOV",
     "EU PAYS UKRAINE EUR 7.9BN",
     "LARGEST SINGLE PAYMENT EVER. TOTAL AID EUR 245.5BN."),
    ("8", "STRAIT OF HORMUZ", "FRI 20 NOV",
     "TANKER HIT BY PROJECTILE, CATCHES FIRE",
     "NO CASUALTIES. TRANSITS DOWN 15% IN A WEEK."),
    ("9", "NEW YORK", "FRI 20 NOV",
     "GUPTA JAILED 19 YEARS 7 MONTHS",
     "FOILED PLOT TO KILL SIKH SEPARATIST PANNUN."),
    ("10", "SAN FRANCISCO", "FRI 20 NOV",
     "ANTHROPIC IPO CLOSES AT $93.5BN - CLAIM ONLY",
     "RIEMANN PROOF CLAIMED IN LEAN CODE, NOT VERIFIED."),
    ("11", "JOHANNESBURG", "FRI 20 NOV",
     "581 WOMEN KILLED IN 3 MONTHS, POLICE SAY",
     "5,590 MURDERS IN THE QUARTER. 16 DAYS CAMPAIGN OPENS."),
    ("12", "NEW ORLEANS", "FRI 20 NOV",
     "COURT VOIDS $1.7TN 2022 SPENDING BILL",
     "PROXY VOTING UNCONSTITUTIONAL, 9-8. ROSE PARDONED."),
    ("13", "LONDON + NYC", "20-21 NOV",
     "PRICE UNDISPUTED CHAMPION. MAMDANI: CLOSE RIKERS",
     "KANE OUT FOR MONTHS. NEPAL PM TO MEET MODI."),
]

BRIEF = [
    "14 UNICEF: 1,144 CHILDREN HURT IN UKRAINE, JAN-OCT",
    "15 ESTONIA TO CLOSE ROAD BORDERS WITH RUSSIA",
    "16 UKRAINE HITS DRUZHBA PIPELINE; LASER DEFENCE USED",
    "17 US SANCTIONS 4 IRANIANS OVER OIL REVENUES",
    "18 INDUSIND BANK SACKS EX-CEO, SEEKS PAY CLAWBACK",
    "19 EUROZONE CONFIDENCE -16.9 IN NOVEMBER",
    "20 DEUTSCHE BANK LEAK: $582M EPSTEIN DEALS FLAGGED",
    "21 ANGOLA TO PAY $180M FOR 10% OF DE BEERS",
    "22 COST-OF-LIVING PROTESTS SWEEP EUROPE",
    "23 FRENCH POLICE SENTENCED OVER ZECLER BEATING",
    "24 BRAZIL: LULA BOOSTS INDIGENOUS LAND PROTECTION",
    "25 PHILIPPINES PET SCANDAL: DEAD PETS ON LIVESTREAM",
    "26 WHITE HOUSE REMOVES ITS CYBER-SECURITY CHIEF",
    "27 US-IRAN LOW-LEVEL STRIKES CONTINUE",
    "28 FTSE BANKS SLIDE: HSBC -2.3%, STAN CHART -3.9%",
    "29 SENATE EASES DATA-CENTRE APPROVALS",
    "30 US TO CURB ADVANCED AI CHIP EXPORTS TO SE ASIA",
    "31 UN WARNS HUDAYDAH ATTACKS THREATEN AID LIFELINE",
    "32 SOUTH AFRICA: ANC FIGHTS TO HOLD CITIES",
    "33 MAPLE LEAFS STILL WINLESS IN NOVEMBER",
    "34 US DECLASSIFIES MORE UFO FOOTAGE",
    "35 HARRY KANE OUT FOR MONTHS WITH ANKLE INJURY",
    "36 GOLD $3,515 AS SAFE HAVENS ALSO SELL OFF",
]

REGIONS = ("EUROPE 13", "AMERICAS 7", "MIDDLE EAST 4", "AFRICA 3",
           "ASIA-PACIFIC 3", "LATIN AMERICA 1", "WORLD 5")

TIMELINE = ("THE DAY IN ORDER: OVERNIGHT - DRONES HIT UKRAINE. "
            "02:00 RIYADH - 3 MISSILES DOWNED. 13:56 CET - EU PAYS "
            "EUR 7.9BN. US CLOSE - NASDAQ -5.28%.")

DATECHECK = ("DATE CHECK - NOT TODAY: 19 NOV - ICJ MYANMAR VERDICT. "
             "SHENZHEN TRILATERAL. ANTHROPIC IPO $83. GTA VI LAUNCH. "
             "MONGOLIA RESIGNS. 17 NOV - KERCH BRIDGE.")


# ---------------------------------------------------------------- draw
def draw():
    s = Sheet(W, H, PAPER)
    s.rect(0, 0, W, 8, RED)

    # ---- masthead
    s.rect(0, 8, W, 100, NAVY)
    s.text(W // 2, 20, "THE WORLD IN ONE DAY", 3, YELLOW, align="c")
    s.text(W // 2, 46, "SATURDAY 21 NOVEMBER 2026", 5, WHITE, align="c")
    s.text(W // 2, 88, "36 STORIES - 7 REGIONS - ONE DAY OF WORLD NEWS",
           2, SKY_DK, align="c")

    # ---- three lead panels
    px, pw, gap = 8, 328, 12
    for i, (num, place, date, h1, h2, body) in enumerate(LEADS):
        x = px + i * (pw + gap)
        y = 116
        s.border(x, y, pw, 280, INK, 2)
        if i == 0:
            scene_kyiv(s, x + 2, y + 2, pw - 4, 150)
        elif i == 1:
            scene_riyadh(s, x + 2, y + 2, pw - 4, 150)
        else:
            scene_markets(s, x + 2, y + 2, pw - 4, 150)
        s.rect(x, y + 152, pw, 22, RED if i == 0 else NAVY)
        s.text(x + 8, y + 157, num + "  " + place, 2, WHITE)
        s.text(x + pw - 8, y + 157, date, 2, YELLOW, align="r")
        yy = s.para(x + 8, y + 180, h1 + " " + h2, 2, INK, pw - 16, lh=17)
        s.para(x + 8, yy + 2, body, 2, NAVY2, pw - 16, lh=15)

    # ---- figures band
    fy, fh, fw = 404, 48, 164
    for i, (big, unit, what) in enumerate(FIGURES):
        x = 8 + i * (fw + 8)
        s.rect(x, fy, fw, fh, WHITE)
        s.border(x, fy, fw, fh, INK, 1)
        s.text(x + fw // 2, fy + 4, big, 3, RED, align="c")
        lines = wrap(unit + " - " + what, 26)
        ly = fy + 27
        for ln in lines[:2]:
            s.text(x + fw // 2, ly, ln, 1, INK, align="c")
            ly += 9

    # ---- map + regions
    my, mh = 460, 152
    s.border(8, my, 700, mh, INK, 2)
    s.text(16, my + 6, "THE WORLD - PINS 1 TO 13", 2, INK)
    draw_map(s, 16, my + 26, 684, mh - 32)
    rx = 716
    s.border(rx, my, 300, mh, INK, 2)
    s.rect(rx, my, 300, 24, NAVY)
    s.text(rx + 10, my + 5, "HOW THE DAY BREAKS DOWN", 2, WHITE)
    yy = my + 30
    for reg in REGIONS:
        s.text(rx + 10, yy, reg, 2, INK)
        yy += 15
    s.text(rx + 10, yy + 2, "36 STORIES, ALL DATED", 1, GREY)

    # ---- cards grid 5 x 2
    cy, ch, cw = 620, 104, 196
    for i, (num, place, date, head, body) in enumerate(CARDS):
        x = 8 + (i % 5) * (cw + 8)
        y = cy + (i // 5) * (ch + 8)
        s.rect(x, y, cw, ch, WHITE)
        s.border(x, y, cw, ch, INK, 1)
        s.rect(x, y, cw, 18, NAVY2)
        s.text(x + 6, y + 3, num + " " + place, 1, WHITE)
        s.text(x + cw - 6, y + 3, date, 1, YELLOW, align="r")
        yy = s.para(x + 6, y + 22, head, 1, INK, cw - 12, lh=10)
        s.para(x + 6, yy + 1, body, 1, GREY, cw - 12, lh=9)

    # ---- world in brief
    by = 836
    s.rect(0, by, W, 24, NAVY)
    s.text(8, by + 5, "THE WORLD IN BRIEF - 14 TO 36", 2, WHITE)
    s.text(W - 8, by + 5, "EVERY ITEM VERIFIED 20-21 NOV", 1, SKY_DK,
           align="r")
    col_w = 328
    for col in range(3):
        x = 8 + col * (col_w + 12)
        yy = by + 30
        for item in BRIEF[col * 8:(col + 1) * 8]:
            s.text(x, yy, item, 1, INK)
            yy += 12

    # ---- footer: timeline + date check + sources
    fy2 = 964
    s.hline(0, fy2, W, INK, 2)
    s.para(8, fy2 + 5, TIMELINE, 1, INK, W - 16, lh=11)
    s.para(8, fy2 + 19, DATECHECK, 1, RED, W - 16, lh=11)
    s.text(W // 2, 1008, "SOURCES: REUTERS - BBC - CNN - AP - EUROPEAN "
           "COMMISSION - US DOJ - UKMTO - 21 NOV 2026", 1, GREY, align="c")
    return s


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    data = draw().png_bytes()
    with open(os.path.join(outdir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
