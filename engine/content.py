"""Chapters in content/learn/*.html: front matter + HTML body + shortcodes.

Front matter is the first lines of the file, between two lines of ``---``::

    ---
    title: How chords are built
    order: 10
    summary: One sentence for the index page.
    level: 1
    sample: true
    ---
    <p>HTML body ...</p>

Shortcodes are ``{{name}}`` or ``{{name: args}}``; see AUTHORING.md for the
full list. Unknown shortcodes and unknown ids are build errors with file:line.
"""

import os
import re
import shlex
from html import escape

from . import components as C
from . import model
from . import theory as T

FM_KEYS = {"title": True, "order": True, "summary": False, "level": False, "sample": False, "slug": False}
SC_RE = re.compile(r"(\\?)\{\{\s*(/?[a-z]+)\s*(?::(.*?))?\}\}", re.S)
BLOCK_CODES = {"chord", "chords", "scale", "neck", "song", "grid", "try", "why", "tip", "/try", "/why", "/tip"}
INLINE_CODES = {"link"}
LABEL_WORDS = {"intervals", "notes", "fingers", "none"}


def parse_front_matter(text, rel, rep):
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        rep.error(rel, "line 1: file must start with a '---' front-matter line")
        return None, text, 0
    meta = {}
    for n in range(1, len(lines)):
        line = lines[n]
        if line.strip() == "---":
            body = "\n".join(lines[n + 1:])
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            rep.error(rel, "line %d: front matter lines look like 'key: value'" % (n + 1))
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if k not in FM_KEYS:
            rep.error(rel, "line %d: unknown front-matter key '%s' (allowed: %s)" % (n + 1, k, ", ".join(FM_KEYS)))
            continue
        meta[k] = v
    else:
        rep.error(rel, "front matter is not closed with a second '---' line")
        return None, text, 0
    for k, req in FM_KEYS.items():
        if req and k not in meta:
            rep.error(rel, "front matter is missing '%s'" % k)
    try:
        meta["order"] = float(meta.get("order", "0"))
    except ValueError:
        rep.error(rel, "front matter 'order' must be a number")
        meta["order"] = 0
    meta["sample"] = str(meta.get("sample", "")).lower() in ("true", "yes", "1")
    return meta, body, n + 1


def load_chapters(root, rep):
    d = os.path.join(root, "content", "learn")
    out = []
    if not os.path.isdir(d):
        return out
    slugs = {}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".html"):
            continue
        rel = os.path.join("content", "learn", fn)
        with open(os.path.join(d, fn), encoding="utf-8") as fh:
            text = fh.read()
        meta, body, offset = parse_front_matter(text, rel, rep)
        if meta is None:
            continue
        slug = meta.get("slug") or re.sub(r"^\d+[-_]", "", fn[:-5])
        if not model.ID_RE.match(slug):
            rep.error(rel, "slug '%s' must use only letters, digits, '_', '-', '.'" % slug)
            continue
        if slug in slugs:
            rep.error(rel, "chapter slug '%s' is also used by %s" % (slug, slugs[slug]))
            continue
        slugs[slug] = rel
        out.append({"slug": slug, "file": rel, "body": body, "line_offset": offset,
                    "title": meta.get("title", slug), "order": meta["order"],
                    "summary": meta.get("summary", ""), "level": meta.get("level", ""),
                    "sample": meta["sample"]})
    out.sort(key=lambda c: (c["order"], c["slug"]))
    return out


def _opts(s):
    """'notes size=large' -> ({'size': 'large'}, ['notes'])"""
    kv, words = {}, []
    for tok in shlex.split(s or ""):
        if "=" in tok:
            k, v = tok.split("=", 1)
            kv[k.strip()] = v
        else:
            words.append(tok)
    return kv, words


