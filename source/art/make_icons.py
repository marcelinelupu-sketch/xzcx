#!/usr/bin/env python3
"""Line icons for the bedtime routine and reward charts (and a few for the scavenger hunt).

One source of truth for:
  * static/assets/img/icons/<name>.svg   (48x48 viewBox, 2px stroke, currentColor)
  * static/assets/js/{scavenger,routine-chart,reward-chart}.js, built from the readable sources in
    source/art/js/ with the shared drawing kit (source/art/drawkit.js) and the icon, frog and font-width
    data inserted at the "<kit>" placeholder, then minified to stay inside the 30 KB per-tool budget.

Run after editing an icon, source/art/drawkit.js or a tool source in source/art/js/:
    python3 source/art/make_icons.py

Icon element mini-format (also used by the JS drawing kit):
    [#rrggbb][~lineWidth][*|+]shape
    shape:  M...   SVG path (M L H V C S Q T Z, absolute or relative; no arcs)
            o cx cy r       circle
            e cx cy rx ry   ellipse
            r x y w h rx    rounded rectangle
    no prefix = stroked outline, * = filled with the icon color, + = filled with the
    background color and outlined (used to overlap shapes, like the teddy bear's head).
"""
import json
import math
import re
from pathlib import Path

from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
SRC = HERE.parent
ICON_DIR = SRC / "static" / "assets" / "img" / "icons"
JS_DIR = SRC / "static" / "assets" / "js"


def star(cx, cy, R, r, n=5, rot=-90):
    pts = []
    for i in range(n * 2):
        a = math.radians(rot + i * 180 / n)
        rad = R if i % 2 == 0 else r
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"


def sparkle(cx, cy, s):
    return f"M{cx} {cy - s}V{cy + s}M{cx - s} {cy}H{cx + s}"


DROP = "M{x} {y}C{x1} {y2} {x3} {y4} {x3} {y5}C{x3} {y6} {x7} {y8} {x} {y8}C{x9} {y8} {x10} {y6} {x10} {y5}C{x10} {y4} {x11} {y2} {x} {y}Z"


def drop(x, y, s=1.0):
    """Water drop with its tip at (x, y), about 8*s tall."""
    def f(v):
        return f"{v:.1f}"
    return (f"M{f(x)} {f(y)}C{f(x + 1.6 * s)} {f(y + 2.6 * s)} {f(x + 3 * s)} {f(y + 4.2 * s)} {f(x + 3 * s)} {f(y + 5.4 * s)}"
            f"C{f(x + 3 * s)} {f(y + 7 * s)} {f(x + 1.7 * s)} {f(y + 8.3 * s)} {f(x)} {f(y + 8.3 * s)}"
            f"C{f(x - 1.7 * s)} {f(y + 8.3 * s)} {f(x - 3 * s)} {f(y + 7 * s)} {f(x - 3 * s)} {f(y + 5.4 * s)}"
            f"C{f(x - 3 * s)} {f(y + 4.2 * s)} {f(x - 1.6 * s)} {f(y + 2.6 * s)} {f(x)} {f(y)}Z")


HEART = ("M24 40C14 33.5 7 27 7 18.5C7 13.3 11 9.5 15.8 9.5C19.3 9.5 22.3 11.5 24 14.5"
         "C25.7 11.5 28.7 9.5 32.2 9.5C37 9.5 41 13.3 41 18.5C41 27 34 33.5 24 40Z")

