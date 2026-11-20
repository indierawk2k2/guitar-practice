"""Load, normalise and validate the JSON data files in ``data/``.

Every problem is collected into a :class:`Report` instead of raising, so one
build run shows *all* errors at once. Each message starts with the file and the
entry it concerns.
"""

import difflib
import json
import os
import re

from . import theory as T

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SESSION_MINUTES = 45
SESSION_NAMES = ["A", "B", "C", "D"]


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, where, msg):
        self.errors.append("%s: %s" % (where, msg))

    def warn(self, where, msg):
        self.warnings.append("%s: %s" % (where, msg))


# ------------------------------------------------------------------ schema

def _t_str(v):
    return isinstance(v, str)


def _t_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _t_bool(v):
    return isinstance(v, bool)


def _t_list(v):
    return isinstance(v, list)


def _t_dict(v):
    return isinstance(v, dict)


def _t_any(v):
    return True


def _t_strlist(v):
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def _t_str_or_list(v):
    return isinstance(v, (str, list))


def _t_int_or_dict(v):
    return _t_int(v) or isinstance(v, dict)


TYPE_NAMES = {_t_str: "a string", _t_int: "a whole number", _t_bool: "true/false",
              _t_list: "a list", _t_dict: "an object {...}", _t_any: "anything",
              _t_strlist: "a list of strings", _t_str_or_list: "a string or a list",
              _t_int_or_dict: "a number or an object {...}"}

# field: (required, type)
SCHEMAS = {
    "chord": {
        "id": (True, _t_str), "name": (True, _t_str), "root": (True, _t_str),
        "quality": (False, _t_str), "formula": (False, _t_str_or_list),
        "omits": (False, _t_str_or_list), "bass": (False, _t_str),
        "frets": (True, _t_str_or_list), "fingers": (False, _t_str_or_list),
        "barre": (False, _t_any), "base_fret": (False, _t_int),
        "tuning": (False, _t_str_or_list), "tags": (False, _t_strlist),
        "group": (False, _t_str), "notes": (False, _t_str), "sample": (False, _t_bool),
    },
    "barre": {"fret": (True, _t_int), "from": (True, _t_int), "to": (True, _t_int),
              "finger": (False, _t_str_or_list)},
    "scale": {
        "id": (True, _t_str), "name": (True, _t_str), "scale": (False, _t_str),
        "root": (True, _t_str), "formula": (True, _t_str_or_list),
        "layout": (False, _t_str), "position": (False, _t_str),
        "frets": (False, _t_list), "dots": (False, _t_dict),
        "labels": (False, _t_str), "tuning": (False, _t_str_or_list),
        "description": (False, _t_str), "sample": (False, _t_bool),
    },
    "song": {
        "id": (True, _t_str), "title": (True, _t_str), "artist": (True, _t_str),
        "key": (True, _t_str), "capo": (False, _t_int), "tuning": (False, _t_str_or_list),
        "tempo": (False, _t_int), "feel": (False, _t_str), "time": (False, _t_str),
        "level": (False, _t_int), "chords": (True, _t_dict), "form": (False, _t_strlist),
        "sections": (True, _t_list), "why": (True, _t_str), "hard_change": (True, _t_str),
        "tips": (False, _t_strlist), "sample": (False, _t_bool),
        "role": (False, _t_str), "mix": (False, _t_bool), "confidence": (False, _t_str),
        "caveat": (False, _t_str), "theory": (False, _t_str), "steps": (False, _t_strlist),
        "sources": (False, _t_strlist), "detune": (False, _t_int), "alt_voicings": (False, _t_list),
        "order": (False, _t_int),
    },
    "voicing_group": {"label": (True, _t_str), "chords": (True, _t_strlist), "note": (False, _t_str)},
    "bench": {"title": (True, _t_str), "artist": (True, _t_str), "teaches": (True, _t_str),
              "mix": (False, _t_bool), "level": (False, _t_str)},
    "section": {"name": (True, _t_str), "bars": (True, _t_str_or_list),
                "repeat": (False, _t_int), "note": (False, _t_str)},
    "level": {
        "id": (True, _t_str), "number": (True, _t_int), "title": (True, _t_str),
        "summary": (True, _t_str), "goals": (True, _t_strlist),
        "exit_criteria": (True, _t_strlist), "drills": (False, _t_list),
        "benchmarks": (False, _t_list), "sessions": (True, _t_list),
        "chords": (False, _t_strlist), "scales": (False, _t_strlist),
        "songs": (False, _t_strlist), "weeks": (False, _t_int), "sample": (False, _t_bool),
        "status": (False, _t_str), "reading": (False, _t_list), "song_plan": (False, _t_str),
        "week_plan": (False, _t_list), "chord_groups": (False, _t_list),
        "stuck": (False, _t_str), "skip_ahead": (False, _t_str), "checkin": (False, _t_strlist),
    },
    "reading": {"chapter": (True, _t_str), "note": (False, _t_str)},
    "week": {"chords": (True, _t_str), "fretboard": (True, _t_str), "song": (True, _t_str),
             "tempo": (False, _t_str)},
    "drill": {"id": (True, _t_str), "title": (True, _t_str), "instructions": (True, _t_str),
              "chords": (False, _t_strlist), "scales": (False, _t_strlist),
              "metronome": (False, _t_int_or_dict)},
    "benchmark": {"name": (True, _t_str), "target": (True, _t_str)},
    "session": {"name": (True, _t_str), "title": (True, _t_str), "focus": (False, _t_str),
                "blocks": (True, _t_list)},
    "block": {"minutes": (True, _t_int), "title": (True, _t_str),
              "instructions": (True, _t_str_or_list), "chords": (False, _t_strlist),
              "scales": (False, _t_strlist), "songs": (False, _t_strlist),
              "drill": (False, _t_str), "metronome": (False, _t_int_or_dict),
              "record": (False, _t_str)},
    "metronome": {"start": (False, _t_int), "target": (False, _t_int)},
}


