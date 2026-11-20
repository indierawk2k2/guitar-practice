"""Music theory helpers: notes, pitch classes, interval formulas, spelling.

Conventions used throughout the engine:

* A *note* is written as a letter A-G followed by optional accidentals:
  ``b`` (flat), ``#`` (sharp), ``bb``, ``##``. Unicode ``♭``/``♯`` are accepted.
* A *pitch class* (pc) is an integer 0-11 with C = 0.
* An *interval token* is a scale degree with optional accidentals in front:
  ``1 b2 2 #2 b3 3 4 #4 b5 5 #5 b6 6 bb7 b7 7 9 b9 #9 11 #11 13 b13``.
  ``R`` is accepted as a synonym of ``1``.
* Strings are numbered the guitar way: string 6 = low E ... string 1 = high E.
  Lists of six per-string values (frets, fingers, tuning) are always written
  low string first (string 6 -> string 1).
"""

import re

LETTERS = "CDEFGAB"
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
DEGREE_SEMIS = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
STANDARD_TUNING = ["E", "A", "D", "G", "B", "E"]

# Default spelling for a bare semitone distance (used for slash-chord basses
# outside the formula and for ad-hoc note sets).
SEMI_TO_TOKEN = {0: "1", 1: "b2", 2: "2", 3: "b3", 4: "3", 5: "4", 6: "b5",
                 7: "5", 8: "b6", 9: "6", 10: "b7", 11: "7"}

# Chord qualities the engine knows by name. ``formula`` in a chord entry may be
# omitted when ``quality`` is one of these; if both are given they must agree.
# group = heading used on the chord library page (in this order).
QUALITIES = {
    "maj":   ("1 3 5", "Major", ""),
    "m":     ("1 b3 5", "Minor", "m"),
    "7":     ("1 3 5 b7", "Dominant 7th", "7"),
    "maj7":  ("1 3 5 7", "Major 7th", "maj7"),
    "m7":    ("1 b3 5 b7", "Minor 7th", "m7"),
    "mmaj7": ("1 b3 5 7", "Minor 7th", "m(maj7)"),
    "6":     ("1 3 5 6", "Sixth", "6"),
    "m6":    ("1 b3 5 6", "Sixth", "m6"),
    "6/9":   ("1 3 5 6 9", "Sixth", "6/9"),
    "sus2":  ("1 2 5", "Suspended", "sus2"),
    "sus4":  ("1 4 5", "Suspended", "sus4"),
    "7sus4": ("1 4 5 b7", "Suspended", "7sus4"),
    "add9":  ("1 3 5 9", "Added tone", "add9"),
    "madd9": ("1 b3 5 9", "Added tone", "m(add9)"),
    "9":     ("1 3 5 b7 9", "Extended", "9"),
    "maj9":  ("1 3 5 7 9", "Extended", "maj9"),
    "m9":    ("1 b3 5 b7 9", "Extended", "m9"),
    "7#9":   ("1 3 5 b7 #9", "Extended", "7♯9"),
    "13":    ("1 3 5 b7 9 13", "Extended", "13"),
    "dim":   ("1 b3 b5", "Diminished & augmented", "dim"),
    "dim7":  ("1 b3 b5 bb7", "Diminished & augmented", "dim7"),
    "m7b5":  ("1 b3 b5 b7", "Diminished & augmented", "m7♭5"),
    "aug":   ("1 3 #5", "Diminished & augmented", "aug"),
    "5":     ("1 5", "Power chords", "5"),
}
GROUP_ORDER = ["Major", "Minor", "Dominant 7th", "Major 7th", "Minor 7th",
               "Sixth", "Suspended", "Added tone", "Extended",
               "Diminished & augmented", "Power chords", "Slash chords",
               "Triads & inversions", "Shell voicings", "Alternate tunings", "Other"]

_NOTE_RE = re.compile(r"^([A-Ga-g])(bb|b|##|#)?$")
_INT_RE = re.compile(r"^(bb|b|##|#)?(\d{1,2})$")
_ACC = {None: 0, "": 0, "b": -1, "bb": -2, "#": 1, "##": 2}


def _clean(s):
    return str(s).strip().replace("♭", "b").replace("♯", "#")


def parse_note(s):
    """Return (letter, accidental_int). Raises ValueError on bad input."""
    m = _NOTE_RE.match(_clean(s))
    if not m:
        raise ValueError("not a note name: %r (use e.g. C, F#, Bb)" % (s,))
    return m.group(1).upper(), _ACC[m.group(2)]


def is_note(s):
    try:
        parse_note(s)
        return True
    except ValueError:
        return False


def pc(note):
    letter, acc = parse_note(note)
    return (NATURAL_PC[letter] + acc) % 12


def note_str(letter, acc):
    return letter + ("#" * acc if acc > 0 else "b" * (-acc))