# name: (label for alt text and the picture library, [elements])
ICONS = {
    "bath": ("Bath time", [
        "M5 24H43",
        "M8 24V29C8 34.5 12.5 39 18 39H30C35.5 39 40 34.5 40 29V24",
        "M14 39L12 43M34 39L36 43",
        "M12 24V12C12 9.2 14.2 7 17 7C19.8 7 22 9.2 22 12",
        "M19 13H25",
        "o 29 17 3", "o 35.5 13.5 2", "o 36 20 1.6",
    ]),
    "brush-teeth": ("Brush teeth", [
        "M15 11C15 7 18.5 5 21.5 6.2L24 7.2L26.5 6.2C29.5 5 33 7 33 11C33 15 31 17 30.5 21L29.5 26.5"
        "C29.1 28.5 27.1 28.5 26.7 26.5L25.6 21.5H22.4L21.3 26.5C20.9 28.5 18.9 28.5 18.5 26.5L17.5 21C17 17 15 15 15 11Z",
        "r 5 38 38 5 2.5",
        "r 28 32 14 6 1.5",
        "M31.5 32V38M35 32V38M38.5 32V38",
    ]),
    "pajamas": ("Pajamas on", [
        "M17 7L10 10L5 23L10.5 25L14 19V42H34V19L37.5 25L43 23L38 10L31 7C30 10 27.5 12 24 12C20.5 12 18 10 17 7Z",
        "M24 12V42",
        "*o 21 20 1.2", "*o 21 27 1.2", "*o 21 34 1.2",
        "M31.5 25C29.5 25.5 28 27.3 28 29.5C28 32 30 34 32.5 34C34.2 34 35.6 33.1 36.3 31.8C33.8 32 31.5 29.9 31.5 27.3C31.5 26.5 31.6 25.7 31.5 25Z",
    ]),
    "potty": ("Potty", [
        "r 8 5 13 17 2",
        "M11.5 10H16",
        "M6 22H42C42 29.5 36.5 34.5 29 35.5L30 42H17L18 35.5C11 34.5 6 29.5 6 22Z",
        "M21 26H36",
    ]),
    "wash-hands": ("Wash hands", [
        "M17 44V31L12.5 25.5C11.3 24 11.6 22 13 21.2C14.3 20.5 15.8 21 16.6 22.2L18 24V13C18 11.6 19 10.6 20.2 10.6"
        "C21.4 10.6 22.4 11.6 22.4 13V22V10.8C22.4 9.4 23.4 8.4 24.6 8.4C25.8 8.4 26.8 9.4 26.8 10.8V22V12.2"
        "C26.8 10.8 27.8 9.8 29 9.8C30.2 9.8 31.2 10.8 31.2 12.2V23V15.6C31.2 14.2 32.2 13.2 33.4 13.2C34.6 13.2 35.6 14.2 35.6 15.6"
        "V31C35.6 37 33 41 32 44",
        "o 40 7 3", "o 43 14.5 2", "o 8 12 2.5", "o 6.5 19.5 1.5",
    ]),
    "book": ("Pick a book", [
        "M13 6H36V35H16C14.3 35 13 36.3 13 38C13 39.7 14.3 41 16 41H36V35",
        "M13 38V6",
        "M27 6V16L30 13.5L33 16V6",
        "M18 13H23M18 18H23",
    ]),
    "story": ("Bedtime story", [
        "M24 22C20 19 14 18 6 19V41C14 40 20 41 24 44C28 41 34 40 42 41V19C34 18 28 19 24 22Z",
        "M24 22V44",
        sparkle(13, 9, 3.5), sparkle(36, 7, 3),
        "M26.5 6.5C24.8 7 23.5 8.6 23.5 10.5C23.5 12.7 25.3 14.5 27.5 14.5C29 14.5 30.2 13.7 30.9 12.6C28.7 12.8 26.7 10.9 26.7 8.6C26.7 7.9 26.6 7.2 26.5 6.5Z",
    ]),
    "reading": ("Read a book", [
        "M24 13C20 10 14 9 6 10V36C14 35 20 36 24 39C28 36 34 35 42 36V10C34 9 28 10 24 13Z",
        "M24 13V39",
        "M10.5 17H19.5M10.5 22H19.5M10.5 27H17.5",
        "M28.5 17H37.5M28.5 22H37.5M28.5 27H35.5",
    ]),
    "hug": ("Hugs and kisses", [
        "+o 15.5 9.5 4", "+o 32.5 9.5 4",
        "+e 12.5 31 3.8 5.5", "+e 35.5 31 3.8 5.5",
        "+e 18 41.5 4.5 3", "+e 30 41.5 4.5 3",
        "+e 24 32.5 10.5 9.5",
        "+o 24 16 9.5",
        "e 24 19.5 4.2 3.2",
        "*o 24 18.6 1.3", "*o 20.3 13.8 1.2", "*o 27.7 13.8 1.2",
        "M24 38.5C21.5 36.8 20 35.4 20 33.8C20 32.7 20.8 31.9 21.9 31.9C22.8 31.9 23.5 32.4 24 33.1C24.5 32.4 25.2 31.9 26.1 31.9C27.2 31.9 28 32.7 28 33.8C28 35.4 26.5 36.8 24 38.5Z",
    ]),
    "bed": ("Into bed", [
        "M6 10V40", "M6 34H42", "M42 26V40",
        "r 9 19 9 7 3",
        "M21 26V23C21 21.3 22.3 20 24 20H37C39.8 20 42 22.2 42 25V26H6",
        "M28 13H33L28 18H33",
    ]),
    "lights-off": ("Lights out", [
        "M24 5C17.4 5 13 9.8 13 15.5C13 19.5 15 22 17.5 24.5C18.8 25.8 19 27.5 19 29H29C29 27.5 29.2 25.8 30.5 24.5C33 22 35 19.5 35 15.5C35 9.8 30.6 5 24 5Z",
        "M19 33H29M20 37H28M22 41H26",
        "M7 7L41 41",
    ]),
    "water": ("Drink of water", [
        "M12 7H36L32.5 41C32.3 42.7 31 44 29.3 44H18.7C17 44 15.7 42.7 15.5 41Z",
        "M13.4 19C17 17.3 20 20.6 24 19.2C28 17.8 31 20.6 34.6 19",
        "o 21 29 1.6", "o 27 34.5 1.3", "o 25.5 26 1",
    ]),
    "snack": ("Healthy snack", [
        "M24 14.5C21 12 15 11.5 11.5 15C8 18.5 8 25.5 10.5 31.5C13 37.5 17 42 21 42C22.5 42 23 41 24 41C25 41 25.5 42 27 42C31 42 35 37.5 37.5 31.5C40 25.5 40 18.5 36.5 15C33 11.5 27 12 24 14.5Z",
        "M24 14.5C24 10.5 25 7.5 27 5",
        "M26 10C28 6 33 5.2 35.5 6C34.5 10 30 11.5 26 10Z",
        "M15 21C14 23 14 25.5 14.5 27.5",
    ]),
    "toys-away": ("Toys away", [
        "M7 23H41V40C41 41.1 40.1 42 39 42H9C7.9 42 7 41.1 7 40Z",
        "M18 31H30",
        "o 16 15 7", "M10 13C13 15 19 15 22 13",
        "r 26 9 12 12 2",
        "M30 15H34M32 13V17",
    ]),
    "get-dressed": ("Get dressed", [
        "M17 8L7 13L10 21.5L14 20V41H34V20L38 21.5L41 13L31 8C30 11 27.5 13 24 13C20.5 13 18 11 17 8Z",
        "M27 25H32V29.5C32 30.6 31.1 31.5 30 31.5H29C27.9 31.5 27 30.6 27 29.5Z",
    ]),
    "shoes": ("Shoes on", [
        "M5 35V23C5 21.3 6.3 20 8 20H13.5C15.3 20 16.4 21.4 17.4 22.8C19.6 26 23.4 28 27.6 28.5L37.5 29.8C40.6 30.3 43 32.6 43 35.5",
        "M5 35H43V37.5C43 38.9 41.9 40 40.5 40H7.5C6.1 40 5 38.9 5 37.5Z",
        "M19.5 27.5L22 24.5M24 29.5L26.5 26.5",
        "M5 30H11",
    ]),
    "breakfast": ("Eat breakfast", [
        "M6 25H42C42 33 36 38.5 28 39.3V42H20V39.3C12 38.5 6 33 6 25Z",
        "M32 25L41 9",
        "M16 20C14.5 17.5 17.5 15.5 16 13M23 20C21.5 17.5 24.5 15.5 23 13",
    ]),
    "backpack": ("Pack my bag", [
        "M14 17C14 13.7 16.7 11 20 11H28C31.3 11 34 13.7 34 17V40C34 41.1 33.1 42 32 42H16C14.9 42 14 41.1 14 40Z",
        "M20 11V9C20 7.3 21.3 6 23 6H25C26.7 6 28 7.3 28 9V11",
        "M18 28H30V35C30 36.7 28.7 38 27 38H21C19.3 38 18 36.7 18 35Z",
        "M18 32H30", "M14 22H34",
        "M14 21C11 22 10 25 10 28V35M34 21C37 22 38 25 38 28V35",
    ]),
    "hair-brush": ("Brush hair", [
        "e 24 15 10 11",
        "M21 26L20 41C20 42.7 21.3 44 23 44H25C26.7 44 28 42.7 28 41L27 26",
        "*o 20 10.5 1.3", "*o 24 9.5 1.3", "*o 28 10.5 1.3",
        "*o 19.5 15.5 1.3", "*o 24 15 1.3", "*o 28.5 15.5 1.3",
        "*o 21 20 1.3", "*o 27 20 1.3",
    ]),
    "vitamins": ("Vitamins", [
        "r 14 5 20 7 2",
        "M16 12H32V40C32 42.2 30.2 44 28 44H20C17.8 44 16 42.2 16 40Z",
        "M16 21H32V35H16",
        "M24 24.5V31.5M20.5 28H27.5",
    ]),
    "quiet-time": ("Quiet time", [
        "M24 11C28.5 15 29.5 22.5 24 30C18.5 22.5 19.5 15 24 11Z",
        "M24 30C20 24 14 21.5 7 22.5C8.5 28.5 15 31 24 30Z",
        "M24 30C28 24 34 21.5 41 22.5C39.5 28.5 33 31 24 30Z",
        "M9 36C15 34 33 34 39 36",
        "M14 41H34",
    ]),
    "music": ("Calm music", [
        "M18 34V12L38 8V30",
        "M18 17.5L38 13.5",
        "*e 14.5 34.5 4.5 3.5", "*e 34.5 30.5 4.5 3.5",
    ]),
    "sun": ("Wake up", [
        "o 24 24 8.5",
        "M24 5V10M24 38V43M5 24H10M38 24H43M10.6 10.6L14.1 14.1M33.9 33.9L37.4 37.4M10.6 37.4L14.1 33.9M33.9 14.1L37.4 10.6",
    ]),
    "moon": ("Goodnight", [
        "M30 7C21 6 11 13 11 24.5C11 35 19.5 42.5 29.5 41.5C23.5 38.5 19.5 32 19.5 24.5C19.5 17 23.5 10.5 30 7Z",
        sparkle(36, 16, 3.5), sparkle(33, 31, 2.5),
    ]),
    "star": ("Do my best", [star(24, 25.5, 19, 8.6)]),
    "sticker": ("Sticker", [
        "M10 6H38C40.2 6 42 7.8 42 10V30L30 42H10C7.8 42 6 40.2 6 38V10C6 7.8 7.8 6 10 6Z",
        "M42 30H34C31.8 30 30 31.8 30 34V42",
        star(22, 22.5, 10, 4.5),
    ]),
    "trophy": ("Reward", [
        "M15 7H33V18C33 23 29 27 24 27C19 27 15 23 15 18Z",
        "M15 10H9.5V13C9.5 17 12 19.5 15.5 19.8M33 10H38.5V13C38.5 17 36 19.5 32.5 19.8",
        "M24 27V34",
        "M18 34H30L31 40H17Z",
        "M14 40H34",
        star(24, 16.5, 4.5, 2),
    ]),
    "make-bed": ("Make my bed", [
        "M6 12V40", "M6 34H42", "M42 26V40",
        "r 9 19.5 9 6.5 3",
        "M21 26V24C21 22.3 22.3 21 24 21H37C39.8 21 42 23.2 42 26H6",
        "M28 30H36",
        sparkle(30, 9, 3.5), sparkle(39, 13, 2.5),
    ]),
    "dishes": ("Clear my dishes", [
        "o 25 25 12", "o 25 25 6.5",
        "M7 7V14C7 16.2 8.3 18 10 18C11.7 18 13 16.2 13 14V7", "M10 7V43",
        "M41 43V7C38 9.5 37 15 37 22H41",
    ]),
    "feed-pet": ("Feed the pet", [
        "M7 32H41", "M9.5 32L12 41H36L38.5 32",
        "M14 32C15.5 28.5 32.5 28.5 34 32",
        "*e 24 19.5 5.5 4.5",
        "*e 15.8 13 2.4 3", "*e 21 8.8 2.4 3", "*e 27 8.8 2.4 3", "*e 32.2 13 2.4 3",
    ]),
    "laundry": ("Help with laundry", [
        "r 9 5 30 38 3",
        "M9 13H39",
        "*o 14 9 1.3", "*o 18.5 9 1.3", "M27 9H34",
        "o 24 28 9.5",
        "M16 29C19 26.5 22 31.5 25 29C28 26.5 30 31 32.5 28.5",
    ]),
    "plants": ("Water the plants", [
        "M13 27H35V31H13Z",
        "M15 31H33L31 43H17Z",
        "M24 27V15",
        "M24 19C24 14 20.5 11 15 11C15 16 18.5 19 24 19Z",
        "M24 16C24 11 27.5 8 33 8C33 13 29.5 16 24 16Z",
        drop(40, 13, 0.9),
    ]),
    "trash": ("Take out the trash", [
        "M12 14H36L34 41C33.9 42.1 33 43 31.9 43H16.1C15 43 14.1 42.1 14 41Z",
        "M8 14H40",
        "M20 14V10C20 8.9 20.9 8 22 8H26C27.1 8 28 8.9 28 10V14",
        "M19.5 20L20.5 37M24 20V37M28.5 20L27.5 37",
    ]),
    "homework": ("Homework", [
        "M30 40H9V6H25L32 13V24",
        "M25 6V13H32",
        "M14 19H27M14 25H27M14 31H22",
        "M28 44V39L39 28L44 33L33 44Z",
        "M36 31L41 36",
    ]),
    "screen-off": ("Screens off", [
        "r 6 9 36 24 3",
        "M24 33V39M17 40H31",
        "M9 5L39 43",
    ]),
    "kindness": ("Be kind", [HEART, sparkle(41, 7, 3), sparkle(7, 38, 2.5)]),
    "clock": ("On time", ["o 24 24 18", "M24 13V24L31 28.5"]),
    "camera": ("Take a photo", [
        "M6 16C6 14.9 6.9 14 8 14H14L17 9H31L34 14H40C41.1 14 42 14.9 42 16V37C42 38.1 41.1 39 40 39H8C6.9 39 6 38.1 6 37Z",
        "o 24 26 8", "o 24 26 3.5", "*o 36 19 1.4",
    ]),
    "search": ("Look closely", ["o 20 20 12", "M29 29L41 41", "M14 17C15 14.5 17 13 19.5 12.5"]),
}