def check_fields(entry, schema_name, where, rep):
    """Report missing/unknown/wrongly-typed fields. Returns False if unusable."""
    schema = SCHEMAS[schema_name]
    if not isinstance(entry, dict):
        rep.error(where, "expected an object {...} for a %s, got %s" % (schema_name, type(entry).__name__))
        return False
    ok = True
    for k, v in entry.items():
        if k not in schema:
            close = difflib.get_close_matches(k, list(schema), n=1)
            hint = (" — did you mean '%s'?" % close[0]) if close else ""
            rep.error(where, "unknown field '%s'%s (allowed: %s)" % (k, hint, ", ".join(schema)))
            ok = False
        elif not schema[k][1](v):
            rep.error(where, "field '%s' must be %s, got %r" % (k, TYPE_NAMES[schema[k][1]], v))
            ok = False
    for k, (req, _) in schema.items():
        if req and k not in entry:
            rep.error(where, "missing required field '%s'" % k)
            ok = False
    return ok


# ------------------------------------------------------------------ loading

def load_dir(root, kind, rep):
    """Load every *.json in data/<kind>/. A file may hold one object or a list.
    Returns list of (entry, relpath)."""
    d = os.path.join(root, "data", kind)
    out = []
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        rel = os.path.join("data", kind, fn)
        try:
            with open(os.path.join(d, fn), encoding="utf-8") as fh:
                obj = json.load(fh)
        except json.JSONDecodeError as e:
            rep.error(rel, "invalid JSON at line %d column %d: %s" % (e.lineno, e.colno, e.msg))
            continue
        for item in (obj if isinstance(obj, list) else [obj]):
            out.append((item, rel))
    return out


def _where(rel, kind, entry):
    ident = entry.get("id") if isinstance(entry, dict) else None
    return "%s [%s %s]" % (rel, kind, ("'%s'" % ident) if ident else "#?")


def _check_id(entry, where, rep, seen, kind):
    i = entry.get("id")
    if not isinstance(i, str) or not ID_RE.match(i):
        rep.error(where, "id %r must use only letters, digits, '_', '-', '.' (no spaces or '#'; write F# as 'Fsharp')" % (i,))
        return False
    if i in seen:
        rep.error(where, "duplicate %s id '%s' (also defined in %s)" % (kind, i, seen[i]))
        return False
    return True


# ------------------------------------------------------------------ chords

def _parse_six(v, what, allow_text):
    """Parse a 6-value per-string spec (list, '0 2 2 1 0 0', or 'x32010')."""
    if isinstance(v, str):
        s = v.strip()
        parts = re.split(r"[\s,]+", s) if re.search(r"[\s,]", s) else list(s)
    else:
        parts = list(v)
    if len(parts) != 6:
        raise ValueError("%s must have exactly 6 values, low E string (6) first; got %d: %r" % (what, len(parts), v))
    return parts


def parse_frets(v):
    out = []
    for p in _parse_six(v, "frets", False):
        if isinstance(p, str) and p.strip().lower() in ("x", "-"):
            out.append(None)
            continue
        try:
            n = int(p)
        except (TypeError, ValueError):
            raise ValueError("fret value %r is not a number or 'x'" % (p,))
        if n < 0 or n > 24:
            raise ValueError("fret value %r out of range 0-24" % (p,))
        out.append(n)
    return out


def parse_fingers(v):
    out = []
    for p in _parse_six(v, "fingers", True):
        s = "" if p is None else str(p).strip().upper()
        if s in ("", "0", "X", "-"):
            out.append(None)
        elif s in ("1", "2", "3", "4", "T"):
            out.append(s)
        else:
            raise ValueError("finger value %r must be 1-4, T (thumb), or 0/x for none" % (p,))
    return out


def string_no(i):
    """Index 0..5 (low->high) -> guitar string number 6..1."""
    return 6 - i


def string_label(i, tuning):
    return "string %d (%s)" % (string_no(i), T.pretty_acc(tuning[i]))


