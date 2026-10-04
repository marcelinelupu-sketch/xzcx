#!/usr/bin/env python3
"""Writes the hand-coded frogsdream mascot SVGs (5 poses), favicon.svg and logo.svg.

Run once after editing: python3 source/art/make_mascots.py
Outputs to source/static/assets/img/ (copied to public_html by build.py) and
source/static/favicon.svg. Then run: node source/art/render_art.mjs to refresh
the PNG rasters in source/art/png/ that build.py uses for OG images and icons.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "static" / "assets" / "img"

DARK = "#2F8F5B"   # pond
MID = "#5DB572"
LIGHT = "#8CCB6E"  # lily
CREAM = "#FFF9EC"
INK = "#1F2A24"
CHEEK = "#F4A09A"
SUN = "#F6C445"
CORAL = "#F07A5A"
DUSK = "#3B3A6B"


def eyes_open(look=0):
    return (
        f'<circle cx="64" cy="60" r="16" fill="#fff"/><circle cx="136" cy="60" r="16" fill="#fff"/>'
        f'<circle cx="{66+look}" cy="62" r="9" fill="{INK}"/><circle cx="{138+look}" cy="62" r="9" fill="{INK}"/>'
        f'<circle cx="{69+look}" cy="58" r="3" fill="#fff"/><circle cx="{141+look}" cy="58" r="3" fill="#fff"/>'
    )


def eyes_closed():
    return (
        f'<path d="M51 62q13 10 26 0M123 62q13 10 26 0" fill="none" stroke="{INK}" stroke-width="4.5" stroke-linecap="round"/>'
    )


def eyes_happy():
    return (
        f'<path d="M52 66q12-14 24 0M124 66q12-14 24 0" fill="none" stroke="{INK}" stroke-width="4.5" stroke-linecap="round"/>'
    )


def frog(eyes, mouth, arms="", extra_back="", extra_front="", cap="", over=""):
    return (
        f'<ellipse cx="100" cy="188" rx="62" ry="7" fill="{INK}" opacity=".08"/>'
        f'{extra_back}'
        # haunches and back feet
        f'<ellipse cx="52" cy="160" rx="30" ry="23" fill="{DARK}"/><ellipse cx="148" cy="160" rx="30" ry="23" fill="{DARK}"/>'
        f'<ellipse cx="42" cy="181" rx="22" ry="8" fill="{DARK}"/><ellipse cx="158" cy="181" rx="22" ry="8" fill="{DARK}"/>'
        # body and belly
        f'<ellipse cx="100" cy="143" rx="56" ry="44" fill="{MID}"/>'
        f'<ellipse cx="100" cy="152" rx="36" ry="30" fill="{CREAM}"/>'
        f'{arms}'
        # head
        f'<ellipse cx="100" cy="97" rx="68" ry="45" fill="{MID}"/>'
        f'<circle cx="64" cy="60" r="24" fill="{MID}"/><circle cx="136" cy="60" r="24" fill="{MID}"/>'
        f'<circle cx="100" cy="80" r="6" fill="{LIGHT}"/><circle cx="86" cy="72" r="3.5" fill="{LIGHT}"/><circle cx="115" cy="73" r="4" fill="{LIGHT}"/>'
        f'{eyes}'
        f'<ellipse cx="52" cy="106" rx="10" ry="6" fill="{CHEEK}" opacity=".85"/><ellipse cx="148" cy="106" rx="10" ry="6" fill="{CHEEK}" opacity=".85"/>'
        f'{mouth}{over}{cap}{extra_front}'
    )


SMILE = f'<path d="M80 110q20 16 40 0" fill="none" stroke="{INK}" stroke-width="4.5" stroke-linecap="round"/>'
SOFT_SMILE = f'<path d="M88 112q12 8 24 0" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>'
OPEN_MOUTH = (
    f'<path d="M80 108q20 26 40 0z" fill="{INK}"/><path d="M90 117q10 8 20 0q-10-5-20 0z" fill="{CORAL}"/>'
)
FRONT_FEET = (
    f'<ellipse cx="74" cy="182" rx="15" ry="7" fill="{DARK}"/><ellipse cx="126" cy="182" rx="15" ry="7" fill="{DARK}"/>'
)


def svg(body, label, vb="0 0 200 200"):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" aria-label="{label}">'
        f'<title>{label}</title>{body}</svg>\n'
    )


def build():
    poses = {}
    poses["frog-mascot"] = svg(frog(eyes_open(), SMILE, FRONT_FEET), "frogsdream mascot, a smiling green frog")

    zz = (
        f'<path d="M26 26h14l-14 14h14M8 8h9l-9 9h9" fill="none" stroke="{DUSK}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    cap = (
        f'<g transform="translate(0 -14)"><path d="M72 60C78 18 140 0 170 34C150 28 132 36 128 60Z" fill="{DUSK}"/>'
        f'<rect x="66" y="52" width="68" height="12" rx="6" fill="{CREAM}"/>'
        f'<circle cx="171" cy="37" r="9" fill="{SUN}"/></g>'
    )
    poses["frog-sleeping"] = svg(
        frog(eyes_closed(), SOFT_SMILE, FRONT_FEET, cap=cap, extra_front=zz),
        "Sleepy green frog in a nightcap",
    )

    wave_arm = (
        f'<path d="M152 136q22-12 22-44" fill="none" stroke="{DARK}" stroke-width="15" stroke-linecap="round"/>'
        f'<circle cx="173" cy="88" r="11" fill="{LIGHT}"/>'
        f'<path d="M184 66q8 6 8 16M189 56q12 9 12 26" fill="none" stroke="{DARK}" stroke-width="3" stroke-linecap="round" opacity=".6"/>'
        f'<ellipse cx="62" cy="150" rx="11" ry="8" fill="{LIGHT}"/>'
    )
    poses["frog-waving"] = svg(frog(eyes_open(), SMILE, FRONT_FEET, over=wave_arm), "Green frog waving hello")

    pencil = (
        '<g transform="rotate(-38 132 150)">'
        f'<rect x="96" y="142" width="74" height="16" rx="3" fill="{SUN}"/>'
        f'<rect x="96" y="142" width="74" height="5" fill="#fff" opacity=".35"/>'
        f'<rect x="164" y="142" width="12" height="16" rx="3" fill="{CORAL}"/>'
        f'<rect x="160" y="142" width="6" height="16" fill="#C9CED6"/>'
        f'<path d="M96 142l-18 8 18 8z" fill="#F3D9A8"/><path d="M84 147.3l-6 2.7 6 2.7z" fill="{INK}"/>'
        '</g>'
    )
    hands = f'<ellipse cx="116" cy="156" rx="11" ry="9" fill="{LIGHT}"/><ellipse cx="140" cy="140" rx="11" ry="9" fill="{LIGHT}"/>'
    poses["frog-pencil"] = svg(
        frog(eyes_open(-2), SMILE, FRONT_FEET + pencil + hands), "Green frog holding a yellow pencil"
    )

    arms_up = (
        f'<path d="M52 138q-32-12-32-56M148 138q32-12 32-56" fill="none" stroke="{DARK}" stroke-width="15" stroke-linecap="round"/>'
        f'<circle cx="20" cy="80" r="11" fill="{LIGHT}"/><circle cx="180" cy="80" r="11" fill="{LIGHT}"/>'
    )
    confetti = (
        f'<rect x="20" y="30" width="9" height="5" rx="2" fill="{SUN}" transform="rotate(30 24 32)"/>'
        f'<rect x="172" y="34" width="9" height="5" rx="2" fill="{CORAL}" transform="rotate(-25 176 36)"/>'
        f'<circle cx="100" cy="14" r="4" fill="{CORAL}"/><circle cx="46" cy="16" r="3.5" fill="{LIGHT}"/>'
        f'<circle cx="156" cy="12" r="3.5" fill="{SUN}"/><rect x="186" y="104" width="8" height="5" rx="2" fill="{DUSK}" transform="rotate(40 190 106)"/>'
        f'<rect x="6" y="106" width="8" height="5" rx="2" fill="{DUSK}" transform="rotate(-40 10 108)"/>'
        f'<circle cx="12" cy="60" r="3" fill="{CORAL}"/><circle cx="190" cy="66" r="3" fill="{LIGHT}"/>'
    )
    poses["frog-celebrating"] = svg(
        frog(eyes_happy(), OPEN_MOUTH, FRONT_FEET, extra_back=confetti, over=arms_up), "Happy green frog celebrating with confetti"
    )

    for name, content in poses.items():
        (IMG / f"{name}.svg").write_text(content, encoding="utf-8")

    head = (
        f'<ellipse cx="100" cy="112" rx="84" ry="58" fill="{MID}"/>'
        f'<circle cx="56" cy="62" r="34" fill="{MID}"/><circle cx="144" cy="62" r="34" fill="{MID}"/>'
        f'<circle cx="56" cy="62" r="22" fill="#fff"/><circle cx="144" cy="62" r="22" fill="#fff"/>'
        f'<circle cx="59" cy="65" r="12" fill="{INK}"/><circle cx="147" cy="65" r="12" fill="{INK}"/>'
        f'<path d="M72 124q28 22 56 0" fill="none" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>'
    )
    fav = svg(head, "frogsdream", "0 20 200 160")
    (ROOT / "static" / "favicon.svg").write_text(fav, encoding="utf-8")

    logo = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 200" role="img" aria-label="frogsdream">'
        "<title>frogsdream</title>"
        + frog(eyes_open(), SMILE, FRONT_FEET)
        # two-color wordmark: "frogs" pond green, "dream" dusk purple
        + f'<text x="214" y="128" font-family="Fredoka, ui-rounded, \'Trebuchet MS\', sans-serif" font-weight="600" font-size="84">'
        f'<tspan fill="{DARK}">frogs</tspan><tspan fill="{DUSK}">dream</tspan></text>'
        + "</svg>\n"
    )
    (IMG / "logo.svg").write_text(logo, encoding="utf-8")
    print("mascots written")


if __name__ == "__main__":
    build()
