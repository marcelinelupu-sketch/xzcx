#!/usr/bin/env python3
"""Build the Frog's Dream Mega Pack (SPEC section 10).

Reads the same content JSON the website uses (source/content/) and writes print-ready vector PDFs
with embedded fonts to deliverables/megapack/Frogs-Dream-Mega-Pack/, then zips the folder to
deliverables/megapack/Frogs-Dream-Mega-Pack.zip. It is safe to re-run: the pack folder is rebuilt
from scratch and every random choice is seeded from the theme slug, so the output is stable.

Usage:
  python3 source/megapack/build_megapack.py                 # full pack + zip + premium previews
  python3 source/megapack/build_megapack.py --only bingo    # quick partial run (no zip)
  python3 source/megapack/build_megapack.py --no-samples    # skip the /premium/ preview PNGs

Requirements: reportlab, svglib (pip install svglib), Pillow, and pdftoppm for the preview PNGs.
"""
import argparse
import io
import json
import math
import random
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

try:
    from svglib.svglib import svg2rlg
except ImportError:  # pragma: no cover
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "svglib"], check=False)
    from svglib.svglib import svg2rlg

from reportlab.graphics import renderPDF
from reportlab.graphics import shapes as _rl_shapes
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4, letter, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = Path(__file__).resolve().parent
SRC = HERE.parent
ROOT = SRC.parent
CONTENT = SRC / "content"
IMG = SRC / "static" / "assets" / "img"
OUT_BASE = ROOT / "deliverables" / "megapack"
PACK = "Frogs-Dream-Mega-Pack"
SAMPLES_DIR = IMG / "premium"

FOOTER = "Frog's Dream Mega Pack, frogsdream.com, personal and classroom use"

# Brand palette (SPEC section 12)
POND = HexColor("#2F8F5B")
LILY = HexColor("#8CCB6E")
LILY_LT = HexColor("#E3F2DA")
TINT = HexColor("#F4FAF0")
INK = HexColor("#1F2A24")
GREY = HexColor("#5F6B65")
SOFT = HexColor("#A9B5AE")
SUN = HexColor("#F6C445")
CORAL = HexColor("#F07A5A")
DUSK = HexColor("#3B3A6B")

CHART_PALETTES = {  # same values as routine-chart.js / reward-chart.js
    "mint": dict(dark="#2C7A50", mid="#8CCB6E", light="#E3F2DA", tint="#F4FAF0", pop="#F6C445", ink="#1F2A24", name="Mint"),
    "sky": dict(dark="#2A6496", mid="#8EC1E8", light="#DFEEFA", tint="#F2F8FD", pop="#F6C445", ink="#1E2A36", name="Sky"),
    "peach": dict(dark="#B5553A", mid="#F3A98E", light="#FCE6DC", tint="#FFF6F2", pop="#8CCB6E", ink="#33231E", name="Peach"),
    "lavender": dict(dark="#3B3A6B", mid="#B4A9E3", light="#ECE8FA", tint="#F8F6FD", pop="#F6C445", ink="#24233F", name="Lavender"),
}

PAPERS = [("Letter", "US-Letter", letter), ("A4", "A4", A4)]
M = 36  # page margin (0.5 in)
BOTTOM = 46  # content must stay above this line (footer lives below)

BANNED = re.compile("[‒–—―]| - ")
WARNINGS = []
STATS = {"pdfs": 0, "pages": 0}


def warn(msg):
    WARNINGS.append(msg)
    print("WARNING:", msg, file=sys.stderr)


# ---------------------------------------------------------------------------------------------
# Fonts and text helpers
# ---------------------------------------------------------------------------------------------
pdfmetrics.registerFont(TTFont("FD", str(SRC / "fonts" / "Fredoka-Medium.ttf")))
pdfmetrics.registerFont(TTFont("FDB", str(SRC / "fonts" / "Fredoka-SemiBold.ttf")))


# keep reportlab from referencing the unembedded base-14 fonts (Helvetica, Times-Roman)
_rl_shapes.STATE_DEFAULTS["fontName"] = "FD"


def sw(s, font, size, cs=0):
    return pdfmetrics.stringWidth(s, font, size) + cs * max(0, len(s) - 1)


def chk(s):
    if BANNED.search(s):
        raise ValueError("Banned dash in PDF text: %r" % s)
    return s


def put(c, x, y, s, font="FD", size=11, color=INK, align="left", cs=0):
    """Draw one line of text. align is left, center or right."""
    chk(s)
    c.setFont(font, size)
    c.setFillColor(color)
    w = sw(s, font, size, cs)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    if cs:
        c.drawString(x, y, s, charSpace=cs)
    else:
        c.drawString(x, y, s)
    return w


def wrap(s, font, size, maxw):
    words = s.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if sw(t, font, size) <= maxw:
            cur = t
        else:
            if sw(w, font, size) > maxw:
                return None
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit(s, font, maxw, maxh, maxsize, minsize=6.0, lead=1.12, maxlines=4, where=""):
    size = maxsize
    while size >= minsize:
        lines = wrap(s, font, size, maxw)
        if lines and len(lines) <= maxlines and len(lines) * size * lead <= maxh + 0.01:
            return size, lines
        size -= 0.25
    warn("text needed a forced break (%s): %r" % (where, s))
    size = minsize
    lines, cur = [], ""
    for ch in s:
        if sw(cur + ch, font, size) > maxw:
            lines.append(cur)
            cur = ch.strip()
        else:
            cur += ch
    lines.append(cur)
    return size, lines


def put_block(c, lines, font, size, cx, cy, color=INK, lead=1.12, align="center", x=None):
    """Draw lines vertically centered on cy."""
    n = len(lines)
    L = size * lead
    y = cy + (n - 1) * L / 2 - size * 0.34
    for ln in lines:
        if align == "center":
            put(c, cx, y, ln, font, size, color, "center")
        else:
            put(c, x, y, ln, font, size, color)
        y -= L


def fit_one(s, font, maxw, maxsize, minsize=6):
    size = maxsize
    while size > minsize and sw(s, font, size) > maxw:
        size -= 0.25
    return size


# ---------------------------------------------------------------------------------------------
# Artwork (the site's own hand-coded SVG mascots and icons, drawn as vectors)
# ---------------------------------------------------------------------------------------------
_svg_cache = {}


def svg_drawing(path, color=None):
    key = (str(path), color)
    if key not in _svg_cache:
        src = Path(path).read_text(encoding="utf-8")
        # svglib draws faint opacity shadows as solid shapes; drop them
        src = re.sub(r'<ellipse[^>]*opacity="\.0\d+"[^>]*/>', "", src)
        src = re.sub(r"<title>.*?</title>", "", src)
        if color:
            src = src.replace("currentColor", color)
        _svg_cache[key] = svg2rlg(io.StringIO(src))
    return _svg_cache[key]


def mascot(c, pose, x, y, size):
    name = "frog-mascot.svg" if pose in (None, "mascot") else "frog-%s.svg" % pose
    d = svg_drawing(IMG / name)
    s = size / max(d.width, d.height)
    c.saveState()
    c.translate(x, y)
    c.scale(s, s)
    renderPDF.draw(d, c, 0, 0)
    c.restoreState()


def icon(c, name, x, y, size, color):
    p = IMG / "icons" / ("%s.svg" % name)
    if not p.exists():
        warn("missing icon %s, using star" % name)
        p = IMG / "icons" / "star.svg"
    hexcol = color if isinstance(color, str) else "#%02X%02X%02X" % tuple(int(v * 255) for v in color.rgb())
    d = svg_drawing(p, hexcol)
    s = size / max(d.width, d.height)
    c.saveState()
    c.translate(x, y)
    c.scale(s, s)
    renderPDF.draw(d, c, 0, 0)
    c.restoreState()


# ---------------------------------------------------------------------------------------------
# Document wrapper with header and footer
# ---------------------------------------------------------------------------------------------
class Doc:
    def __init__(self, path, pagesize, title, subject=""):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.c = canvas.Canvas(str(path), pagesize=pagesize, pageCompression=1, invariant=1,
                                    initialFontName="FD", initialFontSize=11)
        self.c.setTitle(chk(title))
        self.c.setAuthor("Frog's Dream")
        self.c.setSubject(chk(subject or FOOTER))
        self.c.setCreator("frogsdream.com")
        self.c.setKeywords("Frog's Dream, printable, Mega Pack")
        self.set_size(pagesize)
        self.pages = 0

    def set_size(self, size):
        self.c.setPageSize(size)
        self.W, self.H = size

    def end_page(self, label=""):
        c = self.c
        y = 20
        mascot(c, "mascot", M - 1, y - 4, 13)
        put(c, M + 15, y, FOOTER, "FD", 7.5, GREY)
        if label:
            put(c, self.W - M, y, label, "FD", 7.5, GREY, "right")
        c.showPage()
        self.pages += 1

    def save(self):
        self.c.save()
        STATS["pdfs"] += 1
        STATS["pages"] += self.pages