def normalize_chord(raw, rel, rep):
    where = _where(rel, "chord", raw)
    if not check_fields(raw, "chord", where, rep):
        return None
    c = {"id": raw["id"], "name": raw["name"], "file": rel, "where": where,
         "tags": raw.get("tags", []), "notes": raw.get("notes", ""),
         "sample": raw.get("sample", False)}
    ok = True
    try:
        T.parse_note(raw["root"])
        c["root"] = T._clean(raw["root"])
    except ValueError as e:
        rep.error(where, "root: %s" % e)
        return None
    q = raw.get("quality")
    qf = None
    if q is not None:
        if q in T.QUALITIES:
            qf = T.parse_formula(T.QUALITIES[q][0])
        elif "formula" not in raw:
            rep.error(where, "quality '%s' is not a built-in quality (%s); give an explicit \"formula\" too"
                      % (q, ", ".join(T.QUALITIES)))
            return None
    if "formula" in raw:
        try:
            c["formula"] = T.parse_formula(raw["formula"])
        except ValueError as e:
            rep.error(where, "formula: %s" % e)
            return None
        if qf is not None and sorted(set(qf)) != sorted(set(c["formula"])):
            rep.error(where, "formula '%s' disagrees with quality '%s' (= '%s'). Fix one, or drop "
                      "\"formula\" to use the built-in one" % (" ".join(c["formula"]), q, " ".join(qf)))
            ok = False
    elif qf is not None:
        c["formula"] = qf
    else:
        rep.error(where, "needs \"quality\" (one of: %s) and/or \"formula\" (e.g. \"1 3 5 b7\")" % ", ".join(T.QUALITIES))
        return None
    c["quality"] = q
    c["group"] = raw.get("group") or (T.QUALITIES[q][1] if q in T.QUALITIES else "Other")
    if c["group"] not in T.GROUP_ORDER:
        rep.warn(where, "group '%s' is not a standard group; it will be listed after the standard ones" % c["group"])
    try:
        c["omits"] = T.parse_formula(raw["omits"]) if raw.get("omits") else []
    except ValueError as e:
        rep.error(where, "omits: %s" % e)
        return None
    for o in c["omits"]:
        if o not in c["formula"]:
            rep.error(where, "omits '%s' is not in the formula '%s'" % (o, " ".join(c["formula"])))
            ok = False
    c["bass"] = None
    if raw.get("bass"):
        try:
            T.parse_note(raw["bass"])
            c["bass"] = T._clean(raw["bass"])
        except ValueError as e:
            rep.error(where, "bass: %s" % e)
            return None
    try:
        c["tuning"] = T.parse_tuning(raw.get("tuning"))
    except ValueError as e:
        rep.error(where, "tuning: %s" % e)
        return None
    try:
        c["frets"] = parse_frets(raw["frets"])
    except ValueError as e:
        rep.error(where, "frets: %s" % e)
        return None
    c["fingers"] = None
    if "fingers" in raw:
        try:
            c["fingers"] = parse_fingers(raw["fingers"])
        except ValueError as e:
            rep.error(where, "fingers: %s" % e)
            ok = False
    fretted = [f for f in c["frets"] if f]
    if all(f is None for f in c["frets"]):
        rep.error(where, "all six strings are muted")
        return None

    # --- fingers consistent with frets
    if c["fingers"]:
        for i, (f, fg) in enumerate(zip(c["frets"], c["fingers"])):
            if f and not fg:
                rep.error(where, "%s is fretted at %d but has no finger (fingers use 1-4 or T; 0/x only for open or muted strings)"
                          % (string_label(i, c["tuning"]), f))
                ok = False
            if not f and fg:
                rep.error(where, "%s is %s but has finger %s" % (string_label(i, c["tuning"]),
                                                                 "open" if f == 0 else "muted", fg))
                ok = False

    # --- base fret and diagram window
    maxf = max(fretted) if fretted else 0
    minf = min(fretted) if fretted else 1
    if "base_fret" in raw:
        base = raw["base_fret"]
        if base < 1:
            rep.error(where, "base_fret must be 1 or more")
            base = 1
    else:
        base = 1 if maxf <= 4 else minf
    nfrets = max(4, maxf - base + 1)
    if fretted and minf < base:
        rep.error(where, "fret %d is below base_fret %d (frets are absolute fret numbers, not relative to base_fret)" % (minf, base))
        ok = False
    if nfrets > 6:
        rep.error(where, "fretted notes span frets %d-%d, too wide for one diagram (max 6 frets); check the frets" % (base, maxf))
        ok = False
    if base > 1 and any(f == 0 for f in c["frets"]) and "base_fret" not in raw:
        rep.warn(where, "open strings combined with base_fret %d; diagram shows 'o' above the box" % base)
    c["base_fret"], c["nfrets"] = base, nfrets

    # --- barres (explicit, or inferred from fingers)
    c["barres"] = []
    if "barre" in raw:
        b = raw["barre"]
        blist = [] if b is False or b is None else (b if isinstance(b, list) else [b])
        for bb in blist:
            bw = where + " barre"
            if not check_fields(bb, "barre", bw, rep):
                ok = False
                continue
            hi, lo = max(bb["from"], bb["to"]), min(bb["from"], bb["to"])
            if lo < 1 or hi > 6 or hi == lo:
                rep.error(bw, "from/to must be two different string numbers 6 (low E) .. 1 (high E)")
                ok = False
                continue
            c["barres"].append({"fret": bb["fret"], "hi": hi, "lo": lo, "finger": str(bb.get("finger", "1"))})
    elif c["fingers"]:
        groups = {}
        for i, (f, fg) in enumerate(zip(c["frets"], c["fingers"])):
            if f and fg:
                groups.setdefault((fg, f), []).append(string_no(i))
        for (fg, f), strs in groups.items():
            if len(strs) >= 2:
                hi, lo = max(strs), min(strs)
                # only a real barre if no string in between is fretted lower
                between = [c["frets"][6 - s] for s in range(lo, hi + 1)]
                if all(x is not None and x >= f for x in between):
                    c["barres"].append({"fret": f, "hi": hi, "lo": lo, "finger": fg})
    for b in c["barres"]:
        for s in range(b["lo"], b["hi"] + 1):
            f = c["frets"][6 - s]
            if f is None or f < b["fret"]:
                rep.error(where, "barre at fret %d covers string %d, but that string is %s"
                          % (b["fret"], s, "muted" if f is None else "at fret %d" % f))
                ok = False
        for s in (b["lo"], b["hi"]):
            if c["frets"][6 - s] != b["fret"]:
                rep.error(where, "barre at fret %d should end on strings fretted at %d; string %d is at %s"
                          % (b["fret"], b["fret"], s, c["frets"][6 - s]))
                ok = False

    # --- the important check: sounding notes == root + formula (- omits) (+ bass)
    tokens = [t for t in c["formula"] if t not in c["omits"]]
    expected = T.formula_pcs(c["root"], tokens)
    names = T.pc_to_name(c["root"], c["formula"])
    toks = T.pc_to_token(c["root"], c["formula"])
    if c["bass"]:
        bpc = T.pc(c["bass"])
        expected = expected | {bpc}
        if bpc not in names:
            names[bpc] = c["bass"]
            toks[bpc] = T.SEMI_TO_TOKEN[(bpc - T.pc(c["root"])) % 12]
    sounding = []
    for i, f in enumerate(c["frets"]):
        if f is None:
            sounding.append(None)
            continue
        p = (T.pc(c["tuning"][i]) + f) % 12
        sounding.append({"pc": p, "fret": f, "string": string_no(i),
                         "name": names.get(p, T.pc_name(p)), "token": toks.get(p)})
    c["sounding"] = sounding
    got = {s["pc"] for s in sounding if s}
    if got != expected:
        extra = sorted(got - expected)
        missing = sorted(expected - got)
        parts = []
        for p in extra:
            locs = ["%s fret %d" % (string_label(6 - s["string"], c["tuning"]), s["fret"])
                    for s in sounding if s and s["pc"] == p]
            parts.append("%s is not in the chord (from %s)" % (T.pc_both(p), ", ".join(locs)))
        for p in missing:
            tok = toks.get(p, "?")
            parts.append("%s (the %s) is missing — add it, or list \"%s\" in \"omits\"" % (names.get(p, T.pc_both(p)), tok, tok))
        rep.error(where, "frets %s sound {%s} but %s %s + formula '%s'%s%s needs {%s}: %s" % (
            " ".join("x" if f is None else str(f) for f in c["frets"]),
            " ".join(T.pc_both(p) for p in sorted(got)),
            "root", c["root"], " ".join(c["formula"]),
            (" omits '%s'" % " ".join(c["omits"])) if c["omits"] else "",
            (" + bass %s" % c["bass"]) if c["bass"] else "",
            " ".join(names.get(p, T.pc_name(p)) for p in sorted(expected)),
            "; ".join(parts)))
        ok = False
    low = next((s for s in sounding if s), None)
    want_bass = c["bass"] or (None if "1" in c["omits"] else c["root"])
    if low and want_bass and low["pc"] != T.pc(want_bass):
        rep.error(where, "lowest sounding note is %s (%s fret %d) but the bass should be %s. Mute that "
                  "string, or if the inversion is intended name it as a slash chord with \"bass\": \"%s\""
                  % (low["name"], string_label(6 - low["string"], c["tuning"]), low["fret"],
                     want_bass, low["name"]))
        ok = False
    c["notes_spelled"] = [T.spell(c["root"], t) for t in tokens]
    c["valid"] = ok
    return c


