"""Inline SVG renderers: chord boxes, fretboard/scale diagrams, bar grids.

All colours come from CSS classes defined in static/style.css so the same SVG
is correct in light mode, dark mode and print:

    .ink   fill = text colour          .stk  stroke = text colour
    .bgf   fill = page background      .mut  fill = muted text colour
    .faint fill = rule colour          .mstk stroke = muted colour

Presentation attributes (fill="#000" etc.) are kept as a fallback for viewers
without the stylesheet. Roots are always drawn as squares (never by colour).
"""

from html import escape

from . import theory as T

FONT = "font-family=\"-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,'Liberation Sans',sans-serif\""


def _f(x):
    return ("%.1f" % x).rstrip("0").rstrip(".")


def _svg(w, h, body, label, cls, fixed=False):
    size = 'width="%s" height="%s"' % (_f(w), _f(h))
    return ('<svg class="%s" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s" %s '
            'role="img" aria-label="%s" %s><title>%s</title>%s</svg>'
            % (cls, _f(w), _f(h), size, escape(label), FONT, escape(label), "".join(body)))


def _text(x, y, s, size, cls="ink", anchor="middle", weight="normal", extra=""):
    return ('<text x="%s" y="%s" font-size="%s" text-anchor="%s" font-weight="%s" class="%s" fill="#000"%s>%s</text>'
            % (_f(x), _f(y), _f(size), anchor, weight, cls, extra, escape(str(s))))


def _line(x1, y1, x2, y2, w, cls="stk", extra=""):
    return ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke-width="%s" class="%s" stroke="#000"%s/>'
            % (_f(x1), _f(y1), _f(x2), _f(y2), _f(w), cls, extra))


def _dot(cx, cy, r, root, filled=True):
    """Filled circle, or filled square for a root. filled=False -> ring."""
    if root:
        s = r * 0.92
        if filled:
            return ('<rect x="%s" y="%s" width="%s" height="%s" rx="2" class="ink" fill="#000"/>'
                    % (_f(cx - s), _f(cy - s), _f(2 * s), _f(2 * s)))
        return ('<rect x="%s" y="%s" width="%s" height="%s" rx="1.5" class="bgf stk" fill="#fff" stroke="#000" stroke-width="1.6"/>'
                % (_f(cx - s), _f(cy - s), _f(2 * s), _f(2 * s)))
    if filled:
        return '<circle cx="%s" cy="%s" r="%s" class="ink" fill="#000"/>' % (_f(cx), _f(cy), _f(r))
    return ('<circle cx="%s" cy="%s" r="%s" class="bgf stk" fill="#fff" stroke="#000" stroke-width="1.6"/>'
            % (_f(cx), _f(cy), _f(r)))


# ------------------------------------------------------------------ chord box

