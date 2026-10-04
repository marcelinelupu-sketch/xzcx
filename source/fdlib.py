"""Shared helpers for build.py and validate_content.py (frogsdream).

Holds: catalog loading, page-kind detection, the FD inline markup renderer,
plain-text extraction, word counting and every content validation rule.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent
CONTENT = SRC / "content"

BANNED_CHARS = {"\u2014": "em dash", "\u2013": "en dash", "\u2012": "figure dash", "\u2015": "horizontal bar"}
BANNED_ENTITIES = ("&mdash;", "&ndash;", "&#8212;", "&#8211;", "&#x2014;", "&#x2013;")
SPACED_HYPHEN = re.compile(r"(?<=\S) +-{1,2} +(?=\S)")

STATIC_LABELS = {
    "/": "Home",
    "/guides/": "Guides",
    "/about/": "About",
    "/contact/": "Contact",
    "/privacy/": "Privacy",
    "/terms/": "Terms",
    "/disclosure/": "Disclosure",
    "/premium/": "Mega Pack",
    "/embed/": "Embed our tools",
}

THEMED_SECTIONS = ("bingo", "word-search", "scavenger-hunt", "word-scramble", "bedtime-routine-chart", "reward-chart-maker")
REQUIRED_ROLES = ("howTo", "variations", "tips", "printing")
KNOWN_ROLES = REQUIRED_ROLES + ("safety", "about", "extra", "list")
ITEM_RANGES = {
    "bingo": (24, 75),
    "word-search": (12, 25),
    "scavenger-hunt": (20, 40),
    "word-scramble": (12, 30),
    "bedtime-routine-chart": (3, 14),
    "reward-chart-maker": (2, 14),
}


# ---------------------------------------------------------------- catalog

def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Catalog:
    def __init__(self, content_dir: Path = CONTENT):
        self.dir = Path(content_dir)
        site_file = self.dir / "site.json"
        if not site_file.exists():
            site_file = CONTENT / "site.json"
        self.site = load_json(site_file)
        self.tools = {t["id"]: t for t in self.site["tools"]}
        self.tools_by_path = {t["path"]: t for t in self.site["tools"]}
        self.sections = self.site["sections"]
        self.cross = {h["slug"]: h for h in self.site["crossHubs"]}
        self.base = self.site["baseUrl"].rstrip("/")

    def theme_group(self, section: str, slug: str):
        for g in self.sections[section]["groups"]:
            if slug in g["slugs"]:
                return g["name"]
        return None

    def all_theme_refs(self):
        for sec, data in self.sections.items():
            for g in data["groups"]:
                for slug in g["slugs"]:
                    yield sec, slug

    def theme_path(self, section: str, slug: str) -> str:
        return f"{self.sections[section]['path']}{slug}/"

    def known_paths(self) -> set:
        """Every URL the finished site is meant to have (built or not)."""
        p = {"/"}
        p.update(t["path"] for t in self.site["tools"])
        p.update(t["embed"] for t in self.site["tools"] if t.get("embed"))
        p.update(d["path"] for d in self.sections.values())
        p.update(self.theme_path(s, g) for s, g in self.all_theme_refs())
        p.update(f"/{h}/" for h in self.cross)
        p.add("/guides/")
        p.update(f"/guides/{g}/" for g in self.site["guides"])
        p.update(f"/{g}/" for g in self.site["pages"])
        return p

    def is_high_value(self, section: str, slug: str) -> bool:
        if section != "bingo":
            return False
        for pat in self.sections["bingo"].get("highValue", []):
            if pat.endswith("*") and slug.startswith(pat[:-1]):
                return True
            if slug == pat:
                return True
        return False

    def ref_to_path(self, ref: str) -> str:
        """'bingo/christmas' -> '/bingo/christmas/'; '/x/' passes through."""
        if ref.startswith("/"):
            return ref
        sec, _, slug = ref.partition("/")
        if sec in self.sections and slug:
            return self.theme_path(sec, slug)
        return "/" + ref.strip("/") + "/"


def classify(path: Path, content_dir: Path):
    """Return (kind, section, slug) for a content file path."""
    path = Path(path).resolve()
    try:
        rel = path.relative_to(Path(content_dir).resolve())
    except ValueError:
        rel = None
    parts = rel.parts if rel else path.parts[-3:]
    stem = path.stem
    if rel is not None and len(parts) == 1:
        if stem == "home":
            return "home", None, "home"
        if stem == "site":
            return "site", None, "site"
    if len(parts) >= 3 and parts[-3] == "themes":
        return "theme", parts[-2], stem
    if len(parts) >= 2:
        folder = parts[-2]
        if folder == "tools":
            return "tool", None, stem
        if folder == "hubs":
            return "hub", None, stem
        if folder == "guides":
            return "guide", None, stem
        if folder == "pages":
            return "page", None, stem
    if stem == "home":
        return "home", None, "home"
    return "unknown", None, stem


# ---------------------------------------------------------------- markup

INLINE_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
BOLD = re.compile(r"\*\*(.+?)\*\*")
ITAL = re.compile(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])")
UL_LINE = re.compile(r"^\s*[\*\-] +")
OL_LINE = re.compile(r"^\s*\d+[\.\)] +")


def as_blocks(body) -> list:
    if body is None:
        return []
    if isinstance(body, str):
        body = [body]
    out = []
    for chunk in body:
        for b in re.split(r"\n\s*\n", str(chunk).strip()):
            if b.strip():
                out.append(b.strip("\n"))
    return out


def inline(text: str) -> str:
    """Escape text and apply **bold**, *italic* and [label](url)."""
    links = []

    def keep_link(m):
        links.append((m.group(1), m.group(2)))
        return f"\x00{len(links) - 1}\x00"

    text = INLINE_LINK.sub(keep_link, text)
    text = html.escape(text, quote=False)
    text = BOLD.sub(r"<strong>\1</strong>", text)
    text = ITAL.sub(r"<em>\1</em>", text)

    def put_link(m):
        label, url = links[int(m.group(1))]
        lab = html.escape(label, quote=False)
        lab = BOLD.sub(r"<strong>\1</strong>", lab)
        ext = url.startswith("http") and "frogsdream.com" not in url
        rel = ' rel="noopener"' if ext else ""
        return f'<a href="{html.escape(url)}"{rel}>{lab}</a>'

    return re.sub(r"\x00(\d+)\x00", put_link, text)


def markup_to_html(body, allow_html: bool = True) -> str:
    out = []
    for b in as_blocks(body):
        lines = [l for l in b.split("\n") if l.strip()]
        first = lines[0].lstrip()
        if first.startswith("<") and allow_html:
            out.append(b)
        elif first.startswith("#### ") or first.startswith("### "):
            lvl = 4 if first.startswith("#### ") else 3
            out.append(f"<h{lvl}>{inline(first[lvl + 1:].strip())}</h{lvl}>")
            rest = "\n".join(lines[1:]).strip()
            if rest:  # text under the sub-heading in the same block
                out.append(markup_to_html(rest, allow_html))
        elif all(UL_LINE.match(l) for l in lines):
            items = "".join(f"<li>{inline(UL_LINE.sub('', l).strip())}</li>" for l in lines)
            out.append(f"<ul>{items}</ul>")
        elif all(OL_LINE.match(l) for l in lines):
            items = "".join(f"<li>{inline(OL_LINE.sub('', l).strip())}</li>" for l in lines)
            out.append(f"<ol>{items}</ol>")
        elif first.startswith("> "):
            txt = " ".join(re.sub(r"^\s*>\s?", "", l) for l in lines)
            out.append(f'<p class="note">{inline(txt.strip())}</p>')
        else:
            out.append(f"<p>{inline(' '.join(l.strip() for l in lines))}</p>")
    return "\n".join(out)


TAG = re.compile(r"<[^>]+>")


# The two-color brand wordmark build.py puts around every visible "frogsdream" (see build.brand_html).
BRAND_MARKUP = '<span class="fd-brand"><span class="fd-b1">frogs</span><span class="fd-b2">dream</span></span>'


def html_to_text(h: str) -> str:
    h = h.replace(BRAND_MARKUP, "frogsdream")  # the wordmark spans are one word, not three
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.S | re.I)
    h = TAG.sub(" ", h)
    return re.sub(r"\s+", " ", html.unescape(h)).strip()


def markup_to_text(body) -> str:
    """Plain text of markup, exactly as the visible page reads (used in JSON-LD too)."""
    return html_to_text(markup_to_html(body))


def inline_text(s: str) -> str:
    return html_to_text(inline(s))


WORD = re.compile(r"[A-Za-z0-9]+(?:['\u2019][A-Za-z]+)*")


def count_words(text: str) -> int:
    return len(WORD.findall(text))


def markup_links(body) -> list:
    return [m.group(2) for b in as_blocks(body) for m in INLINE_LINK.finditer(b)] + re.findall(
        r'href="([^"]+)"', "\n".join(as_blocks(body))
    )


# ---------------------------------------------------------------- prose helpers

def theme_prose(d: dict) -> str:
    parts = [markup_to_text(d.get("intro", ""))]
    for s in d.get("sections", []) or []:
        parts.append(markup_to_text(s.get("body", "")))
    for f in d.get("faq", []) or []:
        parts.append(inline_text(f.get("q", "")))
        parts.append(markup_to_text(f.get("a", "")))
    return " ".join(p for p in parts if p)


def page_prose(d: dict) -> str:
    parts = [markup_to_text(d.get("intro", "")), markup_to_text(d.get("subhead", ""))]
    for s in d.get("sections", []) or []:
        parts.append(markup_to_text(s.get("body", "")))
    if isinstance(d.get("why"), dict):
        parts.append(markup_to_text(d["why"].get("body", "")))
    for f in d.get("faq", []) or []:
        parts.append(inline_text(f.get("q", "")))
        parts.append(markup_to_text(f.get("a", "")))
    for c in d.get("tools", []) or []:
        if isinstance(c, dict):
            parts.append(inline_text(c.get("blurb", "")))
    return " ".join(p for p in parts if p)


def item_to_line(item) -> str:
    """How a content item appears as one textarea line."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        if "square" in item:
            return f"{item['square']} | {item.get('call', '')}".rstrip(" |")
        if "text" in item:
            pts = item.get("points")
            return f"{item['text']} | {pts}" if pts not in (None, "") else item["text"]
        if "label" in item:
            return item.get("label", "")
    return str(item)