# ------------------------------------------------------------------ scales

def normalize_scale(raw, rel, rep, adhoc=False):
    where = raw.get("_where") or _where(rel, "scale", raw)
    if not adhoc and not check_fields(raw, "scale", where, rep):
        return None
    s = {"id": raw.get("id", ""), "name": raw.get("name", ""), "file": rel, "where": where,
         "scale": raw.get("scale") or raw.get("name", ""), "position": raw.get("position", ""),
         "description": raw.get("description", ""), "sample": raw.get("sample", False)}
    try:
        T.parse_note(raw["root"])
        s["root"] = T._clean(raw["root"])
        s["formula"] = T.parse_formula(raw["formula"])
        s["tuning"] = T.parse_tuning(raw.get("tuning"))
    except ValueError as e:
        rep.error(where, str(e))
        return None
    layout = raw.get("layout", "pattern")
    if layout not in ("pattern", "neck"):
        rep.error(where, "layout must be \"pattern\" (dots listed) or \"neck\" (every scale note in the fret window)")
        return None
    s["layout"] = layout
    labels = raw.get("labels", "intervals")
    if labels not in ("intervals", "notes", "none"):
        rep.error(where, "labels must be \"intervals\", \"notes\" or \"none\"")
        labels = "intervals"
    s["labels"] = labels
    pcs = T.formula_pcs(s["root"], s["formula"])
    s["names"] = T.pc_to_name(s["root"], s["formula"])
    s["tokens"] = T.pc_to_token(s["root"], s["formula"])
    s["notes_spelled"] = [T.spell(s["root"], t) for t in s["formula"]]
    win = raw.get("frets")
    if win is not None:
        if not (isinstance(win, list) and len(win) == 2 and all(_t_int(x) for x in win)
                and 0 <= win[0] < win[1] <= 24):
            rep.error(where, "frets (the window) must be [first, last] with 0 <= first < last <= 24, e.g. [0, 15]")
            return None
    dots = {}  # string number -> sorted fret list
    if layout == "neck":
        if win is None:
            win = [0, 15]
        for i in range(6):
            sn = string_no(i)
            dots[sn] = [f for f in range(win[0], win[1] + 1)
                        if (T.pc(s["tuning"][i]) + f) % 12 in pcs]
        if raw.get("dots"):
            rep.error(where, "layout \"neck\" computes its dots; remove \"dots\" or use layout \"pattern\"")
    else:
        raw_dots = raw.get("dots")
        if not raw_dots:
            rep.error(where, "layout \"pattern\" needs \"dots\": {\"6\": [5, 8], \"5\": [5, 7], ...} (string number -> frets)")
            return None
        ok = True
        for k, frets in raw_dots.items():
            if k not in ("1", "2", "3", "4", "5", "6"):
                rep.error(where, "dots key %r must be a string number \"6\" (low E) .. \"1\" (high E)" % k)
                ok = False
                continue
            if not (isinstance(frets, list) and all(_t_int(f) and 0 <= f <= 24 for f in frets)):
                rep.error(where, "dots for string %s must be a list of fret numbers 0-24" % k)
                ok = False
                continue
            sn = int(k)
            i = 6 - sn
            for f in frets:
                p = (T.pc(s["tuning"][i]) + f) % 12
                if p not in pcs:
                    rep.error(where, "dot on %s fret %d is %s, which is not in %s %s (%s)" % (
                        string_label(i, s["tuning"]), f, T.pc_both(p), s["root"], s["scale"] or "scale",
                        " ".join(s["notes_spelled"])))
                    ok = False
            dots[sn] = sorted(set(frets))
        if not ok:
            return None
        allf = [f for fl in dots.values() for f in fl]
        if win is None:
            win = [max(0, min(allf) - (0 if min(allf) == 0 else 0)), max(allf)]
            if win[1] - win[0] < 3:
                win[1] = win[0] + 3
        for f in allf:
            if f < win[0] or f > win[1]:
                rep.error(where, "dot at fret %d is outside the window frets %s" % (f, win))
                return None
    s["window"] = win
    s["dots"] = dots
    return s