def chord_svg(ch, labels="intervals", size="normal"):
    """Vertical chord box. Low E string on the LEFT, nut at the TOP.

    labels: "intervals" (R, 3, ♭7 under each string), "notes" (note names),
            "fingers" (finger numbers under strings, dots left blank),
            "none".
    Dots show finger numbers (except labels="fingers"). Root notes are squares.
    """
    S, F, r = 22, 26, 8.6
    nf, base = ch["nfrets"], ch["base_fret"]
    left = 42
    top = 34
    bottom = 24 if labels != "none" else 8
    W = left + 5 * S + 18
    H = top + nf * F + bottom
    X = lambda i: left + i * S  # noqa: E731  (i = 0 low E .. 5 high E)
    Y = lambda f: top + (f - base + 0.5) * F  # noqa: E731
    body = []
    root_pc = None if "1" in ch["omits"] else T.pc(ch["root"])
    # frets
    for k in range(nf + 1):
        body.append(_line(X(0), top + k * F, X(5), top + k * F, 1.2))
    for i in range(6):
        body.append(_line(X(i), top, X(i), top + nf * F, 1.2))
    if base == 1:
        body.append('<rect x="%s" y="%s" width="%s" height="5" class="ink" fill="#000"/>'
                    % (_f(X(0) - 0.6), _f(top - 5), _f(5 * S + 1.2)))
    else:
        body.append(_text(left - r - 3, Y(base) + 4.5, "%dfr" % base, 12.5, anchor="end", weight="600"))
    # open / muted markers
    for i, s in enumerate(ch["sounding"]):
        cx, cy = X(i), top - 15
        if s is None:
            d = 4.6
            body.append(_line(cx - d, cy - d, cx + d, cy + d, 1.7))
            body.append(_line(cx - d, cy + d, cx + d, cy - d, 1.7))
        elif s["fret"] == 0:
            body.append(_dot(cx, cy, 5.2, s["pc"] == root_pc, filled=False))
    # barres
    covered = set()
    for b in ch["barres"]:
        x1, x2 = X(6 - b["hi"]), X(6 - b["lo"])
        cy = Y(b["fret"])
        body.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" class="ink" fill="#000"/>'
                    % (_f(x1 - r), _f(cy - r), _f(x2 - x1 + 2 * r), _f(2 * r), _f(r)))
        on_bar = [6 - sn for sn in range(b["lo"], b["hi"] + 1) if ch["frets"][6 - sn] == b["fret"]]
        roots = [i for i in on_bar if ch["sounding"][i]["pc"] == root_pc]
        for i in on_bar:
            covered.add((i, b["fret"]))
        for i in roots:  # roots under a barre: a small square "window" in the bar
            body.append('<rect x="%s" y="%s" width="7" height="7" class="bgf" fill="#fff"/>' % (_f(X(i) - 3.5), _f(cy - 3.5)))
        if labels != "fingers" and b.get("finger"):
            free = [i for i in range(6 - b["hi"], 6 - b["lo"] + 1) if i not in roots]
            mid = (x1 + x2) / 2
            fx = min((X(i) for i in free), key=lambda x: abs(x - mid)) if free else mid
            body.append(_text(fx, cy + 4.3, b["finger"], 12, cls="bgf", weight="700"))
    # fretted dots
    for i, s in enumerate(ch["sounding"]):
        if not s or s["fret"] == 0:
            continue
        cx, cy = X(i), Y(s["fret"])
        is_root = s["pc"] == root_pc
        if (i, s["fret"]) in covered:
            continue
        body.append(_dot(cx, cy, r, is_root))
        fg = ch["fingers"][i] if ch["fingers"] else None
        if fg and labels != "fingers":
            body.append(_text(cx, cy + 4.3, fg, 12, cls="bgf", weight="700"))
    # labels under strings
    if labels != "none":
        ly = top + nf * F + 17
        for i, s in enumerate(ch["sounding"]):
            if labels == "fingers":
                v = (ch["fingers"][i] if ch["fingers"] else None) or ("" if s is None else ("0" if s["fret"] == 0 else ""))
            elif s is None:
                v = ""
            elif labels == "notes":
                v = T.pretty_acc(s["name"])
            else:
                v = T.pretty_interval(s["token"]) if s["token"] else "?"
            if v:
                body.append(_text(X(i), ly, v, 12.5, cls="mut", weight="600"))
    label = "%s chord diagram: %s" % (ch["name"], " ".join("x" if f is None else str(f) for f in ch["frets"]))
    cls = "dg chordbox" + (" large" if size == "large" else "")
    return _svg(W, H, body, label, cls)


# ------------------------------------------------------------------ fretboard

INLAYS = {3, 5, 7, 9, 15, 17, 19, 21}