def header(d, title, subtitle=None, pose="mascot", color=POND, top=None, right_pad=0):
    """Page title, optional subtitle, mascot at right, and a two-tone rule. Returns y below it."""
    c = d.c
    W = d.W
    top = d.H - M if top is None else top
    msz = 50
    mascot(c, pose, W - M - msz - right_pad, top - msz + 6, msz)
    avail = W - 2 * M - msz - 12 - right_pad
    size = fit_one(title, "FDB", avail, 26, 14)
    y = top - size * 0.82
    put(c, M, y, title, "FDB", size, INK)
    y -= 8
    if subtitle:
        ssz, lines = fit(subtitle, "FD", avail, 30, 11, 8.5, maxlines=2, where="subtitle")
        for ln in lines:
            y -= ssz * 1.15
            put(c, M, y, ln, "FD", ssz, GREY)
    y = min(y - 9, top - msz - 2)
    c.setLineCap(1)
    c.setStrokeColor(LILY_LT)
    c.setLineWidth(3)
    c.line(M, y, W - M, y)
    c.setStrokeColor(color)
    c.line(M, y, M + 64, y)
    c.setLineCap(0)
    return y - 14


def checkbox(c, x, y, s, color=POND, lw=1.1, r=2.2):
    c.setStrokeColor(color)
    c.setLineWidth(lw)
    c.roundRect(x, y, s, s, r, stroke=1, fill=0)


def tip_box(c, x, y_top, w, label, body, color=POND, fill=TINT):
    size, lines = fit(body, "FD", w - 28 - sw(label + " ", "FDB", 9.5), 40, 9.5, 7.5, maxlines=3, where="tip")
    h = max(len(lines) * size * 1.25 + 14, 26)
    c.setFillColor(fill)
    c.setStrokeColor(LILY)
    c.setLineWidth(0.8)
    c.roundRect(x, y_top - h, w, h, 8, stroke=1, fill=1)
    lw = put(c, x + 12, y_top - 7 - size, label, "FDB", 9.5, color)
    yy = y_top - 7 - size
    for ln in lines:
        put(c, x + 16 + lw, yy, ln, "FD", size, INK)
        yy -= size * 1.25
    return y_top - h


def safe_name(s):
    s = s.replace("'", "").replace(".", "").replace("&", "and")
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")
    return s


# ---------------------------------------------------------------------------------------------
# Content loading
# ---------------------------------------------------------------------------------------------
def load_site():
    return json.loads((CONTENT / "site.json").read_text(encoding="utf-8"))


def section_slugs(site, section):
    out = []
    for g in site["sections"].get(section, {}).get("groups", []):
        out.extend(g["slugs"])
    return out


def load_theme(section, slug):
    p = CONTENT / "themes" / section / ("%s.json" % slug)
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    d["slug"] = slug
    d["section"] = section
    d["name"] = d.get("toolTitle") or d.get("shortTitle") or slug
    return d


def seeded(*parts):
    return random.Random("frogsdream-megapack:" + ":".join(str(p) for p in parts))


# ---------------------------------------------------------------------------------------------
# BINGO
# ---------------------------------------------------------------------------------------------
NUMBER_SLUGS = {"75-ball-bingo-cards", "90-ball-bingo-tickets", "number-bingo-1-30-for-kids"}
HUMAN_SLUGS = {"icebreaker-find-someone-who"}
CARDS_PER_THEME = 40


def bingo_pool(theme):
    """Unique square texts, plus a caller list of (call, square)."""
    squares, calls, seen = [], [], set()
    for it in theme["items"]:
        if isinstance(it, dict):
            sq, call = str(it["square"]).strip(), str(it.get("call", it["square"])).strip()
        else:
            sq = call = str(it).strip()
        if not sq:
            continue
        calls.append((call, sq))
        k = sq.lower()
        if k not in seen:
            seen.add(k)
            squares.append(sq)
    return squares, calls


def unique_cards(pool, ncells, n, rng, where):
    cards, sets, tries = [], set(), 0
    while len(cards) < n:
        pick = rng.sample(pool, ncells)
        key = frozenset(x.lower() for x in pick)
        tries += 1
        if key in sets and tries < 20000:
            continue
        sets.add(key)
        cards.append(pick)
    layouts = {tuple(x.lower() for x in cd) for cd in cards}
    assert len(layouts) == n, "duplicate bingo card in %s" % where
    if len(sets) < n:
        warn("%s: some cards share the same words in a different order" % where)
    return cards


def card_frame(c, x, y, w, h, title, label, letters=None, pose="mascot"):
    """Rounded card with a title strip. Returns the grid rectangle (gx, gy, gw, gh)."""
    c.setFillColor(white)
    c.setStrokeColor(POND)
    c.setLineWidth(1.8)
    c.roundRect(x, y, w, h, 14, stroke=1, fill=1)
    # title strip
    ts = 32
    mascot(c, pose, x + 12, y + h - ts + 1, 26)
    tsize = fit_one(title, "FDB", w - 44 - 90, 17, 10)
    put(c, x + 44, y + h - ts / 2 - 5 - tsize * 0.32 + 5, title, "FDB", tsize, INK)
    put(c, x + w - 14, y + h - ts / 2 - 3, label, "FD", 9, GREY, "right")
    top = y + h - ts - 6
    gx, gw = x + 12, w - 24
    if letters:
        top -= 28
    return gx, y + 12, gw, top - (y + 12)


def draw_letters(c, rects, letters, top):
    for (rx, ry, rw, rh), L in zip(rects, letters):
        c.setFillColor(POND)
        c.roundRect(rx, top - 24 + 28, rw, 24, 6, stroke=0, fill=1)
        put(c, rx + rw / 2, top + 4 + 6.5, L, "FDB", 16, white, "center")


def draw_free(c, x, y, w, h, txt):
    c.setFillColor(LILY_LT)
    c.roundRect(x, y, w, h, 6, stroke=0, fill=1)
    msz = min(h * 0.55, w * 0.45, 34)
    size, lines = fit(txt, "FDB", w - 8, h - msz - 6, 11, 6, maxlines=2, where="free space")
    th = len(lines) * size * 1.1
    total = msz + 2 + th
    top = y + h / 2 + total / 2
    mascot(c, "mascot", x + w / 2 - msz / 2, top - msz, msz)
    put_block(c, lines, "FDB", size, x + w / 2, top - msz - 2 - th / 2, POND, 1.1)


def draw_grid_cells(c, gx, gy, gw, gh, cols, rows, gap=4, maxratio=1.75):
    """Return list of cell rects (x, y, w, h) row-major from top-left, centered in the area."""
    ch = (gh - gap * (rows - 1)) / rows
    cw = (gw - gap * (cols - 1)) / cols
    cw = min(cw, ch * maxratio)
    totw = cols * cw + gap * (cols - 1)
    ox = gx + (gw - totw) / 2
    rects = []
    for r in range(rows):
        for col in range(cols):
            rects.append((ox + col * (cw + gap), gy + gh - (r + 1) * ch - r * gap, cw, ch))
    return rects, ox, totw