def item_display(item) -> str:
    if isinstance(item, dict):
        if "square" in item:
            return f"{item['square']} ({item.get('call', '')})" if item.get("call") else str(item["square"])
        return str(item.get("text") or item.get("label") or "")
    s = str(item)
    return s.split("|")[0].strip()


# ---------------------------------------------------------------- validation

class Report:
    def __init__(self, name):
        self.name = name
        self.errors = []
        self.warnings = []

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def walk_strings(obj, path="$"):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("_"):
                continue
            yield from walk_strings(v, f"{path}.{k}")


def check_dashes(obj, rep: Report):
    for p, s in walk_strings(obj):
        for ch, name in BANNED_CHARS.items():
            if ch in s:
                i = s.index(ch)
                rep.err(f"{p}: banned {name} (U+{ord(ch):04X}) near '{s[max(0, i - 25):i + 25]}'")
        for ent in BANNED_ENTITIES:
            if ent in s:
                rep.err(f"{p}: banned dash entity {ent}")
        plain = s
        if "\n" in s or s.lstrip().startswith(("*", "-", "#", "<")):
            plain = markup_to_text(s)
        m = SPACED_HYPHEN.search(plain)
        if m:
            i = m.start()
            rep.err(f"{p}: spaced hyphen used as a dash near '{plain[max(0, i - 25):i + 25]}'. Rewrite the sentence naturally (no dash, and not a mechanical colon).")


