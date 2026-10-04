#!/usr/bin/env python3
"""Frog's Dream static site generator.

  python3 source/build.py                     build into ./public_html
  python3 source/build.py --out /tmp/site     build somewhere else
  options: --content DIR   read content from another folder (tests/fixtures)
           --date YYYY-MM-DD  build date (lastmod, policy dates); default today
           --strict        treat warnings (broken links, < 3 inbound links, content rule breaks) as errors
           --force         allow wiping a non-empty --out that does not look like a previous build
           --quiet         fewer messages

Reads source/content/**.json (see CONTENT-FORMAT.md), source/css/*.css (concatenated in name order
into assets/css/site.css), source/static/ (copied verbatim to the output root), source/tools/<id>.controls.html
(tool option controls, see TOOL-CONTRACT.md). Pages whose content file does not exist yet are skipped.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import secrets
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fdlib  # noqa: E402

SRC = fdlib.SRC
STATIC = SRC / "static"
CSS_DIR = SRC / "css"
TOOLS_DIR = SRC / "tools"
ART = SRC / "art" / "png"
FONT_TTF = SRC / "fonts" / "Fredoka-SemiBold.ttf"
FONT_TTF_MED = SRC / "fonts" / "Fredoka-Medium.ttf"
KEY_FILE = SRC / "indexnow.key"

E = lambda s: html.escape(str(s), quote=True)  # noqa: E731
SHARED_JS = ["config.js", "rng.js", "print.js", "pdf.js", "site.js", "toolkit.js"]
LIST_HEADINGS = {
    "bingo": "The word list", "word-search": "The word list", "word-scramble": "The word list",
    "scavenger-hunt": "The hunt list", "bedtime-routine-chart": "The routine steps", "reward-chart-maker": "The chart tasks",
}
TOOL_NOUNS = {"bingo": "Bingo", "word-search": "Word searches", "scavenger-hunt": "Scavenger hunts", "word-scramble": "Word scrambles",
              "bedtime-routine-chart": "Bedtime charts", "reward-chart-maker": "Reward charts"}
WHY_DEFAULT = "Why Frog's Dream"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
SECTION_GUIDES = {
    "bingo": ["/guides/how-to-play-bingo-rules/", "/guides/bingo-patterns/"],
    "scavenger-hunt": ["/guides/how-to-plan-a-scavenger-hunt/"],
    "bedtime-routine-chart": ["/guides/toddler-bedtime-routine/"],
    "word-search": ["/guides/printing-tips-letter-vs-a4/"],
    "word-scramble": ["/guides/printing-tips-letter-vs-a4/"],
}
# Mega Pack line under each generator (shown only when config PACK_URL is set). Counts match deliverables/megapack.
PACK_CTA = {
    "bingo": "Need 40 ready-made cards for every theme, plus caller sheets, in one download?",
    "wordsearch": "Want all 36 word searches at two levels, each with an answer key, in one download?",
    "scramble": "Want all 10 word scrambles with hint versions and answer keys in one download?",
    "scavenger": "Want all 18 scavenger hunts, each ready to print in its own layout?",
    "routine": "Want ready-made routine and reward charts in four soft colors?",
    "reward": "Want ready-made reward, chore and potty charts in four soft colors?",
}


class Page:
    def __init__(self, kind, path, data, file=None, section=None, slug=None):
        self.kind, self.path, self.data, self.file = kind, path, data, file
        self.section, self.slug = section, slug
        self.noindex = bool(data.get("noindex"))
        self.html = ""

    @property
    def label(self):
        d = self.data
        return d.get("shortTitle") or d.get("navLabel") or fdlib.STATIC_LABELS.get(self.path) or d.get("h1") or self.path


class Builder:
    def __init__(self, args):
        self.a = args
        self.content = Path(args.content)
        self.cat = fdlib.Catalog(self.content)
        self.site = self.cat.site
        self.base = self.cat.base
        self.out = Path(args.out)
        self.date = args.date or dt.date.today().isoformat()
        self.pages: dict[str, Page] = {}
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.versions: dict[str, str] = {}
        self.missing: list[str] = []

    # ------------------------------------------------------------ logging
    def warn(self, msg):
        self.warnings.append(msg)

    def error(self, msg):
        self.errors.append(msg)

    def log(self, msg):
        if not self.a.quiet:
            print(msg)

    # ------------------------------------------------------------ content loading
    def load(self):
        c = self.content
        cat = self.cat

        def add(kind, path, f, section=None, slug=None):
            try:
                data = fdlib.load_json(f)
            except Exception as e:  # noqa: BLE001
                self.error(f"{f}: invalid JSON ({e}); page skipped")
                return
            rep = fdlib.validate_file(f, cat, c)
            for e in rep.errors:
                self.warn(f"content {f.relative_to(c)}: {e}")
            if not data.get("h1") and kind not in ("home",):
                self.warn(f"{f}: no h1, page skipped")
                return
            self.pages[path] = Page(kind, path, data, f, section, slug)

        if (c / "home.json").exists():
            add("home", "/", c / "home.json")
        else:
            self.missing.append("/")
        for t in cat.site["tools"]:
            f = c / "tools" / (t["path"].strip("/") + ".json")
            if f.exists():
                add("tool", t["path"], f, slug=t["id"])
            else:
                self.missing.append(t["path"])
        for sec, slug in cat.all_theme_refs():
            f = c / "themes" / sec / f"{slug}.json"
            path = cat.theme_path(sec, slug)
            if f.exists():
                add("theme", path, f, sec, slug)
            else:
                self.missing.append(path)
        for f in sorted((c / "themes").glob("*/*.json")):
            if self.cat.sections.get(f.parent.name) is None or cat.theme_group(f.parent.name, f.stem) is None:
                self.warn(f"{f}: not listed in site.json, skipped")
        hub_slugs = [s for s, d in cat.sections.items() if not d.get("hubIsTool")] + list(cat.cross) + ["guides"]
        for h in hub_slugs:
            f = c / "hubs" / f"{h}.json"
            path = cat.sections[h]["path"] if h in cat.sections else f"/{h}/"
            if f.exists():
                add("hub", path, f, slug=h)
            else:
                self.missing.append(path)
        for g in cat.site["guides"]:
            f = c / "guides" / f"{g}.json"
            if f.exists():
                add("guide", f"/guides/{g}/", f, slug=g)
            else:
                self.missing.append(f"/guides/{g}/")
        for p in cat.site["pages"]:
            f = c / "pages" / f"{p}.json"
            if f.exists():
                try:
                    path = fdlib.load_json(f).get("path") or f"/{p}/"
                except Exception:  # noqa: BLE001
                    path = f"/{p}/"
                add("page", path, f, slug=p)
            else:
                self.missing.append(f"/{p}/")
        # embed pages come from tool page content
        for t in cat.site["tools"]:
            if t.get("embed") and t["path"] in self.pages:
                src = self.pages[t["path"]]
                pg = Page("embed", t["embed"], dict(src.data, noindex=True), src.file, slug=t["id"])
                pg.noindex = True
                self.pages[t["embed"]] = pg
        if self.missing:
            self.warn(f"{len(self.missing)} catalogued pages have no content yet and were skipped"
                      + ("" if self.a.quiet else ": " + ", ".join(self.missing[:12]) + (" ..." if len(self.missing) > 12 else "")))

    def built(self, path):
        return path in self.pages

    def label(self, path):
        if path in self.pages:
            return self.pages[path].label
        t = self.cat.tools_by_path.get(path)
        if t:
            return t["name"]
        for s in self.cat.sections.values():
            if s["path"] == path:
                return s["name"]
        for h in self.cat.cross.values():
            if f"/{h['slug']}/" == path:
                return h["name"]
        return fdlib.STATIC_LABELS.get(path, path.strip("/").split("/")[-1].replace("-", " ").title())

    def url(self, path):
        return self.base + path

    def asset(self, rel):
        v = None if rel.endswith("config.js") else self.versions.get(rel)  # config.js is edited by hand on the server
        return f"/{rel}?v={v}" if v else f"/{rel}"

    # ------------------------------------------------------------ output prep
    def prepare_out(self):
        out = self.out
        if out.exists() and any(out.iterdir()):
            looks_built = (out / "assets" / "js" / "site.js").exists() or (out / "sitemap.xml").exists()
            if not looks_built and not self.a.force:
                sys.exit(f"Refusing to wipe {out}: it is not empty and does not look like a previous build. Use --force.")
            for child in out.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
        out.mkdir(parents=True, exist_ok=True)
        shutil.copytree(STATIC, out, dirs_exist_ok=True)
        # CSS
        parts = []
        for f in sorted(CSS_DIR.glob("*.css")):
            parts.append(minify_css(f.read_text(encoding="utf-8")))
        css = "\n".join(parts)
        (out / "assets" / "css").mkdir(parents=True, exist_ok=True)
        (out / "assets" / "css" / "site.css").write_text(css, encoding="utf-8")
        self.images()
        for f in (out / "assets").rglob("*"):
            if f.is_file():
                self.versions[f.relative_to(out).as_posix()] = hashlib.sha1(f.read_bytes()).hexdigest()[:8]

    # ------------------------------------------------------------ images
    def images(self):
        from PIL import Image
        out = self.out
        fav = Image.open(ART / "favicon.png").convert("RGBA")
        fav_sq = pad_square(fav, 0.04)
        fav_sq.resize((48, 48), Image.LANCZOS).save(out / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
        for size, name in ((180, "apple-touch-icon.png"), (192, "assets/img/icon-192.png"), (512, "assets/img/icon-512.png")):
            bg = Image.new("RGBA", (size, size), (255, 249, 236, 255))
            ic = pad_square(fav, 0.16).resize((size, size), Image.LANCZOS)
            bg.alpha_composite(ic)
            (out / name).parent.mkdir(parents=True, exist_ok=True)
            bg.convert("RGB").save(out / name, optimize=True)
        logo = Image.new("RGBA", (512, 512), (255, 249, 236, 255))
        m = Image.open(ART / "frog-mascot.png").convert("RGBA").resize((440, 440), Image.LANCZOS)
        logo.alpha_composite(m, (36, 30))
        logo.convert("RGB").save(out / "assets/img/logo.png", optimize=True)
        og = out / "assets" / "img" / "og"
        og.mkdir(parents=True, exist_ok=True)
        jobs = [("default", "Free Printable Bingo Cards, Word Searches and Party Games", "Make it, print it, play it. No sign-up.", "waving")]
        for t in self.cat.site["tools"]:
            jobs.append((t["path"].strip("/"), t["ogTitle"], "Free printable generator at frogsdream.com", t["pose"]))
        for p in self.pages.values():
            if p.kind == "hub":
                pose = self.cat.cross.get(p.slug, {}).get("pose", "pencil" if p.slug == "guides" else "celebrating")
                jobs.append((p.slug, p.data.get("ogTitle") or p.label, "Free printables at frogsdream.com", pose))
        for key, title, sub, pose in jobs:
            make_og(og / f"{key}.png", title, sub, pose)

    def og_for(self, p: Page):
        if p.kind in ("tool", "embed"):
            key = self.cat.tools[p.slug]["path"].strip("/")
        elif p.kind == "theme":
            key = self.cat.tools[self.cat.sections[p.section]["tool"]]["path"].strip("/")
        elif p.kind == "hub":
            key = p.slug
        else:
            key = p.data.get("ogImage") or "default"
        return f"{self.base}/assets/img/og/{key}.png"

    # ------------------------------------------------------------ shared chrome
    def head(self, p: Page, title, desc, canonical, jsonld, robots=None, scripts=()):
        og = self.og_for(p)
        tags = [
            '<!doctype html>', '<html lang="en">', '<head>', '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{E(title)}</title>",
        ]
        if desc:
            tags.append(f'<meta name="description" content="{E(desc)}">')
        if canonical:
            tags.append(f'<link rel="canonical" href="{E(canonical)}">')
        if robots:
            tags.append(f'<meta name="robots" content="{robots}">')
        tags += [
            f'<meta name="theme-color" content="{self.site["themeColor"]}">',
            '<link rel="icon" href="/favicon.ico" sizes="32x32">',
            '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
            '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
            '<link rel="manifest" href="/site.webmanifest">',
        ]
        if canonical:
            ogt = p.data.get("ogTitle") or title.replace(" | Frog's Dream", "")
            tags += [
                f'<meta property="og:type" content="{"article" if p.kind == "guide" else "website"}">',
                f'<meta property="og:site_name" content="Frog\'s Dream">',
                f'<meta property="og:title" content="{E(ogt)}">',
                f'<meta property="og:description" content="{E(desc)}">',
                f'<meta property="og:url" content="{E(canonical)}">',
                f'<meta property="og:image" content="{og}">',
                '<meta property="og:image:width" content="1200">', '<meta property="og:image:height" content="630">',
                '<meta name="twitter:card" content="summary_large_image">',
            ]
        tags.append(f'<link rel="preload" href="/assets/fonts/fredoka-600.woff2" as="font" type="font/woff2" crossorigin>')
        tags.append(f'<link rel="stylesheet" href="{self.asset("assets/css/site.css")}">')
        for s in ["config.js", "site.js"] + list(scripts):
            rel = f"assets/js/{s}"
            if not (self.out / rel).exists():
                self.warn(f"{p.path}: script {rel} does not exist yet")
                continue
            tags.append(f'<script src="{self.asset(rel)}" defer></script>')
        for j in jsonld:
            tags.append('<script type="application/ld+json">' + json.dumps(j, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>")
        tags.append("</head>")
        return "\n".join(tags)

    def header(self, p: Page):
        nav = []
        for n in self.site["nav"]:
            cur = ' aria-current="page"' if p.path == n["path"] or (n["path"] != "/" and p.path.startswith(n["path"])) else ""
            nav.append(f'<li><a href="{n["path"]}"{cur}>{E(n["label"])}</a></li>')
        nav.append('<li data-pack hidden><a href="/premium/">Mega Pack</a></li>')
        return (
            '<a class="skip" href="#main">Skip to content</a>'
            '<header class="site-header"><div class="wrap hdr">'
            '<a class="brand" href="/"><img src="/assets/img/frog-mascot.svg" width="46" height="46" alt="">Frog\'s Dream</a>'
            '<input type="checkbox" id="nav-t" class="nav-t" aria-label="Show menu">'
            '<label for="nav-t" class="nav-btn" aria-hidden="true"><i></i>Menu</label>'
            f'<ul class="nav" id="nav">{"".join(nav)}</ul>'
            "</div></header>"
        )

    def crumbs(self, trail):
        lis = []
        for i, (name, path) in enumerate(trail):
            last = i == len(trail) - 1
            if last:
                lis.append(f'<li aria-current="page">{E(name)}</li>')
            elif path and self.built(path):
                lis.append(f'<li><a href="{path}">{E(name)}</a></li>')
            else:
                lis.append(f"<li>{E(name)}</li>")
        return f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{"".join(lis)}</ol></nav>'

    def crumb_ld(self, trail):
        return {
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": n, "item": self.url(path)} for i, (n, path) in enumerate(trail)
            ],
        }

    def footer(self):
        tools = "".join(f'<li><a href="{t["path"]}">{E(t["name"])}</a></li>' for t in self.site["tools"])
        hubs = "".join(f'<li><a href="{h}">{E(self.label(h))}</a></li>' for h in self.site["footer"]["hubs"])
        about = "".join(f'<li><a href="{h}">{E(self.label(h))}</a></li>' for h in self.site["footer"]["about"])
        about += '<li><a href="/privacy/#choices" data-privacy-choices>Privacy choices</a></li>'
        about += '<li data-pack hidden><a href="/premium/">Mega Pack</a></li>'
        about += '<li hidden><a data-tip hidden>Buy the frog a coffee</a></li>'
        year = self.date[:4]
        return (
            '<footer class="site-footer">'
            '<img class="ft-frog" src="/assets/img/frog-sleeping.svg" width="92" height="92" alt="" loading="lazy">'
            '<div class="wrap"><div class="ft-grid">'
            f'<div><h2>Make it</h2><ul>{tools}</ul></div>'
            f'<div><h2>Browse</h2><ul>{hubs}</ul></div>'
            f'<div><h2>Frog\'s Dream</h2><ul>{about}</ul></div>'
            "</div>"
            f'<div class="ft-base"><p>&copy; <span data-year>{year}</span> Frog\'s Dream</p>'
            "<p>Everything here is free to print for home, classroom and party use.</p></div>"
            "</div></footer>"
        )

    def no_ads(self, p: Page):
        return bool(p.data.get("noAds")) or any(p.path.startswith(x) for x in self.site.get("noAdsPaths", []))

    def page_shell(self, p: Page, title, desc, body, jsonld, crumbs=None, scripts=(), body_cls="", robots=None, canonical=None, chrome=True):
        canonical = canonical if canonical is not None else self.url(p.path)
        no_ads = self.no_ads(p)
        attrs = f' class="{body_cls}"' if body_cls else ""
        if no_ads:
            attrs += " data-no-ads"
        parts = [self.head(p, title, desc, canonical, jsonld, robots, scripts), f"<body{attrs}>"]
        if chrome:
            parts.append(self.header(p))
        parts.append('<main id="main"><div class="wrap">')
        if crumbs and chrome:
            parts.append(self.crumbs(crumbs))
        parts.append(body)
        parts.append("</div></main>")
        if chrome:
            parts.append(self.footer())
        parts.append("</body></html>")
        return "\n".join(parts) + "\n"

    # ------------------------------------------------------------ blocks
    def prose_sections(self, sections, ad_after_role=None, no_ads=False, skip_roles=("list",)):
        out = []
        ads = 0
        for s in sections or []:
            if s.get("role") in skip_roles:
                continue
            sid = s.get("id") or slugify(s.get("heading", ""))
            out.append(f'<section class="prose" id="{E(sid)}"><h2>{fdlib.inline(s["heading"])}</h2>{fdlib.markup_to_html(s["body"])}</section>')
            if not no_ads and ads == 0 and ad_after_role and s.get("role") == ad_after_role:
                out.append('<div class="ad-slot"></div>')
                ads += 1
        return "\n".join(out)

    def faq_block(self, faq, heading="FAQ"):
        if not faq:
            return ""
        items = "".join(
            f'<div class="faq-item"><h3>{fdlib.inline(f["q"])}</h3>{fdlib.markup_to_html(f["a"], allow_html=False)}</div>' for f in faq
        )
        return f'<section class="faq" id="faq"><h2>{E(heading)}</h2>{items}</section>'

    def faq_ld(self, faq):
        return {
            "@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": fdlib.inline_text(f["q"]),
                 "acceptedAnswer": {"@type": "Answer", "text": fdlib.markup_to_text(f["a"])}} for f in faq
            ],
        }

    def chips(self, paths, hub_paths=(), strip_prefix=None, labels=None):
        lis = []
        for path in paths:
            if not self.built(path):
                continue
            lab = (labels or {}).get(path) or self.label(path)
            if strip_prefix and lab.lower().startswith(strip_prefix.lower() + " ") and path not in hub_paths:
                rest = lab[len(strip_prefix) + 1:]
                if rest.split(" ")[0] in ("Bingo", "Word", "Scavenger"):  # "Christmas Bingo" -> "Bingo", but keep "Spring and Easter ..."
                    lab = rest
            cls = ' class="hub"' if path in hub_paths else ""
            lis.append(f'<li{cls}><a href="{path}">{E(lab)}</a></li>')
        return f'<ul class="chips">{"".join(lis)}</ul>' if lis else ""

    def season_score(self, mmdd, tail):
        today = dt.date.fromisoformat(self.date)
        m, d = (int(x) for x in mmdd.split("-"))
        try:
            when = dt.date(today.year, m, d)
        except ValueError:
            when = dt.date(today.year, m, 28)
        diff = (when - today).days
        if diff < -tail:
            diff += 365
        if diff <= 0:
            return diff * 0.01 - 1 if tail <= 10 else 46 - diff * 0.001
        return diff if diff <= 45 else 1000 + diff

    def in_season(self, heading="In season now"):
        rows = []
        for s in self.site["seasons"]:
            links = [l for l in s["links"] if self.built(l)]
            if not links:
                continue
            hubs = [l for l in links if l.strip("/") in self.cat.cross]
            labels = {h: "All " + s["name"] + " printables" for h in hubs}
            m, d = s["date"].split("-")
            lab = s.get("label") or f"{MONTHS[int(m) - 1]} {int(d)}"
            rows.append((self.season_score(s["date"], s.get("tail", 1)),
                         f'<li class="season" data-date="{s["date"]}" data-tail="{s.get("tail", 1)}"><h3>{E(s["name"])} <small>{E(lab)}</small></h3>'
                         f'{self.chips(links, hubs, strip_prefix=s["name"], labels=labels)}</li>'))
        if not rows:
            return ""
        rows.sort(key=lambda r: r[0])
        lis = [r[1] for r in rows]
        lis[0] = lis[0].replace('class="season"', 'class="season next"', 1)
        return f'<section class="in-season" id="in-season"><h2>{E(heading)}</h2><ul class="season-list">{"".join(lis)}</ul></section>'

    def theme_guides(self, p: Page):
        """Guides linked from a themed page's related block, by section (and ESL bingo)."""
        g = list(SECTION_GUIDES.get(p.section, []))
        if p.section == "bingo" and p.slug.startswith("esl-"):
            g.insert(0, "/guides/esl-vocabulary-games-printable/")
        if p.section == "bingo" and p.slug in ("sight-words-kindergarten", "sight-words-first-grade", "cvc-words", "addition-facts-to-20", "multiplication-facts"):
            g.append("/guides/classroom-bingo-ideas-for-teachers/")
        return g

    def pack_cta(self, tool_id="bingo"):
        text = PACK_CTA.get(tool_id, PACK_CTA["bingo"])
        return f'<p class="pack-cta" data-pack hidden>{text} <a href="/premium/">Get the Mega Pack</a></p>'

    def tool_shell(self, p: Page, tool, items, options, tool_title, theme: bool, embed=False):
        partial_f = TOOLS_DIR / f"{tool['id']}.controls.html"
        partial = partial_f.read_text(encoding="utf-8") if partial_f.exists() else ""
        if not partial_f.exists():
            self.warn(f"{p.path}: tools/{tool['id']}.controls.html missing; no tool options rendered")
        lines = [fdlib.item_to_line(i) for i in items or []]
        data = {
            "tool": tool["id"], "path": p.path, "url": self.url(p.path), "title": tool_title, "lines": lines, "items": items or [],
            "options": options or {}, "theme": theme, "slug": p.slug, "section": p.section, "noun": tool.get("noun", "items"),
            "toolUrl": self.url(tool["path"]), "embed": embed,
        }
        js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        if p.data.get("shell") == "custom":  # e.g. the bingo caller draws its own UI inside #tool
            return (f'<section class="tool tool-custom no-ads" id="tool" data-tool="{tool["id"]}" aria-label="{E(tool["name"])}">'
                    f'<script type="application/json" id="fd-data">{js}</script>{partial}</section>')
        noun = tool.get("noun", "items")
        list_label = {"items": "Item list", "steps": "Routine steps", "tasks": "Tasks"}.get(noun, "Word list")
        reset_label = "Reset to theme list" if theme else "Reset to sample list"
        embed_btn = ""
        if tool.get("embed") and not embed and (self.built(tool["embed"])):
            embed_btn = (f'<button type="button" class="linkish" data-embed-open data-embed-src="{self.url(tool["embed"])}" '
                         f'data-embed-link="{self.url(tool["path"])}" data-embed-name="{E(tool["name"])}">Embed this tool</button>')
        return (
            f'<section class="tool no-ads" id="tool" data-tool="{tool["id"]}" aria-label="{E(tool["name"])}">'
            f'<script type="application/json" id="fd-data">{js}</script>'
            '<form class="tool-controls" id="fd-form" autocomplete="off">'
            f'<div class="field"><label for="fd-title">Title</label><input type="text" id="fd-title" name="title" maxlength="80" value="{E(tool_title)}"></div>'
            f'<div class="field"><label for="fd-words">{list_label} <span class="count" id="fd-count">{len(lines)} {noun}</span></label>'
            f'<textarea id="fd-words" name="words" rows="8" spellcheck="true" aria-describedby="fd-msg">{E(chr(10).join(lines))}</textarea>'
            '<p class="field-msg" id="fd-msg" aria-live="polite">One per line. Edit, add or remove anything you like.</p></div>'
            '<details class="opts" open><summary>Options</summary><div class="opts-body">'
            f'<div data-tool-partial>{partial}</div>'
            '<div class="field"><label for="fd-paper">Paper</label><select id="fd-paper" name="paper">'
            '<option value="letter">US Letter</option><option value="a4">A4</option></select></div>'
            '<label class="check"><input type="checkbox" id="fd-ink" name="ink"> Ink saver (black and white)</label>'
            '<label class="check"><input type="checkbox" id="fd-stamp" name="stamp" checked> Little frog stamp in the corner</label>'
            '</div></details>'
            '<input type="hidden" id="fd-seed" name="seed" value="">'
            '<div class="tool-actions"><button type="submit" class="btn btn-primary" id="fd-generate">Generate</button>'
            '<button type="button" class="btn" id="fd-print">Print</button>'
            '<button type="button" class="btn" id="fd-pdf">Download PDF</button></div>'
            f'<div class="tool-more"><button type="button" class="linkish" id="fd-share">Copy share link</button>'
            f'<button type="button" class="linkish" id="fd-reset">{reset_label}</button>{embed_btn}</div>'
            "</form>"
            '<div class="tool-preview"><p class="tool-status" id="fd-status" aria-live="polite">Your preview appears here.</p>'
            '<div class="sheets" id="fd-sheets" data-paper="letter"><noscript><p class="tool-noscript">The generator needs JavaScript. '
            "The full list is printed below so you can still copy it.</p></noscript></div></div>"
            "</section>"
        )

    def webapp_ld(self, p: Page, tool, name, desc):
        return {
            "@context": "https://schema.org", "@type": "WebApplication", "name": name, "url": self.url(p.path),
            "description": desc, "applicationCategory": tool.get("category", "EducationalApplication"),
            "operatingSystem": "Any (web browser)", "isAccessibleForFree": True, "inLanguage": "en",
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "publisher": {"@type": "Organization", "name": "Frog's Dream", "url": self.base + "/"},
        }

    def tool_scripts(self, tool):
        return ["rng.js", "print.js", "pdf.js", "toolkit.js", tool["js"]]

    # ------------------------------------------------------------ page renderers
    def render_theme(self, p: Page):
        d, cat = p.data, self.cat
        sec = cat.sections[p.section]
        tool = cat.tools[sec["tool"]]
        hub_path = sec["path"]
        trail = [("Home", "/"), (sec["name"] if not sec.get("hubIsTool") else tool["name"], hub_path), (p.label, p.path)]
        items = d.get("items", [])
        no_ads = self.no_ads(p)
        list_sec = next((s for s in d.get("sections", []) if s.get("role") == "list"), None)
        list_h = (list_sec or {}).get("heading") or LIST_HEADINGS[p.section]
        list_note = d.get("itemsNote") or (fdlib.markup_to_html(list_sec["body"]) if list_sec else "")
        list_html = ""
        if items:
            lis = "".join(f"<li>{E(fdlib.item_display(i))}{scav_points(i)}</li>" for i in items)
            note = list_note if list_note.startswith("<") else (f"<p>{fdlib.inline(list_note)}</p>" if list_note else
                                                                 f"<p>All {len(items)} are already loaded in the generator above, ready to edit.</p>")
            list_html = f'<section class="prose" id="list"><h2>{E(list_h)}</h2>{note}</section><ul class="wordlist">{lis}</ul>'
        sections = d.get("sections", [])
        before_faq = '<div class="ad-slot"></div>' if not no_ads and len(sections) >= 4 else ""
        related = [cat.ref_to_path(r) for r in d.get("related", [])]
        hubs = [f"/{h}/" for h in d.get("hubs", [])]
        rel_paths = related + hubs + ([hub_path] if hub_path != tool["path"] else []) + [tool["path"]]
        rel_html = self.chips(list(dict.fromkeys(rel_paths)), hub_paths=set(hubs + [hub_path, tool["path"]]))
        guides = [g for g in self.theme_guides(p) if self.built(g)]
        if rel_html and guides:
            rel_html += f'<h3>{E(d.get("guidesHeading") or "Helpful guides")}</h3>' + self.chips(guides)
        body = (
            f'<div class="page-head"><h1>{fdlib.inline(d["h1"])}</h1><div class="lede">{fdlib.markup_to_html(d["intro"], allow_html=False)}</div></div>'
            + self.tool_shell(p, tool, items, d.get("defaultOptions"), d.get("toolTitle") or p.label, theme=True)
            + self.pack_cta(tool["id"])
            + list_html
            + self.prose_sections(sections, ad_after_role="howTo", no_ads=no_ads)
            + before_faq
            + self.faq_block(d.get("faq"))
            + (f'<section class="related" id="related"><h2>{E(d.get("relatedHeading") or "More printables")}</h2>{rel_html}</section>' if rel_html else "")
        )
        ld = [self.crumb_ld(trail), self.webapp_ld(p, tool, d.get("shortTitle") or d["h1"], d["metaDescription"])]
        if d.get("faq"):
            ld.append(self.faq_ld(d["faq"]))
        return self.page_shell(p, d["title"], d["metaDescription"], body, ld, trail, self.tool_scripts(tool), body_cls="has-tool")

    def themes_in_section(self, section):
        sec = self.cat.sections.get(section)
        if not sec:
            return []
        return [self.cat.theme_path(section, s) for g in sec["groups"] for s in g["slugs"] if self.built(self.cat.theme_path(section, s))]

    def render_tool(self, p: Page):
        d, tool = p.data, self.cat.tools[p.slug]
        trail = [("Home", "/"), (tool["name"], p.path)]
        section = tool.get("section") or "bingo"
        featured = [self.cat.ref_to_path(r) for r in d.get("featured", [])] or self.themes_in_section(section)[:12]
        featured = [f for f in featured if self.built(f)]
        sec = self.cat.sections.get(section, {})
        hub = sec.get("path") if sec and not sec.get("hubIsTool") else None
        total = len(self.themes_in_section(section))
        feat_html = ""
        if featured:
            more = f'<p><a href="{hub}">See all {total} {E(sec.get("label", "printable"))} themes</a></p>' if hub and self.built(hub) else ""
            feat_html = (f'<section class="featured" id="themes"><h2>{E(d.get("featuredHeading") or "Ready-made themes")}</h2>'
                         f'{self.chips(featured)}{more}</section>')
        no_ads = self.no_ads(p)
        body = (
            f'<div class="page-head"><h1>{fdlib.inline(d["h1"])}</h1><div class="lede">{fdlib.markup_to_html(d["intro"], allow_html=False)}</div></div>'
            + self.tool_shell(p, tool, d.get("items", []), d.get("defaultOptions"), d.get("toolTitle") or tool["name"], theme=False)
            + ("" if d.get("shell") == "custom" else self.pack_cta(tool["id"]))
            + feat_html
            + self.prose_sections(d.get("sections"), ad_after_role=d.get("sections", [{}])[0].get("role") if d.get("sections") else None, no_ads=no_ads)
            + ("" if no_ads else '<div class="ad-slot"></div>')
            + self.faq_block(d.get("faq"))
        )
        ld = [self.crumb_ld(trail), self.webapp_ld(p, tool, tool["name"], d["metaDescription"])]
        if d.get("faq"):
            ld.append(self.faq_ld(d["faq"]))
        custom = d.get("shell") == "custom"
        scripts = ["rng.js", tool["js"]] if custom else self.tool_scripts(tool)
        return self.page_shell(p, d["title"], d["metaDescription"], body, ld, trail, scripts, body_cls="" if custom else "has-tool")

    def render_embed(self, p: Page):
        d, tool = p.data, self.cat.tools[p.slug]
        credit = f'<a href="{self.url(tool["path"])}" target="_blank" rel="noopener">Free tool by Frog\'s Dream at frogsdream.com</a>'
        body = (
            f'<h1 class="vh">{E(tool["name"])}</h1>'
            + f'<p class="embed-credit embed-top">{credit}</p>'
            + self.tool_shell(p, tool, d.get("items", []), d.get("defaultOptions"), d.get("toolTitle") or tool["name"], theme=False, embed=True)
            + f'<p class="embed-credit">{credit}</p>'
        )
        return self.page_shell(p, f"{tool['name']} (embedded) | Frog's Dream", d.get("metaDescription", ""), body, [], None,
                               self.tool_scripts(tool), body_cls="embed has-tool", robots="noindex,follow",
                               canonical="", chrome=False)  # noindex page: no canonical (mixed signals otherwise)

    def hub_links(self, p: Page):
        """Section hub: grouped theme chips. Cross hub: links grouped by tool. Guides hub: guide cards."""
        cat = self.cat
        out = []
        if p.slug in cat.sections:
            for g in cat.sections[p.slug]["groups"]:
                paths = [cat.theme_path(p.slug, s) for s in g["slugs"]]
                ch = self.chips(paths)
                if ch:
                    out.append(f"<h3>{E(g['name'])}</h3>{ch}")
            members = self.themes_in_section(p.slug)
        elif p.slug == "guides":
            cards = []
            for g in cat.site["guides"]:
                gp = f"/guides/{g}/"
                if self.built(gp):
                    gd = self.pages[gp].data
                    cards.append(f'<li><a class="tcard" href="{gp}"><b>{E(self.label(gp))}</b><span>{E(gd.get("cardBlurb") or gd["metaDescription"])}</span></a></li>')
            out.append(f'<ul class="grid">{"".join(cards)}</ul>')
            members = [f"/guides/{g}/" for g in cat.site["guides"] if self.built(f"/guides/{g}/")]
        else:
            members = []
            for sec_key, sec in cat.sections.items():
                paths = [pp.path for pp in self.pages.values() if pp.kind == "theme" and pp.section == sec_key and p.slug in pp.data.get("hubs", [])]
                order = {cat.theme_path(sec_key, s): i for i, s in enumerate(s for g in sec["groups"] for s in g["slugs"])}
                paths.sort(key=lambda x: order.get(x, 999))
                if paths:
                    out.append(f"<h3>{E(TOOL_NOUNS.get(sec_key, sec['name']))}</h3>{self.chips(paths)}")
                    members += paths
        for ex in p.data.get("extraLinks", []):
            paths = [cat.ref_to_path(x) for x in ex.get("paths", [])]
            ch = self.chips(paths)
            if ch:
                out.append(f"<h3>{E(ex.get('heading', 'More'))}</h3>{ch}")
                members += [x for x in paths if self.built(x)]
        return "\n".join(out), list(dict.fromkeys(members))

    def render_hub(self, p: Page):
        d, cat = p.data, self.cat
        trail = [("Home", "/"), (p.label, p.path)]
        links, members = self.hub_links(p)
        tool_card = ""
        if p.slug in cat.sections:
            tool = cat.tools[cat.sections[p.slug]["tool"]]
            if self.built(tool["path"]):
                tool_card = (f'<p class="btns"><a class="btn btn-primary" href="{tool["path"]}">Open the {E(tool["name"].lower())}</a></p>')
        links_h = d.get("linksHeading") or ("All guides" if p.slug == "guides" else "Pick a theme" if p.slug in cat.sections else "Printables by type")
        body = (
            f'<div class="page-head"><h1>{fdlib.inline(d["h1"])}</h1><div class="lede">{fdlib.markup_to_html(d.get("intro", ""), allow_html=False)}</div>{tool_card}</div>'
            + (f'<section class="hub-links" id="links"><h2>{E(links_h)}</h2>{links}</section>' if links.strip() else "")
            + self.in_season()
            + self.prose_sections(d.get("sections"), no_ads=self.no_ads(p))
            + self.faq_block(d.get("faq"))
        )
        ld = [self.crumb_ld(trail), {
            "@context": "https://schema.org", "@type": "CollectionPage", "name": d["h1"], "url": self.url(p.path),
            "description": d["metaDescription"],
            "mainEntity": {"@type": "ItemList", "numberOfItems": len(members), "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": self.url(m), "name": self.label(m)} for i, m in enumerate(members)]},
        }]
        if d.get("faq"):
            ld.append(self.faq_ld(d["faq"]))
        return self.page_shell(p, d["title"], d["metaDescription"], body, ld, trail)

    def render_guide(self, p: Page):
        d = p.data
        trail = [("Home", "/"), ("Guides", "/guides/"), (p.label, p.path)]
        secs = d.get("sections", [])
        out, no_ads = [], self.no_ads(p)
        for i, s in enumerate(secs):
            out.append(f'<section class="prose" id="{E(s.get("id") or slugify(s["heading"]))}"><h2>{fdlib.inline(s["heading"])}</h2>{fdlib.markup_to_html(s["body"])}</section>')
            if i == int(d.get("adSlotAfter", 1)) and not no_ads and len(secs) > 3:
                out.append('<div class="ad-slot"></div>')
        src = ""
        if d.get("sources"):
            lis = "".join(f'<li><a href="{E(s["url"])}" rel="noopener">{E(s["label"])}</a></li>' for s in d["sources"])
            src = f'<section class="prose sources" id="sources"><h2>Sources</h2><ul>{lis}</ul></section>'
        rel = self.chips([self.cat.ref_to_path(r) for r in d.get("related", [])])
        body = (
            f'<article><div class="page-head"><h1>{fdlib.inline(d["h1"])}</h1><div class="lede">{fdlib.markup_to_html(d.get("intro", ""), allow_html=False)}</div></div>'
            + "\n".join(out)
            + ("" if no_ads or len(secs) <= 3 else '<div class="ad-slot"></div>')
            + self.faq_block(d.get("faq"))
            + src
            + (f'<section class="related" id="related"><h2>{E(d.get("relatedHeading") or "Try these next")}</h2>{rel}</section>' if rel else "")
            + "</article>"
        )
        ld = [self.crumb_ld(trail), {
            "@context": "https://schema.org", "@type": "Article", "headline": d["h1"], "description": d["metaDescription"],
            "url": self.url(p.path), "mainEntityOfPage": self.url(p.path), "image": self.og_for(p),
            "datePublished": d.get("datePublished") or self.date, "dateModified": self.date, "inLanguage": "en",
            "author": {"@type": "Organization", "name": "Frog's Dream", "url": self.base + "/"},
            "publisher": {"@type": "Organization", "name": "Frog's Dream", "url": self.base + "/",
                          "logo": {"@type": "ImageObject", "url": self.base + "/assets/img/logo.png"}},
        }]
        if d.get("faq"):
            ld.append(self.faq_ld(d["faq"]))
        scripts = [s for s in d.get("scripts", [])]
        return self.page_shell(p, d["title"], d["metaDescription"], body, ld, trail, scripts)

    def render_page(self, p: Page):
        d = p.data
        trail = [("Home", "/"), (p.label, p.path)]
        pose = d.get("mascot")
        aside = f'<img class="mascot-aside" src="/assets/img/frog-{pose}.svg" width="120" height="120" alt="">' if pose else ""
        intro = d.get("intro", "")
        body = (
            f'<div class="page-head">{aside}<h1>{fdlib.inline(d["h1"])}</h1>'
            + (f'<div class="lede">{fdlib.markup_to_html(intro)}</div>' if intro else "") + "</div>"
            + self.prose_sections(d.get("sections"), no_ads=True)
            + self.faq_block(d.get("faq"))
        )
        ld = [self.crumb_ld(trail)]
        if d.get("faq"):
            ld.append(self.faq_ld(d["faq"]))
        if d.get("product"):
            pr = d["product"]
            ld.append({
                "@context": "https://schema.org", "@type": "Product", "name": pr["name"], "description": pr.get("description", d["metaDescription"]),
                "image": [self.url(i) if i.startswith("/") else i for i in pr.get("images", [])] or [self.base + "/assets/img/logo.png"],
                "brand": {"@type": "Brand", "name": "Frog's Dream"},
                # OWNER: when PACK_URL is set in config.js, change PreOrder to InStock (see the comment in premium/index.html).
                "offers": {"@type": "Offer", "price": pr.get("price", "7.00"), "priceCurrency": "USD", "url": self.url(p.path),
                           "availability": "https://schema.org/" + pr.get("availability", "PreOrder")},
            })
        robots = "noindex,follow" if p.noindex else None
        html_out = self.page_shell(p, d["title"], d["metaDescription"], body, ld, trail, d.get("scripts", []), robots=robots)
        if d.get("product"):
            note = ("<!-- OWNER: the Product data below says availability PreOrder while the Buy button shows Coming soon. "
                    "When you set PACK_URL in assets/js/config.js, change PreOrder to InStock in it, and keep the $ price here in sync with PACK_PRICE. -->")
            html_out = html_out.replace('<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product"',
                                        note + '\n<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product"', 1)
        return html_out

    def render_home(self, p: Page):
        d, cat = p.data, self.cat
        cards = []
        for c in d.get("tools", []):
            t = cat.tools.get(c.get("tool"))
            if not t or not self.built(t["path"]):
                continue
            pose = "mascot" if t["pose"] == "mascot" else t["pose"]
            cards.append(f'<li><a class="tcard" href="{t["path"]}"><img src="/assets/img/frog-{pose}.svg" width="84" height="84" alt="" loading="lazy">'
                         f'<b>{E(c.get("name") or t["name"])}</b><span>{fdlib.inline(c.get("blurb", ""))}</span></a></li>')
        popular = self.chips([cat.ref_to_path(x["path"]) for x in d.get("popular", [])],
                             labels={cat.ref_to_path(x["path"]): x.get("label") for x in d.get("popular", [])})
        hubs = []
        for h in cat.site["crossHubs"]:
            hp = f"/{h['slug']}/"
            if self.built(hp):
                hubs.append(f'<li><a class="tcard" href="{hp}"><img src="/assets/img/frog-{h["pose"]}.svg" width="64" height="64" alt="" loading="lazy">'
                            f'<b>{E(self.label(hp))}</b></a></li>')
        why = d.get("why") or {}
        cta_d = d.get("cta") or {"label": "Make bingo cards", "path": "/bingo-card-generator/"}
        cta = ""
        if self.built(cta_d.get("path", "")):
            cta = (f'<p class="btns"><a class="btn btn-primary" href="{cta_d["path"]}">{E(cta_d["label"])}</a>'
                   f'<a class="btn" href="#in-season">See what\'s in season</a></p>')
        body = (
            f'<section class="hero"><div><h1>{fdlib.inline(d["h1"])}</h1><p class="lede">{fdlib.inline(d.get("subhead", ""))}</p>'
            f'{fdlib.markup_to_html(d.get("intro", ""))}{cta}</div>'
            '<img src="/assets/img/frog-waving.svg" width="280" height="280" alt="Frog\'s Dream mascot waving hello" fetchpriority="high"></section>'
            + (f'<section id="tools"><h2>{E(d.get("toolsHeading") or "Pick a tool")}</h2><ul class="grid">{"".join(cards)}</ul></section>' if cards else "")
            + self.in_season()
            + (f'<section id="popular"><h2>{E(d.get("popularHeading") or "Popular themes")}</h2>{popular}</section>' if popular else "")
            + (f'<section id="hubs"><h2>{E(d.get("hubsHeading") or "Printables for every occasion")}</h2><ul class="grid">{"".join(hubs)}</ul></section>' if hubs else "")
            + (f'<section class="prose" id="why"><h2>{fdlib.inline(why.get("heading", WHY_DEFAULT))}</h2>{fdlib.markup_to_html(why.get("body", ""))}</section>' if why else "")
            + self.prose_sections(d.get("sections"), no_ads=True)
        )
        ld = [
            {"@context": "https://schema.org", "@type": "WebSite", "name": "Frog's Dream", "url": self.base + "/", "inLanguage": "en"},
            {"@context": "https://schema.org", "@type": "Organization", "name": "Frog's Dream", "url": self.base + "/", "logo": self.base + "/assets/img/logo.png"},
        ]
        return self.page_shell(p, d["title"], d["metaDescription"], body, ld, None)

    def render_404(self):
        p = Page("404", "/404.html", {"h1": "Page not found"})
        tools = "".join(f'<li><a class="tcard" href="{t["path"]}"><b>{E(t["name"])}</b></a></li>' for t in self.site["tools"] if self.built(t["path"]))
        hubs = self.chips(self.site["footer"]["hubs"])
        body = (
            '<section class="hero"><div><h1>This page hopped away</h1>'
            '<p class="lede">We could not find that page. It may have moved, or the link has a typo. These are good places to jump back in.</p>'
            '<p class="btns"><a class="btn btn-primary" href="/">Go to the home page</a></p></div>'
            '<img src="/assets/img/frog-sleeping.svg" width="260" height="260" alt="A sleepy frog in a nightcap"></section>'
            + (f'<h2>Free tools</h2><ul class="grid">{tools}</ul>' if tools else "")
            + (f"<h2>Browse printables</h2>{hubs}" if hubs else "")
        )
        p.data["noAds"] = True  # no ads on an error page (AdSense valuable inventory policy)
        return self.page_shell(p, "Page Not Found | Frog's Dream", "", body, [], None, robots="noindex", canonical="")

    # ------------------------------------------------------------ write everything
    def render_all(self):
        renderers = {"theme": self.render_theme, "tool": self.render_tool, "hub": self.render_hub, "guide": self.render_guide,
                     "page": self.render_page, "home": self.render_home, "embed": self.render_embed}
        for path, p in sorted(self.pages.items()):
            try:
                p.html = renderers[p.kind](p)
                if "{{BUILD_DATE}}" in p.html:  # e.g. the effective date on /privacy/ and /terms/
                    bd = dt.date.fromisoformat(self.date)
                    p.html = p.html.replace("{{BUILD_DATE}}", f"{bd:%B} {bd.day}, {bd.year}")
            except Exception as e:  # noqa: BLE001
                self.error(f"{path}: render failed: {type(e).__name__}: {e}")
                continue
            target = self.out / path.strip("/") / "index.html" if path != "/" else self.out / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(p.html, encoding="utf-8")
        (self.out / "404.html").write_text(self.render_404(), encoding="utf-8")

    def write_root_files(self):
        out = self.out
        idx = [p for p in self.pages.values() if not p.noindex and p.kind != "embed" and p.html]
        idx.sort(key=lambda p: (p.path != "/", p.path))
        urls = "".join(f"<url><loc>{self.url(p.path)}</loc><lastmod>{self.date}</lastmod></url>\n" for p in idx)
        (out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                         + urls + "</urlset>\n", encoding="utf-8")
        (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {self.base}/sitemap.xml\n", encoding="utf-8")
        (out / "ads.txt").write_text("# Replace with: google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
        if KEY_FILE.exists():
            key = KEY_FILE.read_text().strip()
        else:
            key = secrets.token_hex(16)
            KEY_FILE.write_text(key + "\n")
        (out / f"{key}.txt").write_text(key, encoding="utf-8")
        self.indexnow_key = key
        (out / ".htaccess").write_text(HTACCESS, encoding="utf-8")
        manifest = {
            "name": "Frog's Dream Printables", "short_name": "Frog's Dream", "start_url": "/", "scope": "/", "display": "standalone",
            "background_color": "#FFF9EC", "theme_color": self.site["themeColor"], "lang": "en",
            "description": "Free printable bingo cards, word searches, scavenger hunts and charts.",
            "icons": [{"src": "/assets/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
                      {"src": "/assets/img/icon-512.png", "sizes": "512x512", "type": "image/png"},
                      {"src": "/favicon.svg", "sizes": "any", "type": "image/svg+xml"}],
        }
        (out / "site.webmanifest").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
        themes = []
        for p in sorted(self.pages.values(), key=lambda x: x.path):
            if p.kind != "theme":
                continue
            d = p.data
            themes.append({
                "slug": p.slug, "section": p.section, "tool": self.cat.sections[p.section]["tool"], "path": p.path,
                "title": p.label, "h1": d["h1"], "metaTitle": d["title"], "metaDescription": d["metaDescription"],
                "items": d.get("items", []), "defaultOptions": d.get("defaultOptions", {}), "season": d.get("season", []),
                "hubs": d.get("hubs", []), "related": d.get("related", []),
            })
        (out / "assets" / "js" / "themes.json").write_text(json.dumps(themes, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # ------------------------------------------------------------ QA
    def qa(self):
        out = self.out
        titles, descs = {}, {}
        inbound: dict[str, set] = {}
        files = {f.relative_to(out).as_posix() for f in out.rglob("*") if f.is_file()}
        broken = []
        for path, p in self.pages.items():
            if not p.html:
                continue
            h = p.html
            size = len(h.encode("utf-8"))
            if size > 60_000:
                self.error(f"{path}: HTML is {size // 1024} KB, budget is 60 KB")
            n_h1 = len(re.findall(r"<h1[\s>]", h))
            if n_h1 != 1:
                self.error(f"{path}: {n_h1} <h1> elements")
            t = re.search(r"<title>(.*?)</title>", h, re.S).group(1)
            t = html.unescape(t)
            m = re.search(r'<meta name="description" content="([^"]*)"', h)
            desc = html.unescape(m.group(1)) if m else ""
            if p.kind != "embed" and not p.noindex:
                if not 50 <= len(t) <= 60:
                    self.warn(f"{path}: title {len(t)} chars (50-60)")
                if not 140 <= len(desc) <= 160:
                    self.warn(f"{path}: meta description {len(desc)} chars (140-160)")
                if t in titles:
                    self.error(f"{path}: duplicate title with {titles[t]}")
                titles[t] = path
                if desc in descs:
                    self.error(f"{path}: duplicate meta description with {descs[desc]}")
                descs[desc] = path
            self.lint_jsonld(path, h)
            body = h.split("<body", 1)[1]
            for href in set(re.findall(r'(?:href|src)="(/[^"]*)"', body)):
                clean = href.split("#")[0].split("?")[0]
                if not clean:
                    continue
                target = clean.lstrip("/")
                ok = (target + "index.html" in files) if clean.endswith("/") else (target in files) or clean == "/"
                if clean == "/":
                    ok = "index.html" in files
                if not ok:
                    broken.append((path, href))
                elif clean.endswith("/") and clean != path:
                    inbound.setdefault(clean, set()).add(path)
            text = fdlib.html_to_text(body)
            m = fdlib.SPACED_HYPHEN.search(text)
            if m:
                self.error(f"{path}: spaced hyphen used as a dash in visible text near '{text[max(0, m.start() - 30):m.start() + 30]}'")
        if broken:
            msg = f"{len(broken)} broken internal links (first: {broken[0][0]} -> {broken[0][1]})"
            self.warn(msg)
            if not self.a.quiet:
                seen = set()
                for src, href in broken:
                    if href not in seen:
                        seen.add(href)
                print("   broken targets:", ", ".join(sorted(seen)[:20]), "..." if len(seen) > 20 else "")
        for path, p in self.pages.items():
            if p.noindex or p.kind == "embed" or path == "/":
                continue
            n = len(inbound.get(path, ()))
            if n < 3:
                self.warn(f"{path}: only {n} internal pages link here (need 3+)")
        # banned dashes anywhere in output text files
        for f in out.rglob("*"):
            if f.suffix.lower() in (".html", ".js", ".json", ".css", ".txt", ".xml", ".webmanifest", ".svg", ".md") or f.name == ".htaccess":
                s = f.read_text(encoding="utf-8", errors="ignore")
                for ch, name in fdlib.BANNED_CHARS.items():
                    if ch in s:
                        i = s.index(ch)
                        self.error(f"{f.relative_to(out)}: banned {name} near '{s[max(0, i - 30):i + 30]}'")
                for ent in fdlib.BANNED_ENTITIES:
                    if ent in s:
                        self.error(f"{f.relative_to(out)}: banned dash entity {ent}")
        # budgets
        css = (out / "assets/css/site.css").stat().st_size
        if css > 25_000:
            self.error(f"site.css is {css} bytes, budget 25 KB")
        shared = sum((out / "assets/js" / j).stat().st_size for j in SHARED_JS if (out / "assets/js" / j).exists())
        if shared > 40_000:
            self.error(f"shared JS is {shared} bytes, budget 40 KB")
        for t in self.site["tools"]:
            f = out / "assets/js" / t["js"]
            if f.exists() and f.stat().st_size > 30_000:
                self.error(f"{t['js']} is {f.stat().st_size} bytes, budget 30 KB")
        self.stats = {"css": css, "shared_js": shared}

    def lint_jsonld(self, path, h):
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)
        visible_faq = [fdlib.html_to_text(x) for x in re.findall(r'<div class="faq-item"><h3>.*?</h3>(.*?)</div>', h, re.S)]
        for raw in blocks:
            try:
                j = json.loads(raw)
            except Exception as e:  # noqa: BLE001
                self.error(f"{path}: invalid JSON-LD ({e})")
                continue
            if j.get("@context") != "https://schema.org":
                self.error(f"{path}: JSON-LD missing @context")
            t = j.get("@type")
            req = {
                "BreadcrumbList": ["itemListElement"], "WebApplication": ["name", "url", "applicationCategory", "operatingSystem", "offers"],
                "FAQPage": ["mainEntity"], "CollectionPage": ["name", "url", "mainEntity"], "Article": ["headline", "datePublished", "author", "publisher"],
                "WebSite": ["name", "url"], "Organization": ["name", "url", "logo"], "Product": ["name", "offers"],
            }.get(t)
            if req is None:
                self.warn(f"{path}: unexpected JSON-LD type {t}")
                continue
            for k in req:
                if not j.get(k):
                    self.error(f"{path}: {t} missing {k}")
            if "aggregateRating" in raw or "review" in j:
                self.error(f"{path}: ratings/reviews are not allowed in JSON-LD")
            if t == "BreadcrumbList":
                for i, it in enumerate(j["itemListElement"]):
                    if it.get("position") != i + 1 or not it.get("name") or not str(it.get("item", "")).startswith(self.base):
                        self.error(f"{path}: bad BreadcrumbList item {i + 1}")
            if t == "FAQPage":
                answers = [q["acceptedAnswer"]["text"] for q in j["mainEntity"]]
                if answers != visible_faq:
                    self.error(f"{path}: FAQPage answers do not match the visible FAQ text")
            if t == "WebApplication" and j["offers"].get("price") != "0":
                self.error(f"{path}: WebApplication offers.price must be '0'")

    # ------------------------------------------------------------ main
    def run(self):
        self.load()
        self.prepare_out()
        self.render_all()
        self.write_root_files()
        self.qa()
        n_pages = sum(1 for p in self.pages.values() if p.html)
        for w in self.warnings:
            self.log(f"warn: {w}")
        for e in self.errors:
            print(f"ERROR: {e}")
        print(f"Built {n_pages} pages into {self.out} (build date {self.date}); css {self.stats['css']} B, shared js {self.stats['shared_js']} B; "
              f"{len(self.errors)} errors, {len(self.warnings)} warnings.")
        if self.errors or (self.a.strict and self.warnings):
            return 1
        return 0


# ---------------------------------------------------------------- helpers

def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", fdlib.inline_text(s).lower()).strip("-") or "section"


def scav_points(item):
    if isinstance(item, dict) and item.get("points") not in (None, ""):
        return f' <small>({E(item["points"])} pts)</small>'
    if isinstance(item, str) and "|" in item:
        pts = item.split("|", 1)[1].strip()
        if pts.isdigit():
            return f" <small>({pts} pts)</small>"
    return ""


def minify_css(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    css = re.sub(r":\s+", ":", css)
    css = re.sub(r"(?<![\w.])0\.(\d)", r".\1", css)
    css = re.sub(r"\s*!important", "!important", css)
    css = css.replace(";}", "}")
    return css.strip()


def pad_square(img, pad):
    w, h = img.size
    side = int(max(w, h) * (1 + 2 * pad))
    from PIL import Image
    c = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    c.alpha_composite(img, ((side - w) // 2, (side - h) // 2))
    return c


def make_og(path, title, sub, pose):
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1200, 630
    im = Image.new("RGBA", (W, H), (255, 249, 236, 255))
    d = ImageDraw.Draw(im)
    # soft pond shapes
    d.ellipse((-160, 470, 520, 820), fill=(234, 245, 225, 255))
    d.ellipse((640, 430, 1380, 860), fill=(222, 240, 210, 255))
    d.ellipse((760, 70, 1150, 460), fill=(234, 245, 225, 255))
    for x, y, r in ((44, 40, 7), (1110, 60, 6), (620, 70, 5), (560, 560, 6)):
        d.ellipse((x - r, y - r, x + r, y + r), fill=(246, 196, 69, 255))
    name = "frog-mascot" if pose == "mascot" else f"frog-{pose}"
    src = ART / f"{name}.png"
    if not src.exists():
        src = ART / "frog-mascot.png"
    frog = Image.open(src).convert("RGBA").resize((430, 430), Image.LANCZOS)
    im.alpha_composite(frog, (735, 120))
    brand = ImageFont.truetype(str(FONT_TTF), 40)
    d.text((80, 70), "Frog's Dream", font=brand, fill=(33, 104, 63, 255))
    size = 76
    while size > 40:
        f = ImageFont.truetype(str(FONT_TTF), size)
        lines = wrap_text(d, title, f, 620)
        if len(lines) <= 3:
            break
        size -= 4
    y = 170 if len(lines) < 3 else 150
    for ln in lines:
        d.text((80, y), ln, font=f, fill=(31, 42, 36, 255))
        y += int(size * 1.12)
    small = ImageFont.truetype(str(FONT_TTF_MED), 32)
    bw = d.textlength(sub, font=small) + 48
    d.rounded_rectangle((80, y + 28, 80 + bw, y + 28 + 58), radius=29, fill=(47, 143, 91, 255))
    d.text((104, y + 37), sub, font=small, fill=(255, 255, 255, 255))
    im.convert("RGB").save(path, optimize=True)


def wrap_text(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


HTACCESS = """# Frog's Dream: Apache settings for Hostinger
# /lessoncorner/ holds the owner's separately managed lesson files. The rules below
# leave it alone: no forced folder listing setting, index.php still works there,
# no long caching and no index.html rewrites, and it is kept out of search engines.
DirectoryIndex index.html index.php
ErrorDocument 404 /404.html

<IfModule mod_rewrite.c>
  RewriteEngine On
  # Force HTTPS and the bare domain in a single 301 (http://www. goes straight to https://frogsdream.com)
  RewriteCond %{HTTPS} off [OR]
  RewriteCond %{HTTP_HOST} ^www\\. [NC]
  RewriteRule ^ https://frogsdream.com%{REQUEST_URI} [R=301,L]
  # /some/page/index.html to /some/page/ so each page has one URL
  RewriteCond %{REQUEST_URI} !^/lessoncorner/ [NC]
  RewriteCond %{THE_REQUEST} \\s/(.*/)?index\\.html[\\s?] [NC]
  RewriteRule ^ /%1 [R=301,L]
</IfModule>

# Trailing slashes on folders are added by mod_dir (DirectorySlash is on by default)
<IfModule mod_dir.c>
  DirectorySlash On
</IfModule>

<IfModule mod_deflate.c>
  <IfModule mod_filter.c>
    AddOutputFilterByType DEFLATE text/html text/plain text/css text/xml application/javascript application/json image/svg+xml application/manifest+json
  </IfModule>
</IfModule>

<IfModule mod_mime.c>
  AddType application/manifest+json .webmanifest
  AddType font/woff2 .woff2
  AddType image/svg+xml .svg
</IfModule>

<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresDefault "access plus 1 hour"
  ExpiresByType text/html "access plus 1 hour"
  ExpiresByType text/css "access plus 1 year"
  ExpiresByType application/javascript "access plus 1 year"
  ExpiresByType text/javascript "access plus 1 year"
  ExpiresByType image/svg+xml "access plus 1 year"
  ExpiresByType image/png "access plus 1 year"
  ExpiresByType image/x-icon "access plus 1 year"
  ExpiresByType font/woff2 "access plus 1 year"
  ExpiresByType application/json "access plus 1 hour"
</IfModule>

<IfModule mod_setenvif.c>
  SetEnvIfNoCase Request_URI "^/lessoncorner/" LESSONCORNER
</IfModule>

<IfModule mod_headers.c>
  Header always set X-Robots-Tag "noindex, nofollow" env=LESSONCORNER
  Header always set Cache-Control "no-cache" env=LESSONCORNER
  Header always unset Expires env=LESSONCORNER
  Header always set X-Content-Type-Options "nosniff"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  <FilesMatch "config\\.js$">
    Header set Cache-Control "no-cache"
  </FilesMatch>
</IfModule>
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(SRC.parent / "public_html"))
    ap.add_argument("--content", default=str(fdlib.CONTENT))
    ap.add_argument("--date")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    return Builder(ap.parse_args(argv)).run()


if __name__ == "__main__":
    sys.exit(main())
