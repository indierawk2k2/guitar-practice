"""HTML building blocks shared by the page generator and the shortcodes."""

import re
from html import escape

from . import svg
from . import theory as T


def rel(depth):
    return "../" * depth


def inline(text):
    """Plain text from JSON -> safe HTML. Supports **bold** and *italic* only."""
    s = escape(text)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    return s


def sample_badge(e):
    return ' <span class="badge sample">SAMPLE</span>' if e.get("sample") else ""


def chord_href(depth, cid):
    return "%schords/index.html#chord-%s" % (rel(depth), cid)


def scale_href(depth, sid):
    return "%sscales/index.html#scale-%s" % (rel(depth), sid)


def song_href(depth, sid):
    return "%ssongs/%s.html" % (rel(depth), sid)


def level_href(depth, lid):
    return "%spractice/%s.html" % (rel(depth), lid)


def chord_figure(ch, depth, labels="intervals", size="normal", link=True, detail=False):
    pic = svg.chord_svg(ch, labels=labels, size=size)
    if link:
        pic = '<a href="%s" class="dg-link">%s</a>' % (chord_href(depth, ch["id"]), pic)
    nm = T.pretty_symbol(ch["name"])
    cap = '<span class="cname%s">%s</span>' % (" long" if len(nm) > 8 else "", escape(nm))
    if detail:
        cap += '<span class="cmeta">%s</span>' % escape(T.pretty_formula(ch["formula"]))
    return '<figure class="chord%s">%s<figcaption>%s</figcaption></figure>' % (
        " large" if size == "large" else "", pic, cap)


def chord_row(chs, depth, labels="intervals", size="normal"):
    cls = "chord-row compact" if labels == "none" else "chord-row"
    return '<div class="%s">%s</div>' % (cls, "".join(chord_figure(c, depth, labels, size) for c in chs))


def scale_figure(sc, depth, heading=True):
    cap = ""
    if heading:
        cap = ('<figcaption><span class="sname">%s</span> <span class="smeta">%s &middot; %s</span></figcaption>'
               % (escape(sc["name"]), escape(T.pretty_formula(sc["formula"])),
                  escape(" ".join(T.pretty_acc(n) for n in sc["notes_spelled"]))))
    return '<figure class="scale">%s<div class="scroll">%s</div></figure>' % (cap, svg.neck_svg(sc))


def grid_html(bars, beats=4, repeat=1, title=None, note=None):
    h = '<div class="prog">'
    if title:
        h += '<h4 class="prog-title">%s%s</h4>' % (escape(title), (' <span class="rep">play %d times</span>' % repeat) if repeat > 1 else "")
    h += '<div class="scroll">%s</div>' % svg.grid_svg(bars, beats=beats, repeat=repeat,
                                                     label=(title or "Chord progression"))
    if note:
        h += '<p class="prog-note">%s</p>' % inline(note)
    return h + "</div>"


def song_meta(s):
    bits = ["Key of %s" % T.pretty_acc(s["key"])]
    if s.get("capo"):
        bits.append("Capo %d" % s["capo"])
    if s.get("detune"):
        down = s["detune"]
        notes = " ".join(T.pretty_acc(T.pc_name(T.pc(n) - down, prefer_flat=True)) for n in s["tuning"])
        bits.append("Tune down %s (%s); shapes as written" % (
            {1: "a half step", 2: "a whole step"}.get(down, "%d half steps" % down), notes))
    else:
        bits.append(T.tuning_label(s["tuning"]) if s["tuning"] != T.STANDARD_TUNING else "Standard tuning")
    if s.get("tempo"):
        bits.append("♩ = %d" % s["tempo"])
    bits.append(s["time"])
    if s.get("feel"):
        bits.append(s["feel"])
    return " &middot; ".join(escape(b) for b in bits)


def song_badges(s):
    """Level / core-or-alternate / from-the-mixes pills for a song."""
    out = []
    if s.get("level"):
        out.append("Level %d" % s["level"])
    if s.get("role"):
        out.append("Core" if s["role"] == "core" else "Alternate")
    if s.get("mix"):
        out.append("From your mixes")
    return "".join(' <span class="badge%s">%s</span>' % (" core" if b == "Core" else "", escape(b)) for b in out)


def song_sections(s):
    out = []
    if s.get("form"):
        out.append('<p class="form"><strong>Form:</strong> %s</p>' % " &rarr; ".join(escape(f) for f in s["form"]))
    out.append('<div class="sections">%s</div>' % "".join(
        grid_html(sec["bars"], s["beats"], sec["repeat"], sec["name"], sec["note"]) for sec in s["sections"]))
    return "".join(out)


def song_card(s, proj, depth):
    chords = [proj.chords[c] for c in s["chords"].values() if c in proj.chords]
    return ('<section class="song-card"><h3><a href="%s">%s</a>%s</h3><p class="meta">%s &middot; %s</p>%s%s</section>'
            % (song_href(depth, s["id"]), escape(s["title"]), sample_badge(s), escape(s["artist"]),
               song_meta(s), chord_row(chords, depth, labels="none"), song_sections(s)))


CALLOUTS = {"try": "Try it on the guitar", "why": "Why it's named that", "tip": "Tip"}


def callout_open(kind, title=None):
    return '<aside class="callout %s"><p class="callout-title">%s</p>' % (kind, escape(title or CALLOUTS[kind]))


def checkbox():
    return '<span class="cb" aria-hidden="true"></span>'


def blank(width="5em", label=None):
    return '<span class="blank" style="width:%s"%s></span>' % (width, (' aria-label="%s"' % escape(label)) if label else "")


def metronome_line(m):
    parts = []
    if m.get("start"):
        parts.append("start %d" % m["start"])
    if m.get("target"):
        parts.append("target %d" % m["target"])
    return ('<p class="metro"><span class="metro-icon" aria-hidden="true">♩</span> Metronome: %s &middot; today %s bpm</p>'
            % (" &rarr; ".join(parts), blank("3.2em", "today's tempo")))