def check_len(rep, d, key, lo, hi, required=True):
    v = d.get(key)
    if not v:
        if required:
            rep.err(f"missing '{key}'")
        return
    n = len(v)
    if n < lo or n > hi:
        rep.err(f"'{key}' is {n} characters, needs {lo}-{hi}: {v!r}")


def check_words(rep, label, n, lo, hi, hard=True):
    if n < lo or n > hi:
        (rep.err if hard else rep.warn)(f"{label}: {n} words, needs {lo}-{hi}")


def check_faq(rep, d, lo, hi, required=True):
    faq = d.get("faq")
    if not faq:
        if required:
            rep.err("missing 'faq'")
        return
    if not (lo <= len(faq) <= hi):
        rep.err(f"faq has {len(faq)} entries, needs {lo}-{hi}")
    for i, f in enumerate(faq):
        if not f.get("q") or not f.get("a"):
            rep.err(f"faq[{i}] needs 'q' and 'a'")
        elif not f["q"].rstrip().endswith("?"):
            rep.warn(f"faq[{i}].q should be a question ending in '?'")


def check_sections(rep, d, required_roles=(), allow_html=False):
    secs = d.get("sections")
    if secs is None:
        if required_roles:
            rep.err("missing 'sections'")
        return
    roles = []
    for i, s in enumerate(secs):
        if not isinstance(s, dict) or "body" not in s:
            rep.err(f"sections[{i}] must be an object with 'heading' and 'body'")
            continue
        if not s.get("heading") and s.get("role") != "list":
            rep.err(f"sections[{i}] needs a 'heading'")
        role = s.get("role", "extra")
        roles.append(role)
        if required_roles and role not in KNOWN_ROLES:
            rep.err(f"sections[{i}].role '{role}' unknown; use one of {', '.join(KNOWN_ROLES)}")
        if not allow_html:
            for b in as_blocks(s["body"]):
                if b.lstrip().startswith("<"):
                    rep.err(f"sections[{i}] contains a raw HTML block; themed pages use markup only")
    for r in required_roles:
        if r not in roles:
            rep.err(f"sections: missing a section with role '{r}'")
    for s in secs:
        if s.get("role") == "variations":
            body = markup_to_html(s.get("body", ""))
            n = body.count("<li>") + body.count("<h3>")
            if n < 3:
                rep.err("variations section needs at least 3 variations (list items or ### subheadings)")