class Renderer:
    """Expands shortcodes in an HTML fragment for a page at a given depth."""

    def __init__(self, proj, chapters):
        self.proj = proj
        self.chapters = {c["slug"]: c for c in chapters}

    def render(self, text, rel, depth, line_offset=0):
        rep = self.proj.rep
        blocks = []
        stack = []

        def where(m):
            return "%s:%d" % (rel, line_offset + text.count("\n", 0, m.start()) + 1)

        def sub(m):
            if m.group(1):  # escaped \{{ ... }}
                return m.group(0)[1:]
            name, arg = m.group(2), (m.group(3) or "").strip()
            w = where(m)
            if name in INLINE_CODES:
                return self.inline_code(name, arg, w, depth)
            if name not in BLOCK_CODES:
                rep.error(w, "unknown shortcode '{{%s}}' (known: %s)" % (name, ", ".join(sorted(BLOCK_CODES | INLINE_CODES))))
                return ""
            if name in C.CALLOUTS:
                stack.append((name, w))
                html = C.callout_open(name, arg or None)
            elif name.startswith("/"):
                if not stack or stack[-1][0] != name[1:]:
                    rep.error(w, "'{{%s}}' closes nothing (open: %s)" % (name, stack[-1][0] if stack else "none"))
                    return ""
                stack.pop()
                html = "</aside>"
            else:
                html = self.block_code(name, arg, w, depth)
            blocks.append(html)
            return "\x00SC%d\x00" % (len(blocks) - 1)

        out = SC_RE.sub(sub, text)
        for name, w in stack:
            rep.error(w, "'{{%s}}' is never closed with '{{/%s}}'" % (name, name))
        # a block shortcode alone in a <p> must not stay wrapped in it
        out = re.sub(r"<p>\s*(\x00SC\d+\x00)\s*</p>", r"\1", out)
        out = re.sub(r"\x00SC(\d+)\x00", lambda m: blocks[int(m.group(1))], out)
        return out

    # -------------------------------------------------------------- codes

    def _chord(self, cid, w):
        return self.proj.ref("chord", cid.strip(), w)

    def block_code(self, name, arg, w, depth):
        p, rep = self.proj, self.proj.rep
        if name in ("chord", "chords"):
            ids, _, opt = arg.partition("|")
            kv, words = _opts(opt)
            labels = kv.get("labels") or next((x for x in words if x in LABEL_WORDS), "intervals")
            size = "large" if ("large" in words or kv.get("size") == "large") else "normal"
            for x in words:
                if x not in LABEL_WORDS and x != "large":
                    rep.error(w, "unknown option '%s' for {{%s}} (use intervals, notes, fingers, none, large)" % (x, name))
            ids = [i.strip() for i in ids.split(",") if i.strip()]
            if not ids:
                rep.error(w, "{{%s:...}} needs a chord id" % name)
                return ""
            if name == "chord" and len(ids) > 1:
                rep.error(w, "{{chord:...}} takes one id; use {{chords:a,b,c}} for a row")
            chs = [c for c in (self._chord(i, w) for i in ids) if c]
            if name == "chord":
                return "".join('<div class="chord-row single">%s</div>' % C.chord_figure(c, depth, labels, size, detail=True) for c in chs)
            return C.chord_row(chs, depth, labels, size)
        if name == "scale":
            sc = p.ref("scale", arg, w)
            return C.scale_figure(sc, depth) if sc else ""
        if name == "song":
            s = p.ref("song", arg, w)
            return C.song_card(s, p, depth) if s else ""
        if name == "neck":
            try:
                kv, words = _opts(arg)
            except ValueError as e:
                rep.error(w, "{{neck:...}} could not parse options: %s" % e)
                return ""
            raw = {"_where": w, "name": kv.pop("title", ""), "layout": "neck"}
            if "notes" in kv:
                try:
                    notes = kv.pop("notes").split()
                    root = notes[0]
                    rp = T.pc(root)
                    raw["formula"] = [T.SEMI_TO_TOKEN[(T.pc(n) - rp) % 12] for n in notes]
                    raw["root"] = root
                except (ValueError, IndexError) as e:
                    rep.error(w, "{{neck:...}} notes=: %s" % e)
                    return ""
            else:
                raw["root"] = kv.pop("root", None)
                raw["formula"] = kv.pop("formula", "1")
                if not raw["root"]:
                    rep.error(w, "{{neck:...}} needs root=X (and formula=\"...\") or notes=\"C E G\"")
                    return ""
            fr = kv.pop("frets", "0-15")
            m = re.match(r"^(\d+)-(\d+)$", fr)
            if not m:
                rep.error(w, "{{neck:...}} frets must look like 0-15")
                return ""
            raw["frets"] = [int(m.group(1)), int(m.group(2))]
            raw["labels"] = kv.pop("labels", "notes")
            for k in kv:
                rep.error(w, "unknown option '%s' for {{neck:...}} (root, formula, notes, frets, labels, title)" % k)
            for x in words:
                rep.error(w, "{{neck:...}} options must be key=value; got '%s'" % x)
            sc = model.normalize_scale(raw, w, rep, adhoc=True)
            if not sc:
                return ""
            if not sc["name"]:
                sc["name"] = "%s: %s" % (T.pretty_acc(sc["root"]), " ".join(T.pretty_acc(n) for n in sc["notes_spelled"]))
            return C.scale_figure(sc, depth, heading=bool(raw["name"]))
        if name == "grid":
            bars_s, _, opt = arg.partition(";")
            kv, words = _opts(opt)
            bars = model.parse_bars(bars_s)
            if not bars:
                rep.error(w, "{{grid:...}} needs bars, e.g. {{grid: G | C | D | G}}")
                return ""
            try:
                repeat = int(kv.get("repeat", 1))
                beats = int(kv.get("beats", 4))
            except ValueError:
                rep.error(w, "{{grid:...}} repeat= and beats= must be numbers")
                return ""
            for bar in bars:
                for tok in bar:
                    if tok not in model.SPECIAL_SLOTS and not re.match(r"^[A-G]", tok):
                        rep.error(w, "{{grid:...}} '%s' does not look like a chord symbol" % tok)
            return C.grid_html(bars, beats, repeat, kv.get("title"))
        return ""

    def inline_code(self, name, arg, w, depth):
        rep = self.proj.rep
        target, _, text = arg.partition("|")
        kind, _, ident = target.strip().partition(":")
        ident = ident.strip()
        text = text.strip()
        pages = {"home": ("index.html", "Home"), "learn": ("learn/index.html", "Learn"),
                 "chords": ("chords/index.html", "Chord library"), "scales": ("scales/index.html", "Scales & fretboard"),
                 "songs": ("songs/index.html", "Songs"), "practice": ("practice/index.html", "Practice")}
        p = self.proj
        if kind == "page":
            if ident not in pages:
                rep.error(w, "{{link:page:%s}} — page must be one of %s" % (ident, ", ".join(pages)))
                return escape(text or ident)
            href, title = C.rel(depth) + pages[ident][0], pages[ident][1]
        elif kind == "learn":
            ch = self.chapters.get(ident)
            if not ch:
                rep.error(w, "{{link:learn:%s}} — no chapter with slug '%s' (have: %s)" % (ident, ident, ", ".join(self.chapters)))
                return escape(text or ident)
            href, title = "%slearn/%s.html" % (C.rel(depth), ident), ch["title"]
        elif kind in ("chord", "scale", "song", "level"):
            e = p.ref(kind, ident, w)
            if not e:
                return escape(text or ident)
            href = {"chord": C.chord_href, "scale": C.scale_href, "song": C.song_href, "level": C.level_href}[kind](depth, ident)
            title = {"chord": lambda: T.pretty_symbol(e["name"]), "scale": lambda: e["name"],
                     "song": lambda: e["title"], "level": lambda: "Level %d: %s" % (e["number"], e["title"])}[kind]()
        else:
            rep.error(w, "{{link:...}} needs kind:id, kind one of page, learn, chord, scale, song, level")
            return escape(text or arg)
        return '<a href="%s">%s</a>' % (href, escape(text or title))