# ------------------------------------------------------------------ songs

SPECIAL_SLOTS = (".", "%", "N.C.", "NC")
SONG_ROLES = ("core", "alternate")
CONFIDENCE = ("high", "medium", "low")

# A bar may start with a time-signature token: "[11/8]" or "[11/8=3+3+3+2]"
# (eighth-note grouping; the groups must add up to the top number). It applies
# to that bar and the following bars of the same section, until the next one.
METER_RE = re.compile(r"^\[(\d{1,2})/(\d{1,2})(?:=(\d{1,2}(?:\+\d{1,2})*))?\]$")


def parse_meter(tok):
    """'[11/8=3+3+3+2]' -> (11, 8, [3, 3, 3, 2]); '[7/8]' -> (7, 8, None); else None."""
    m = METER_RE.match(tok)
    if not m:
        return None
    groups = [int(x) for x in m.group(3).split("+")] if m.group(3) else None
    return int(m.group(1)), int(m.group(2)), groups


def is_slot_special(tok):
    return tok in SPECIAL_SLOTS or bool(METER_RE.match(tok))


def parse_bars(v):
    """'A7 | D7 | A7 . . E7 | %' or ['A7', 'D7', ...] -> list of slot lists."""
    if isinstance(v, str):
        items = [b for b in (x.strip() for x in v.split("|")) if b != ""]
    else:
        items = [str(b).strip() for b in v]
    return [b.split() for b in items]