def check_links(rep, cat: Catalog, d):
    known = cat.known_paths()
    blobs = []
    for _, s in walk_strings(d):
        blobs.append(s)
    for url in set(u for s in blobs for u in markup_links(s)):
        if url.startswith("/"):
            base = url.split("#")[0].split("?")[0]
            if base and not base.endswith("/") and "." not in base.rsplit("/", 1)[-1]:
                rep.err(f"internal link {url} must end with a slash")
            elif base.endswith("/") and base not in known:
                rep.err(f"internal link {url} is not a page in site.json")
        elif url.startswith("http://"):
            rep.warn(f"use https for {url}")


def validate_items(rep, section, items, opts, cat):
    lo, hi = ITEM_RANGES[section]
    mode = str((opts or {}).get("mode", "word"))
    if section == "bingo" and mode in ("75", "90", "30"):
        return
    if not isinstance(items, list) or not items:
        rep.err("missing 'items'")
        return
    if not (lo <= len(items) <= hi):
        rep.err(f"items: {len(items)}, needs {lo}-{hi} for {section}")
    seen = set()
    for i, it in enumerate(items):
        line = item_to_line(it)
        key = re.sub(r"\s+", " ", line.lower()).strip()
        if not key:
            rep.err(f"items[{i}] is empty")
            continue
        if key in seen:
            rep.err(f"items[{i}] duplicate: {line!r}")
        seen.add(key)
        if "\n" in line:
            rep.err(f"items[{i}] contains a line break")
        if section == "word-search":
            letters = re.sub(r"[^A-Za-z]", "", line)
            if len(letters) > 15:
                rep.err(f"items[{i}] {line!r} has {len(letters)} letters; word search max is 15")
            elif len(letters) > 12:
                rep.warn(f"items[{i}] {line!r} has {len(letters)} letters; needs a grid of 13+ (fine for adult puzzles)")
            if len(letters) < 3:
                rep.err(f"items[{i}] {line!r} is too short for a word search")
        if section == "word-scramble":
            letters = re.sub(r"[^A-Za-z]", "", line)
            if len(letters) < 3:
                rep.err(f"items[{i}] {line!r}: scramble words need 3+ letters")
            elif len(set(letters.lower())) < 2:
                rep.err(f"items[{i}] {line!r} cannot be scrambled")
            if len(letters) > 14:
                rep.warn(f"items[{i}] {line!r} is long ({len(letters)} letters) for a scramble")
        if section == "bingo" and len(item_display(it)) > 34:
            rep.warn(f"items[{i}] {item_display(it)!r} is long for a bingo square")
        if section == "scavenger-hunt" and "|" in line:
            pts = line.split("|", 1)[1].strip()
            if not pts.isdigit():
                rep.err(f"items[{i}] points after | must be a whole number")