# Decoration only (not written as files, not shown in the picture library).
DECOR = {"_star": ("Star", ["*" + star(24, 25.5, 19, 8.6)])}

# Which icons each tool embeds (the charts get the whole picture library).
CHART_ICONS = [n for n in ICONS if n not in ("search", "camera")]
TOOL_ICONS = {
    "scavenger.js": ["search", "camera", "star", "trophy", "clock"],
    "routine-chart.js": [n for n in CHART_ICONS if n not in ("dishes", "laundry", "trash", "plants", "trophy", "sticker")],
    "reward-chart.js": CHART_ICONS,
}
TOOL_FROGS = {"scavenger.js": [], "routine-chart.js": ["sleep", "happy"], "reward-chart.js": ["happy"]}

# Mascot frogs (200x200 art) for the chart corners, ported from static/assets/img/frog-*.svg.
FROG_BODY = [
    "#2F8F5B*e 52 160 30 23", "#2F8F5B*e 148 160 30 23", "#2F8F5B*e 42 181 22 8", "#2F8F5B*e 158 181 22 8",
    "#5DB572*e 100 143 56 44", "#FFF9EC*e 100 152 36 30", "#2F8F5B*e 74 182 15 7", "#2F8F5B*e 126 182 15 7",
    "#5DB572*e 100 97 68 45", "#5DB572*o 64 60 24", "#5DB572*o 136 60 24",
]
FROGS = {
    "sleep": FROG_BODY + [
        "#8CCB6E*o 100 80 6", "#8CCB6E*o 86 72 3.5", "#8CCB6E*o 115 73 4",
        "#1F2A24~4.5M51 62q13 10 26 0M123 62q13 10 26 0",
        "#F4A09A*e 52 106 10 6", "#F4A09A*e 148 106 10 6",
        "#1F2A24~4M88 112q12 8 24 0",
        "#3B3A6B*M72 46C78 4 140 -14 170 20C150 14 132 22 128 46Z", "#FFF9EC*r 66 38 68 12 6", "#F6C445*o 171 23 9",
        "#3B3A6B~3.5M26 26h14l-14 14h14M8 8h9l-9 9h9",
    ],
    "happy": FROG_BODY + [
        "#FFFFFF*o 64 60 16", "#FFFFFF*o 136 60 16", "#1F2A24*o 66 62 9", "#1F2A24*o 138 62 9",
        "#FFFFFF*o 69 58 3", "#FFFFFF*o 141 58 3", "#F4A09A*e 52 106 10 6", "#F4A09A*e 148 106 10 6",
        "#1F2A24~4.5M80 110q20 16 40 0",
    ],
}


