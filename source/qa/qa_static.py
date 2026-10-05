#!/usr/bin/env python3
"""Static QA for a built frogsdream site (SPEC section 13 and related rules).

  python3 source/qa/qa_static.py [SITE_DIR] [--json OUT.json]

SITE_DIR defaults to ./public_html. Reads source/content and source/SPEC.md for the expected page list.
Every check prints PASS or FAIL with details; the exit code is 1 if any check fails.
Checks are independent of build.py's own QA so the two cross-check each other.
"""
from __future__ import annotations

import html
import json
import re
import sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urldefrag

QA = Path(__file__).resolve().parent
SRC = QA.parent
sys.path.insert(0, str(SRC))
import fdlib  # noqa: E402

BASE = "https://frogsdream.com"
BANNED = {"—": "U+2014 em dash", "–": "U+2013 en dash"}
BANNED_ENT = re.compile(r"&(mdash|ndash);|&#(8212|8211);|&#x(2014|2013);", re.I)
# Old brand spellings. The brand is "frogsdream": one word, all lowercase. Matches Frog's Dream with any apostrophe
# (straight, curly, HTML entity or JS escape) and Frogs Dream in any case, plus a whole-word frogsdream in any case
# other than all lowercase (Frogsdream, FrogsDream, FROGSDREAM). Lowercase "frogsdream" and frogsdream.com pass.
OLD_BRAND = re.compile(
    r"(?i:frog(?:['\u2019`]|&#0*39;|&#x0*27;|&apos;|&rsquo;|\\u2019|\\')s[\s\u00a0]*dream)"
    r"|(?i:\bfrogs(?:[\s\u00a0]|&nbsp;)+dream\b)"
    r"|\b(?!frogsdream\b)(?i:frogsdream)\b"
)
YEAR = re.compile(r"(?<!\d)(19|20)\d\d(?!\d)")
TEXT_EXT = {".html", ".css", ".js", ".json", ".txt", ".xml", ".svg", ".webmanifest", ".htaccess", ".md"}
SHARED_JS = ["config.js", "site.js", "rng.js", "print.js", "pdf.js", "toolkit.js"]
TOOL_JS = ["bingo.js", "wordsearch.js", "scavenger.js", "scramble.js", "routine-chart.js", "reward-chart.js", "caller.js"]
NOADS = ["/embed/", "/premium/", "/privacy/", "/terms/", "/contact/", "/bingo-caller/", "/404.html"]