def validate_file(path: Path, cat: Catalog, content_dir: Path) -> Report:
    rep = Report(str(path))
    try:
        d = load_json(path)
    except Exception as e:  # noqa: BLE001
        rep.err(f"invalid JSON: {e}")
        return rep
    kind, section, slug = classify(path, content_dir)
    check_dashes(d, rep)
    check_links(rep, cat, d)
    if kind == "site":
        return rep
    if kind == "unknown":
        rep.err("cannot tell the page type from the file location; see CONTENT-FORMAT.md")
        return rep
    allow_html = kind in ("guide", "page", "home", "hub")
    check_sections(rep, d, REQUIRED_ROLES if kind == "theme" else (), allow_html=allow_html)

    if kind != "home":
        check_len(rep, d, "title", 50, 60)
        check_len(rep, d, "metaDescription", 140, 160)
        if not d.get("h1"):
            rep.err("missing 'h1'")
    else:
        check_len(rep, d, "title", 50, 60)
        check_len(rep, d, "metaDescription", 140, 160)

    if kind == "theme":
        if section not in cat.sections:
            rep.err(f"unknown section folder '{section}'")
            return rep
        if cat.theme_group(section, slug) is None:
            rep.err(f"slug '{slug}' is not listed under sections.{section} in site.json")
        for k in ("shortTitle", "intro", "relatedHeading"):
            if not d.get(k):
                rep.err(f"missing '{k}'")
        intro_words = count_words(markup_to_text(d.get("intro", "")))
        if intro_words > 60:
            rep.warn(f"intro is {intro_words} words; keep it to 1-2 answer-first sentences")
        validate_items(rep, section, d.get("items"), d.get("defaultOptions"), cat)
        if not isinstance(d.get("defaultOptions", {}), dict):
            rep.err("defaultOptions must be an object")
        season = d.get("season", [])
        if not isinstance(season, list) or any(not isinstance(m, int) or not 1 <= m <= 12 for m in season):
            rep.err("season must be a list of month numbers 1-12 ([] for evergreen)")
        hubs = d.get("hubs", [])
        for h in hubs:
            if h not in cat.cross:
                rep.err(f"hubs: unknown cross-tool hub '{h}' (one of {', '.join(cat.cross)})")
        if not 1 <= len(hubs) <= 2 and section not in ("bedtime-routine-chart", "reward-chart-maker"):
            rep.err(f"hubs: list 1-2 cross-tool hub slugs (has {len(hubs)})")
        rel = d.get("related", [])
        if len(rel) != 6:
            rep.err(f"related: needs exactly 6 entries (has {len(rel)})")
        if len(set(rel)) != len(rel):
            rep.err("related: duplicates")
        for r in rel:
            if not re.fullmatch(r"[a-z0-9-]+/[a-z0-9-]+", r):
                rep.err(f"related: '{r}' must look like 'section/slug'")
                continue
            sec2, slug2 = r.split("/")
            if sec2 not in cat.sections or cat.theme_group(sec2, slug2) is None:
                rep.err(f"related: '{r}' is not a themed page in site.json")
            if sec2 == section and slug2 == slug:
                rep.err("related: links to itself")
        check_faq(rep, d, 2, 4)
        n = count_words(theme_prose(d))
        if cat.is_high_value(section, slug):
            check_words(rep, "prose (intro + sections + FAQ)", n, 600, 900)
        else:
            check_words(rep, "prose (intro + sections + FAQ)", n, 350, 700)
        if section == "scavenger-hunt" and not any(s.get("role") == "safety" for s in d.get("sections", [])):
            rep.warn("outdoor hunts need a 'safety' section (adult supervision, stay in sight, no picking protected plants)")
    elif kind == "tool":
        tool = cat.tools_by_path.get(f"/{slug}/")
        if not tool:
            rep.err(f"tools/{slug}.json does not match any tool path in site.json")
        for k in ("shortTitle", "intro"):
            if not d.get(k):
                rep.err(f"missing '{k}'")
        check_faq(rep, d, 2, 8, required=False)
        n = count_words(page_prose(d))
        check_words(rep, "prose", n, 300, 1200, hard=False)
        for r in d.get("featured", []):
            p = cat.ref_to_path(r)
            if p not in cat.known_paths():
                rep.err(f"featured: '{r}' unknown")
    elif kind == "hub":
        is_cross = slug in cat.cross
        is_section = any(s["path"] == f"/{slug}/" for s in cat.sections.values()) or slug == "guides"
        if not (is_cross or is_section):
            rep.err(f"hubs/{slug}.json is not a hub in site.json")
        n = count_words(page_prose(d))
        if is_cross:
            check_words(rep, "hub intro prose", n, 300, 500)
        else:
            check_words(rep, "hub prose", n, 120, 700, hard=False)
        check_faq(rep, d, 2, 6, required=False)
    elif kind == "guide":
        if slug not in cat.site["guides"]:
            rep.err(f"guide '{slug}' is not listed in site.json guides")
        n = count_words(page_prose(d))
        check_words(rep, "guide prose", n, 1000, 1800)
        check_faq(rep, d, 2, 6, required=False)
        for s in d.get("sources", []):
            if not s.get("url", "").startswith("https://"):
                rep.err("sources[] need https 'url' and 'label'")
    elif kind == "page":
        if slug not in cat.site["pages"]:
            rep.err(f"page '{slug}' is not listed in site.json pages")
    elif kind == "home":
        for k in ("h1", "subhead", "tools", "popular", "why"):
            if not d.get(k):
                rep.err(f"missing '{k}'")
        if len(d.get("popular", [])) != 12:
            rep.err("popular: needs exactly 12 entries")
        for p in d.get("popular", []):
            if cat.ref_to_path(p.get("path", "")) not in cat.known_paths():
                rep.err(f"popular: unknown path {p.get('path')}")
        n = count_words(page_prose(d))
        check_words(rep, "home prose", n, 300, 500)
    return rep