def widths(ttf: Path, bold_synth=False) -> str:
    """95 width codes for chars 32..126: chr(35 + round(advance * 1000 / unitsPerEm / 12))."""
    f = TTFont(str(ttf))
    upm = f["head"].unitsPerEm
    cmap = f.getBestCmap()
    hmtx = f["hmtx"]
    out = []
    for c in range(32, 127):
        g = cmap.get(c)
        w = hmtx[g][0] * 1000 / upm if g else 556
        out.append(chr(35 + round(w / 12)))
    return "".join(out)


def svg_file(name, label, els):
    parts = []
    for e in els:
        parts.append(element_svg(e))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="{label}"><title>{label}</title>'
            + "".join(parts) + "</svg>\n")


EL = re.compile(r"^(#[0-9A-Fa-f]{6})?(?:~([\d.]+))?([*+]?)\s*(.*)$")


def element_svg(e):
    m = EL.match(e)
    color, lw, mode, body = m.groups()
    attrs = ""
    if mode == "*":
        attrs = ' fill="currentColor" stroke="none"'
    elif mode == "+":
        attrs = ' fill="#fff"'
    if body.startswith("M"):
        return f'<path d="{body}"{attrs}/>'
    k, *n = body.split()
    if k == "o":
        return f'<circle cx="{n[0]}" cy="{n[1]}" r="{n[2]}"{attrs}/>'
    if k == "e":
        return f'<ellipse cx="{n[0]}" cy="{n[1]}" rx="{n[2]}" ry="{n[3]}"{attrs}/>'
    if k == "r":
        return f'<rect x="{n[0]}" y="{n[1]}" width="{n[2]}" height="{n[3]}" rx="{n[4]}"{attrs}/>'
    raise ValueError(e)