def normalize_song(raw, rel, rep):
    where = _where(rel, "song", raw)
    if not check_fields(raw, "song", where, rep):
        return None
    s = dict(raw)
    s["file"], s["where"] = rel, where
    s.setdefault("capo", 0)
    s.setdefault("time", "4/4")
    s.setdefault("tips", [])
    s.setdefault("sample", False)
    s.setdefault("feel", "")
    m = re.match(r"^(\d+)/(\d+)$", s["time"])
    if not m:
        rep.error(where, "time must look like \"4/4\" or \"6/8\"")
        return None
    s["beats"] = int(m.group(1))
    try:
        s["tuning"] = T.parse_tuning(raw.get("tuning"))
    except ValueError as e:
        rep.error(where, "tuning: %s" % e)
        return None
    for sym, cid in raw["chords"].items():
        if not isinstance(cid, str):
            rep.error(where, "chords: value for '%s' must be a chord id string" % sym)
    secs = []
    names = set()
    for n, sec in enumerate(raw["sections"]):
        sw = "%s section #%d" % (where, n + 1)
        if not check_fields(sec, "section", sw, rep):
            continue
        sw = "%s section '%s'" % (where, sec["name"])
        bars = parse_bars(sec["bars"])
        if not bars:
            rep.error(sw, "has no bars")
            continue
        for bi, bar in enumerate(bars):
            if bar == ["%"]:
                if bi == 0:
                    rep.error(sw, "bar 1 is '%' (repeat previous bar) but there is no previous bar")
                continue
            for ti, tok in enumerate(bar):
                if tok.startswith("["):
                    mt = parse_meter(tok)
                    if mt is None:
                        rep.error(sw, "bar %d: '%s' is not a time signature; write it like [7/8] or [11/8=3+3+3+2]" % (bi + 1, tok))
                    elif ti != 0:
                        rep.error(sw, "bar %d: the time signature '%s' must come first in its bar" % (bi + 1, tok))
                    elif len(bar) == 1:
                        rep.error(sw, "bar %d: '%s' needs at least one chord after it" % (bi + 1, tok))
                    elif mt[2] and sum(mt[2]) != mt[0]:
                        rep.error(sw, "bar %d: grouping %s adds up to %d, not %d" % (bi + 1, "+".join(map(str, mt[2])), sum(mt[2]), mt[0]))
                    continue
                if tok in SPECIAL_SLOTS:
                    if tok == "%":
                        rep.error(sw, "bar %d: '%%' must be alone in its bar" % (bi + 1))
                    continue
                if tok not in raw["chords"]:
                    rep.error(sw, "bar %d uses chord symbol '%s' which is not a key in the song's \"chords\" map (%s)"
                              % (bi + 1, tok, ", ".join(raw["chords"]) or "empty"))
        rpt = sec.get("repeat", 1)
        if rpt < 1:
            rep.error(sw, "repeat must be 1 or more")
            rpt = 1
        names.add(sec["name"])
        secs.append({"name": sec["name"], "bars": bars, "repeat": rpt, "note": sec.get("note", "")})
    s["sections"] = secs
    for f in s.get("form", []):
        if f not in names:
            rep.error(where, "form lists '%s' but there is no section with that name (%s)" % (f, ", ".join(sorted(names))))
    used = {tok for sec in secs for bar in sec["bars"] for tok in bar if not is_slot_special(tok)}
    for sym in raw["chords"]:
        if sym not in used:
            rep.warn(where, "chord symbol '%s' is in \"chords\" but never used in a section" % sym)
    if s.get("role") is not None and s["role"] not in SONG_ROLES:
        rep.error(where, "role must be one of %s" % ", ".join(SONG_ROLES))
    if s.get("confidence") is not None and s["confidence"] not in CONFIDENCE:
        rep.error(where, "confidence must be one of %s" % ", ".join(CONFIDENCE))
    if s.get("detune") is not None and not 1 <= s["detune"] <= 3:
        rep.error(where, "detune is semitones the whole guitar is tuned DOWN, 1-3 (e.g. 2 = D G C F A D)")
    for u in s.get("sources", []):
        if not re.match(r"^https?://\S+$", u):
            rep.error(where, "sources: %r is not a URL (http:// or https://)" % u)
    groups = []
    for n, g in enumerate(raw.get("alt_voicings", [])):
        if check_fields(g, "voicing_group", "%s alt_voicings #%d" % (where, n + 1), rep):
            groups.append({"label": g["label"], "chords": g["chords"], "note": g.get("note", "")})
    s["alt_voicings"] = groups
    s.setdefault("steps", [])
    s.setdefault("sources", [])
    return s


# ------------------------------------------------------------------ levels

def _metronome(v, where, rep):
    if v is None:
        return None
    if _t_int(v):
        return {"start": None, "target": v}
    if not check_fields(v, "metronome", where + " metronome", rep):
        return None
    return {"start": v.get("start"), "target": v.get("target")}