def neck_svg(sc):
    """Horizontal fretboard. High E string on TOP (like tab), low E at the bottom,
    nut on the left, fret numbers below. Roots are filled squares; other notes are
    rings. Labels inside dots: intervals, note names or none (sc["labels"])."""
    lo, hi = sc["window"]
    first = max(lo, 1)
    ncell = hi - first + 1
    FW = 46 if ncell <= 6 else 42
    SG = 23
    r = 9.8
    show_open = lo == 0
    names_x = 12
    left = 30 + (30 if show_open else 0)
    top = 16
    W = left + ncell * FW + 12
    H = top + 5 * SG + 34
    tun = sc["tuning"]
    Ys = lambda sn: top + (sn - 1) * SG  # noqa: E731  string 1 (high) on top
    Xc = lambda f: (left - 17) if f == 0 else left + (f - first + 0.5) * FW  # noqa: E731
    body = []
    # inlays (faint)
    def has(sn, f):
        return f in sc["dots"].get(sn, [])
    for f in range(first, hi + 1):
        if f in INLAYS:
            if has(3, f) or has(4, f):
                continue
            body.append('<circle cx="%s" cy="%s" r="4.5" class="faint" fill="#ddd"/>' % (_f(Xc(f)), _f((Ys(3) + Ys(4)) / 2)))
        elif f % 12 == 0:
            for a, yy in ((2, (Ys(2) + Ys(3)) / 2), (4, (Ys(4) + Ys(5)) / 2)):
                if has(a, f) or has(a + 1, f):
                    continue
                body.append('<circle cx="%s" cy="%s" r="4.5" class="faint" fill="#ddd"/>' % (_f(Xc(f)), _f(yy)))
    # strings
    for sn in range(1, 7):
        body.append(_line(left - (30 if show_open else 0) + 4, Ys(sn), left + ncell * FW, Ys(sn), 1 + (sn - 1) * 0.16))
        body.append(_text(names_x, Ys(sn) + 4, T.pretty_acc(tun[6 - sn]), 11, cls="mut", weight="600"))
    # frets / nut
    for k in range(ncell + 1):
        x = left + k * FW
        w = 5 if (k == 0 and first == 1) else 1.2
        body.append(_line(x, Ys(1) - (0.5 if w > 2 else 0), x, Ys(6) + (0.5 if w > 2 else 0), w))
    # fret numbers
    ny = Ys(6) + 26
    for f in range(first, hi + 1):
        bold = f in INLAYS or f % 12 == 0
        body.append(_text(Xc(f), ny, f, 11.5, cls="ink" if bold else "mut", weight="700" if bold else "normal"))
    if show_open:
        body.append(_text(Xc(0), ny, "0", 11.5, cls="mut"))
    # dots
    root = T.pc(sc["root"])
    for sn, frets in sc["dots"].items():
        for f in frets:
            p = (T.pc(tun[6 - sn]) + f) % 12
            cx, cy = Xc(f), Ys(sn)
            is_root = p == root
            body.append(_dot(cx, cy, r, is_root, filled=is_root))
            if sc["labels"] == "notes":
                lab = T.pretty_acc(sc["names"].get(p, T.pc_name(p)))
            elif sc["labels"] == "intervals":
                lab = T.pretty_interval(sc["tokens"].get(p, "?"))
            else:
                lab = ""
            if lab:
                fs = 10.5 if len(lab) <= 2 else 8.8
                body.append(_text(cx, cy + 3.8, lab, fs, cls="bgf" if is_root else "ink", weight="700"))
    label = "%s fretboard diagram, frets %d to %d" % (sc.get("name") or sc["root"], lo, hi)
    return _svg(W, H, body, label, "dg neck")


# ------------------------------------------------------------------ bar grid

def _meter(tok):
    """'[11/8=3+3+3+2]' -> (11, 8, [3, 3, 3, 2]) or None (kept here so svg has no model import)."""
    import re
    m = re.match(r"^\[(\d{1,2})/(\d{1,2})(?:=(\d{1,2}(?:\+\d{1,2})*))?\]$", tok)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), ([int(x) for x in m.group(3).split("+")] if m.group(3) else None)