def check(els, name):
    for e in els:
        m = EL.match(e)
        body = m.group(4)
        if body.startswith("M") and re.search(r"[AaSsTt]", body):
            raise SystemExit(f"{name}: arcs and S/T are not supported in icon paths: {body[:40]}")


def compact(els):
    return [re.sub(r"\s+", " ", e.strip()) for e in els]


IDENT = re.compile(r"[A-Za-z0-9_$]")


def minify_js(src: str) -> str:
    """Small, conservative JS minifier for the kit: drops comments and any whitespace that does not
    separate two identifier characters. Strings and regex literals are copied untouched."""
    out, i, n, last = [], 0, len(src), ""
    while i < n:
        ch = src[i]
        if src.startswith("/*", i):
            i = src.index("*/", i) + 2
            continue
        if src.startswith("//", i) and (not out or out[-1] != "\\"):
            i = src.find("\n", i)
            i = n if i < 0 else i
            continue
        if ch in "'\"`":
            j = i + 1
            while src[j] != ch:
                j += 2 if src[j] == "\\" else 1
            out.append(src[i:j + 1]); last = ch; i = j + 1
            continue
        if ch == "/" and (last in "(,=:[!&|?{};+-*%<>~^" or last == ""):
            j, cls = i + 1, False
            while True:
                c = src[j]
                if c == "\\": j += 2; continue
                if c == "[": cls = True
                elif c == "]": cls = False
                elif c == "/" and not cls: break
                j += 1
            j += 1
            while j < n and src[j].isalpha(): j += 1
            out.append(src[i:j]); last = "/"; i = j
            continue
        if ch.isspace():
            j = i
            while j < n and src[j].isspace(): j += 1
            nxt = src[j] if j < n else ""
            if last and nxt and IDENT.match(last) and IDENT.match(nxt):
                out.append(" ")
            elif last and nxt and last in "+-" and nxt == last:
                out.append(" ")
            i = j
            continue
        out.append(ch); last = ch; i += 1
    return "".join(out)