def draw_word_card(c, x, y, w, h, theme, cells, grid, free_text, label, human=False):
    letters = list("BINGO") if grid == 5 else None
    gx, gy, gw, gh = card_frame(c, x, y, w, h, theme["name"], label, letters)
    rects, ox, totw = draw_grid_cells(c, gx, gy, gw, gh, grid, grid, maxratio=1.9 if human else 1.75)
    # one shared text size per card so the squares look even; only long entries shrink below it
    rw0, rh0 = rects[0][2], rects[0][3]
    numeric = all(v is None or re.fullmatch(r"[0-9]{1,3}", v) for v in cells)
    cap = 24 if numeric else (21 if all(v is None or len(v) <= 5 for v in cells) else (18 if grid <= 4 else 15))
    fitted = sorted(fit(v, "FD", rw0 - 16, rh0 - 10, cap, 6, maxlines=2)[0] for v in cells if v)
    base = max(fitted[len(fitted) // 4], 10.5)
    if letters:
        draw_letters(c, rects, letters, gy + gh)
    for (rx, ry, rw, rh), val in zip(rects, cells):
        if val is None:
            draw_free(c, rx, ry, rw, rh, free_text)
            c.setStrokeColor(POND)
            c.setLineWidth(1)
            c.roundRect(rx, ry, rw, rh, 6, stroke=1, fill=0)
            continue
        c.setStrokeColor(POND)
        c.setLineWidth(1)
        c.roundRect(rx, ry, rw, rh, 6, stroke=1, fill=0)
        if human:
            line_y = ry + 11
            size, lines = fit(val, "FD", rw - 10, rh - 26, 13, 6, maxlines=5, where=theme["slug"])
            put_block(c, lines, "FD", size, rx + rw / 2, ry + 18 + (rh - 18) / 2, INK)
            c.setStrokeColor(SOFT)
            c.setLineWidth(0.7)
            c.line(rx + 8, line_y, rx + rw - 8, line_y)
        else:
            size, lines = fit(val, "FD", rw - 14, rh - 8, base, 6, maxlines=4, where=theme["slug"])
            put_block(c, lines, "FD", size, rx + rw / 2, ry + rh / 2, INK)
    return ox, totw


def cut_line(c, y, W):
    c.setStrokeColor(SOFT)
    c.setLineWidth(0.6)
    c.setDash([4, 4])
    c.line(M, y, W - M, y)
    c.setDash()


def caller_checklist(d, theme, squares, calls):
    """Caller checklist page(s) with tick boxes, in alphabetical order."""
    c = d.c
    is_math = any(call != sq for call, sq in calls)
    if is_math:
        entries = sorted(calls, key=lambda t: (int(re.sub(r"\D", "", t[1]) or 0), t[0]))
        labels = ["%s  (answer %s)" % (call, sq) for call, sq in entries]
        sub = "Read out the problem. Players cover the answer if it is on their card. Tick each problem once you have called it."
    else:
        labels = sorted(squares, key=lambda s: s.lower())
        sub = "Tick each one as you call it, in any order you like. A quick way to choose: cut the list into slips and draw them from a bowl."
    y0 = header(d, "Caller checklist for %s" % theme["name"], sub, "pencil")
    n = len(labels)
    longest = max(sw(t, "FD", 10.5) for t in labels)
    cols = 3 if longest < (d.W - 2 * M) / 3 - 30 else 2
    rows = math.ceil(n / cols)
    avail = y0 - BOTTOM - 10
    rh = min(26, avail / rows)
    colw = (d.W - 2 * M) / cols
    for i, t in enumerate(labels):
        col, r = divmod(i, rows)
        x = M + col * colw
        y = y0 - (r + 1) * rh + 4
        bs = min(11, rh - 6)
        checkbox(c, x, y + (rh - bs) / 2 - 3, bs)
        size, lines = fit(t, "FD", colw - bs - 18, rh - 2, 10.5, 6.5, maxlines=2, where="caller")
        put_block(c, lines, "FD", size, 0, y + rh / 2 - 3, INK, align="left", x=x + bs + 8)
    d.end_page("Caller checklist")


def build_word_bingo(theme, out_dirs, counts):
    squares, calls = bingo_pool(theme)
    opts = theme.get("defaultOptions", {})
    human = theme["slug"] in HUMAN_SLUGS
    grid = 4 if int(opts.get("grid", 5) or 5) <= 4 else 5
    free = grid == 5
    need = grid * grid - (1 if free else 0)
    if len(squares) < need and grid == 5:
        grid, free, need = 4, False, 16
    if len(squares) < need:
        warn("bingo/%s has only %d unique squares, skipped" % (theme["slug"], len(squares)))
        return
    free_text = (opts.get("freeText") or "FREE").strip() or "FREE"
    rng = seeded("bingo", theme["slug"])
    cards = unique_cards(squares, need, CARDS_PER_THEME, rng, theme["slug"])
    per_page = 1 if human else 2
    for paper, folder, size in PAPERS:
        path = out_dirs["bingo"] / folder / ("%s-%s.pdf" % (safe_name(theme["name"]), paper))
        d = Doc(path, size, "%s, %d cards (%s)" % (theme["name"], CARDS_PER_THEME, paper))
        c = d.c
        for p in range(0, CARDS_PER_THEME, per_page):
            avail_top, avail_bot = d.H - M + 6, BOTTOM - 4
            gap = 26
            ch = (avail_top - avail_bot - gap * (per_page - 1)) / per_page
            for k in range(per_page):
                idx = p + k
                cells = list(cards[idx])
                if free:
                    cells.insert(len(cells) // 2, None)
                y = avail_top - (k + 1) * ch - k * gap
                draw_word_card(c, M, y, d.W - 2 * M, ch, theme, cells, grid, free_text,
                               "Card %d of %d" % (idx + 1, CARDS_PER_THEME), human)
                if k < per_page - 1:
                    cut_line(c, y - gap / 2, d.W)
            lab = "Cards %d and %d" % (p + 1, p + 2) if per_page == 2 else "Card %d" % (p + 1)
            d.end_page(lab)
        caller_checklist(d, theme, squares, calls)
        d.save()
    counts["bingo_themes"] += 1
    counts["bingo_cards"] += CARDS_PER_THEME


# ----- 75-ball -----------------------------------------------------------------------------------
def make_75_cards(n, rng):
    cards, seen = [], set()
    while len(cards) < n:
        cols = [rng.sample(range(15 * i + 1, 15 * i + 16), 5) for i in range(5)]
        cols[2][2] = 0
        key = tuple(tuple(col) for col in cols)
        if key in seen:
            continue
        seen.add(key)
        cards.append(cols)
    for cols in cards:  # validate
        for i, col in enumerate(cols):
            for r, v in enumerate(col):
                if i == 2 and r == 2:
                    assert v == 0
                else:
                    assert 15 * i + 1 <= v <= 15 * i + 15
            assert len(set(col)) == 5
    assert len({tuple(map(tuple, cd)) for cd in cards}) == n
    return cards


def draw_75_card(c, x, y, w, h, cols, label):
    gx, gy, gw, gh = card_frame(c, x, y, w, h, "75-Ball Bingo", label, list("BINGO"))
    rects, ox, totw = draw_grid_cells(c, gx, gy, gw, gh, 5, 5, maxratio=1.75)
    draw_letters(c, rects, "BINGO", gy + gh)
    for i, (rx, ry, rw, rh) in enumerate(rects):
        r, col = divmod(i, 5)
        v = cols[col][r]
        if v == 0:
            draw_free(c, rx, ry, rw, rh, "FREE")
        c.setStrokeColor(POND)
        c.setLineWidth(1)
        c.roundRect(rx, ry, rw, rh, 6, stroke=1, fill=0)
        if v:
            put(c, rx + rw / 2, ry + rh / 2 - 9, str(v), "FDB", 26, INK, "center")


def caller_board(d, title, sub, rows, col_labels=None):
    """rows: list of (label, [numbers]). col_labels: optional header row above the columns."""
    c = d.c
    y0 = header(d, title, sub, "pencil")
    nrows = len(rows)
    ncols = max(len(r[1]) for r in rows)
    lab_w = 34 if rows[0][0] else 0
    avail_w = d.W - 2 * M - lab_w
    cell = min(avail_w / ncols, (y0 - BOTTOM - 10) / nrows, 44)
    if col_labels:
        cell = min(avail_w / ncols, (y0 - BOTTOM - 40) / nrows, 44)
    ox = M + (d.W - 2 * M - lab_w - cell * ncols) / 2
    if col_labels:
        for k, L in enumerate(col_labels):
            c.setFillColor(POND)
            c.roundRect(ox + k * cell + 4, y0 - 30, cell - 8, 28, 7, stroke=0, fill=1)
            put(c, ox + k * cell + cell / 2, y0 - 22, L, "FDB", 17, white, "center")
        y0 -= 36
    for r, (lab, nums) in enumerate(rows):
        y = y0 - (r + 1) * cell
        if lab:
            c.setFillColor(POND)
            c.roundRect(ox, y + 3, lab_w - 6, cell - 6, 6, stroke=0, fill=1)
            put(c, ox + (lab_w - 6) / 2, y + cell / 2 - 6, lab, "FDB", 16, white, "center")
        for k, v in enumerate(nums):
            cx = ox + lab_w + k * cell + cell / 2
            c.setStrokeColor(LILY)
            c.setLineWidth(1)
            c.circle(cx, y + cell / 2, cell / 2 - 3, stroke=1, fill=0)
            put(c, cx, y + cell / 2 - cell * 0.13, str(v), "FDB", cell * 0.38, INK, "center")
    d.end_page("Caller board")


def build_75(out_dirs, counts, n=100):
    rng = seeded("bingo", "75-ball")
    cards = make_75_cards(n, rng)
    for paper, folder, size in PAPERS:
        path = out_dirs["number"] / folder / ("75-Ball-Bingo-100-Cards-%s.pdf" % paper)
        d = Doc(path, size, "75-Ball Bingo, 100 cards (%s)" % paper)
        for p in range(0, n, 2):
            top, bot, gap = d.H - M + 6, BOTTOM - 4, 26
            ch = (top - bot - gap) / 2
            for k in range(2):
                y = top - (k + 1) * ch - k * gap
                draw_75_card(d.c, M, y, d.W - 2 * M, ch, cards[p + k], "Card %d of %d" % (p + k + 1, n))
            cut_line(d.c, top - ch - gap / 2, d.W)
            d.end_page("Cards %d and %d" % (p + 1, p + 2))
        caller_board(d, "75-ball caller board",
                     "Cross off each number as you call it. B is 1 to 15, I is 16 to 30, N is 31 to 45, G is 46 to 60 and O is 61 to 75.",
                     [("", [15 * i + r + 1 for i in range(5)]) for r in range(15)], col_labels="BINGO")
        d.save()
    counts["cards_75"] = n


# ----- 90-ball strips -----------------------------------------------------------------------------
COL_RANGES = [list(range(1, 10))] + [list(range(10 * i, 10 * i + 10)) for i in range(1, 8)] + [list(range(80, 91))]


def _layout_ticket(colcounts, rng):
    order = sorted(range(9), key=lambda i: (-colcounts[i], rng.random()))
    grid = [[False] * 9 for _ in range(3)]
    rowfill = [0, 0, 0]

    def combos(k):
        from itertools import combinations
        cs = list(combinations(range(3), k))
        rng.shuffle(cs)
        return cs

    def dfs(i):
        if i == 9:
            return all(f == 5 for f in rowfill)
        col = order[i]
        left = 9 - i - 1
        for rows in combos(colcounts[col]):
            if any(rowfill[r] >= 5 for r in rows):
                continue
            for r in rows:
                rowfill[r] += 1
                grid[r][col] = True
            if all(5 - rowfill[r] <= left for r in range(3)) and dfs(i + 1):
                return True
            for r in rows:
                rowfill[r] -= 1
                grid[r][col] = False
        return False

    return grid if dfs(0) else None


def make_strip(rng):
    for _ in range(2000):
        counts = [[1] * 9 for _ in range(6)]
        rem_t = [6] * 6
        units = []
        for col, rngs in enumerate(COL_RANGES):
            units += [col] * (len(rngs) - 6)
        rng.shuffle(units)
        units.sort(key=lambda col: -len(COL_RANGES[col]))  # bigger columns first
        ok = True
        for col in units:
            ch = [t for t in range(6) if rem_t[t] > 0 and counts[t][col] < 3]
            if not ch:
                ok = False
                break
            mx = max(rem_t[t] for t in ch)
            t = rng.choice([t for t in ch if rem_t[t] == mx])
            counts[t][col] += 1
            rem_t[t] -= 1
        if not ok or any(rem_t):
            continue
        layouts = [_layout_ticket(counts[t], rng) for t in range(6)]
        if any(l is None for l in layouts):
            continue
        tickets = [[[0] * 9 for _ in range(3)] for _ in range(6)]
        for col, rngs in enumerate(COL_RANGES):
            nums = rngs[:]
            rng.shuffle(nums)
            pos = 0
            for t in range(6):
                k = counts[t][col]
                mine = sorted(nums[pos:pos + k])
                pos += k
                rows = [r for r in range(3) if layouts[t][r][col]]
                for r, v in zip(rows, mine):
                    tickets[t][r][col] = v
        validate_strip(tickets)
        return tickets
    raise RuntimeError("could not build a 90-ball strip")


def validate_strip(tickets):
    assert len(tickets) == 6
    allnums = []
    for t in tickets:
        assert len(t) == 3 and all(len(r) == 9 for r in t)
        for r in t:
            assert sum(1 for v in r if v) == 5, "row must hold 5 numbers"
        for col in range(9):
            vals = [t[r][col] for r in range(3) if t[r][col]]
            assert vals, "every column needs a number on every ticket"
            assert vals == sorted(vals), "numbers go down each column in order"
            assert all(v in COL_RANGES[col] for v in vals), "number in the wrong column"
        allnums += [v for r in t for v in r if v]
    assert sorted(allnums) == list(range(1, 91)), "strip must use 1 to 90 exactly once"


def build_90(out_dirs, counts, n=20):
    rng = seeded("bingo", "90-ball")
    strips, seen = [], set()
    while len(strips) < n:
        s = make_strip(rng)
        key = tuple(tuple(tuple(r) for r in t) for t in s)
        if key in seen:
            continue
        seen.add(key)
        strips.append(s)
    alltickets = [tuple(tuple(r) for r in t) for s in strips for t in s]
    assert len(set(alltickets)) == len(alltickets)
    for paper, folder, size in PAPERS:
        path = out_dirs["number"] / folder / ("90-Ball-Bingo-20-Strips-%s.pdf" % paper)
        d = Doc(path, size, "90-Ball Bingo, 20 strips of 6 tickets (%s)" % paper)
        c = d.c
        for si, strip in enumerate(strips):
            y0 = header(d, "90-Ball Bingo Tickets",
                        "Strip %d of %d. These 6 tickets use every number from 1 to 90 exactly once. Cut along the dashed lines." % (si + 1, n),
                        "celebrating")
            slot = (y0 - BOTTOM + 4) / 6
            th = slot - 22
            tw = d.W - 2 * M
            for ti, t in enumerate(strip):
                ty = y0 - ti * slot - 13 - th
                put(c, M + 4, ty + th + 4, "Strip %d, ticket %d" % (si + 1, ti + 1), "FD", 8.5, GREY)
                c.setStrokeColor(POND)
                c.setLineWidth(1.6)
                c.setFillColor(white)
                c.roundRect(M, ty, tw, th, 10, stroke=1, fill=1)
                cw, rh = (tw - 12) / 9, (th - 12) / 3
                for r in range(3):
                    for col in range(9):
                        x = M + 6 + col * cw
                        y = ty + 6 + (2 - r) * rh
                        v = t[r][col]
                        if v:
                            c.setStrokeColor(LILY)
                            c.setLineWidth(0.8)
                            c.roundRect(x + 1.5, y + 1.5, cw - 3, rh - 3, 4, stroke=1, fill=0)
                            put(c, x + cw / 2, y + rh / 2 - rh * 0.2, str(v), "FDB", min(rh * 0.58, 20), INK, "center")
                        else:
                            c.setFillColor(LILY_LT)
                            c.roundRect(x + 1.5, y + 1.5, cw - 3, rh - 3, 4, stroke=0, fill=1)
                if ti < 5:
                    cut_line(c, ty - 4.5, d.W)
            d.end_page("Strip %d of %d" % (si + 1, n))
        caller_board(d, "90-ball caller board",
                     "Cross off each number as you call it. Each row holds ten numbers, so a quick glance shows what is left.",
                     [("", list(range(10 * r + 1, 10 * r + 11))) for r in range(9)])
        d.save()
    counts["strips_90"] = n
    counts["tickets_90"] = n * 6


# ---------------------------------------------------------------------------------------------
# WORD SEARCH
# ---------------------------------------------------------------------------------------------
DIRS8 = [(0, 1), (1, 0), (1, 1), (-1, 1), (0, -1), (-1, 0), (-1, -1), (1, -1)]
LEVELS = [
    ("easy", "Easy", [(0, 1), (1, 0)], "Words run across from left to right and down from top to bottom."),
    ("hard", "Challenge", DIRS8, "Words hide in all 8 directions, including diagonals and backwards."),
]
BLOCK = ["FUCK", "FUK", "SHIT", "CUNT", "DICK", "COCK", "PISS", "TWAT", "SLUT", "WHORE", "FAG", "NAZI",
         "ASS", "TIT", "CUM", "SEX", "PORN", "RAPE", "KKK", "NIGG", "DAMN", "BOOB", "PENIS", "BUTT", "POOP",
         "CRAP", "HOMO", "JIZZ", "WANK", "KILL", "DIE", "GOD"]


def clean_word(w):
    return re.sub(r"[^A-Za-z]", "", w).upper()


def lines_of(grid):
    n = len(grid)
    out = []
    for r in range(n):
        for col in range(n):
            for dr, dc in DIRS8:
                cells = []
                rr, cc = r, col
                while 0 <= rr < n and 0 <= cc < n and len(cells) < 6:
                    cells.append((rr, cc))
                    rr += dr
                    cc += dc
                out.append(cells)
    return out


def occurrences(grid, word):
    n = len(grid)
    found = set()
    for r in range(n):
        for col in range(n):
            if grid[r][col] != word[0]:
                continue
            for dr, dc in DIRS8:
                cells = []
                for k, ch in enumerate(word):
                    rr, cc = r + dr * k, col + dc * k
                    if not (0 <= rr < n and 0 <= cc < n) or grid[rr][cc] != ch:
                        break
                    cells.append((rr, cc))
                else:
                    found.add(frozenset(cells))
    return found


def make_wordsearch(words, size, dirs, rng, where):
    entries = [(w, clean_word(w)) for w in words if len(clean_word(w)) >= 2]
    entries.sort(key=lambda e: -len(e[1]))
    size = max(size, max(len(e[1]) for e in entries))
    for attempt in range(60):
        if attempt and attempt % 12 == 0:
            size += 1
        g = [[None] * size for _ in range(size)]
        placed = []
        ok = True
        for orig, w in entries:
            done = False
            hard_dirs = [dd for dd in dirs if dd not in ((0, 1), (1, 0))]
            for _ in range(500):
                # in the Challenge level, favor diagonal and backward words so the level earns its name
                dr, dc = rng.choice(hard_dirs) if hard_dirs and rng.random() < 0.85 else rng.choice(dirs)
                r0 = rng.randrange(size)
                c0 = rng.randrange(size)
                r1, c1 = r0 + dr * (len(w) - 1), c0 + dc * (len(w) - 1)
                if not (0 <= r1 < size and 0 <= c1 < size):
                    continue
                cells = [(r0 + dr * k, c0 + dc * k) for k in range(len(w))]
                if all(g[r][c] in (None, w[k]) for k, (r, c) in enumerate(cells)):
                    # avoid placing a word entirely on top of another
                    if all(g[r][c] is not None for r, c in cells):
                        continue
                    for k, (r, c) in enumerate(cells):
                        g[r][c] = w[k]
                    placed.append(dict(orig=orig, word=w, cells=cells))
                    done = True
                    break
            if not done:
                ok = False
                break
        if not ok:
            continue
        word_cells = set(cl for p in placed for cl in p["cells"])
        for _ in range(200):
            grid = [[g[r][c] or chr(65 + rng.randrange(26)) for c in range(size)] for r in range(size)]
            if fill_ok(grid, word_cells, placed):
                return grid, placed, size
        # give up on this layout, try again
    raise RuntimeError("word search could not place all words: %s" % where)


def fill_ok(grid, word_cells, placed):
    for cells in lines_of(grid):
        s = "".join(grid[r][c] for r, c in cells)
        for b in BLOCK:
            if s.startswith(b) and not all(cl in word_cells for cl in cells[:len(b)]):
                return False
    allsets = [frozenset(p["cells"]) for p in placed]
    for p in placed:
        occ = occurrences(grid, p["word"])
        extra = [o for o in occ if o != frozenset(p["cells"])]
        for o in extra:
            # a second copy is fine only when it sits inside another listed word (STAR inside STARFISH)
            if not any(o <= s for s in allsets if s != frozenset(p["cells"])) and o != frozenset(p["cells"]):
                return False
    return True


def draw_wordsearch_page(d, theme, level_name, level_desc, grid, placed, key=False, label=""):
    c = d.c
    sub = ("Answer key, %s level. " % level_name + "Every hidden word is circled.") if key else \
          ("%s level. %s" % (level_name, level_desc))
    ttl = ("%s Answer Key" % theme["name"]) if key else theme["name"]
    y0 = header(d, ttl, sub, "pencil" if not key else "celebrating")
    words = [p["orig"] for p in sorted(placed, key=lambda p: p["orig"].lower())]
    n = len(grid)
    fullw = d.W - 2 * M
    wsz = 12
    longest = max(sw(w, "FD", wsz) for w in words) + 18
    ncol = 4 if longest < fullw / 4 - 6 else (3 if longest < fullw / 3 - 6 else 2)
    rows = math.ceil(len(words) / ncol)
    list_h = 30 + rows * 18 + 8
    side = min(fullw, y0 - BOTTOM - list_h - 14)
    cell = min(side / n, 36)
    side = cell * n
    gx = (d.W - side) / 2
    gy = y0 - side
    # frame
    c.setStrokeColor(POND)
    c.setLineWidth(1.8)
    pad = 6
    c.roundRect(gx - pad, gy - pad, side + 2 * pad, side + 2 * pad, 12, stroke=1, fill=0)
    if key:
        for p in placed:
            (r0, c0), (r1, c1) = p["cells"][0], p["cells"][-1]
            x0, y0c = gx + c0 * cell + cell / 2, gy + side - r0 * cell - cell / 2
            x1, y1c = gx + c1 * cell + cell / 2, gy + side - r1 * cell - cell / 2
            ang = math.degrees(math.atan2(y1c - y0c, x1 - x0))
            ln = math.hypot(x1 - x0, y1c - y0c)
            rad = cell * 0.4
            c.saveState()
            c.translate(x0, y0c)
            c.rotate(ang)
            c.setFillColor(LILY)
            c.setFillAlpha(0.35)
            c.setStrokeColor(POND)
            c.setLineWidth(1.1)
            c.roundRect(-rad, -rad, ln + 2 * rad, 2 * rad, rad, stroke=1, fill=1)
            c.restoreState()
    word_cells = set(cl for p in placed for cl in p["cells"])
    fs = cell * 0.56
    for r in range(n):
        for col in range(n):
            ch = grid[r][col]
            colr = INK
            font = "FDB"
            if key and (r, col) not in word_cells:
                colr, font = SOFT, "FD"
            put(c, gx + col * cell + cell / 2, gy + side - r * cell - cell / 2 - fs * 0.35, ch, font, fs, colr, "center")
    # word list box
    ly = gy - pad - 12
    bh = list_h - 6
    c.setFillColor(TINT)
    c.roundRect(M, ly - bh, fullw, bh, 10, stroke=0, fill=1)
    put(c, M + 14, ly - 18, "Words to find (%d)" % len(words), "FDB", 11.5, POND)
    colw = (fullw - 28) / ncol
    for i, w in enumerate(words):
        col, r = divmod(i, rows)
        x = M + 14 + col * colw
        y = ly - 38 - r * 18
        checkbox(c, x, y - 1, 8.5, POND if not key else SOFT, 0.9, 1.6)
        size = fit_one(w, "FD", colw - 20, wsz, 7)
        put(c, x + 14, y, w, "FD", size, INK if not key else GREY)
    d.end_page(label)


def build_wordsearch(theme, out_dirs, counts):
    words = [str(w) for w in theme["items"] if str(w).strip()]
    opts = theme.get("defaultOptions", {})
    base = int(opts.get("size", 14) or 14)
    puzzles = []
    for lvl, name, dirs, desc in LEVELS:
        size = max(12, base) if lvl == "easy" else min(max(base + 1, 14), 18)
        rng = seeded("wordsearch", theme["slug"], lvl)
        grid, placed, size = make_wordsearch(words, size, dirs, rng, theme["slug"])
        assert len(placed) == len(words), "dropped a word in %s" % theme["slug"]
        for p in placed:
            assert len(occurrences(grid, p["word"])) >= 1
        puzzles.append((name, desc, grid, placed))
    for paper, folder, size in PAPERS:
        path = out_dirs["wordsearch"] / folder / ("%s-%s.pdf" % (safe_name(theme["name"]), paper))
        d = Doc(path, size, "%s, 2 levels with answer keys (%s)" % (theme["name"], paper))
        for name, desc, grid, placed in puzzles:
            draw_wordsearch_page(d, theme, name, desc, grid, placed, False, "%s puzzle" % name)
        for name, desc, grid, placed in puzzles:
            draw_wordsearch_page(d, theme, name, desc, grid, placed, True, "%s answer key" % name)
        d.save()
    counts["wordsearch_themes"] += 1
    counts["wordsearch_puzzles"] += len(puzzles)


# ---------------------------------------------------------------------------------------------
# WORD SCRAMBLE
# ---------------------------------------------------------------------------------------------
def scramble_word(w, rng, others):
    letters_only = re.sub(r"[^A-Za-z]", "", w)
    if len(letters_only) < 3 or len(set(letters_only.lower())) < 2:
        return None
    parts = w.upper().split()
    for _ in range(400):
        out = []
        for p in parts:
            chars = list(p)
            if len(set(chars)) > 1:
                for _ in range(50):
                    rng.shuffle(chars)
                    if "".join(chars) != p or len(parts) == 1:
                        break
            out.append("".join(chars))
        s = " ".join(out)
        if s.replace(" ", "") == w.upper().replace(" ", ""):
            continue
        if s.replace(" ", "") in others:
            continue
        if any(b in s.replace(" ", "") for b in BLOCK if len(b) >= 4):
            continue
        return s
    return None


def draw_scramble_page(d, theme, rows_data, hint, bank, label):
    c = d.c
    sub = ("Hint version: the first letter of each answer is filled in for you." if hint
           else "Unscramble each word and write it on the line.")
    y0 = header(d, theme["name"] + (" (Hint Version)" if hint else ""), sub, "pencil")
    fullw = d.W - 2 * M
    bank_h = 0
    if bank:
        words = sorted((w for w, _ in rows_data), key=str.lower)
        bsz = 10.5
        longest = max(sw(w, "FD", bsz) for w in words) + 14
        bcols = max(2, min(5, int((fullw - 24) // longest)))
        brows = math.ceil(len(words) / bcols)
        bank_h = 30 + brows * 15 + 6
    n = len(rows_data)
    cols = 2
    per = math.ceil(n / cols)
    avail = y0 - BOTTOM - (bank_h + 16 if bank else 0)
    rh = min(42, avail / per)
    colw = fullw / cols
    for i, (word, scr) in enumerate(rows_data):
        col, r = divmod(i, per)
        x = M + col * colw
        cy = y0 - r * rh - rh / 2
        c.setFillColor(POND)
        c.circle(x + 10, cy, 9.5, stroke=0, fill=1)
        put(c, x + 10, cy - 3.6, str(i + 1), "FDB", 10, white, "center")
        fs = fit_one(scr, "FDB", colw * 0.5, 14, 8)
        cs = 1.6
        pw = sw(scr, "FDB", fs, cs) + 16
        while pw > colw * 0.52 and cs > 0:
            cs -= 0.4
            pw = sw(scr, "FDB", fs, cs) + 16
        c.setFillColor(LILY_LT)
        c.roundRect(x + 25, cy - 11, pw, 22, 11, stroke=0, fill=1)
        put(c, x + 33, cy - fs * 0.35, scr, "FDB", fs, INK, cs=cs)
        lx0, lx1 = x + 25 + pw + 10, x + colw - 14
        c.setStrokeColor(SOFT)
        c.setLineWidth(0.9)
        c.line(lx0, cy - 8, lx1, cy - 8)
        if hint:
            put(c, lx0 + 2, cy - 5, word.strip()[0].upper(), "FDB", 13, POND)
    if bank:
        by = BOTTOM + bank_h
        c.setFillColor(TINT)
        c.roundRect(M, BOTTOM, fullw, bank_h, 10, stroke=0, fill=1)
        put(c, M + 14, by - 19, "Word bank", "FDB", 11.5, POND)
        colw2 = (fullw - 28) / bcols
        for i, w in enumerate(words):
            col, r = divmod(i, brows)
            put(c, M + 14 + col * colw2, by - 38 - r * 15, w, "FD", fit_one(w, "FD", colw2 - 6, bsz, 7), INK)
    d.end_page(label)


def draw_scramble_key(d, theme, rows_data):
    c = d.c
    y0 = header(d, "%s Answer Key" % theme["name"], "The answers for both the standard and the hint version, in the same order.", "celebrating")
    n = len(rows_data)
    per = math.ceil(n / 2)
    rh = min(30, (y0 - BOTTOM) / per)
    colw = (d.W - 2 * M) / 2
    for i, (word, scr) in enumerate(rows_data):
        col, r = divmod(i, per)
        x = M + col * colw
        y = y0 - r * rh - rh / 2 - 4
        put(c, x + 14, y, "%d." % (i + 1), "FDB", 11, POND, "right")
        put(c, x + 22, y, scr, "FD", fit_one(scr, "FD", colw * 0.42, 11, 7), GREY)
        put(c, x + 22 + colw * 0.45, y, word, "FDB", fit_one(word, "FDB", colw * 0.5, 12, 7), INK)
    d.end_page("Answer key")


def build_scramble(theme, out_dirs, counts):
    words = [str(w).strip() for w in theme["items"] if str(w).strip()]
    rng = seeded("scramble", theme["slug"])
    order = words[:]
    rng.shuffle(order)
    others = {re.sub(r"[^A-Z]", "", w.upper()) for w in words}
    rows = []
    for w in order:
        s = scramble_word(w, rng, others)
        if s is None:
            warn("scramble/%s: skipped %r (cannot be scrambled)" % (theme["slug"], w))
            continue
        rows.append((w, s))
    bank = bool(theme.get("defaultOptions", {}).get("bank", True))
    for paper, folder, size in PAPERS:
        path = out_dirs["scramble"] / folder / ("%s-%s.pdf" % (safe_name(theme["name"]), paper))
        d = Doc(path, size, "%s with answer key (%s)" % (theme["name"], paper))
        draw_scramble_page(d, theme, rows, False, bank, "Puzzle")
        draw_scramble_page(d, theme, rows, True, bank, "Hint version")
        draw_scramble_key(d, theme, rows)
        d.save()
    counts["scramble_themes"] += 1
    counts["scramble_words"] += len(rows)


# ---------------------------------------------------------------------------------------------
# SCAVENGER HUNT
# ---------------------------------------------------------------------------------------------
OUTDOOR = {"backyard", "nature-walk", "park", "neighborhood-walk", "beach", "camping", "fall", "winter",
           "spring-easter", "christmas-lights", "halloween"}


def parse_hunt(items):
    out = []
    for it in items:
        s = str(it)
        pts = None
        if "|" in s:
            s, p = s.rsplit("|", 1)
            try:
                pts = int(p.strip())
            except ValueError:
                pts = None
        out.append((s.strip(), pts))
    return out


def draw_hunt_page(d, theme, items, layout, opts, label):
    c = d.c
    instr = {
        "checklist": "Tick each box when you find it.",
        "two-column": "Tick each box when you find it.",
        "photo": "Find it, snap a photo, then tick the box.",
        "team": "Tick each find, then add up your points at the end.",
    }[layout]
    age = opts.get("ageNote")
    sub = instr + (" %s." % age if age else "")
    y = header(d, theme["name"], sub, "waving")
    fullw = d.W - 2 * M
    # name and time lines
    fields = []
    if opts.get("names", True) or layout == "team":
        fields.append("Team" if layout == "team" else "Name")
    if opts.get("timeLimit"):
        fields.append("Time limit")
    if layout == "team":
        fields.append("Total points")
    if fields:
        fw = fullw / len(fields)
        for i, f in enumerate(fields):
            x = M + i * fw
            w = put(c, x, y - 12, f, "FDB", 11, POND)
            c.setStrokeColor(SOFT)
            c.setLineWidth(0.9)
            c.line(x + w + 6, y - 14, x + fw - 16, y - 14)
        y -= 30
    safety_h = 0
    if theme["slug"] in OUTDOOR:
        safety_h = 54
    any_pts = any(p for _, p in items)
    n = len(items)
    two = layout == "two-column"
    cols = 2 if two else 1
    per = math.ceil(n / cols)
    avail = y - BOTTOM - safety_h
    head_h = 22 if layout in ("team", "photo") else 0
    rh = min(34, (avail - head_h) / per)
    colw = fullw / cols
    if head_h:
        c.setFillColor(LILY_LT)
        c.roundRect(M, y - head_h, fullw, head_h - 2, 6, stroke=0, fill=1)
        put(c, M + 34, y - 15, "Find", "FDB", 10.5, POND)
        if layout == "team":
            put(c, M + fullw - 112, y - 15, "Points", "FDB", 10.5, POND, "center")
            put(c, M + fullw - 40, y - 15, "Found", "FDB", 10.5, POND, "center")
        else:
            put(c, M + fullw - 40, y - 15, "Snap it", "FDB", 10.5, POND, "center")
        y -= head_h
    for i, (txt, pts) in enumerate(items):
        col, r = divmod(i, per)
        x = M + col * colw
        top = y - r * rh
        cy = top - rh / 2
        if r % 2 == 0 and not two:
            c.setFillColor(TINT)
            c.roundRect(x, top - rh + 1, colw, rh - 2, 6, stroke=0, fill=1)
        bs = min(14, rh - 8)
        right = 16
        if layout == "team":
            right = 150
        elif layout == "photo":
            right = 84
        elif any_pts:
            right = 56
        if layout == "team":
            put(c, x + fullw - 112, cy - 4, str(pts or 1), "FDB", 12, INK, "center")
            checkbox(c, x + fullw - 40 - bs / 2, cy - bs / 2, bs)
            tx = x + 12
        else:
            checkbox(c, x + 10, cy - bs / 2, bs)
            tx = x + 10 + bs + 10
        if layout == "photo":
            icon(c, "camera", x + fullw - 40 - 11, cy - 11, 22, "#2F8F5B")
        elif layout != "team" and pts:
            c.setFillColor(SUN)
            c.roundRect(x + colw - 50, cy - 8, 40, 16, 8, stroke=0, fill=1)
            put(c, x + colw - 30, cy - 3.6, "%d pts" % pts, "FDB", 9, INK, "center")
        size, lines = fit(txt, "FD", colw - (tx - x) - right, rh - 4, 12.5, 7, maxlines=2, where=theme["slug"])
        put_block(c, lines, "FD", size, 0, cy, INK, align="left", x=tx)
    if safety_h:
        tip_box(c, M, BOTTOM + safety_h - 6, fullw, "Safety first.",
                "An adult stays close by, everyone stays in sight, and protected plants and wild animals are left where they are found.")
    d.end_page(label)


def build_hunt(theme, out_dirs, counts):
    items = parse_hunt(theme["items"])
    opts = theme.get("defaultOptions", {})
    layout = opts.get("layout", "checklist")
    if layout not in ("checklist", "two-column", "photo", "team"):
        layout = "checklist"
    rng = seeded("hunt", theme["slug"])
    second = None
    if theme["slug"] != "toddler":
        second = "photo" if layout != "photo" else "checklist"
    for paper, folder, size in PAPERS:
        path = out_dirs["hunt"] / folder / ("%s-%s.pdf" % (safe_name(theme["name"]), paper))
        d = Doc(path, size, "%s (%s)" % (theme["name"], paper))
        draw_hunt_page(d, theme, items, layout, opts, "Hunt sheet")
        if second:
            mixed = items[:]
            seeded("hunt", theme["slug"], "b").shuffle(mixed)
            draw_hunt_page(d, theme, mixed, second, opts, "%s version" % ("Photo" if second == "photo" else "Checklist"))
        d.save()
    counts["hunt_themes"] += 1


# ---------------------------------------------------------------------------------------------
# CHARTS
# ---------------------------------------------------------------------------------------------
CHART_DESIGNS = [
    ("bedtime-routine-chart", "toddler-picture-chart", "cards", "Bedtime Picture Chart"),
    ("bedtime-routine-chart", "preschool", "strip", "Bedtime Routine Strip"),
    ("bedtime-routine-chart", "school-age", "weekly", "School Night Weekly Routine"),
    ("reward-chart-maker", "potty-training-chart", "reward", "Potty Training Chart"),
    ("reward-chart-maker", "chore-chart-for-kids", "reward", "Chore Chart"),
    ("reward-chart-maker", "weekly-sticker-chart", "reward", "Weekly Sticker Chart"),
]
PALETTE_ORDER = ["mint", "sky", "peach", "lavender"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def parse_steps(items):
    out = []
    for it in items:
        s = str(it)
        if "|" in s:
            lab, ic = s.split("|", 1)
            out.append((lab.strip(), ic.strip()))
        elif s.strip().endswith(":"):
            continue
        else:
            out.append((s.strip(), "star"))
    return out


def chart_header(d, pal, title, pose="sleeping"):
    c = d.c
    W, H = d.W, d.H
    dark, light = HexColor(pal["dark"]), HexColor(pal["light"])
    # soft page border
    c.setStrokeColor(HexColor(pal["mid"]))
    c.setLineWidth(3)
    c.roundRect(M - 12, BOTTOM - 10, W - 2 * M + 24, H - M - BOTTOM + 22, 18, stroke=1, fill=0)
    bh = 82
    top = H - M
    c.setFillColor(light)
    c.roundRect(M, top - bh, W - 2 * M, bh, 14, stroke=0, fill=1)
    msz = 74
    mascot(c, pose, W - M - msz - 8, top - bh + 4, msz)
    size = fit_one(title, "FDB", W - 2 * M - msz - 50, 32, 16)
    put(c, M + 20, top - 44, title, "FDB", size, dark)
    lw = put(c, M + 20, top - 68, "This chart belongs to", "FD", 11.5, HexColor(pal["ink"]))
    c.setStrokeColor(dark)
    c.setLineWidth(0.9)
    c.line(M + 26 + lw, top - 70, min(M + 26 + lw + 210, W - M - msz - 20), top - 70)
    return top - bh - 16


def draw_chart_cards(d, pal, steps, title):
    c = d.c
    y0 = chart_header(d, pal, title)
    dark, mid, light, pop = (HexColor(pal[k]) for k in ("dark", "mid", "light", "pop"))
    cols = 2
    rows = math.ceil(len(steps) / cols)
    gap = 14
    w = (d.W - 2 * M - gap) / cols
    h = (y0 - BOTTOM - gap * (rows - 1)) / rows
    for i, (lab, ic) in enumerate(steps):
        r, col = divmod(i, cols)
        x = M + col * (w + gap)
        y = y0 - (r + 1) * h - r * gap
        c.setFillColor(white)
        c.setStrokeColor(mid)
        c.setLineWidth(2)
        c.roundRect(x, y, w, h, 16, stroke=1, fill=1)
        c.setFillColor(pop)
        c.circle(x + 22, y + h - 22, 13, stroke=0, fill=1)
        put(c, x + 22, y + h - 27.5, str(i + 1), "FDB", 15, HexColor(pal["ink"]), "center")
        isz = min(h - 70, w * 0.55, 120)
        c.setFillColor(light)
        c.circle(x + w / 2, y + 40 + isz / 2 + 4, isz / 2 + 8, stroke=0, fill=1)
        icon(c, ic, x + w / 2 - isz / 2, y + 44, isz, pal["dark"])
        size = fit_one(lab, "FDB", w - 70, 18, 10)
        put(c, x + w / 2, y + 16, lab, "FDB", size, dark, "center")
        c.setStrokeColor(mid)
        c.setLineWidth(1.5)
        c.circle(x + w - 24, y + h - 24, 13, stroke=1, fill=0)
    d.end_page("%s, %s" % (title, pal["name"]))


def draw_chart_strip(d, pal, steps, title):
    c = d.c
    y0 = chart_header(d, pal, title)
    dark, mid, light, pop = (HexColor(pal[k]) for k in ("dark", "mid", "light", "pop"))
    n = len(steps)
    rh = (y0 - BOTTOM) / n
    w = d.W - 2 * M
    for i, (lab, ic) in enumerate(steps):
        y = y0 - (i + 1) * rh
        bh = rh - 8
        c.setFillColor(HexColor(pal["tint"]) if i % 2 else white)
        c.setStrokeColor(mid)
        c.setLineWidth(1.4)
        c.roundRect(M, y + 4, w, bh, 12, stroke=1, fill=1)
        cy = y + 4 + bh / 2
        c.setFillColor(pop)
        c.circle(M + 24, cy, 13, stroke=0, fill=1)
        put(c, M + 24, cy - 5.5, str(i + 1), "FDB", 15, HexColor(pal["ink"]), "center")
        isz = bh - 12
        c.setFillColor(light)
        c.roundRect(M + 48, cy - isz / 2 - 2, isz + 4, isz + 4, 10, stroke=0, fill=1)
        icon(c, ic, M + 50, cy - isz / 2, isz, pal["dark"])
        size = fit_one(lab, "FDB", w - isz - 160, 22, 11)
        put(c, M + 66 + isz, cy - size * 0.35, lab, "FDB", size, dark)
        bs = min(bh - 16, 36)
        c.setStrokeColor(dark)
        c.setLineWidth(1.6)
        c.roundRect(M + w - bs - 18, cy - bs / 2, bs, bs, 8, stroke=1, fill=0)
    d.end_page("%s, %s" % (title, pal["name"]))


def draw_chart_table(d, pal, steps, title, ncols, colnames, mark, goal=None, times=False):
    c = d.c
    y0 = chart_header(d, pal, title, "sleeping" if not goal else "celebrating")
    dark, mid, light = (HexColor(pal[k]) for k in ("dark", "mid", "light"))
    w = d.W - 2 * M
    goal_h = 40 if goal else 0
    blocks = [list(range(i, min(i + 7, ncols))) for i in range(0, ncols, 7)]
    if len(blocks) > 2:  # long logs (30 days): use one wide table with small boxes
        blocks = [list(range(ncols))]
    nb = len(blocks)
    first_w = min(250, w * 0.34) if len(blocks[0]) <= 7 else min(200, w * 0.26)
    cw = (w - first_w) / len(blocks[0])
    head = 26
    n = len(steps)
    gap = 14 if nb > 1 else 0
    usable = y0 - BOTTOM - (goal_h + 10 if goal else 0) - gap * (nb - 1)
    rh = min(70, (usable / nb - head) / n)
    yb = y0
    for bi, cols in enumerate(blocks):
        c.setFillColor(dark)
        c.roundRect(M, yb - head, w, head, 8, stroke=0, fill=1)
        lab0 = ("Steps" if not goal else "Goals") + ("  (week %d)" % (bi + 1) if nb > 1 else "")
        put(c, M + 14, yb - head + 8.5, lab0, "FDB", 12, white)
        for k, ci in enumerate(cols):
            nm = colnames[ci]
            put(c, M + first_w + k * cw + cw / 2, yb - head + 8.5, nm, "FDB", fit_one(nm, "FDB", cw - 4, 12, 7), white, "center")
        for i, (lab, ic) in enumerate(steps):
            y = yb - head - (i + 1) * rh
            if i % 2 == 0:
                c.setFillColor(HexColor(pal["tint"]))
                c.rect(M, y, w, rh, stroke=0, fill=1)
            cy = y + rh / 2
            isz = min(rh - 12, 40)
            c.setFillColor(light)
            c.roundRect(M + 8, cy - isz / 2 - 3, isz + 6, isz + 6, 8, stroke=0, fill=1)
            icon(c, ic, M + 11, cy - isz / 2, isz, pal["dark"])
            tx = M + 22 + isz
            avail = first_w - (tx - M) - 8
            tsize, lines = fit(lab, "FDB", avail, rh - (16 if times else 6), 14, 7.5, maxlines=2, where="chart")
            off = 6 if times else 0
            put_block(c, lines, "FDB", tsize, 0, cy + off, dark, align="left", x=tx)
            if times:
                put(c, tx, y + 8, "Time ______", "FD", 8.5, HexColor(pal["ink"]))
            for k in range(len(cols)):
                cx = M + first_w + k * cw + cw / 2
                sz = min(cw - 10, rh - 14, 40)
                c.setStrokeColor(mid)
                c.setLineWidth(1.4)
                if mark == "sticker":
                    c.setDash([3, 2.5])
                    c.circle(cx, cy, sz / 2, stroke=1, fill=0)
                    c.setDash()
                else:
                    c.roundRect(cx - sz / 2, cy - sz / 2, sz, sz, 6, stroke=1, fill=0)
        c.setStrokeColor(light)
        c.setLineWidth(0.8)
        tb = yb - head - n * rh
        for k in range(len(cols) + 1):
            x = M + first_w + k * cw
            c.line(x, yb - head, x, tb)
        c.setStrokeColor(mid)
        c.setLineWidth(1.2)
        c.roundRect(M, tb, w, yb - tb, 8, stroke=1, fill=0)
        yb = tb - gap
    if goal:
        gy = BOTTOM + 2
        c.setFillColor(light)
        c.roundRect(M, gy, w, goal_h, 12, stroke=0, fill=1)
        icon(c, "trophy", M + 12, gy + 8, 24, pal["dark"])
        lw = put(c, M + 44, gy + goal_h / 2 - 4.5, "My goal:", "FDB", 13, dark)
        gs = fit_one(goal, "FD", w - lw - 70, 13, 8)
        put(c, M + 50 + lw, gy + goal_h / 2 - 4.5, goal, "FD", gs, HexColor(pal["ink"]))
    d.end_page("%s, %s" % (title, pal["name"]))


def build_chart(section, slug, kind, title, out_dirs, counts):
    theme = load_theme(section, slug)
    if not theme:
        return
    steps = parse_steps(theme["items"])
    opts = theme.get("defaultOptions", {})
    for paper, folder, size in PAPERS:
        land = kind in ("weekly", "reward")
        psize = landscape(size) if land else size
        path = out_dirs["charts"] / folder / ("%s-4-Colors-%s.pdf" % (safe_name(title), paper))
        d = Doc(path, psize, "%s in 4 colors (%s)" % (title, paper))
        for pk in PALETTE_ORDER:
            pal = CHART_PALETTES[pk]
            nm = theme["name"]
            if kind == "cards":
                draw_chart_cards(d, pal, steps, nm)
            elif kind == "strip":
                draw_chart_strip(d, pal, steps, nm)
            elif kind == "weekly":
                draw_chart_table(d, pal, steps, nm, 7, DAYS, "tick", None, times=bool(opts.get("times")))
            else:
                days = int(opts.get("days", 7) or 7)
                names = DAYS if days == 7 else [("Day %d" if days <= 14 else "%d") % (i + 1) for i in range(days)]
                draw_chart_table(d, pal, steps, nm, days, names, opts.get("mark", "sticker"), opts.get("goal") or None)
        d.save()
    counts["chart_designs"] += 1


# ---------------------------------------------------------------------------------------------
# START HERE
# ---------------------------------------------------------------------------------------------
def build_start_here(path, counts):
    d = Doc(path, letter, "Start here: Frog's Dream Mega Pack")
    c = d.c
    W, H = d.W, d.H
    # banner
    c.setFillColor(LILY_LT)
    c.roundRect(M, H - M - 120, W - 2 * M, 120, 18, stroke=0, fill=1)
    mascot(c, "waving", W - M - 120, H - M - 116, 112)
    put(c, M + 22, H - M - 42, "Welcome to the", "FD", 16, POND)
    put(c, M + 22, H - M - 76, "Frog's Dream Mega Pack", "FDB", 30, INK)
    put(c, M + 22, H - M - 100, "Thank you for your support. Here is how to find your way around.", "FD", 11.5, GREY)
    y = H - M - 140

    def h2(t):
        nonlocal y
        y -= 4
        put(c, M, y, t, "FDB", 16, POND)
        y -= 21

    def para(t, size=11, x=M, w=None):
        nonlocal y
        w = w or (W - 2 * M)
        for ln in wrap(t, "FD", size, w):
            put(c, x, y, ln, "FD", size, INK)
            y -= size * 1.36
        y -= 5

    h2("What's inside")
    rows = [
        ("01-Themed-Bingo", "%d bingo themes, %d unique cards each (2 per page) plus a caller checklist" % (counts["bingo_themes"], CARDS_PER_THEME)),
        ("02-Number-Bingo", "%d unique 75-ball cards and %d strips of 6 tickets for 90-ball bingo, with caller boards" % (counts.get("cards_75", 0), counts.get("strips_90", 0))),
        ("03-Word-Searches", "%d themes at 2 levels (Easy and Challenge), each with an answer key" % counts["wordsearch_themes"]),
        ("04-Word-Scrambles", "%d themes, each with a standard sheet, a hint version and an answer key" % counts["scramble_themes"]),
        ("05-Scavenger-Hunts", "%d hunts, most with a second photo or checklist version" % counts["hunt_themes"]),
        ("06-Charts", "%d bedtime routine and reward chart designs, each in 4 colors" % counts["chart_designs"]),
    ]
    for folder, desc in rows:
        c.setFillColor(TINT)
        c.roundRect(M, y - 9, W - 2 * M, 24, 7, stroke=0, fill=1)
        put(c, M + 10, y - 1, folder, "FDB", 11.5, INK)
        put(c, M + 158, y - 1, desc, "FD", fit_one(desc, "FD", W - 2 * M - 166, 11, 7.5), INK)
        y -= 27
    y -= 6
    h2("Letter or A4?")
    para("Every folder holds two copies of each file. Use the US-Letter folder if your printer takes 8.5 x 11 inch paper "
         "(USA, Canada, Mexico), and the A4 folder everywhere else. The start of each file name tells you the theme "
         "and the end tells you the paper size.")
    h2("Printing tips")
    tips = [
        "Print at 100% or Actual size. Fit to page also works but makes everything a little smaller.",
        "Bingo cards last longer on cardstock. A sheet protector and a dry-erase marker make them reusable.",
        "Printing in grayscale works well for every page if you want to save colored ink.",
        "Answer keys are at the back of each word search and word scramble file, so you can stop printing before them.",
        "Each chart file has 4 color versions. Print only the page with the color you like.",
    ]
    for t in tips:
        c.setFillColor(LILY)
        c.circle(M + 5, y + 3.5, 3, stroke=0, fill=1)
        para(t, 11, M + 16, W - 2 * M - 16)
        y += 2
    y -= 4
    h2("Your license")
    para("You may print these files as often as you like for your own home, your own parties and events, and the classes "
         "you teach yourself. Please do not resell or share the files, or upload them where others can download them. "
         "Each teacher who wants the pack needs their own copy. Thank you for keeping a small project going.")
    h2("Need help?")
    para("If a file does not open or print the way it should, write to us through frogsdream.com/contact/ and we will sort it out. "
         "The free generators at frogsdream.com let you change any word list and make fresh cards whenever you need them.")
    if y < BOTTOM:
        warn("Start here page overflows")
    d.end_page("Start here")
    d.save()


# ---------------------------------------------------------------------------------------------
# Previews for /premium/
# ---------------------------------------------------------------------------------------------
def render_png(pdf, page, out_png, w, h):
    tmp = out_png.with_suffix("")
    subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-png", "-singlefile",
                    "-scale-to-x", str(w), "-scale-to-y", str(h), str(pdf), str(tmp)], check=True)
    return tmp.with_suffix(".png")


def make_samples(pack_dir):
    from PIL import Image, ImageDraw, ImageFont
    if not shutil.which("pdftoppm"):
        warn("pdftoppm not found, preview PNGs not made")
        return []
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    picks = [
        ("sample-bingo.png", pack_dir / "01-Themed-Bingo" / "US-Letter", "Christmas-Bingo-Letter.pdf", 1),
        ("sample-word-search.png", pack_dir / "03-Word-Searches" / "US-Letter", "Christmas-Word-Search-Letter.pdf", 1),
        ("sample-chart.png", pack_dir / "06-Charts" / "US-Letter", "Bedtime-Routine-Strip-4-Colors-Letter.pdf", 2),
    ]
    made = []
    font = ImageFont.truetype(str(SRC / "fonts" / "Fredoka-SemiBold.ttf"), 120)
    for name, folder, fname, page in picks:
        pdf = folder / fname
        if not pdf.exists():
            cands = sorted(folder.glob("*.pdf"))
            if not cands:
                continue
            pdf = cands[0]
        out = SAMPLES_DIR / name
        W, H = 900, 1164
        png = render_png(pdf, page, out, W, H)
        im = Image.open(png).convert("RGBA")
        im = im.resize((W, H), Image.LANCZOS)
        layer = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
        dr = ImageDraw.Draw(layer)
        label = "SAMPLE"
        tw = dr.textlength(label, font=font)
        for k, yy in enumerate(range(150, H * 2, 330)):
            off = (k % 2) * 260
            for xx in range(-300 + off, W * 2, int(tw) + 220):
                dr.text((xx, yy), label, font=font, fill=(240, 122, 90, 70))
        layer = layer.rotate(32, resample=Image.BICUBIC)
        layer = layer.crop((W // 2, H // 2, W // 2 + W, H // 2 + H))
        im = Image.alpha_composite(im, layer)
        # corner ribbon
        dr2 = ImageDraw.Draw(im)
        f2 = ImageFont.truetype(str(SRC / "fonts" / "Fredoka-SemiBold.ttf"), 30)
        # top center, so it never covers the page title or the "Card 1 of 40" label
        dr2.rounded_rectangle((W // 2 - 106, 6, W // 2 + 106, 50), 22, fill=(47, 143, 91, 235))
        dr2.text((W // 2, 28), "SAMPLE PAGE", font=f2, fill=(255, 255, 255, 255), anchor="mm")
        # light border
        dr2.rectangle((0, 0, W - 1, H - 1), outline=(214, 222, 217, 255), width=2)
        im = im.convert("RGB").quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE)
        im.save(out, optimize=True)
        made.append(out)
    return made


# ---------------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------------
def zip_pack(pack_dir, zpath):
    if zpath.exists():
        zpath.unlink()
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(pack_dir.rglob("*")):
            if p.is_file():
                info = zipfile.ZipInfo(str(p.relative_to(pack_dir.parent)), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                z.writestr(info, p.read_bytes(), compresslevel=9)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["bingo", "number", "wordsearch", "scramble", "hunt", "charts", "start"])
    ap.add_argument("--limit", type=int, default=0, help="only the first N themes per section (testing)")
    ap.add_argument("--out", default=str(OUT_BASE))
    ap.add_argument("--no-samples", action="store_true")
    ap.add_argument("--no-zip", action="store_true")
    args = ap.parse_args()

    out_base = Path(args.out)
    pack_dir = out_base / PACK
    if args.only is None and pack_dir.exists():
        shutil.rmtree(pack_dir)
    pack_dir.mkdir(parents=True, exist_ok=True)
    out_dirs = {
        "bingo": pack_dir / "01-Themed-Bingo",
        "number": pack_dir / "02-Number-Bingo",
        "wordsearch": pack_dir / "03-Word-Searches",
        "scramble": pack_dir / "04-Word-Scrambles",
        "hunt": pack_dir / "05-Scavenger-Hunts",
        "charts": pack_dir / "06-Charts",
    }
    counts = dict(bingo_themes=0, bingo_cards=0, wordsearch_themes=0, wordsearch_puzzles=0, scramble_themes=0,
                  scramble_words=0, hunt_themes=0, chart_designs=0, cards_75=0, strips_90=0, tickets_90=0)
    site = load_site()

    def themes(section):
        out = []
        for slug in section_slugs(site, section):
            t = load_theme(section, slug)
            if t is None:
                warn("no content yet for %s/%s, skipped" % (section, slug))
                continue
            out.append(t)
        return out[: args.limit] if args.limit else out

    want = lambda k: args.only in (None, k)
    if want("bingo"):
        for t in themes("bingo"):
            if t["slug"] in NUMBER_SLUGS:
                continue
            build_word_bingo(t, out_dirs, counts)
            print("bingo", t["slug"], flush=True)
    if want("number"):
        build_75(out_dirs, counts)
        build_90(out_dirs, counts)
        print("number bingo done", flush=True)
    if want("wordsearch"):
        for t in themes("word-search"):
            build_wordsearch(t, out_dirs, counts)
        print("word searches done", flush=True)
    if want("scramble"):
        for t in themes("word-scramble"):
            build_scramble(t, out_dirs, counts)
        print("scrambles done", flush=True)
    if want("hunt"):
        for t in themes("scavenger-hunt"):
            build_hunt(t, out_dirs, counts)
        print("hunts done", flush=True)
    if want("charts"):
        for section, slug, kind, title in CHART_DESIGNS:
            build_chart(section, slug, kind, title, out_dirs, counts)
        print("charts done", flush=True)
    if want("start") and args.only is None:
        build_start_here(pack_dir / "00-Start-Here.pdf", counts)
    elif args.only == "start":
        build_start_here(pack_dir / "00-Start-Here.pdf", counts)

    summary = dict(counts)
    summary.update(STATS)
    if args.only is None and not args.no_zip:
        zpath = out_base / (PACK + ".zip")
        zip_pack(pack_dir, zpath)
        summary["zip_mb"] = round(zpath.stat().st_size / 1e6, 2)
        if summary["zip_mb"] > 60:
            warn("ZIP is %.1f MB, over the 60 MB target" % summary["zip_mb"])
    summary["folder_mb"] = round(sum(p.stat().st_size for p in pack_dir.rglob("*") if p.is_file()) / 1e6, 2)
    if args.only is None and not args.no_samples:
        summary["samples"] = [str(p.relative_to(ROOT)) for p in make_samples(pack_dir)]
    summary["warnings"] = len(WARNINGS)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