def normalize_level(raw, rel, rep):
    where = _where(rel, "level", raw)
    if not check_fields(raw, "level", where, rep):
        return None
    lv = dict(raw)
    lv["file"], lv["where"] = rel, where
    lv.setdefault("sample", False)
    lv.setdefault("weeks", 4)
    for k in ("status", "song_plan", "stuck", "skip_ahead"):
        lv.setdefault(k, "")
    lv.setdefault("checkin", [])
    reading = []
    for n, r in enumerate(raw.get("reading", [])):
        if isinstance(r, str):
            r = {"chapter": r}
        if check_fields(r, "reading", "%s reading #%d" % (where, n + 1), rep):
            reading.append({"chapter": r["chapter"], "note": r.get("note", "")})
    lv["reading"] = reading
    plan = []
    for n, w in enumerate(raw.get("week_plan", [])):
        if check_fields(w, "week", "%s week_plan #%d" % (where, n + 1), rep):
            plan.append(dict(w, tempo=w.get("tempo", "")))
    lv["week_plan"] = plan
    if plan and len(plan) > lv["weeks"]:
        rep.error(where, "week_plan has %d rows but the level has only %d weeks" % (len(plan), lv["weeks"]))
    groups = []
    for n, g in enumerate(raw.get("chord_groups", [])):
        if check_fields(g, "voicing_group", "%s chord_groups #%d" % (where, n + 1), rep):
            groups.append({"label": g["label"], "chords": list(g["chords"]), "note": g.get("note", "")})
    lv["chord_groups"] = groups
    drills = []
    for n, d in enumerate(raw.get("drills", [])):
        dw = "%s drill #%d" % (where, n + 1)
        if not check_fields(d, "drill", dw, rep):
            continue
        d = dict(d)
        d["metronome"] = _metronome(d.get("metronome"), dw, rep)
        d.setdefault("chords", [])
        d.setdefault("scales", [])
        drills.append(d)
    lv["drills"] = drills
    benches = []
    for n, b in enumerate(raw.get("benchmarks", [])):
        if check_fields(b, "benchmark", "%s benchmark #%d" % (where, n + 1), rep):
            benches.append(b)
    lv["benchmarks"] = benches
    sessions = []
    for n, sraw in enumerate(raw["sessions"]):
        sw = "%s session #%d" % (where, n + 1)
        if not check_fields(sraw, "session", sw, rep):
            continue
        sw = "%s session %s" % (where, sraw["name"])
        blocks = []
        for bn, b in enumerate(sraw["blocks"]):
            bw = "%s block #%d" % (sw, bn + 1)
            if not check_fields(b, "block", bw, rep):
                continue
            b = dict(b)
            if b["minutes"] <= 0:
                rep.error(bw, "minutes must be positive")
            if isinstance(b["instructions"], list):
                if not all(isinstance(x, str) for x in b["instructions"]):
                    rep.error(bw, "instructions list must contain only strings")
                    continue
            else:
                b["instructions"] = [b["instructions"]]
            b["metronome"] = _metronome(b.get("metronome"), bw, rep)
            for k in ("chords", "scales", "songs"):
                b.setdefault(k, [])
            blocks.append(b)
        total = sum(b["minutes"] for b in blocks)
        if total != SESSION_MINUTES:
            rep.error(sw, "blocks add up to %d minutes; a session must be exactly %d (%s)" % (
                total, SESSION_MINUTES, " + ".join(str(b["minutes"]) for b in blocks)))
        text = sum(len(" ".join(b["instructions"])) + len(b["title"]) for b in blocks)
        if len(blocks) > 8:
            rep.warn(sw, "%d blocks; more than 8 rarely fits on one printed page" % len(blocks))
        if text > 1500:
            rep.warn(sw, "about %d characters of text; over ~1500 may not fit on one printed page "
                     "(`python3 build.py pdf` checks this exactly)" % text)
        sessions.append({"name": sraw["name"], "title": sraw["title"],
                         "focus": sraw.get("focus", ""), "blocks": blocks})
    got = [s["name"] for s in sessions]
    if got != SESSION_NAMES:
        rep.error(where, "sessions must be exactly A, B, C, D in that order; got %s" % (", ".join(got) or "none"))
    lv["sessions"] = sessions
    return lv


# ------------------------------------------------------------------ project