# ---------------------------------------------------------------- similarity

def shingles(text: str, k: int = 5) -> set:
    w = [x.lower() for x in WORD.findall(text)]
    return {" ".join(w[i:i + k]) for i in range(max(0, len(w) - k + 1))}


def sentences(text: str):
    for s in re.split(r"(?<=[.!?])\s+", text):
        w = [x.lower() for x in WORD.findall(s)]
        if len(w) > 12:
            yield " ".join(w)


def similarity_report(content_dir: Path, focus: set | None = None):
    """Compare all themed pages. Returns list of (a, b, jaccard) over 0.25 and shared long sentences."""
    pages = {}
    for f in sorted((Path(content_dir) / "themes").glob("*/*.json")):
        try:
            pages[str(f)] = theme_prose(load_json(f))
        except Exception:  # noqa: BLE001
            continue
    sh = {k: shingles(v) for k, v in pages.items()}
    keys = list(pages)
    sims = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if focus and a not in focus and b not in focus:
                continue
            A, B = sh[a], sh[b]
            if not A or not B:
                continue
            j = len(A & B) / len(A | B)
            if j >= 0.25:
                sims.append((a, b, j))
    sent_owner = {}
    dupes = []
    for k in keys:
        for s in set(sentences(pages[k])):
            if s in sent_owner and sent_owner[s] != k:
                if not focus or k in focus or sent_owner[s] in focus:
                    dupes.append((sent_owner[s], k, s))
            else:
                sent_owner[s] = k
    return sims, dupes