def grid_svg(bars, beats=4, repeat=1, display=None, label="chord progression"):
    """Bar grid, 4 bars per row. `bars` is a list of slot lists (see
    model.parse_bars). `display` maps a symbol to the text shown (default:
    the symbol with ♭/♯). Repeat > 1 draws |: ... :| with "×N".

    A bar starting with a time signature token ("[7/8]", "[11/8=3+3+3+2]")
    switches the meter from that bar on: the signature is drawn stacked at the
    left of the bar, and the slashes show the beats (or one slash per eighth-
    note group, spaced by group length, when a grouping is given)."""
    BW, BH, GAP = 94, 54, 12
    left, right = 8, 8
    top = 17 if repeat > 1 and len(bars) <= 4 else 6
    rows = (len(bars) + 3) // 4
    W = left + 4 * BW + right
    H = top + rows * BH + (rows - 1) * GAP + 6
    disp = display or (lambda s: T.pretty_symbol(s))
    body = []
    prev_last = None
    meter = (beats, 4, None)
    for bi, bar in enumerate(bars):
        show_meter = None
        if bar and _meter(bar[0]):
            new_m = _meter(bar[0])
            bar = bar[1:]
            if new_m != meter or bi == 0:
                show_meter = new_m
            meter = new_m
        row, col = divmod(bi, 4)
        x0 = left + col * BW
        y0 = top + row * (BH + GAP)
        # top & bottom rules of the cell
        body.append(_line(x0, y0, x0 + BW, y0, 0.8, cls="mstk"))
        body.append(_line(x0, y0 + BH, x0 + BW, y0 + BH, 0.8, cls="mstk"))
        # left barline (repeat start on very first bar)
        if bi == 0 and repeat > 1:
            body.append(_line(x0 + 1.5, y0, x0 + 1.5, y0 + BH, 3))
            body.append(_line(x0 + 6, y0, x0 + 6, y0 + BH, 1))
            for dy in (-7, 7):
                body.append('<circle cx="%s" cy="%s" r="2.3" class="ink" fill="#000"/>' % (_f(x0 + 11), _f(y0 + BH / 2 + dy)))
        else:
            body.append(_line(x0, y0, x0, y0 + BH, 1.2))
        last = bi == len(bars) - 1
        end_of_row = col == 3 or last
        if end_of_row:
            xe = x0 + BW
            if last and repeat > 1:
                for dy in (-7, 7):
                    body.append('<circle cx="%s" cy="%s" r="2.3" class="ink" fill="#000"/>' % (_f(xe - 11), _f(y0 + BH / 2 + dy)))
                body.append(_line(xe - 6, y0, xe - 6, y0 + BH, 1))
                body.append(_line(xe - 1.5, y0, xe - 1.5, y0 + BH, 3))
                body.append(_text(xe - 2, y0 - 4, "×%d" % repeat, 12.5, anchor="end", weight="700"))
            elif last:
                body.append(_line(xe - 5, y0, xe - 5, y0 + BH, 1))
                body.append(_line(xe - 1.5, y0, xe - 1.5, y0 + BH, 3))
            else:
                body.append(_line(xe, y0, xe, y0 + BH, 1.2))
        inner_l = x0 + (19 if (bi == 0 and repeat > 1) else 7)
        inner_r = x0 + BW - (19 if (last and repeat > 1) else 7)
        if show_meter:
            mx = inner_l + 5
            body.append(_text(mx, y0 + BH / 2 - 3, show_meter[0], 13, weight="800"))
            body.append(_text(mx, y0 + BH / 2 + 11, show_meter[1], 13, weight="800"))
            inner_l += 13
        if bar == ["%"]:
            body.append(_text((inner_l + inner_r) / 2, y0 + BH / 2 + 8, "%", 24, weight="700"))
            continue
        m = len(bar)
        slot_w = (inner_r - inner_l) / m
        for k, tok in enumerate(bar):
            if tok == ".":
                continue
            s = "N.C." if tok in ("N.C.", "NC") else disp(tok)
            fs = 17 if m == 1 else (15 if m == 2 else 13)
            span = 1
            while k + span < m and bar[k + span] == ".":
                span += 1
            room = slot_w * span - 3
            est = len(s) * fs * 0.62
            fit = ' textLength="%s" lengthAdjust="spacingAndGlyphs"' % _f(room) if est > room else ""
            body.append(_text(inner_l + k * slot_w + 1, y0 + 23, s, fs, anchor="start", weight="700", extra=fit))
        # beat slashes (one per beat, or one per eighth-note group of an odd meter)
        n_beats, _, groups = meter
        if groups:
            unit = (inner_r - inner_l) / sum(groups)
            starts = [sum(groups[:g]) for g in range(len(groups))]
            centres = [inner_l + (st + 0.5) * unit for st in starts]
            for st, g in zip(starts, groups):  # a faint underline shows each group's length
                body.append(_line(inner_l + st * unit + 1.5, y0 + BH - 5, inner_l + (st + g) * unit - 1.5, y0 + BH - 5, 1, cls="mstk"))
        else:
            bw = (inner_r - inner_l) / n_beats
            centres = [inner_l + (b + 0.5) * bw for b in range(n_beats)]
        sl = 3.5 if len(centres) <= 6 else 2.2
        for cx in centres:
            body.append(_line(cx - sl, y0 + BH - 9, cx + sl, y0 + BH - 25, 1.6, cls="mstk"))
        prev_last = bar
    del prev_last
    return _svg(W, H, body, label, "dg grid")