def parse_interval(tok):
    """Return (degree, semitones_above_root_mod_12) for an interval token."""
    t = _clean(tok)
    if t.upper() == "R":
        t = "1"
    m = _INT_RE.match(t)
    if not m:
        raise ValueError("not an interval: %r (use e.g. 1 b3 5 b7 9 #11)" % (tok,))
    deg = int(m.group(2))
    if deg < 1 or deg > 15:
        raise ValueError("interval degree out of range: %r" % (tok,))
    base = (deg - 1) % 7 + 1
    semis = DEGREE_SEMIS[base] + _ACC[m.group(1)]
    return deg, semis % 12


def norm_interval(tok):
    t = _clean(tok)
    return "1" if t.upper() == "R" else t


def parse_formula(f):
    """Formula as string "1 3 5 b7" (spaces or commas) or list -> list of tokens.
    Raises ValueError for a bad token."""
    if isinstance(f, (list, tuple)):
        toks = [str(x) for x in f]
    else:
        toks = re.split(r"[\s,]+", str(f).strip())
    toks = [norm_interval(t) for t in toks if t]
    if not toks:
        raise ValueError("empty formula")
    for t in toks:
        parse_interval(t)
    return toks


def spell(root, tok):
    """Spell the note `tok` above `root` with the correct letter name."""
    letter, _ = parse_note(root)
    deg, semis = parse_interval(tok)
    target = (pc(root) + semis) % 12
    new_letter = LETTERS[(LETTERS.index(letter) + (deg - 1)) % 7]
    acc = (target - NATURAL_PC[new_letter]) % 12
    if acc > 6:
        acc -= 12
    if abs(acc) > 2:
        return pc_name(target)
    return note_str(new_letter, acc)


SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def pc_name(p, prefer_flat=False):
    return (FLAT_NAMES if prefer_flat else SHARP_NAMES)[p % 12]


def pc_both(p):
    a, b = SHARP_NAMES[p % 12], FLAT_NAMES[p % 12]
    return a if a == b else a + "/" + b


def formula_pcs(root, tokens):
    r = pc(root)
    return {(r + parse_interval(t)[1]) % 12 for t in tokens}


def pc_to_token(root, tokens):
    """Map pitch class -> interval token for the given root + formula."""
    r = pc(root)
    out = {}
    for t in tokens:
        out.setdefault((r + parse_interval(t)[1]) % 12, t)
    return out


def pc_to_name(root, tokens):
    r = pc(root)
    out = {}
    for t in tokens:
        out.setdefault((r + parse_interval(t)[1]) % 12, spell(root, t))
    return out


# ---------------------------------------------------------------- display

def pretty_acc(s):
    """b/# -> ♭/♯ inside a note name or interval token ('Bb' -> 'B♭', 'b3' -> '♭3')."""
    s = str(s)
    m = re.match(r"^([A-G])(bb|b|##|#)?(.*)$", s)
    if m:
        acc = (m.group(2) or "").replace("b", "♭").replace("#", "♯")
        return m.group(1) + acc + m.group(3)
    return s.replace("b", "♭").replace("#", "♯")


def pretty_interval(tok, root_as_r=True):
    t = norm_interval(tok)
    if t == "1" and root_as_r:
        return "R"
    return t.replace("bb", "𝄫").replace("b", "♭").replace("#", "♯")


def pretty_formula(tokens):
    return " ".join(pretty_interval(t, root_as_r=False) for t in tokens)


_SYM_RE = re.compile(r"^([A-G])(b|#)?([^/]*)(?:/([A-G])(b|#)?)?$")


def pretty_symbol(sym):
    """Chord symbol 'Bb7/F' -> 'B♭7/F' (only root and bass accidentals change)."""
    m = _SYM_RE.match(sym)
    if not m:
        return sym
    acc = {"b": "♭", "#": "♯", None: ""}
    out = m.group(1) + acc[m.group(2)] + m.group(3).replace("b5", "♭5").replace("#5", "♯5").replace("#9", "♯9").replace("b9", "♭9").replace("#11", "♯11")
    if m.group(4):
        out += "/" + m.group(4) + acc[m.group(5)]
    return out


def parse_tuning(t):
    """Tuning as list of 6 notes low->high, or a space-separated string.
    Returns list of note names. Raises ValueError."""
    if t is None:
        return list(STANDARD_TUNING)
    if isinstance(t, str):
        parts = t.split()
    else:
        parts = [str(x) for x in t]
    if len(parts) != 6:
        raise ValueError("tuning must list 6 notes low string first, e.g. \"D A D G B E\"; got %r" % (t,))
    for p in parts:
        parse_note(p)
    return [_clean(p) for p in parts]


TUNING_NAMES = {"D A D G B E": "Drop D", "D A D G B D": "Double drop D", "D G D G B D": "Open G",
                "D A D G A D": "DADGAD", "D A D F# A D": "Open D", "E A D G B E": "Standard"}


def tuning_label(t):
    notes = " ".join(pretty_acc(x) for x in t)
    name = TUNING_NAMES.get(" ".join(_clean(x) for x in t))
    return "%s (%s)" % (name, notes) if name else notes