class Doc(HTMLParser):
    """Collects what the checks need from one HTML page."""

    SKIP_TEXT = {"script", "style", "noscript", "textarea", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = None
        self.meta = {}
        self.links = []          # (tag, attr, value, attrs)
        self.canonical = []
        self.h1 = 0
        self.h1_text = []
        self.jsonld = []
        self.text = []
        self.attr_text = []
        self.imgs = []
        self.head_scripts = []
        self.head_styles = []
        self.inputs = []
        self.labels_for = set()
        self.label_depth = 0
        self.faq_q = []
        self.faq_a = []
        self.ids = set()
        self.html_lang = None
        self._stack = []
        self._in_head = False
        self._cur = None
        self._buf = []
        self._faq = False
        self._faq_depth = 0
        self._faq_mode = None
        self._faq_buf = []
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self._depth += 1
        if tag == "html":
            self.html_lang = a.get("lang")
        if tag == "head":
            self._in_head = True
        if tag == "body":
            self._in_head = False
        if "id" in a:
            self.ids.add(a["id"])
        for k in ("alt", "title", "aria-label", "placeholder", "content"):
            if a.get(k) and not (tag == "meta" and k == "content" and not (a.get("name") in ("description",) or (a.get("property") or "").startswith("og:"))):
                self.attr_text.append(a[k])
        if tag == "meta":
            key = a.get("name") or a.get("property") or ("charset" if "charset" in a else None)
            if key:
                self.meta.setdefault(key, []).append(a.get("content", a.get("charset")))
        if tag == "link":
            if a.get("rel") == "canonical":
                self.canonical.append(a.get("href"))
            if a.get("href"):
                self.links.append(("link", "href", a["href"], a))
            if self._in_head and a.get("rel") == "stylesheet":
                self.head_styles.append(a)
        if tag == "a" and a.get("href") is not None:
            self.links.append(("a", "href", a["href"], a))
        if tag in ("img", "script", "iframe", "source") and a.get("src"):
            self.links.append((tag, "src", a["src"], a))
        if tag == "img":
            self.imgs.append(a)
        if tag == "script":
            if self._in_head and a.get("src"):
                self.head_scripts.append(a)
            if a.get("type") == "application/ld+json":
                self._cur, self._buf = "jsonld", []
            else:
                self._cur = "script"
        if tag == "title":
            self._cur, self._buf = "title", []
        if tag == "h1":
            self.h1 += 1
            self._cur, self._buf = "h1", []
        if tag in ("input", "select", "textarea") and a.get("type") not in ("hidden", "submit", "button"):
            self.inputs.append(a)
        if tag == "label":
            if a.get("for"):
                self.labels_for.add(a["for"])
            self.label_depth += 1
            if tag in ("input",):
                pass
        if tag in ("input", "select", "textarea") and self.label_depth:
            a["_wrapped"] = True
        if tag == "section" and "faq" in (a.get("class") or "").split():
            self._faq, self._faq_depth = True, self._depth
        if self._faq and tag == "h3":
            self._faq_mode, self._faq_buf = "q", []
        if self._faq and tag == "div" and "faq-item" in (a.get("class") or ""):
            self._faq_mode = None
        if self._faq and tag in ("p", "ul", "ol") and self._faq_mode in (None, "a") and self.faq_q:
            if self._faq_mode is None:
                self._faq_mode, self._faq_buf = "a", []
        self._stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self._stack and tag in self._stack:
            while self._stack:
                t = self._stack.pop()
                if t == tag:
                    break
        if tag == "title" and self._cur == "title":
            self.title = "".join(self._buf)
            self._cur = None
        if tag == "h1" and self._cur == "h1":
            self.h1_text.append(" ".join("".join(self._buf).split()))
            self._cur = None
        if tag == "script":
            if self._cur == "jsonld":
                self.jsonld.append("".join(self._buf))
            self._cur = None
        if tag == "label":
            self.label_depth = max(0, self.label_depth - 1)
        if self._faq:
            if tag == "h3" and self._faq_mode == "q":
                self.faq_q.append(" ".join("".join(self._faq_buf).split()))
                self._faq_mode = None
            if tag == "div" and self._faq_mode == "a":
                self.faq_a.append(" ".join("".join(self._faq_buf).split()))
                self._faq_mode = None
            if tag == "section":
                if self._faq_mode == "a":
                    self.faq_a.append(" ".join("".join(self._faq_buf).split()))
                self._faq = False
                self._faq_mode = None
        self._depth -= 1

    def handle_data(self, data):
        if self._cur in ("title", "h1", "jsonld"):
            self._buf.append(data)
        if self._faq_mode:
            self._faq_buf.append(data + (" " if data.endswith("\n") else ""))
        if not any(t in self.SKIP_TEXT for t in self._stack):
            self.text.append(data)


class QA:
    def __init__(self, site: Path):
        self.site = site
        self.results = []
        self.pages = {}       # url path -> Doc
        self.raw = {}
        self.cat = fdlib.Catalog(SRC / "content")

    def check(self, name, problems, info=""):
        problems = list(problems)
        ok = not problems
        self.results.append({"check": name, "pass": ok, "problems": problems[:50], "count": len(problems), "info": info})
        print(("PASS " if ok else "FAIL ") + name + (f"  ({info})" if info else ""))
        for p in problems[:25]:
            print("     - " + str(p))
        if len(problems) > 25:
            print(f"     ... and {len(problems) - 25} more")

    # ------------------------------------------------------------------ loading
    def load(self):
        for f in sorted(self.site.rglob("*.html")):
            rel = f.relative_to(self.site).as_posix()
            if rel == "index.html":
                path = "/"
            elif rel.endswith("/index.html"):
                path = "/" + rel[: -len("index.html")]
            else:
                path = "/" + rel
            raw = f.read_text("utf-8")
            d = Doc()
            d.feed(raw)
            self.pages[path] = d
            self.raw[path] = raw

    def indexable(self):
        out = []
        for p, d in self.pages.items():
            robots = ",".join(d.meta.get("robots", []) or [])
            if "noindex" in robots or p.endswith(".html"):
                continue
            out.append(p)
        return sorted(out)

    def resolve(self, path):
        path = path.split("?")[0]
        f = self.site / path.lstrip("/")
        if path.endswith("/"):
            return (f / "index.html").exists()
        return f.exists() and f.is_file()

    # ------------------------------------------------------------------ expected page list
    def expected_paths(self):
        spec = (SRC / "SPEC.md").read_text("utf-8")
        exp = {"/"}
        for m in re.finditer(r"^- (/[a-z0-9\-/]+/)", spec, re.M):
            exp.add(m.group(1))
        sec_rx = {
            "bingo": r"Themed bingo pages:.*?\n(.*?)\nHub: /bingo/",
            "word-search": r"Themed word search pages:.*?\n(.*?)\nHub: /word-search/",
            "scavenger-hunt": r"Themed scavenger hunt pages:.*?\n(.*?)\nHub: /scavenger-hunt/",
            "word-scramble": r"Themed word scramble pages:.*?\n(.*?)\nHub: /word-scramble/",
            "bedtime-routine-chart": r"Bedtime chart variants:.*?\n(.*?)\n\n",
            "reward-chart-maker": r"Reward chart variants:.*?\n(.*?)\n\n",
        }
        for sec, rx in sec_rx.items():
            blk = re.search(rx, spec, re.S).group(1)
            for line in blk.splitlines():
                line = re.sub(r"\(.*?\)", "", line.lstrip("- "))
                for slug in re.split(r",\s*", line):
                    slug = slug.strip()
                    if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
                        exp.add(f"/{sec}/{slug}/")
        for hub in ("bingo", "word-search", "scavenger-hunt", "word-scramble", "guides"):
            exp.add(f"/{hub}/")
        gblk = re.search(r"Guides: /guides/<slug>/.*?\n(.*?)\n\nHub: /guides/", spec, re.S).group(1)
        for m in re.finditer(r"^- ([a-z0-9\-]+)", gblk, re.M):
            exp.add(f"/guides/{m.group(1)}/")
        exp = {e for e in exp if "<" not in e and not e.startswith("/assets/")}
        return exp

    # ------------------------------------------------------------------ checks
    def run(self):
        self.load()
        site = self.site
        idx = self.indexable()

        # 1. root and asset files
        need = ["index.html", "404.html", ".htaccess", "robots.txt", "sitemap.xml", "ads.txt", "favicon.svg", "favicon.ico",
                "apple-touch-icon.png", "site.webmanifest", "assets/css/site.css", "assets/js/themes.json",
                "assets/img/frog-mascot.svg", "assets/img/frog-waving.svg", "assets/img/frog-sleeping.svg",
                "assets/img/frog-pencil.svg", "assets/img/frog-celebrating.svg", "assets/img/og/default.png"]
        need += [f"assets/js/{j}" for j in SHARED_JS + TOOL_JS]
        probs = [f"missing {n}" for n in need if not (site / n).exists()]
        keys = [f for f in site.glob("*.txt") if re.fullmatch(r"[0-9a-f]{32}\.txt", f.name)]
        if len(keys) != 1:
            probs.append(f"expected one IndexNow key file, found {len(keys)}")
        elif keys[0].read_text().strip() != keys[0].stem:
            probs.append("IndexNow key file content does not equal its name")
        icons = list((site / "assets/img/icons").glob("*.svg"))
        if len(icons) < 36:
            probs.append(f"only {len(icons)} icons")
        for ic in icons:
            t = ic.read_text()
            if 'viewBox="0 0 48 48"' not in t or "currentColor" not in t:
                probs.append(f"icon {ic.name}: not 48x48 viewBox with currentColor")
        try:
            from PIL import Image
            with Image.open(site / "apple-touch-icon.png") as im:
                if im.size != (180, 180):
                    probs.append(f"apple-touch-icon is {im.size}")
            for og in (site / "assets/img/og").glob("*.png"):
                with Image.open(og) as im:
                    if im.size != (1200, 630):
                        probs.append(f"og {og.name} is {im.size}")
            for p in ["bingo-card-generator", "word-search-maker", "scavenger-hunt-generator", "word-scramble-maker",
                      "bedtime-routine-chart", "reward-chart-maker", "bingo-caller", "bingo", "word-search", "scavenger-hunt",
                      "word-scramble", "guides"] + list(self.cat.cross):
                if not (site / f"assets/img/og/{p}.png").exists():
                    probs.append(f"no OG image for {p}")
        except ImportError:
            pass
        if (site / "deliverables").exists() or list(site.rglob("*.zip")):
            probs.append("deliverables or zip files inside public_html")
        self.check("Root files, assets, icons, OG images, IndexNow key", probs, f"{len(icons)} icons")

        # 2. sitemap vs spec
        sm = (site / "sitemap.xml").read_text("utf-8")
        locs = re.findall(r"<loc>(.*?)</loc>", sm)
        lastmods = re.findall(r"<lastmod>(\d{4}-\d\d-\d\d)</lastmod>", sm)
        sm_paths = {urlparse(u).path for u in locs}
        exp = self.expected_paths()
        probs = []
        probs += [f"spec page missing from sitemap: {p}" for p in sorted(exp - sm_paths) if not (p.startswith("/embed/") and p != "/embed/")]
        probs += [f"sitemap URL has no file: {p}" for p in sorted(sm_paths) if not self.resolve(p)]
        probs += [f"sitemap lists non-indexable {p}" for p in sorted(sm_paths) if (p.startswith("/embed/") and p != "/embed/") or p not in idx]
        probs += [f"indexable page not in sitemap: {p}" for p in idx if p not in sm_paths]
        probs += [f"sitemap URL not absolute https canonical host: {u}" for u in locs if not u.startswith(BASE + "/")]
        if len(lastmods) != len(locs):
            probs.append("lastmod missing on some URLs")
        if len(set(locs)) != len(locs):
            probs.append("duplicate sitemap URLs")
        for e in ("/embed/bingo/", "/embed/word-search/"):
            if not self.resolve(e):
                probs.append(f"missing {e}")
        self.check("Every spec sitemap URL exists and sitemap.xml is correct", probs,
                   f"{len(locs)} URLs in sitemap, {len(exp)} pages named in SPEC, {len(idx)} indexable pages built")

        # 3. robots, htaccess, ads.txt, config defaults
        probs = []
        rob = (site / "robots.txt").read_text()
        if "Disallow: /embed/" in rob or "Allow: /" not in rob or f"Sitemap: {BASE}/sitemap.xml" not in rob:
            probs.append("robots.txt does not match spec (Allow: / plus Sitemap, no embed disallow)")
        ht = (site / ".htaccess").read_text()
        for needle in ["RewriteEngine On", "%{HTTPS} off", "www", "DirectoryIndex index.html", "ErrorDocument 404 /404.html",
                       "mod_deflate", "mod_expires", "nosniff", "strict-origin-when-cross-origin", "<IfModule"]:
            if needle not in ht:
                probs.append(f".htaccess lacks {needle}")
        if "Content-Security-Policy" in ht:
            probs.append(".htaccess sets a CSP")
        ads = (site / "ads.txt").read_text()
        if "# Replace with: google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0" not in ads:
            probs.append("ads.txt placeholder line differs from spec")
        cfg = (site / "assets/js/config.js").read_text()
        for k in ("ADSENSE_CLIENT", "AD_SLOT_IN_ARTICLE", "PACK_URL", "TIP_URL"):
            if not re.search(k + r':\s*""', cfg):
                probs.append(f"config.js {k} is not empty")
        if 'PACK_PRICE: "$7"' not in cfg or 'CONTACT_EMAIL: "hello@frogsdream.com"' not in cfg:
            probs.append("config.js PACK_PRICE or CONTACT_EMAIL differs from spec")
        self.check("robots.txt, .htaccess, ads.txt and config.js defaults", probs)

        # 4. internal link check
        probs, n = [], 0
        for p, d in self.pages.items():
            for tag, attr, v, a in d.links:
                v = html.unescape(v)
                if v.startswith(("mailto:", "tel:", "javascript:", "data:")) or v == "":
                    continue
                # The paid pack zip is uploaded by the owner straight to the server, never built.
                if p.startswith("/pack-download-") and v == "frogsdream-Mega-Pack.zip":
                    continue
                u = urlparse(v)
                if u.scheme in ("http", "https") and u.netloc and u.netloc != "frogsdream.com":
                    if u.scheme != "https":
                        probs.append(f"{p}: insecure external link {v}")
                    if tag == "a" and "noopener" not in (a.get("rel") or ""):
                        probs.append(f"{p}: external link without rel=noopener {v}")
                    continue
                if u.netloc == "frogsdream.com" and tag == "a" and not p.startswith("/embed/") and a.get("rel") != "canonical":
                    pass
                target, frag = urldefrag(u.path if u.path else p)
                if not target.startswith("/"):
                    target = "/" + target if not p.endswith("/") else p + target
                n += 1
                if not self.resolve(target):
                    probs.append(f"{p}: broken {tag} {attr}={v}")
                elif u.fragment and (target == p or target.endswith("/")) and tag == "a":
                    td = self.pages.get(target)
                    if td and u.fragment not in td.ids and not u.fragment.startswith(("s=", ":~:")):
                        probs.append(f"{p}: anchor #{u.fragment} not found on {target}")
                if tag == "a" and target.endswith("/index.html"):
                    probs.append(f"{p}: link to index.html instead of folder URL {v}")
                if tag == "a" and not target.endswith("/") and "." not in target.rsplit("/", 1)[-1]:
                    probs.append(f"{p}: internal link without trailing slash {v}")
        self.check("Internal link check (href, src, anchors) and external link safety", probs, f"{n} internal references checked")

        # 5. head metadata: title, description, canonical, h1, OG, lang
        probs = []
        seen = defaultdict(lambda: defaultdict(list))
        for p in idx:
            d = self.pages[p]
            t = html.unescape(d.title or "")
            desc = (d.meta.get("description") or [""])[0]
            canon = d.canonical[0] if d.canonical else ""
            if not 50 <= len(t) <= 60:
                probs.append(f"{p}: title length {len(t)} ({t})")
            if not 140 <= len(desc) <= 160:
                probs.append(f"{p}: meta description length {len(desc)}")
            if len(d.canonical) != 1 or canon != BASE + p:
                probs.append(f"{p}: canonical {d.canonical}")
            if d.h1 != 1:
                probs.append(f"{p}: {d.h1} H1 elements")
            if d.html_lang != "en":
                probs.append(f"{p}: html lang={d.html_lang}")
            for k in ("viewport", "theme-color", "charset", "og:title", "og:description", "og:url", "og:image", "og:type", "og:site_name", "twitter:card"):
                if not d.meta.get(k):
                    probs.append(f"{p}: missing meta {k}")
            if d.meta.get("og:site_name", [""])[0] != "frogsdream":
                probs.append(f"{p}: og:site_name")
            if (d.meta.get("og:url") or [""])[0] != BASE + p:
                probs.append(f"{p}: og:url mismatch")
            img = (d.meta.get("og:image") or [""])[0]
            if not img.startswith(BASE + "/") or not self.resolve(urlparse(img).path):
                probs.append(f"{p}: og:image {img}")
            if (d.meta.get("twitter:card") or [""])[0] != "summary_large_image":
                probs.append(f"{p}: twitter:card")
            seen["title"][t].append(p)
            seen["description"][desc].append(p)
            seen["canonical"][canon].append(p)
        for kind, m in seen.items():
            for val, ps in m.items():
                if len(ps) > 1:
                    probs.append(f"duplicate {kind} on {ps}: {val[:70]}")
        self.check("Unique titles (50-60), meta descriptions (140-160), canonicals, single H1, OG tags", probs, f"{len(idx)} indexable pages")

        # 6. noindex pages
        probs = []
        for p, d in self.pages.items():
            robots = ",".join(d.meta.get("robots", []) or [])
            if p.startswith("/embed/") and p != "/embed/":
                if "noindex" not in robots or "follow" not in robots.replace("nofollow", ""):
                    probs.append(f"{p}: robots={robots}")
                credit = [a for t, at, v, a in d.links if t == "a" and "frogsdream.com" in v and a.get("target") == "_blank" and "noopener" in (a.get("rel") or "")]
                if not credit:
                    probs.append(f"{p}: no visible credit link with target=_blank rel=noopener")
                txt = " ".join("".join(d.text).split())
                if "Free tool by frogsdream" not in txt:
                    probs.append(f"{p}: credit text missing")
                if d.h1 > 1:
                    probs.append(f"{p}: {d.h1} H1")
            if p == "/404.html" and "noindex" not in robots:
                probs.append("404.html is not noindex")
        if "/404.html" not in self.pages:
            probs.append("no 404.html")
        self.check("Embed pages and 404 are noindex with credit link", probs)

        # 7. JSON-LD
        probs, nblocks = [], 0
        for p, d in self.pages.items():
            types = defaultdict(list)
            for blk in d.jsonld:
                nblocks += 1
                try:
                    j = json.loads(blk)
                except Exception as e:  # noqa: BLE001
                    probs.append(f"{p}: invalid JSON-LD ({e})")
                    continue
                for node in (j if isinstance(j, list) else j.get("@graph", [j])):
                    if j.get("@context", node.get("@context")) not in ("https://schema.org", "http://schema.org", "https://schema.org/"):
                        probs.append(f"{p}: JSON-LD @context {j.get('@context')}")
                    types[node.get("@type")].append(node)
                if "aggregateRating" in blk or '"review"' in blk.lower():
                    probs.append(f"{p}: JSON-LD contains ratings or reviews")
            if p not in idx:
                continue
            kind = self.kind(p)
            if p != "/" and "BreadcrumbList" not in types:
                probs.append(f"{p}: no BreadcrumbList")
            for bl in types.get("BreadcrumbList", []):
                items = bl.get("itemListElement", [])
                for i, it in enumerate(items, 1):
                    if it.get("position") != i or not it.get("name") or not str(it.get("item", "")).startswith(BASE + "/"):
                        probs.append(f"{p}: bad breadcrumb item {it}")
                    elif not self.resolve(urlparse(it["item"]).path):
                        probs.append(f"{p}: breadcrumb target missing {it['item']}")
                if items and items[-1].get("item") != BASE + p:
                    probs.append(f"{p}: last breadcrumb is not the page itself")
            if kind == "home":
                if "WebSite" not in types or "Organization" not in types:
                    probs.append("home: needs WebSite and Organization")
                for o in types.get("Organization", []):
                    if o.get("name") != "frogsdream" or not o.get("url") or not o.get("logo"):
                        probs.append("home: Organization needs name, url, logo")
            if kind in ("tool", "theme"):
                wa = types.get("WebApplication", [])
                if len(wa) != 1:
                    probs.append(f"{p}: {len(wa)} WebApplication blocks")
                for w in wa:
                    cat = "GameApplication" if p == "/bingo-caller/" else "EducationalApplication"
                    if w.get("applicationCategory") not in (cat, "EducationalApplication") or w.get("operatingSystem") != "Any (web browser)":
                        probs.append(f"{p}: WebApplication category/OS")
                    if w.get("isAccessibleForFree") is not True or (w.get("offers") or {}).get("price") != "0" or (w.get("offers") or {}).get("priceCurrency") != "USD":
                        probs.append(f"{p}: WebApplication offers/isAccessibleForFree")
                    if w.get("url") != BASE + p or not w.get("name"):
                        probs.append(f"{p}: WebApplication url/name")
            if kind == "hub":
                cp = types.get("CollectionPage", [])
                if not cp:
                    probs.append(f"{p}: no CollectionPage")
                il = types.get("ItemList", []) + [c.get("mainEntity") for c in cp if isinstance(c.get("mainEntity"), dict)]
                if not any(x and x.get("itemListElement") for x in il):
                    probs.append(f"{p}: no ItemList with items")
                for x in il:
                    for it in (x or {}).get("itemListElement", []):
                        u = it.get("url") or it.get("item")
                        if isinstance(u, dict):
                            u = u.get("@id") or u.get("url")
                        if not u or not self.resolve(urlparse(u).path):
                            probs.append(f"{p}: ItemList entry not found {u}")
            if kind == "guide":
                art = types.get("Article", []) + types.get("BlogPosting", [])
                if not art:
                    probs.append(f"{p}: no Article")
                for a in art:
                    if not a.get("headline") or not re.fullmatch(r"\d{4}-\d\d-\d\d.*", str(a.get("datePublished", ""))):
                        probs.append(f"{p}: Article headline/datePublished")
                    if (a.get("author") or {}).get("@type") != "Organization" or (a.get("author") or {}).get("name") != "frogsdream" or not a.get("publisher"):
                        probs.append(f"{p}: Article author/publisher")
                    if len(a.get("headline", "")) > 110:
                        probs.append(f"{p}: headline over 110 chars")
            if p == "/premium/":
                pr = types.get("Product", [])
                if not pr or not pr[0].get("offers") or not pr[0].get("name") or not pr[0].get("image"):
                    probs.append("/premium/: Product with offers, name and image needed")
                elif str(pr[0]["offers"].get("price")) not in ("7", "7.00") or pr[0]["offers"].get("priceCurrency") != "USD":
                    probs.append("/premium/: Product price must be 7 USD")
                if "$7" not in "".join(d.text):
                    probs.append("/premium/: $7 not in HTML text")
                for im in (pr[0].get("image") if pr else []) or []:
                    if not self.resolve(urlparse(im).path):
                        probs.append(f"/premium/: Product image missing {im}")
            # FAQ markup must match visible FAQ exactly
            faq = types.get("FAQPage", [])
            if d.faq_q and not faq:
                probs.append(f"{p}: visible FAQ but no FAQPage")
            for f in faq:
                ents = f.get("mainEntity", [])
                qs = [e.get("name") for e in ents]
                ans = [" ".join(str((e.get("acceptedAnswer") or {}).get("text", "")).split()) for e in ents]
                if qs != d.faq_q:
                    probs.append(f"{p}: FAQPage questions differ from visible FAQ")
                elif [a.replace(" ", "") for a in ans] != [a.replace(" ", "") for a in d.faq_a]:
                    probs.append(f"{p}: FAQPage answers differ from visible FAQ")
        self.check("JSON-LD valid and complete (Breadcrumb, WebApplication, FAQPage = visible FAQ, CollectionPage, Article, Product)", probs, f"{nblocks} blocks")

        # 8. inbound links
        inbound = defaultdict(set)
        for p, d in self.pages.items():
            if p.startswith("/embed/") and p != "/embed/" or p == "/404.html":
                continue
            for tag, attr, v, a in d.links:
                if tag != "a":
                    continue
                u = urlparse(html.unescape(v))
                if u.netloc and u.netloc != "frogsdream.com":
                    continue
                t = u.path or p
                if t != p:
                    inbound[t].add(p)
        low = [f"{p}: {len(inbound[p])} inbound" for p in idx if len(inbound[p]) < 3]
        mn = min(len(inbound[p]) for p in idx)
        self.check("3+ internal inbound links for every indexable page", low, f"minimum {mn}")

        # 8b. themed page linking rules
        probs = []
        for p in idx:
            if self.kind(p) != "theme":
                continue
            sec = p.strip("/").split("/")[0]
            data = fdlib.load_json(SRC / "content/themes" / sec / (p.strip("/").split("/")[1] + ".json"))
            outs = {urlparse(v).path for t, at, v, a in self.pages[p].links if t == "a"}
            tool = self.cat.sections[sec]["path"] if self.cat.sections[sec].get("hubIsTool") else next(
                t["path"] for t in self.cat.site["tools"] if t["id"] == self.cat.sections[sec]["tool"])
            if tool not in outs:
                probs.append(f"{p}: no link to its tool {tool}")
            if self.cat.sections[sec]["path"] not in outs:
                probs.append(f"{p}: no link to its hub")
            for h in data.get("hubs", []):
                if f"/{h}/" not in outs:
                    probs.append(f"{p}: no link to cross hub {h}")
            rel = [r for r in data.get("related", [])]
            if len(rel) != 6:
                probs.append(f"{p}: {len(rel)} related")
            for r in rel:
                if "/" + r + "/" not in outs:
                    probs.append(f"{p}: related {r} not linked")
        for t in self.cat.site["tools"]:
            if t["path"] not in self.pages:
                continue
            outs = {urlparse(v).path for tg, at, v, a in self.pages[t["path"]].links if tg == "a"}
            themed = [o for o in outs if self.kind(o) == "theme"]
            if t["id"] != "caller" and len(themed) < (len(self.theme_paths(t)) if len(self.theme_paths(t)) < 12 else 12):
                probs.append(f"{t['path']}: links to only {len(themed)} themes")
        self.check("Themed pages link to tool, hub, cross hubs and 6 related; tools link to top themes", probs)

        # 9. sizes
        probs = []
        big = 0
        for p, raw in self.raw.items():
            n = len(raw.encode("utf-8"))
            big = max(big, n)
            if n >= 60 * 1024:
                probs.append(f"{p}: {n} bytes HTML")
        css = (site / "assets/css/site.css").stat().st_size
        if css >= 25 * 1024:
            probs.append(f"site.css {css} bytes")
        if len(list((site / "assets/css").glob("*.css"))) != 1:
            probs.append("more than one CSS file")
        shared = sum((site / "assets/js" / j).stat().st_size for j in SHARED_JS)
        if shared >= 40 * 1024:
            probs.append(f"shared JS {shared} bytes")
        tsz = {}
        for j in TOOL_JS + ["guide-patterns.js"]:
            f = site / "assets/js" / j
            if f.exists():
                tsz[j] = f.stat().st_size
                if tsz[j] >= 30 * 1024:
                    probs.append(f"{j}: {tsz[j]} bytes")
        for f in site.rglob("*"):
            if f.is_file() and f.suffix in (".png", ".svg", ".woff2") and f.stat().st_size > 200 * 1024:
                probs.append(f"{f.relative_to(site)}: {f.stat().st_size} bytes")
        total = sum(f.stat().st_size for f in site.rglob("*") if f.is_file())
        self.check("Size budgets (HTML < 60 KB, CSS < 25 KB, shared JS < 40 KB, tool JS < 30 KB)", probs,
                   f"largest HTML {big} B, CSS {css} B, shared JS {shared} B, largest tool JS {max(tsz.values())} B, site total {total // 1024} KB")

        # 10. banned dashes in output and source content
        probs = []
        roots = [(site, None), (SRC / "content", None), (SRC / "tools", None), (SRC / "static", None), (SRC / "css", None)]
        files = []
        for r, _ in roots:
            files += [f for f in r.rglob("*") if f.is_file() and (f.suffix in TEXT_EXT or f.name == ".htaccess")]
        files += [SRC / "CONTENT-FORMAT.md", SRC / "TOOL-CONTRACT.md"] + list((SRC / "art" / "js").glob("*.js")) + [SRC / "art" / "drawkit.js"]
        for f in files:
            if not f.exists():
                continue
            try:
                t = f.read_text("utf-8")
            except UnicodeDecodeError:
                continue
            for ch, name in BANNED.items():
                for m in re.finditer(ch, t):
                    ln = t.count("\n", 0, m.start()) + 1
                    probs.append(f"{f}: line {ln}: {name}")
            for m in BANNED_ENT.finditer(t):
                probs.append(f"{f}: entity {m.group(0)}")
        # spaced hyphen used as a dash, in visible text and text attributes of every page
        for p, d in self.pages.items():
            txt = " ".join("".join(d.text).split())
            for m in re.finditer(r"\S+ - \S+", txt):
                probs.append(f"{p}: spaced hyphen dash in text: ...{m.group(0)}...")
            for at in d.attr_text:
                if " - " in at:
                    probs.append(f"{p}: spaced hyphen dash in attribute: {at[:60]}")
            for blk in d.jsonld:
                if " - " in blk:
                    probs.append(f"{p}: spaced hyphen dash in JSON-LD")
        for f in (SRC / "content").rglob("*.json"):
            for path, s in fdlib.walk_strings(fdlib.load_json(f)):
                if re.search(r"(?<!<)\S - \S", s) and not s.lstrip().startswith("<"):
                    for line in s.split("\n"):
                        if re.search(r"\S - \S", line) and not line.startswith("- "):
                            probs.append(f"{f.relative_to(SRC)} {path}: spaced hyphen dash")
        self.check("No em/en dashes (U+2014, U+2013) or spaced-hyphen dashes in public_html and source content", probs, f"{len(files)} files scanned")

        # 10b. brand spelling: always "frogsdream" (one word, lowercase). Old variants fail the build.
        probs, n = [], 0
        for r in (site, SRC / "content"):
            for f in r.rglob("*"):
                if not f.is_file() or not (f.suffix in TEXT_EXT or f.name == ".htaccess"):
                    continue
                try:
                    t = f.read_text("utf-8")
                except UnicodeDecodeError:
                    continue
                n += 1
                for m in OLD_BRAND.finditer(t):
                    ln = t.count("\n", 0, m.start()) + 1
                    probs.append(f"{f}: line {ln}: old brand spelling {m.group(0)!r} (write frogsdream)")
        self.check("Brand is written frogsdream (no Frog's Dream, Frogs Dream or capitalized Frogsdream)", probs, f"{n} files scanned")

        # 11. years in titles and URLs
        probs = []
        for p, d in self.pages.items():
            for label, val in (("title", d.title or ""), ("og:title", (d.meta.get("og:title") or [""])[0]), ("h1", " ".join(d.h1_text)), ("url", p)):
                if YEAR.search(val):
                    probs.append(f"{p}: year in {label}: {val}")
        for f in site.rglob("*"):
            if YEAR.search(f.relative_to(site).as_posix()) and f.suffix not in (".woff2",):
                probs.append(f"file path with a year: {f.relative_to(site)}")
        self.check("No year numbers in titles, H1s or URLs", probs)

        # 12. render blocking, images, accessibility basics
        probs = []
        for p, d in self.pages.items():
            for s in d.head_scripts:
                u = urlparse(s.get("src", ""))
                if "defer" not in s and "async" not in s and s.get("type") != "module":
                    probs.append(f"{p}: render-blocking script {s.get('src')}")
                if u.netloc:
                    probs.append(f"{p}: third-party script in head {s.get('src')}")
            for s in d.head_styles:
                if urlparse(s.get("href", "")).netloc:
                    probs.append(f"{p}: third-party stylesheet {s.get('href')}")
            if len(d.head_styles) > 1:
                probs.append(f"{p}: {len(d.head_styles)} stylesheets")
            if re.search(r"fonts\.googleapis|fonts\.gstatic|google-analytics|googletagmanager", self.raw[p]):
                probs.append(f"{p}: Google Fonts or analytics reference")
            if re.search(r"pagead2\.googlesyndication", self.raw[p]):
                probs.append(f"{p}: AdSense tag hard coded in HTML (must come from site.js only)")
            for im in d.imgs:
                if "alt" not in im:
                    probs.append(f"{p}: img without alt {im.get('src')}")
                if not (im.get("width") and im.get("height")) and not str(im.get("src", "")).endswith(".svg"):
                    probs.append(f"{p}: img without width/height {im.get('src')}")
                elif not (im.get("width") and im.get("height")):
                    probs.append(f"{p}: img without width/height {im.get('src')}")
            for inp in d.inputs:
                if not (inp.get("id") in d.labels_for or inp.get("aria-label") or inp.get("aria-labelledby") or inp.get("_wrapped")):
                    probs.append(f"{p}: form control without label {inp.get('id') or inp.get('name')}")
            vp = (d.meta.get("viewport") or [""])[0]
            if "user-scalable=no" in vp or "maximum-scale=1" in vp:
                probs.append(f"{p}: viewport blocks zoom")
        cssText = (site / "assets/css/site.css").read_text()
        if "prefers-reduced-motion" not in cssText:
            probs.append("site.css has no prefers-reduced-motion rule")
        if ":focus-visible" not in cssText and ":focus" not in cssText:
            probs.append("site.css has no focus styles")
        if "font-display:swap" not in cssText.replace(" ", ""):
            probs.append("display font without font-display: swap")
        if "@media print" not in cssText:
            probs.append("no print CSS")
        self.check("No render-blocking or third-party resources in head; img alt/size; labelled inputs; a11y CSS", probs)

        # 13. ad placement rules in markup
        probs = []
        for p, d in self.pages.items():
            raw = self.raw[p]
            m = re.search(r'<section class="tool[^"]*"[^>]*>(.*?)</section>(?=<p class="pack-cta|<section|</div>)', raw, re.S)
            if m and ("ad-slot" in m.group(1) or "adsbygoogle" in m.group(1)):
                probs.append(f"{p}: ad markup inside the tool")
            if 'class="tool' in raw and "no-ads" not in re.search(r'<section class="tool[^"]*"', raw).group(0):
                probs.append(f"{p}: tool container without no-ads class")
            if raw.count('class="ad-slot') > 2:
                probs.append(f"{p}: more than 2 manual ad slots")
            if any(p.startswith(n) for n in NOADS) and 'class="ad-slot' in raw:
                probs.append(f"{p}: ad slot on a no-ads page")
        css_ads = re.search(r"\.ad-slot\{[^}]*display:none", cssText.replace(" ", ""))
        if not css_ads:
            probs.append("ad slots are not display:none by default")
        if not re.search(r"@media print\{[^@]*\.ad-slot", cssText.replace(" ", "")) and ".ad-slot" not in cssText.split("@media print", 1)[-1]:
            probs.append("ad slots not hidden in print")
        self.check("Ad placement rules in markup (none in tools, max 2 slots, none on no-ads pages, hidden by default and in print)", probs)

        # 14. similarity across themed pages
        sims, dupes = fdlib.similarity_report(SRC / "content")
        probs = [f"Jaccard {j:.3f}: {Path(a).parent.name}/{Path(a).stem} vs {Path(b).parent.name}/{Path(b).stem}" for a, b, j in sims]
        probs += [f"shared sentence over 12 words: {Path(a).stem} / {Path(b).stem}: {s[:80]}" for a, b, s in dupes]
        texts = {f: fdlib.theme_prose(fdlib.load_json(f)) for f in sorted((SRC / "content/themes").glob("*/*.json"))}
        sh = {f: fdlib.shingles(t) for f, t in texts.items()}
        ks = list(sh)
        mx, pair = 0.0, None
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                if sh[a] and sh[b]:
                    j = len(sh[a] & sh[b]) / len(sh[a] | sh[b])
                    if j > mx:
                        mx, pair = j, (a, b)
        self.check("5-word shingle Jaccard < 0.25 across themed pages and no shared sentence over 12 words", probs,
                   f"{len(ks)} themed pages, {len(ks) * (len(ks) - 1) // 2} pairs, max {mx:.3f} ({pair[0].parent.name}/{pair[0].stem} vs {pair[1].parent.name}/{pair[1].stem})")

        # 15. content rules per page: word counts, items, faq
        probs = []
        for f in sorted((SRC / "content").rglob("*.json")):
            if f.name == "site.json":
                continue
            rep = fdlib.validate_file(f, self.cat, SRC / "content")
            probs += [f"{f.relative_to(SRC)}: {e}" for e in rep.errors]
        self.check("Content validator (word counts, item counts, FAQ counts, links) on every content file", probs)

        # 16. themes.json
        probs = []
        tj = json.loads((site / "assets/js/themes.json").read_text())
        n = len(tj) if isinstance(tj, list) else len(tj.get("themes", tj))
        if n < sum(1 for p in idx if self.kind(p) == "theme"):
            probs.append(f"themes.json has {n} entries")
        self.check("themes.json covers every themed page", probs, f"{n} entries")

        # 17. Honesty and trademark spot checks
        probs = []
        tm = re.compile(r"\b(Super Bowl|Disney|Pok[eé]mon|Harry Potter|Taboo|Pictionary|Wordle|Marvel|Lego|Barbie|Star Wars|Minecraft|Fortnite|Hello Kitty|Peppa Pig|Bluey|Paw Patrol|Sesame Street|M&M'?s|Oreo|Coca-Cola|Pepsi|Nerf|Play-Doh|Crayola|Monopoly|Scrabble|Jenga|Twister|Uno|Popsicle|Tupperware|Polaroid|Boogie board|Frisbee|Jell-O|Velcro|Post-it|Sharpie|Kleenex|Band-Aid|Ziploc|Crock-Pot|Bubble Wrap|Styrofoam|Q-tip|Jacuzzi)\b", re.I)
        for p, d in self.pages.items():
            txt = "".join(d.text)
            for m in tm.finditer(txt):
                probs.append(f"{p}: trademark {m.group(0)}")
            if re.search(r"aggregateRating|ratingValue|reviewRating|\bas seen (in|on)\b", self.raw[p], re.I):
                probs.append(f"{p}: rating or testimonial markup")
        about = "".join(self.pages.get("/about/", Doc()).text)
        if "AI assistance" not in about:
            probs.append("/about/ does not say it was written with AI assistance")
        if re.search(r"(checked|reviewed|verified) by (a|one) (person|human|real)", about, re.I):
            probs.append("/about/ claims a person checked the content")
        for p, raw in self.raw.items():
            if re.search(r"\{\{[A-Z_]+\}\}", raw):
                probs.append(f"{p}: unreplaced template placeholder")
            if re.search(r"lorem ipsum|TODO|FIXME", raw, re.I):
                probs.append(f"{p}: placeholder text (lorem/TODO/FIXME)")
        if "Effective date" not in "".join(self.pages.get("/privacy/", Doc()).text):
            probs.append("/privacy/ has no effective date")
        priv = self.raw.get("/privacy/", "")
        if "OWNER: replace" not in priv or "[OWNER FULL NAME]" not in priv:
            probs.append("/privacy/ lacks the OWNER: replace marker or placeholder")
        self.check("Trademarks, fake ratings, About honesty and privacy owner placeholder", probs)

        return self.results

    # ------------------------------------------------------------------ helpers
    def theme_paths(self, tool):
        sec = next((s for s, d in self.cat.sections.items() if d["tool"] == tool["id"]), None)
        if not sec:
            return []
        return [p for p in self.pages if p.startswith(self.cat.sections[sec]["path"]) and p != self.cat.sections[sec]["path"]]

    def kind(self, p):
        if p == "/":
            return "home"
        tools = {t["path"] for t in self.cat.site["tools"]}
        if p in tools:
            return "tool"
        parts = p.strip("/").split("/")
        if len(parts) == 2 and parts[0] in self.cat.sections:
            return "theme"
        if len(parts) == 2 and parts[0] == "guides":
            return "guide"
        if p in ("/guides/",) or (len(parts) == 1 and (parts[0] in self.cat.sections or parts[0] in self.cat.cross)):
            return "hub"
        return "page"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    site = Path(args[0]) if args else SRC.parent / "public_html"
    q = QA(site)
    res = q.run()
    fails = [r for r in res if not r["pass"]]
    print(f"\nStatic QA: {len(res) - len(fails)} passed, {len(fails)} failed")
    if "--json" in sys.argv:
        out = sys.argv[sys.argv.index("--json") + 1]
        Path(out).write_text(json.dumps(res, indent=1))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