class Project:
    """All loaded data. Attributes are dicts id -> normalised entry,
    in file order (chords, scales, songs) or by number (levels)."""

    def __init__(self, root):
        self.root = root
        self.rep = Report()
        self.chords, self.scales, self.songs, self.levels = {}, {}, {}, {}
        self.bench = []
        self.raw_counts = {}
        self.broken = set()  # (kind, id) of entries that exist but failed validation
        self._load()
        self._load_bench()
        self._check_refs()

    def _load(self):
        rep = self.rep
        for kind, store, norm in (("chords", self.chords, normalize_chord),
                                  ("scales", self.scales, normalize_scale),
                                  ("songs", self.songs, normalize_song),
                                  ("levels", self.levels, normalize_level)):
            seen = {}
            items = load_dir(self.root, kind, rep)
            self.raw_counts[kind] = len(items)
            for raw, rel in items:
                w = _where(rel, kind[:-1], raw)
                if not isinstance(raw, dict):
                    rep.error(w, "each entry must be an object {...}")
                    continue
                if not _check_id(raw, w, rep, seen, kind[:-1]):
                    continue
                seen[raw["id"]] = rel
                e = norm(raw, rel, rep)
                if e is not None:
                    store[e["id"]] = e
                else:
                    self.broken.add((kind[:-1], raw["id"]))
        nums = {}
        for lv in self.levels.values():
            if lv["number"] in nums:
                self.rep.error(lv["where"], "level number %d already used by level '%s'" % (lv["number"], nums[lv["number"]]))
            nums[lv["number"]] = lv["id"]
        self.levels = dict(sorted(self.levels.items(), key=lambda kv: kv[1]["number"]))

    def _load_bench(self):
        """data/song-bench.json: songs queued for later, listed on the Songs page without charts."""
        rel = os.path.join("data", "song-bench.json")
        path = os.path.join(self.root, rel)
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as fh:
                items = json.load(fh)
        except json.JSONDecodeError as e:
            self.rep.error(rel, "invalid JSON at line %d column %d: %s" % (e.lineno, e.colno, e.msg))
            return
        if not isinstance(items, list):
            self.rep.error(rel, "must be a list of {title, artist, teaches}")
            return
        for n, b in enumerate(items):
            if check_fields(b, "bench", "%s entry #%d" % (rel, n + 1), self.rep):
                self.bench.append(b)

    def ref(self, kind, ident, where):
        """Check a reference; returns the entry or None (and records an error)."""
        store = {"chord": self.chords, "scale": self.scales, "song": self.songs, "level": self.levels}[kind]
        if ident in store:
            return store[ident]
        if (kind, ident) in self.broken:
            return None  # already reported where it is defined
        close = difflib.get_close_matches(ident, list(store), n=1)
        self.rep.error(where, "unknown %s id '%s'%s" % (kind, ident, (" — did you mean '%s'?" % close[0]) if close else ""))
        return None

    def _check_refs(self):
        for s in self.songs.values():
            pairs = list(s["chords"].items())
            pairs += [("%s: %s" % (g["label"], cid), cid) for g in s["alt_voicings"] for cid in g["chords"]]
            for sym, cid in pairs:
                ch = self.ref("chord", cid, s["where"] + " chords['%s']" % sym)
                if ch and [T.pc(x) for x in ch["tuning"]] != [T.pc(x) for x in s["tuning"]]:
                    self.rep.error(s["where"], "chord '%s' is for tuning %s but the song is in %s"
                                   % (cid, " ".join(ch["tuning"]), " ".join(s["tuning"])))
        for lv in self.levels.values():
            drill_ids = {d["id"] for d in lv["drills"]}
            for d in lv["drills"]:
                for c in d["chords"]:
                    self.ref("chord", c, "%s drill '%s'" % (lv["where"], d["id"]))
                for c in d["scales"]:
                    self.ref("scale", c, "%s drill '%s'" % (lv["where"], d["id"]))
            for k, kind in (("chords", "chord"), ("scales", "scale"), ("songs", "song")):
                for i in lv.get(k, []):
                    self.ref(kind, i, lv["where"] + " " + k)
            for g in lv["chord_groups"]:
                for i in g["chords"]:
                    self.ref("chord", i, "%s chord_groups '%s'" % (lv["where"], g["label"]))
            for s in lv["sessions"]:
                for bn, b in enumerate(s["blocks"]):
                    bw = "%s session %s block #%d '%s'" % (lv["where"], s["name"], bn + 1, b["title"])
                    for k, kind in (("chords", "chord"), ("scales", "scale"), ("songs", "song")):
                        for i in b[k]:
                            self.ref(kind, i, bw)
                    if b.get("drill") and b["drill"] not in drill_ids:
                        self.rep.error(bw, "unknown drill id '%s' (this level defines: %s)" % (b["drill"], ", ".join(sorted(drill_ids)) or "none"))

    def level_refs(self, lv):
        """Chord/scale/song ids for a level's reference pages: the level's own
        lists first (chord_groups, then chords), then everything its blocks and
        drills mention, de-duplicated. Song chords are not added: every song
        chart in the packet prints its own chord row."""
        out = {}
        for k in ("chords", "scales", "songs"):
            ids = [i for g in lv["chord_groups"] for i in g["chords"]] if k == "chords" else []
            ids += list(lv.get(k, []))
            for d in lv["drills"]:
                ids += d.get(k, []) if k != "songs" else []
            for s in lv["sessions"]:
                for b in s["blocks"]:
                    ids += b[k]
            store = {"chords": self.chords, "scales": self.scales, "songs": self.songs}[k]
            seen = []
            for i in ids:
                if i in store and i not in seen:
                    seen.append(i)
            out[k] = seen
        return out

    def samples(self):
        out = []
        for kind, store in (("chord", self.chords), ("scale", self.scales), ("song", self.songs), ("level", self.levels)):
            out += ["%s %s (%s)" % (kind, e["id"], e["file"]) for e in store.values() if e.get("sample")]
        return out