def splice(path: Path, block: str):
    s = path.read_text(encoding="utf-8")
    a, b = "/* <kit>", "/* </kit> */"
    i, j = s.find(a), s.find(b)
    if i < 0 or j < 0:
        raise SystemExit(f"{path.name}: missing <kit> markers")
    s = s[:i] + block + s[j + len(b):]
    path.write_text(s, encoding="utf-8")


def main():
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    for name, (label, els) in ICONS.items():
        check(els, name)
        (ICON_DIR / f"{name}.svg").write_text(svg_file(name, label, els), encoding="utf-8")
    print(f"wrote {len(ICONS)} icons to {ICON_DIR}")

    fonts = SRC / "fonts"
    wt = {
        "d": widths(SRC / "static" / "assets" / "fonts" / "fredoka-600.ttf"),
        "r": widths(Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf")),
        "b": widths(Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf")),
    }
    kit = (HERE / "drawkit.js").read_text(encoding="utf-8")
    kit_core, _, kit_editor = kit.partition("/* @editor */")
    for fname, names in TOOL_ICONS.items():
        src = HERE / "js" / fname
        if not src.exists():
            continue
        names = names + (list(DECOR) if fname != "scavenger.js" else [])
        allicons = {**ICONS, **DECOR}
        icons = {n: compact(allicons[n][1]) for n in names}
        labels = {n: ICONS[n][0] for n in names if n in ICONS}
        frogs = {k: FROGS[k] for k in TOOL_FROGS[fname]}
        body = kit_core + (kit_editor if fname != "scavenger.js" else "")
        body = (body.replace("__WIDTHS__", json.dumps(wt, separators=(",", ":")))
                .replace("__ICONS__", json.dumps(icons, separators=(",", ":")))
                .replace("__LABELS__", json.dumps(labels, separators=(",", ":")))
                .replace("__FROGS__", json.dumps({k: compact(v) for k, v in frogs.items()}, separators=(",", ":"))))
        code = src.read_text(encoding="utf-8")
        if "/* <kit> */\n/* </kit> */" not in code:
            raise SystemExit(f"{src}: missing the empty <kit> placeholder")
        code = code.replace("/* <kit> */\n/* </kit> */", body)
        head = (f"/* frogsdream {fname}: generated and minified by source/art/make_icons.py from source/art/js/{fname}\n"
                "   and source/art/drawkit.js. Edit those files, then run: python3 source/art/make_icons.py */\n")
        out = head + minify_js(code).strip() + "\n"
        out = re.sub(r"[^\x00-\x7f]", lambda m: "\\u%04x" % ord(m.group()), out)
        (JS_DIR / fname).write_text(out, encoding="utf-8")
        print(f"wrote {fname} ({len(out.encode())} bytes)")


if __name__ == "__main__":
    main()
