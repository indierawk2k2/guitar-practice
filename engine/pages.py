"""Generate every HTML page into site/. All links are relative so the site works
from file://, from `build.py serve`, and under a GitHub Pages project sub-path."""

import json
import os
from html import escape

from . import components as C
from . import theory as T

# The named drills of the "Changing chords" Learn chapter; a level drill with one of these ids is marked
# "(Ch. N)", N being that chapter's current position in the Learn sequence.
DRILLS_CHAPTER = "changing-chords"
NAMED_DRILLS = {"one-minute", "air-shape", "place-lift", "slow-motion", "anchor", "bass-first", "leave-early",
              "change-loop", "tempo-ladder", "eyes-closed", "barre-pulse", "random-pairs", "song-loop"}

NAV = [("home", "index.html", "Home"), ("learn", "learn/index.html", "Learn"),
       ("chords", "chords/index.html", "Chords"), ("scales", "scales/index.html", "Scales"),
       ("songs", "songs/index.html", "Songs"), ("practice", "practice/index.html", "Practice")]


def load_site(root):
    p = os.path.join(root, "data", "site.json")
    site = {"title": "Guitar Practice", "tagline": ""}
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            site.update(json.load(fh))
    return site


def layout(site, title, body, depth, active, body_class=""):
    p = C.rel(depth)
    nav = "".join('<a href="%s%s"%s>%s</a>' % (p, href, ' aria-current="page"' if key == active else "", label)
                  for key, href, label in NAV)
    full_title = title if active == "home" else "%s · %s" % (title, site["title"])
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>%s</title>
<link rel="stylesheet" href="%sstyle.css">
</head>
<body class="%s">
<header class="site-nav"><nav aria-label="Main">%s</nav></header>
<main>
%s
</main>
<footer class="site-foot"><p>%s &middot; generated from plain data files &middot; works offline once loaded</p></footer>
</body>
</html>
""" % (escape(full_title), p, body_class, nav, body, escape(site["title"]))


class SiteWriter:
    def __init__(self, root, proj, chapters, renderer, pdf_links=False):
        self.root = root
        self.out = os.path.join(root, "site")
        self.proj = proj
        self.chapters = chapters
        self.r = renderer
        self.site = load_site(root)
        self.pdf_links = pdf_links
        self.written = []

    def write(self, relpath, html):
        path = os.path.join(self.out, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        self.written.append(relpath)

    def page(self, relpath, title, body, active, body_class=""):
        depth = relpath.count("/")
        self.write(relpath, layout(self.site, title, body, depth, active, body_class))

    def fragment(self, name, depth):
        """Optional authorable intro fragment content/pages/<name>.html (shortcodes allowed)."""
        rel = os.path.join("content", "pages", name + ".html")
        path = os.path.join(self.root, rel)
        if not os.path.exists(path):
            return ""
        with open(path, encoding="utf-8") as fh:
            return self.r.render(fh.read(), rel, depth)

    # ---------------------------------------------------------------- all

    def build_all(self):
        self.home()
        self.learn()
        self.chord_library()
        self.scale_library()
        self.songs()
        self.practice()

    # ---------------------------------------------------------------- home

    def roadmap(self, depth):
        if not self.proj.levels:
            return "<p>No levels yet.</p>"
        items = []
        for lv in self.proj.levels.values():
            pdf = ""
            if self.pdf_links:
                pdf = ' &middot; <a href="%spdf/%s.pdf">PDF</a>' % (C.rel(depth), lv["id"])
            items.append('<li><a href="%s"><strong>Level %d:</strong> %s</a>%s%s<br><span class="muted">%s</span></li>'
                         % (C.level_href(depth, lv["id"]), lv["number"], escape(lv["title"]), C.sample_badge(lv),
                            pdf, C.inline(lv["summary"])))
        return '<ol class="roadmap">%s</ol>' % "".join(items)

    def home(self):
        body = ['<h1>%s</h1>' % escape(self.site["title"])]
        if self.site.get("tagline"):
            body.append('<p class="lede">%s</p>' % escape(self.site["tagline"]))
        body.append(self.fragment("home", 0))
        body.append("<h2>Roadmap</h2>")
        body.append(self.roadmap(0))
        self.page("index.html", self.site["title"], "\n".join(body), "home", "prose")

    # ---------------------------------------------------------------- learn

    def learn(self):
        items = []
        for c in self.chapters:
            items.append('<li><a href="%s.html">%s</a>%s%s<br><span class="muted">%s</span></li>'
                         % (c["slug"], escape(c["title"]), self._lvl(c), C.sample_badge(c), escape(c["summary"])))
        body = '<h1>Learn</h1>%s<ol class="toc">%s</ol>' % (self.fragment("learn", 1), "".join(items))
        self.page("learn/index.html", "Learn", body, "learn", "prose")
        for n, c in enumerate(self.chapters):
            prev = self.chapters[n - 1] if n > 0 else None
            nxt = self.chapters[n + 1] if n + 1 < len(self.chapters) else None
            html = self.r.render(c["body"], c["file"], 1, c["line_offset"])
            pn = '<nav class="prevnext" aria-label="Chapters">'
            pn += ('<a class="prev" href="%s.html"><span>Previous</span>%s</a>' % (prev["slug"], escape(prev["title"]))) if prev else "<span></span>"
            pn += ('<a class="next" href="%s.html"><span>Next</span>%s</a>' % (nxt["slug"], escape(nxt["title"]))) if nxt else "<span></span>"
            pn += "</nav>"
            head = '<p class="crumb"><a href="index.html">Learn</a>%s</p><h1>%s%s</h1>' % (
                self._lvl(c), escape(c["title"]), C.sample_badge(c))
            if c["summary"]:
                head += '<p class="lede">%s</p>' % escape(c["summary"])
            self.page("learn/%s.html" % c["slug"], c["title"], head + html + pn, "learn", "prose chapter")

    @staticmethod
    def _lvl(c):
        lv = str(c.get("level") or "").strip()
        if not lv:
            return ""
        return ' <span class="badge">%s</span>' % escape(("Level " + lv) if lv.isdigit() else lv)

    # ---------------------------------------------------------------- chords

    def chord_library(self):
        groups = {}
        for ch in self.proj.chords.values():
            groups.setdefault(ch["group"], []).append(ch)
        order = [g for g in T.GROUP_ORDER if g in groups] + sorted(g for g in groups if g not in T.GROUP_ORDER)
        body = ['<h1>Chord library</h1>', self.fragment("chords", 1)]
        body.append('<p class="legend">Low E string on the left, nut at the top. Numbers in dots are fingers '
                    '(1 index … 4 little, T thumb). <span class="sq"></span> square = root. '
                    'Under each string: the interval it plays (R = root). x = don’t play, o = open.</p>')
        body.append('<nav class="jump">%s</nav>' % " ".join('<a href="#g-%s">%s</a>' % (_slug(g), escape(g)) for g in order))
        for g in order:
            body.append('<h2 id="g-%s">%s</h2><div class="card-grid">' % (_slug(g), escape(g)))
            for ch in groups[g]:
                snd = " ".join("x" if s is None else T.pretty_acc(s["name"]) for s in ch["sounding"])
                tags = "".join('<span class="tag">%s</span>' % escape(t) for t in ch["tags"])
                body.append(
                    '<article class="chord-card" id="chord-%s">%s<div class="cinfo"><h3>%s%s</h3>'
                    '<p><span class="k">Formula</span> %s</p><p><span class="k">Notes</span> %s</p>'
                    '<p><span class="k">Strings 6→1</span> %s</p>%s%s%s</div></article>'
                    % (ch["id"], C.chord_figure(ch, 1, link=False).replace("<figcaption>", '<figcaption class="vh">'),
                       escape(T.pretty_symbol(ch["name"])), C.sample_badge(ch),
                       escape(T.pretty_formula(ch["formula"])) + ((" (no %s)" % ", ".join(T.pretty_interval(o, False) for o in ch["omits"])) if ch["omits"] else ""),
                       escape(" ".join(T.pretty_acc(n) for n in ch["notes_spelled"])), escape(snd),
                       ('<p><span class="k">Tuning</span> %s</p>' % escape(T.tuning_label(ch["tuning"])))
                       if ch["tuning"] != T.STANDARD_TUNING else "",
                       ('<p class="tags">%s</p>' % tags) if tags else "",
                       ('<p class="cnote">%s</p>' % C.inline(ch["notes"])) if ch["notes"] else ""))
            body.append("</div>")
        self.page("chords/index.html", "Chord library", "\n".join(body), "chords", "wide")

    # ---------------------------------------------------------------- scales

    def scale_library(self):
        body = ['<h1>Scales &amp; fretboard</h1>', self.fragment("scales", 1),
                '<p class="legend">High E string on top, low E at the bottom (like tab); nut on the left. '
                '<span class="sq"></span> filled square = root; ring = other scale notes. '
                'Wide diagrams scroll sideways.</p>']
        for sc in self.proj.scales.values():
            body.append('<section class="scale-entry" id="scale-%s"><h2>%s%s</h2><p class="meta">%s%s &middot; Formula %s &middot; Notes %s</p>%s%s</section>'
                        % (sc["id"], escape(sc["name"]), C.sample_badge(sc),
                           escape(sc["scale"]) + (" &middot; " + escape(sc["position"]) if sc["position"] else ""),
                           " &middot; frets %d–%d" % tuple(sc["window"]),
                           escape(T.pretty_formula(sc["formula"])),
                           escape(" ".join(T.pretty_acc(n) for n in sc["notes_spelled"])),
                           C.scale_figure(sc, 1, heading=False),
                           ('<p>%s</p>' % C.inline(sc["description"])) if sc["description"] else ""))
        self.page("scales/index.html", "Scales & fretboard", "\n".join(body), "scales", "wide")

    # ---------------------------------------------------------------- songs

    def song_sheet(self, s, depth, heading_level=1):
        chords = [self.proj.chords[c] for c in s["chords"].values() if c in self.proj.chords]
        h = "h%d" % heading_level
        out = ['<%s class="song-title">%s%s%s</%s>' % (h, escape(s["title"]), C.sample_badge(s), C.song_badges(s), h),
               '<p class="meta"><strong>%s</strong> &middot; %s</p>' % (escape(s["artist"]), C.song_meta(s)),
               '<div class="song-chords">%s' % C.chord_row(chords, depth, labels="none")]
        for g in s["alt_voicings"]:
            gch = [self.proj.chords[c] for c in g["chords"] if c in self.proj.chords]
            out.append('<div class="alt-voicings"><p class="alt-label"><strong>%s</strong>%s</p>%s</div>'
                       % (C.inline(g["label"]), (": " + C.inline(g["note"])) if g["note"] else "",
                          C.chord_row(gch, depth, labels="none")))
        out.append("</div>")
        out.append(C.song_sections(s))
        teach = ['<p><strong>Why this song:</strong> %s</p>' % C.inline(s["why"]),
                 '<p><strong>The hard change:</strong> %s</p>' % C.inline(s["hard_change"])]
        if s.get("theory"):
            teach.append('<p><strong>Theory:</strong> %s</p>' % C.inline(s["theory"]))
        if s["steps"]:
            teach.append('<p class="steps-h"><strong>Learn it in %d steps:</strong></p><ol class="steps">%s</ol>'
                         % (len(s["steps"]), "".join("<li>%s</li>" % C.inline(t) for t in s["steps"])))
        if s["tips"]:
            teach.append("<ul>%s</ul>" % "".join("<li>%s</li>" % C.inline(t) for t in s["tips"]))
        if s.get("caveat"):
            teach.append('<p class="caveat"><strong>Caveat:</strong> %s</p>' % C.inline(s["caveat"]))
        out.append('<div class="teach">%s</div>' % "".join(teach))
        if s["sources"]:
            out.append('<p class="sources noprint">Sources: %s</p>' % " &middot; ".join(
                '<a href="%s" rel="noopener">%s</a>' % (escape(u, quote=True), escape(_host(u))) for u in s["sources"]))
        return "".join(out)

    def songs(self):
        by_level = {}
        for s in self.proj.songs.values():
            by_level.setdefault(s.get("level") or 0, []).append(s)
        role_order = {"core": 0, "alternate": 1}
        body = ['<h1>Songs</h1>', self.fragment("songs", 1),
                '<p class="muted">Chord charts only — no lyrics. Each chart prints on one page. '
                '<span class="badge core">Core</span> songs are the ones each level is built around; '
                '<span class="badge">Alternate</span> songs teach the same things. '
                '<span class="badge">From your mixes</span> marks songs from your own mixes. '
                'Within each level, songs run from easiest to hardest.</p>']
        levels = sorted(by_level)
        if len(levels) > 1:
            body.append('<nav class="jump">%s%s</nav>' % (" ".join(
                '<a href="#level-%d">%s</a>' % (n, ("Level %d" % n) if n else "Other") for n in levels),
                ' <a href="#next-up">Next up</a>' if self.proj.bench else ""))
        for n in levels:
            songs = sorted(by_level[n], key=lambda s: (s.get("order", 99), role_order.get(s.get("role"), 2)))
            lv = next((l for l in self.proj.levels.values() if l["number"] == n), None)
            head = ("Level %d" % n) if n else "Other songs"
            if lv and not lv.get("sample"):
                head += ': <a href="%s">%s</a>' % (C.level_href(1, lv["id"]), escape(lv["title"]))
            items = []
            for s in songs:
                items.append('<li><a href="%s.html"><strong>%s</strong></a> — %s%s%s<br><span class="muted">%s &middot; chords: %s</span></li>'
                             % (s["id"], escape(s["title"]), escape(s["artist"]), C.sample_badge(s),
                                C.song_badges(dict(s, level=None)), C.song_meta(s),
                                escape(", ".join(T.pretty_symbol(k) for k in s["chords"]))))
            body.append('<h2 id="level-%d">%s</h2><ul class="toc">%s</ul>' % (n, head, "".join(items)))
        if self.proj.bench:
            items = "".join('<li><strong>%s</strong> — %s%s%s<br><span class="muted">%s</span></li>'
                            % (escape(b["title"]), escape(b["artist"]),
                               (' <span class="badge">%s</span>' % escape(b["level"])) if b.get("level") else "",
                               ' <span class="badge">From your mixes</span>' if b.get("mix") else "",
                               C.inline(b["teaches"])) for b in self.proj.bench)
            body.append('<h2 id="next-up">Next up</h2><p class="muted">Songs on the bench: good candidates whose '
                        'charts aren’t verified yet, so there are no charts for them here.</p><ul class="toc">%s</ul>' % items)
        self.page("songs/index.html", "Songs", "\n".join(body), "songs", "prose")
        for s in self.proj.songs.values():
            pdf = ""
            if self.pdf_links:
                pdf = ' <a href="../pdf/song-%s.pdf">Download PDF</a>' % s["id"]
            body = ('<p class="crumb noprint"><a href="index.html">Songs</a></p>'
                    '<p class="print-hint noprint">Prints on one US Letter page.%s</p>'
                    '<article class="sheet song-sheet">%s</article>' % (pdf, self.song_sheet(s, 1)))
            self.page("songs/%s.html" % s["id"], s["title"], body, "songs", "wide packet")

    # ---------------------------------------------------------------- practice

    def practice(self):
        body = '<h1>Practice</h1>%s<h2>Levels</h2>%s' % (self.fragment("practice", 1), self.roadmap(1))
        self.page("practice/index.html", "Practice", body, "practice", "prose")
        for lv in self.proj.levels.values():
            self.page("practice/%s.html" % lv["id"], "Level %d: %s" % (lv["number"], lv["title"]),
                      self.level_body(lv), "practice", "wide packet")

    def level_body(self, lv, sessions_only=False):
        refs = self.proj.level_refs(lv)
        kicker = "Level %d%s · %s" % (lv["number"], " · SAMPLE" if lv["sample"] and "SAMPLE" not in lv["title"] else "", lv["title"])
        out = []
        if not sessions_only:
            pdf = (' &middot; <a href="../pdf/%s.pdf">Download PDF</a>' % lv["id"]) if self.pdf_links else ""
            out.append('<div class="noprint level-head"><p class="crumb"><a href="index.html">Practice</a></p>'
                       '<h1>Level %d: %s%s</h1><p class="lede">%s</p>'
                       '<p class="print-hint"><strong>Print this packet</strong> for the music stand: '
                       '<button type="button" onclick="window.print()">Print…</button>%s<br>'
                       '<span class="muted">US Letter, default margins, “Headers and footers” off. '
                       'One page per session, then reference pages and a practice log.</span></p></div>'
                       % (lv["number"], escape(lv["title"]), C.sample_badge(lv), C.inline(lv["summary"]), pdf))
            out.append(self.overview_sheet(lv, kicker))
            if self._has_plan(lv):
                out.append(self.plan_sheet(lv, kicker))
            if lv["drills"]:
                out.append(self.drills_sheet(lv, kicker))
        for s in lv["sessions"]:
            out.append(self.session_sheet(lv, s, kicker))
        if sessions_only:
            return "\n".join(out)
        legend = ('<p class="legend">Low E left, nut on top · numbers = fingers (T = thumb) · square = root · '
                  'under strings = intervals</p>')
        if lv["chord_groups"]:
            # grouped reference: a heading per group; the browser breaks pages between rows
            grouped = {i for g in lv["chord_groups"] for i in g["chords"]}
            groups = [(g["label"], g["note"], g["chords"]) for g in lv["chord_groups"]]
            rest = [i for i in refs["chords"] if i not in grouped]
            if rest:
                groups.append(("Also in the sessions", "", rest))
            body = []
            for label, note, ids in groups:
                body.append('<div class="cgroup"><h3>%s%s</h3><div class="chord-row big">%s</div></div>' % (
                    C.inline(label), (' <span class="gnote">%s</span>' % C.inline(note)) if note else "",
                    "".join(C.chord_figure(self.proj.chords[i], 1, "intervals", "large", link=False, detail=True)
                            for i in ids if i in self.proj.chords)))
            out.append('<section class="sheet ref-sheet grouped"><p class="kicker">%s</p><h2>Chord shapes</h2>%s%s</section>'
                       % (escape(kicker), legend, "".join(body)))
        else:
            chords = [self.proj.chords[i] for i in refs["chords"]]
            for n in range(0, len(chords), 9):  # 3 x 3 large diagrams per printed page
                part = chords[n:n + 9]
                out.append('<section class="sheet ref-sheet"><p class="kicker">%s</p><h2>Chord shapes%s</h2>%s'
                           '<div class="chord-row big">%s</div></section>'
                           % (escape(kicker), " (cont.)" if n else "", legend,
                              "".join(C.chord_figure(c, 1, "intervals", "large", link=False, detail=True) for c in part)))
        scales = [self.proj.scales[i] for i in refs["scales"]]
        if scales:
            out.append('<section class="sheet ref-sheet"><p class="kicker">%s</p><h2>Scales &amp; fretboard</h2>'
                       '<p class="legend">High E on top, low E at the bottom · filled square = root</p>%s</section>'
                       % (escape(kicker), "".join(C.scale_figure(sc, 1) for sc in scales)))
        for sid in refs["songs"]:
            out.append('<section class="sheet song-sheet"><p class="kicker">%s</p>%s</section>'
                       % (escape(kicker), self.song_sheet(self.proj.songs[sid], 1, heading_level=2)))
        out.append(self.log_sheet(lv, kicker))
        out.append(self.checkin_sheet(lv, kicker))
        return "\n".join(out)

    @staticmethod
    def _has_plan(lv):
        """Levels with a week plan or advancement rules get a second front page for them."""
        return bool(lv["week_plan"] or lv["stuck"] or lv["skip_ahead"])

    def _exit_list(self, lv):
        return '<ul class="checklist">%s</ul>' % "".join(
            "<li>%s %s</li>" % (C.checkbox(), C.inline(x)) for x in lv["exit_criteria"])

    def _rules(self, lv):
        out = ""
        if lv["stuck"]:
            out += '<p class="rule"><strong>Stuck?</strong> %s</p>' % C.inline(lv["stuck"])
        if lv["skip_ahead"]:
            out += '<p class="rule"><strong>Too easy?</strong> %s</p>' % C.inline(lv["skip_ahead"])
        return out

    def overview_sheet(self, lv, kicker):
        days = " · ".join("<strong>%s</strong> %s" % (escape(s["name"]), escape(s["title"])) for s in lv["sessions"])
        how = ('<div class="howto"><p><strong>Level %d.</strong> Four 45-minute sessions a week: %s — '
               'any order, but A before C.</p><p>At the top of each session page circle the week and write the date. '
               'Do the blocks in order; tick each box; write tempos and counts in the blanks. '
               '“This week’s …” means the week-plan row for the week you circled. '
               'After each session tick it in the practice log at the back.</p></div>' % (lv["number"], days))
        status = ('<p class="status">%s</p>' % C.inline(lv["status"])) if lv["status"] else ""
        reading = ""
        if lv["reading"]:
            idx = {c["slug"]: (n + 1, c) for n, c in enumerate(self.chapters)}
            items = []
            for r in lv["reading"]:
                if r["chapter"] in idx:
                    num, c = idx[r["chapter"]]
                    items.append("<li>%s <strong>Ch. %d</strong> %s%s</li>" % (
                        C.checkbox(), num, escape(c["title"]), (" — " + C.inline(r["note"])) if r["note"] else ""))
            reading = ('<h3>Read this month — away from the guitar, on the site</h3><ul class="checklist reading">%s</ul>'
                       % "".join(items))
        songs = ""
        sids = [i for i in (lv.get("songs") or self.proj.level_refs(lv)["songs"]) if i in self.proj.songs]
        if sids:
            items = []
            for sid in sids:
                s = self.proj.songs[sid]
                role = {"core": "Core", "alternate": "Alternate"}.get(s.get("role"), "")
                items.append("<li>%s<strong>%s</strong> — %s</li>" % (
                    ('<span class="role">%s</span> ' % role) if role else "", escape(s["title"]), escape(s["artist"])))
            plan_here = lv["song_plan"] and not self._has_plan(lv)
            songs = '<h3>Songs</h3><ul class="songlist">%s</ul>%s' % (
                "".join(items), ('<p>%s</p>' % C.inline(lv["song_plan"])) if plan_here else
                ('<p class="muted">When to switch songs: next page.</p>' if lv["song_plan"] else ""))
        tail = ""
        if not self._has_plan(lv):
            tail = '<h3>Ready to move on when…</h3>%s' % self._exit_list(lv)
        return ('<section class="sheet overview"><p class="kicker">%s</p><h2>Level %d: %s</h2>%s<p>%s</p>%s'
                '<h3>Goals</h3><ul>%s</ul>%s%s%s</section>'
                % (escape(kicker), lv["number"], escape(lv["title"]), status, C.inline(lv["summary"]), how,
                   "".join("<li>%s</li>" % C.inline(g) for g in lv["goals"]), reading, songs, tail))

    def plan_sheet(self, lv, kicker):
        table = ""
        if lv["week_plan"]:
            rows = "".join('<tr><th>Week %d</th><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                           % (n + 1, C.inline(w["chords"]), C.inline(w["fretboard"]), C.inline(w["song"]), C.inline(w["tempo"]))
                           for n, w in enumerate(lv["week_plan"]))
            more = ""
            if len(lv["week_plan"]) < lv["weeks"]:
                more = ('<p class="muted">Weeks %d–%d (only if needed): repeat the week-%d row, starting each session with '
                        'the benchmark you are furthest from.</p>' % (len(lv["week_plan"]) + 1, lv["weeks"], len(lv["week_plan"])))
            table = ('<table class="weekplan"><thead><tr><th></th><th>Changes &amp; shapes</th>'
                     '<th>Fretboard</th><th>Song focus</th><th>Song tempo</th></tr></thead><tbody>%s</tbody></table>%s'
                     % (rows, more))
        songs = ('<h3>Songs: when to switch</h3><p>%s</p>' % C.inline(lv["song_plan"])) if lv["song_plan"] else ""
        return ('<section class="sheet plan"><p class="kicker">%s</p><h2>The month, week by week</h2>%s%s'
                '<h3>Ready to move on when…</h3>%s%s</section>'
                % (escape(kicker), table, songs, self._exit_list(lv), self._rules(lv)))

    def drills_sheet(self, lv, kicker):
        num = next((n + 1 for n, c in enumerate(self.chapters) if c["slug"] == DRILLS_CHAPTER), None)
        tag = ("(Ch. %d)" % num) if num else "(Learn)"
        items = []
        for d in lv["drills"]:
            extra = []
            if d["chords"]:
                extra.append("Chords: " + ", ".join(T.pretty_symbol(self.proj.chords[c]["name"]) for c in d["chords"] if c in self.proj.chords))
            if d["scales"]:
                extra.append("Scales: " + ", ".join(self.proj.scales[c]["name"] for c in d["scales"] if c in self.proj.scales))
            m = d.get("metronome")
            if m:
                extra.append("Metronome " + " → ".join(str(x) for x in (m.get("start"), m.get("target")) if x))
            items.append('<li><strong>%s</strong>%s %s%s</li>'
                         % (escape(d["title"]), (' <span class="drill-id">%s</span>' % tag) if d["id"] in NAMED_DRILLS else "",
                            C.inline(d["instructions"]),
                            ('<br><span class="muted">%s</span>' % escape(" · ".join(extra))) if extra else ""))
        return ('<section class="sheet drills-sheet"><p class="kicker">%s</p><h2>Drills</h2>'
                '<p class="muted">The session pages name these drills; this is exactly how to do each one at this level. '
                '%s = one of the named drills in the Learn chapter on changing chords.</p><ol class="drills">%s</ol></section>'
                % (escape(kicker), tag, "".join(items)))

    def session_sheet(self, lv, s, kicker):
        drills = {d["id"]: d for d in lv["drills"]}
        rows = []
        t = 0
        for b in s["blocks"]:
            refs = []
            if b["chords"]:
                refs.append("Chords: " + ", ".join(T.pretty_symbol(self.proj.chords[c]["name"]) for c in b["chords"] if c in self.proj.chords))
            if b["scales"]:
                refs.append("Scale: " + ", ".join(self.proj.scales[c]["name"] for c in b["scales"] if c in self.proj.scales))
            if b["songs"]:
                refs.append("Song: " + ", ".join(self.proj.songs[c]["title"] for c in b["songs"] if c in self.proj.songs))
            if b.get("drill") and b["drill"] in drills:
                refs.append("Drill: %s" % drills[b["drill"]]["title"])
            instr = "".join("<p>%s</p>" % C.inline(x) for x in b["instructions"])
            extra = ""
            if refs:
                extra += '<p class="refs">%s</p>' % escape(" · ".join(refs))
            fill = []
            if b.get("metronome"):
                fill.append(C.metronome_line(b["metronome"]).replace('<p class="metro">', "").replace("</p>", ""))
            if b.get("record"):
                fill.append('<span class="rec">%s: %s</span>' % (C.inline(b["record"]), C.blank("3.6em")))
            if fill:
                extra += '<p class="metro">%s</p>' % " &nbsp;·&nbsp; ".join(fill)
            rows.append('<li class="block"><div class="b-time">%s<span class="mins">%d<small> min</small></span>'
                        '<span class="clock">%d:%02d–%d:%02d</span></div><div class="b-body"><h3>%s</h3>%s%s</div></li>'
                        % (C.checkbox(), b["minutes"], t // 60, t % 60, (t + b["minutes"]) // 60, (t + b["minutes"]) % 60,
                           escape(b["title"]), instr, extra))
            t += b["minutes"]
        weeks = "".join('<span class="wk">%d</span>' % (n + 1) for n in range(lv["weeks"]))
        return ('<section class="sheet session" id="session-%s"><header class="sheet-head"><p class="kicker">%s</p>'
                '<div class="sh-row"><h2>Session %s <span>%s</span></h2><p class="date">Week %s &nbsp; Date %s</p></div>%s</header>'
                '<ol class="blocks">%s</ol><p class="sheet-foot">Notes %s</p><p class="sheet-foot2">%s</p></section>'
                % (s["name"], escape(kicker), escape(s["name"]), escape(s["title"]), weeks, C.blank("6em", "date"),
                   ('<p class="focus">%s</p>' % C.inline(s["focus"])) if s["focus"] else "",
                   "".join(rows), C.blank("90%"), C.blank("97%")))

    def log_sheet(self, lv, kicker):
        weeks = lv["weeks"]
        head = "".join("<th>Session %s</th>" % s["name"] for s in lv["sessions"])
        rows = "".join('<tr><th>Week %d</th>%s</tr>' % (w + 1, "".join(
            '<td>%s <span class="lbl">date</span>%s<br><span class="lbl">minutes</span>%s</td>'
            % (C.checkbox(), C.blank("4.2em"), C.blank("3em")) for _ in lv["sessions"]))
            for w in range(weeks))
        out = ['<section class="sheet log"><p class="kicker">%s</p><h2>Practice log</h2>' % escape(kicker),
               '<p class="muted">Tick each session when done; write the date and how many minutes it really took.</p>'
               '<table class="logt"><thead><tr><th></th>%s</tr></thead><tbody>%s</tbody></table>' % (head, rows)]
        if lv["benchmarks"]:
            bh = "".join("<th>Wk %d</th>" % (w + 1) for w in range(weeks))
            br = "".join('<tr><th>%s</th><td class="tgt">%s</td>%s</tr>' % (C.inline(b["name"]), C.inline(b["target"]), "<td></td>" * weeks)
                         for b in lv["benchmarks"])
            out.append('<h3>Benchmarks — Session D, every week</h3><table class="bench"><thead><tr><th>Benchmark</th><th>Target</th>%s</tr></thead><tbody>%s</tbody></table>' % (bh, br))
        if self._has_plan(lv):
            out.append('<p class="muted">Exit checklist: on the week-plan page at the front. Leaving the level? '
                       'Fill in the check-in sheet overleaf.</p>')
        else:
            out.append('<h3>Exit checklist — ready for the next level when every box is ticked</h3>%s' % self._exit_list(lv))
        out.append("</section>")
        return "".join(out)

    def checkin_sheet(self, lv, kicker):
        """One page the player fills in at the end of a level; it is what the next level is revised from."""
        def line(label, width="100%"):
            return '<p class="wl"><span class="wl-lbl">%s</span>%s</p>' % (label, C.blank(width))
        bench = ""
        if lv["benchmarks"]:
            bench = ('<table class="bench checkin-bench"><thead><tr><th>Benchmark</th><th>Target</th><th>Final</th>'
                     '<th>Felt (easy / OK / hard)</th></tr></thead><tbody>%s</tbody></table>'
                     % "".join('<tr><th>%s</th><td class="tgt">%s</td><td></td><td></td></tr>'
                               % (C.inline(b["name"]), C.inline(b["target"])) for b in lv["benchmarks"]))
        extra = "".join(line(C.inline(q)) for q in lv["checkin"])
        return ('<section class="sheet checkin"><p class="kicker">%s</p><h2>Level %d check-in</h2>'
                '<p class="muted">Fill this in when you leave the level (or at week 6) and bring it to the check-in. '
                'The next level is re-tuned from it.</p>'
                '<p class="wl3"><span>Finished %s</span><span>Weeks taken %s</span><span>Sessions done %s</span>'
                '<span>Exit boxes ticked %s of %d</span></p>%s%s%s%s%s%s%s%s%s</section>'
                % (escape(kicker), lv["number"], C.blank("5.5em"), C.blank("2.5em"), C.blank("2.5em"),
                   C.blank("2em"), len(lv["exit_criteria"]), bench,
                   line("Chords or changes that still feel bad"), line(""),
                   line("Songs I loved"), line("Songs I disliked, and why"),
                   line("Sessions really took about %s min. Blocks that ran long or got skipped" % C.blank("2.5em")),
                   line("I want more of"), line("I want less of"), extra + line("Anything else")))


def _host(url):
    """'https://www.example.com/a/b' -> 'example.com' (link text for sources)."""
    h = url.split("://", 1)[-1].split("/", 1)[0]
    return h[4:] if h.startswith("www.") else h


def _slug(s):
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in s).strip("-")
