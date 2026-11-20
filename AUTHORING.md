# Authoring guide

This is the contract for anyone adding content to GuitarPractice: chords,
scales, songs, Learn chapters, practice levels. Everything is plain files;
`python3 build.py` validates them and generates the site. If the build passes,
the content is structurally and musically consistent (chord frets really make
the named chord, scale dots really are in the scale, every reference exists,
every session is exactly 45 minutes).

Python 3 standard library only. No packages to install.

---

## 1. Commands

| Command | What it does |
|---|---|
| `python3 build.py` | Validate everything, then build the website into `site/`. |
| `python3 build.py check` | Validate only (including chapter shortcodes); writes nothing. |
| `python3 build.py pdf` | Build, then print every level packet to `out/pdf/<level-id>.pdf` and every song chart to `out/pdf/song-<song-id>.pdf`, copy them into `site/pdf/`, and add "Download PDF" links to level and song pages. **Fails if any session prints on more than one page.** |
| `python3 build.py serve [PORT]` | Serve `site/` at `http://localhost:8000/` (builds first if `site/` is missing). |
| `python3 build.py samples` | List every entry still marked as a sample. |
| `python3 build.py clean` | Delete `site/` and `out/`. |

`site/` and `out/` are build output and are git-ignored. Never commit them.

**PDF browser.** `pdf` uses a headless Chromium-family browser. It looks for, in
order: the `CHROME` environment variable; `/Applications/Google Chrome.app/…`;
`google-chrome`, `google-chrome-stable`, `chromium`, `chromium-browser`,
`microsoft-edge` on `PATH`; then Chromium.app or Microsoft Edge.app on macOS.
If none is found it stops with a message listing what it tried.

**Deploy.** `.github/workflows/pages.yml` runs `python3 build.py pdf` on every
push to `main` (the Ubuntu runner has Chrome) and publishes `site/`, PDFs
included, to GitHub Pages. A validation error or an over-long session fails the
workflow, and nothing is deployed.

---

## 2. File layout

```
build.py                    the build command
engine/                     the build engine (no content here)
  theory.py                   notes, intervals, chord qualities, spelling
  model.py                    JSON loading, schemas, all data validation
  svg.py                      chord box / fretboard / bar-grid SVG renderers
  components.py               HTML snippets shared by pages and shortcodes
  content.py                  chapter front matter + shortcodes
  pages.py                    every generated page, incl. the print packet
  pdf.py                      headless-browser PDF printing
static/style.css            the one stylesheet (screen light/dark + print)
data/
  site.json                   site title and tagline
  chords/*.json               chord shapes
  scales/*.json               scale patterns and whole-neck diagrams
  songs/*.json                song charts (one song per file)
  song-bench.json             songs queued for later ("Next up" on the Songs page)
  levels/*.json               practice levels (one level per file)
content/
  learn/*.html                Learn chapters (front matter + HTML + shortcodes)
  pages/*.html                optional intro text for generated pages (see §8)
.github/workflows/pages.yml GitHub Pages deploy
```

Every `*.json` file in a `data/<kind>/` folder is read, in filename order. A
file may contain **one object or a list of objects** — group chords however you
like (`open-chords.json`, `barre-E-shape.json`, …). Songs and levels are
clearest one per file.

### IDs

Every chord, scale, song and level has an `id`. IDs must be unique within their
kind and use only letters, digits, `_`, `-`, `.` — no spaces and **no `#`**
(it breaks links). Write sharps out: `Fsharp_m_E2`, `D_over_Fsharp`. Flats are
fine as `b`: `Bb_A1`. Song and level ids become file names
(`songs/<id>.html`, `practice/<id>.html`, `pdf/<id>.pdf`), so keep them short
and lowercase-with-dashes for those.

#### Chord id conventions

`<Sym>_<form>`, where `<Sym>` is the chord symbol with `#` written `sharp`
and `/` written `_over_` (flats stay `b`): `Fsharpm`, `E7sharp9`, `Gm7b5`,
`Ammaj7` for Am(maj7), `Emadd9` for Em(add9). `<form>` says what kind of
shape it is; the number is the fret of the root (or lowest fret):

| Form | Meaning | Examples |
|---|---|---|
| `open`, `open2`, `open3` | Open position (alternates numbered) | `C_open`, `G_open2`, `Em7_open3` |
| `<Sym>_over_<Bass>` | Slash chord (open unless suffixed) | `D_over_Fsharp`, `Am_over_Gsharp` |
| `barre_E<f>` / `barre_A<f>` | Movable, root on string 6 / 5 at fret f — barred or not | `G7_barre_E3`, `Cm7b5_barre_A3` |
| `part_E<f>` / `part_A<f>` / `thumb_E<f>` | Economy (partial) version of an E/A-shape | `G_part_E3`, `G_thumb_E3` |
| `s4_<f>` / `s5_<f>` | Other movable shapes rooted on string 4 / 5 | `Fdim7_s4_3`, `Bdim_s5_2` |
| `caged_<Shape><f>` | CAGED C-, G- or D-shape (E/A-shapes use `barre_`) | `C_caged_G5`, `A_caged_C9` |
| `tri123_` / `tri234_` / `tri345_` + `root` / `inv1` / `inv2` | Triad on that string set, in that inversion | `G_tri123_inv1` (G/B) |
| `shell643_<f>` etc. | Shell voicing on the listed strings, root at fret f | `Gmaj7_shell643_3` |
| `dropD`, `ddropD`, `dadgad`, `openG`, `openD` | Alternate tuning (chord sets `tuning`) | `G5_dropD`, `C_openG` |

Library shapes are stored at one representative root: E-shapes mostly at G
(fret 3), A-shapes mostly at C (fret 3), triads at G, modes and pentatonics on
A, major-scale positions in G. Commonly needed pitches also get their own entry
(`F_barre_E1`, `Bm_barre_A2`, `Fsharpm_barre_E2`).

Chord files are grouped by family and numbered to fix the library order:
`01-open-major-minor`, `02-open-colour`, `03-open-slash`, `04-barre-E-shape`,
`05-barre-A-shape`, `06-triads`, `07-caged`, `08-tension`, `09-shells`,
`10-alt-tunings`.

#### Scale id conventions

`<Root>_<scale>_<where>`: `G_major_pos_E` (G major, E-shape CAGED position),
`A_minor_pent_pos1` … `pos5` (boxes), `A_dorian_pos5` (position at fret 5),
`G_major_neck` (whole-neck map), `interval_M3_C` (interval-shape diagrams),
`D_major_dadgad_neck` (alternate tuning).

### Notes, intervals, strings — conventions used everywhere

- **Notes:** a letter A–G plus `b`, `bb`, `#`, `##` (`C`, `F#`, `Bb`). The site
  displays them as ♭/♯ automatically; always type `b`/`#` in data.
- **Interval tokens:** `1 b2 2 #2 b3 3 4 #4 b5 5 #5 b6 6 bb7 b7 7 9 b9 #9 11 #11 13 b13`.
  `R` is accepted for `1`. Notes are spelled from the root with correct letter
  names (B♭ not A♯ in F major; `bb7` of C is B𝄫).
- **Per-string lists of six** (`frets`, `fingers`, `tuning`) are always written
  **low string first**: low E, A, D, G, B, high E.
- **String numbers** (in `barre` and scale `dots`) use guitar numbering:
  **6 = low E … 1 = high E.**
- **Frets are absolute fret numbers** as you'd say them on the guitar, never
  relative to the diagram's top.

These two orderings (lists low→high; string numbers 6→1) are the most common
source of mistakes. Validation catches almost all of them because the notes
come out wrong.

### Samples

Entries with `"sample": true` (and chapter front matter `sample: true`) show a
SAMPLE badge and are listed by `python3 build.py samples`. All sample content
has been replaced by real content (the former sample chords keep their ids,
e.g. `C_open`, `G_barre_E3`, `D_over_Fsharp`); `samples` should print nothing.

---

## 3. Chords — `data/chords/*.json`

```json
{
  "id": "C_open",
  "name": "C",
  "root": "C",
  "quality": "maj",
  "frets": "x32010",
  "fingers": "x32010",
  "tags": ["open"]
}
```

| Field | Req. | Meaning |
|---|---|---|
| `id` | yes | Unique id (see IDs). |
| `name` | yes | Chord symbol shown on the page: `C`, `Am7`, `D/F#`, `Bbmaj7`. Displayed with ♭/♯. |
| `root` | yes | Root note, e.g. `C`, `F#`, `Bb`. |
| `quality` | one of these two | A built-in quality name (table below). Supplies the formula and the library group. |
| `formula` | " | Interval tokens, `"1 3 5 b7"` or `["1","3","5","b7"]`. If `quality` is also given, the two must contain the same intervals. Required if `quality` isn't built in. |
| `omits` | no | Intervals of the formula deliberately absent from this voicing, e.g. `"5"` or `"5 9"`. Each must be in the formula. |
| `bass` | no | Slash-chord bass note: `D/F#` → `"bass": "F#"`. The lowest sounding string must be this note. May be outside the chord (`C/Bb`). |
| `frets` | yes | Six values low E → high E. `x` = muted, `0` = open, `N` = fret N (absolute). Three spellings: `"x32010"` (only when every fret is 0–9), `"x 3 2 0 1 0"` / `"x,3,2,0,1,0"`, or a list `["x", 3, 2, 0, 1, 0]`. **Use the list or spaced form for any fret ≥ 10.** |
| `fingers` | no (recommended) | Six values like `frets`: `1` index, `2` middle, `3` ring, `4` little, `T` thumb; `0`/`x`/`-` for open or muted strings. Every fretted string needs a finger and no open/muted string may have one. |
| `barre` | no | Usually leave it out — barres are **inferred from fingers** (same finger on the same fret on 2+ strings, with nothing lower fretted between them). Give it explicitly as `{"fret": 3, "from": 6, "to": 1, "finger": "1"}` (string numbers 6–1) or a list of those; `"barre": false` disables inference. |
| `base_fret` | no | Fret shown at the top of the diagram. Default: 1 (diagram shows the nut) if the highest fret is ≤ 4, else the lowest fretted fret (diagram shows "5fr"). |
| `tuning` | no | Six notes low → high, `"D A D G B E"` or a list. Default standard E A D G B E. A non-standard tuning is shown on the chord's library card (chord boxes don't print string names, so say the tuning in surrounding text too). |
| `tags` | no | Free labels shown as pills: `open`, `barre`, `E-shape`, `A-shape`, `slash`, `movable`, … |
| `group` | no | Override the library heading (default comes from `quality`; "Other" if unknown). Extra standard headings: `Slash chords`, `Triads & inversions`, `Shell voicings`, `Alternate tunings`. |
| `notes` | no | One or two sentences shown in the library (supports `**bold**`, `*italic*`). |
| `sample` | no | `true` for sample content. |

### Built-in qualities

| `quality` | formula | library group |
|---|---|---|
| `maj` | 1 3 5 | Major |
| `m` | 1 b3 5 | Minor |
| `7` | 1 3 5 b7 | Dominant 7th |
| `maj7` | 1 3 5 7 | Major 7th |
| `m7` | 1 b3 5 b7 | Minor 7th |
| `mmaj7` | 1 b3 5 7 | Minor 7th |
| `6` / `m6` / `6/9` | 1 3 5 6 / 1 b3 5 6 / 1 3 5 6 9 | Sixth |
| `sus2` / `sus4` / `7sus4` | 1 2 5 / 1 4 5 / 1 4 5 b7 | Suspended |
| `add9` / `madd9` | 1 3 5 9 / 1 b3 5 9 | Added tone |
| `9` / `maj9` / `m9` / `7#9` / `13` | 1 3 5 b7 9 / 1 3 5 7 9 / 1 b3 5 b7 9 / 1 3 5 b7 #9 / 1 3 5 b7 9 13 | Extended |
| `dim` / `dim7` / `m7b5` / `aug` | 1 b3 b5 / 1 b3 b5 bb7 / 1 b3 b5 b7 / 1 3 #5 | Diminished & augmented |
| `5` | 1 5 | Power chords |

Add a new quality by adding a line to `QUALITIES` in `engine/theory.py`, or
just give `quality` + `formula` in the entry (it goes in the "Other" group
unless you set `group`).

### What chord validation checks

1. The **set of pitch classes** sounding from the frets (in the chord's tuning)
   equals exactly root + formula − `omits` (+ `bass`). Octaves and doublings
   don't matter; a missing or extra note is an error. For 9/11/13 chords you
   will usually need `omits` (commonly `5`, sometimes `1` or `11`).
2. **Bass:** the lowest sounding string must be `bass` if given, otherwise the
   root (unless `"1"` is in `omits`). So open C played with the low E ringing
   fails — either mute it (`x32010`) or call it `C/E` with `"bass": "E"`.
3. Fingers agree with frets (see table); barres cover only strings fretted at
   or above the barre fret and both ends sit exactly on the barre fret.
4. All fretted notes fit one diagram (≤ 6 frets from `base_fret`), and no fret
   is below `base_fret`.
5. `formula` agrees with `quality`; `omits` are in the formula; notes,
   intervals, tuning are well-formed; no unknown fields (typos are caught,
   with a "did you mean" hint).

### How it is drawn

Chord box: **low E on the left, nut (thick bar) at the top**, or "Nfr" on the
left when `base_fret` > 1. `x`/`o` above the strings. Fingers in the dots.
**Roots are squares** (an open root is a hollow square above the nut; a root
under a barre is a small square window in the bar). Under the strings: interval
labels (`R 3 5 ♭7`) by default, or note names (shortcode option).

---

## 4. Scales and fretboard diagrams — `data/scales/*.json`

Two layouts share one schema.

**Pattern** — you list the dots (a box/position, a fingering):

```json
{
  "id": "A_minor_pent_pos1",
  "name": "A minor pentatonic — position 1",
  "scale": "Minor pentatonic",
  "root": "A",
  "formula": "1 b3 4 5 b7",
  "position": "Position 1 (root on string 6, fret 5)",
  "frets": [4, 8],
  "dots": {"6": [5, 8], "5": [5, 7], "4": [5, 7], "3": [5, 7], "2": [5, 8], "1": [5, 8]},
  "labels": "intervals"
}
```

**Neck** — every note of root + formula inside a fret window is drawn for you:

```json
{
  "id": "A_minor_pent_neck",
  "name": "A minor pentatonic — whole neck",
  "scale": "Minor pentatonic",
  "root": "A",
  "formula": "1 b3 4 5 b7",
  "layout": "neck",
  "frets": [0, 15],
  "labels": "intervals"
}
```

| Field | Req. | Meaning |
|---|---|---|
| `id`, `name` | yes | As for chords. `name` is the diagram heading. |
| `root`, `formula` | yes | E.g. `"A"`, `"1 b3 4 5 b7"`. A single-note formula `"1"` shows every occurrence of one note; `"1 3 5"` shows a triad. |
| `scale` | no | Family name for grouping/meta ("Major", "Minor pentatonic"). |
| `layout` | no | `"pattern"` (default; needs `dots`) or `"neck"` (computes dots; must not have `dots`). |
| `frets` | no | Window `[first, last]`, 0–24. `0` as first shows open strings left of the nut. Neck default `[0, 15]`; pattern default is the span of the dots (at least 4 frets). |
| `dots` | pattern only | Object: **string number** `"6"` (low E) … `"1"` (high E) → list of fret numbers. Strings with no notes can be left out. |
| `labels` | no | Text inside dots: `"intervals"` (default; R, ♭3 …), `"notes"` (A, C …), `"none"`. |
| `position`, `description` | no | Shown on the scales page. |
| `tuning` | no | As for chords. |
| `sample` | no | |

Roots are found automatically (filled **squares**; other notes are rings), so
there is no "which dots are roots" field — it can't get out of sync.

**Validation:** every dot's note must be in root + formula (the error names the
string, fret and the note it actually is), dots must be inside the window, and
string keys must be `"1"`–`"6"`.

**Drawing:** horizontal neck, **high E on top, low E at the bottom** (like tab),
nut on the left, fret numbers underneath (inlay frets bold), string names at
the left. Wide diagrams scroll sideways on a phone and scale to fit in print.

---

## 5. Songs — `data/songs/<id>.json`

**No lyrics, ever** — charts are chords and structure only. There is no field
for lyrics and unknown fields are rejected.

```json
{
  "id": "blues-in-a",
  "title": "Twelve-Bar Shuffle in A",
  "artist": "Traditional",
  "key": "A",
  "capo": 0,
  "tempo": 84,
  "feel": "Shuffle (swung eighths)",
  "time": "4/4",
  "level": 1,
  "chords": {"A7": "A7_open", "D7": "D7_open", "E7": "E7_open"},
  "form": ["Intro", "Chorus", "Ending"],
  "sections": [
    {"name": "Intro", "bars": "E7 | %"},
    {"name": "Chorus", "bars": "A7 | D7 | A7 | % | D7 | % | A7 | % | E7 | D7 | A7 | E7", "repeat": 3,
     "note": "Quick-change: bar 2 goes to the IV."},
    {"name": "Ending", "bars": "A7 . . E7 | A7"}
  ],
  "why": "Why this song is in the program.",
  "hard_change": "The change that will trip you up, and how to practise it.",
  "tips": ["Optional extra bullet points."]
}
```

| Field | Req. | Meaning |
|---|---|---|
| `id`, `title`, `artist` | yes | |
| `key` | yes | The key you hear (as on the recording). |
| `capo` | no | Capo fret (default 0). Chord shapes in `chords` are what you **finger** with the capo on. |
| `tuning` | no | As for chords. Every chord used must declare the same tuning. |
| `tempo` | no | BPM (shown as ♩ = N). |
| `feel` | no | "Straight eighths", "Shuffle", "Ballad"… |
| `time` | no | `"4/4"` (default), `"3/4"`, `"6/8"`… The top number = beat slashes per bar. |
| `level` | no | Level number this song belongs to (informational). |
| `chords` | yes | Map **symbol used in the bars → chord id**. The grid shows the symbol; the diagram row shows the chord. One symbol can map to any voicing (e.g. `"G": "G_barre_E3"`). |
| `sections` | yes | Ordered list; each `{name, bars, repeat?, note?}`. |
| `form` | no | Play order by section name (names must exist). |
| `why`, `hard_change` | yes | Teaching notes. `**bold**` / `*italic*` allowed. |
| `tips` | no | List of strings. |
| `sample` | no | |
| `order` | no | Position within its level on the Songs page (1 = easiest). Songs without it sort last. |
| `role` | no | `"core"` (a song the level is built around) or `"alternate"`. Shown as a badge. |
| `mix` | no | `true` = from the owner's own mixes; shown as a "From your mixes" badge. |
| `confidence` | no | `"high"`, `"medium"` or `"low"`: how well the chart is sourced. Informational (not displayed); give a `caveat` for medium/low. |
| `caveat` | no | One honest line shown in italics under the teaching notes, e.g. "Voicings vary between transcriptions — trust your ear and your teacher's version." |
| `theory` | no | A short roman-numeral note ("I–IV–V in A; the bridge is ♭III–♭VII–IV–I"). |
| `steps` | no | List of strings: a suggested way to learn the song, printed as a numbered list ("Changes alone, slowly", "With the rhythm at 70%", "With the record"). |
| `sources` | no | List of URLs. Shown small at the bottom of the web page only — **not printed**. |
| `detune` | no | Semitones the *whole guitar* is tuned down (1–3), e.g. `2` = D G C F A D. The chords stay ordinary standard-tuning shapes (validated and named as shapes, like with a capo); the page says "Tune down a whole step (D G C F A D); shapes as written". Set `key` to the key you hear. For other tunings (drop D, open G…) use `tuning` instead. |
| `alt_voicings` | no | Extra chord rows next to the main one, each `{"label": "Riff version B", "chords": ["C_spread542_3", …], "note": "optional"}`: colour chords, a second way to play a riff, a simplification. The chords need not appear in the bars, and must be in the song's tuning. |

### Bar syntax (`bars`)

Write bars separated by `|` (or give a JSON list, one string per bar). 4 bars
per row are drawn.

- `A7` — one chord for the whole bar.
- `C G` — two tokens split the bar in halves; `C . . G` — four slots: 3 beats
  of C, 1 of G. A token's position in the bar is where the chord starts; `.`
  means "keep the previous chord for this slot".
- `%` — repeat the previous bar (must be alone in its bar, not bar 1).
- `N.C.` or `NC` — no chord.
- `C G Am` — three tokens split the bar in thirds; with `C . G Am` (four slots)
  you choose the beats. Use a section `note` when the rhythm is approximate.
- `[7/8]` or `[11/8=3+3+3+2]` as the **first token of a bar** — a time
  signature change. It applies to that bar and the rest of the section (the
  next section starts again in the song's `time`); write `[4/4] D` to switch
  back. It is drawn stacked at the left of the bar. With `=a+b+…` (eighth-note
  groups, which must add up to the top number) the bar shows one slash per
  group, spaced by length, with the group lengths underlined; without it, one
  slash per beat. Slots split the bar evenly, so for 11/8 use 11 slots:
  `[11/8=3+3+3+2] F . . C . . G . . D .` puts one chord on each group.
  `[1/4] Am | Asus4 | Am | Asus2` draws one-beat boxes (useful for a figure of
  four one-beat chords that would be unreadable in one box; say so in a note).
- Every other token must be a key of `chords`.

`"repeat": 3` draws repeat barlines around the section with "×3". Validation
warns about symbols in `chords` that no bar uses. There are no 1st/2nd endings:
write the second ending as its own section ("Bridge, 2nd time").

### The song page and its print

The page shows: title with Level / Core-or-Alternate / From-your-mixes badges;
the meta line (key, capo, tuning or detune, tempo, time, feel); the chord row
plus any `alt_voicings` rows; the form; the section grids (two columns on wide
screens and in print); then why / hard change / theory / steps / tips / caveat
(two columns in print) and, on screen only, the sources. Every chart should
print on **one Letter page** — `build.py pdf` warns otherwise. If one doesn't
fit: merge identical sections ("Intro / Verse"), use `%` and `repeat`, keep
notes to one line, and keep the chord row to about ten shapes.

### Songs page and the bench — `data/song-bench.json`

The Songs index groups songs by `level` (sorted by `order`), with badges.
Songs queued for later go in `data/song-bench.json` (optional) and are listed
under "Next up" without charts:

```json
[{"title": "Wild World", "artist": "Cat Stevens", "level": "Level 1/4", "mix": false,
  "teaches": "What it would teach, and why it is benched."}]
```

`title`, `artist`, `teaches` are required; `level` (free text) and `mix` are optional.

### Song voicings

Song-specific shapes the chord library lacks live in
`data/chords/song-voicings.json` (standard tuning) and
`data/chords/song-voicings-alt-tunings.json` (drop D, double drop D, open G —
each chord declares its `tuning`, which must match the song's). Before adding
one, look for an identical library chord (same name and frets) and use its id.
A chord with open strings drawn at a higher fret ("10fr") states its
`base_fret` explicitly, which acknowledges the open strings and silences the
warning.

---

## 6. Practice levels — `data/levels/<id>.json`

A level = one printable packet. It must have **exactly four sessions named
A, B, C, D, in that order, each exactly 45 minutes** (sum of block minutes).

```json
{
  "id": "level-02",
  "number": 2,
  "title": "Minor chords and the I–vi–IV–V",
  "summary": "One paragraph for the roadmap and the overview page.",
  "goals": ["…", "…"],
  "exit_criteria": ["30 clean G ↔ Em changes in a minute.", "…"],
  "drills": [
    {"id": "one-minute", "title": "One-minute changes",
     "instructions": "Set a one-minute timer…", "chords": ["G_open", "Em_open"],
     "metronome": {"start": 60, "target": 80}}
  ],
  "benchmarks": [{"name": "G ↔ Em changes in 1 min", "target": "30"}],
  "chords": [], "scales": [], "songs": [],
  "weeks": 4,
  "sessions": [
    {"name": "A", "title": "Short title", "focus": "One-line focus (optional)",
     "blocks": [
       {"minutes": 5, "title": "Warm-up", "instructions": "…"},
       {"minutes": 10, "title": "Changes", "instructions": "…",
        "chords": ["G_open", "Em_open"], "drill": "one-minute",
        "metronome": {"start": 60, "target": 80}, "record": "Changes in 1 minute"}
     ]},
    {"name": "B", "…": "…"}, {"name": "C", "…": "…"}, {"name": "D", "…": "…"}
  ]
}
```

| Field | Req. | Meaning |
|---|---|---|
| `id` | yes | Becomes `practice/<id>.html` and `pdf/<id>.pdf`. Use `level-01`, `level-02`… |
| `number` | yes | Unique; the roadmap is sorted by it. |
| `title`, `summary` | yes | |
| `goals` | yes | List of strings (overview page). |
| `exit_criteria` | yes | "Ready to move on when…" — 4–6 checkable items, printed as a checklist (on the week-plan page if the level has one, otherwise on the overview and the log page). |
| `status` | no | One line shown in a bar under the title, e.g. "First draft — re-tune from the Level 2 check-in". |
| `reading` | no | Learn chapters to read that month, in order: a chapter slug (`"changing-chords"`) or `{"chapter": slug, "note": "week 1 — …"}`. Validated against the chapters; printed as "Ch. 7 Changing chords — note" with a tick box. |
| `song_plan` | no | When to switch from a core song to an alternate (printed on the week-plan page). |
| `week_plan` | no | List of weeks (row 1 = week 1), each `{"chords", "fretboard", "song", "tempo"}` (strings; `tempo` optional; `**bold**` allowed). Printed as the week-by-week table. Sessions say "this week's pair / scale / section" and the table supplies it, so the same four pages stay fresh for a month. At most `weeks` rows; extra log weeks get a "repeat the last row" note. |
| `chord_groups` | no | `[{"label", "chords", "note"?}]`: the curated chord reference, printed group by group (4 large diagrams per row). Any chord a drill or block uses that is not in a group is added under "Also in the sessions". |
| `stuck`, `skip_ahead` | no | The rules for "still not there after 6 weeks" and "too easy", printed under the exit checklist. |
| `checkin` | no | Extra level-specific questions for the check-in sheet. |
| `drills` | no | Reusable exercises `{id, title, instructions, chords?, scales?, metronome?}`; printed on their own Drills page(s); blocks point at them with `"drill": "<id>"`. Drill ids are local to the level. A drill whose id is one of Learn chapter 7's named drills (`one-minute`, `air-shape`, `place-lift`, `slow-motion`, `anchor`, `bass-first`, `leave-early`, `change-loop`, `tempo-ladder`, `eyes-closed`, `barre-pulse`, `random-pairs`, `song-loop`) is marked "(Ch. 7)"; keep its title the chapter's name. |
| `benchmarks` | no | `{name, target}` rows of the log page's benchmark table and the check-in sheet (target is text: `"30"`, `"84 bpm"`). Session D measures them. |
| `chords`, `scales`, `songs` | no | Extra ids to include on the reference pages. `songs` is also the overview's song list (with Core/Alternate from each song's `role`). |
| `weeks` | no | Rows in the practice log, benchmark columns and the "Week 1 2 3 …" strip on each session page (default 4; the six levels use 6 so a stuck level has room). |
| `sessions` | yes | Exactly A, B, C, D. |

Session: `name` (A–D), `title`, optional `focus`, `blocks`.

Block:

| Field | Req. | Meaning |
|---|---|---|
| `minutes` | yes | Positive whole number. Blocks must total 45. |
| `title` | yes | |
| `instructions` | yes | A string, or a list of strings (one paragraph each). `**bold**`/`*italic*` allowed. |
| `chords`, `scales`, `songs` | no | Ids; listed by name under the block and pulled into the reference pages. |
| `drill` | no | Id of one of this level's drills. |
| `metronome` | no | `{"start": 60, "target": 80}` (either key optional) or just `80` (target). Prints "Metronome: start 60 → target 80 · today ____ bpm". |
| `record` | no | Label for a write-in blank, e.g. `"Changes in 1 minute"`. |

**Reference pages** contain, de-duplicated and in this order: the level's own
`chord_groups`, `chords`/`scales`/`songs` lists, then everything the drills and
blocks reference. Song chords are **not** added to the chord pages (every song
chart in the packet prints its own chord row) — put the hard ones in a
`chord_group` so they are drilled from the reference page.

### The printed packet (and on-screen page)

1. Overview — level, `status`, summary, a fixed "how to use this packet" box
   (the four day types from the session titles, circle the week, tick, log),
   goals, reading list, songs.
2. The month, week by week (if `week_plan`, `stuck` or `skip_ahead` is set) —
   week-plan table, `song_plan`, exit checklist, stuck / too-easy rules.
3. Drills — every drill's full instructions.
4. Session A, B, C, D — **one Letter page each**, checkbox + clock times per
   block, a "Week 1 2 3 4 …" strip to circle, Date, metronome/record blanks,
   two Notes lines.
5. Chord shapes — grouped (`chord_groups`), or 9 per page.
6. Scales & fretboard (if any).
7. One page per song chart (the level kicker is hidden on song pages so the
   chart fits as it does on its own).
8. Practice log — weeks × sessions grid (tick, date, minutes), benchmark table.
9. Check-in sheet — finished / weeks / sessions / exit boxes, final benchmark
   numbers, chords that still feel bad, songs loved and disliked, real session
   length, more of / less of, plus the level's `checkin` questions. It is what
   the next level is re-tuned from.

**Fitting a session on one page.** Plan on at most ~6–7 blocks and ~1,200
characters of instructions per session. `build.py` warns above 8 blocks or
~1,500 characters; `build.py pdf` prints each level's sessions on their own and
**fails** if any session takes more than one page, naming the session. Shorten
instructions (move detail into a drill, which prints on the Drills page)
rather than fighting the layout. Song charts should also fit one page (`pdf`
warns if not): keep sections, notes and tips short; use `%` and `repeat`.

---

## 7. Learn chapters — `content/learn/*.html`

```html
---
title: How chords are built
order: 20
summary: Stacking thirds; why C major is C–E–G.
level: 1
---
<p>Plain HTML body. Use h2/h3 for headings (h1 is the title).</p>

{{chord: C_open}}

<p>More text…</p>
```

- **File name** → URL: `20-how-chords-are-built.html` becomes
  `learn/how-chords-are-built.html` (a leading number and `-`/`_` is stripped;
  use it to keep files sorted). `slug:` in the front matter overrides it.
- **Front matter** (between the first two `---` lines, `key: value`, `#`
  comments allowed): `title` (required), `order` (required number; chapters are
  listed and prev/next-linked in this order), `summary` (one line for the index),
  `level` (a number → "Level 1" badge, or any short text like `Reference`),
  `sample` (`true`/`false`), `slug`. Unknown keys are errors.
- The body is trusted HTML: `<p>`, `<h2>`, `<h3>`, `<ul>`, `<ol>`, `<table>`,
  `<strong>`, `<em>`, `<code>`… Don't use `<h1>`; don't add `<style>`/`<script>`.
  Type ♭/♯ directly or use `b`/`#`.
- **Tables** go inside `<div class="table-wrap">…</div>` so a wide table
  scrolls in its own box on a phone; add `wide` (`class="table-wrap wide"`)
  for tables with many columns — it gives the table a minimum width instead
  of squashing it.
- **Self-check questions** use `<details><summary>Question</summary><p>Answer</p></details>`;
  answers stay hidden until tapped.
- Chapter convention: end with a `{{try: What to take to the guitar}}` box
  (3–5 bullets), then `<h2>Check yourself</h2>` and 3–4 `<details>` questions.

### Shortcodes

Put block shortcodes **on their own line, between paragraphs** (a block
shortcode wrapped alone in `<p>…</p>` is also unwrapped automatically). Spaces
inside `{{ }}` are optional. Errors report `file:line`.

| Shortcode | Renders |
|---|---|
| `{{chord: C_open}}` | One chord box with name and formula. |
| `{{chord: C_open \| notes}}` | Options after `\|`: `intervals` (default under-string labels), `notes`, `fingers` (finger numbers under the strings instead of in dots), `none`, and `large`. Also as `labels=notes size=large`. |
| `{{chords: C_open, Am_open, G_open}}` | A row of chord boxes (same options after `\|`). |
| `{{scale: A_minor_pent_pos1}}` | A scale/neck diagram from `data/scales`. |
| `{{neck: root=C formula="1" frets=0-12 labels=notes title="Every C"}}` | An ad-hoc fretboard: every note of root+formula in the window. Options: `root`, `formula` (default `"1"`), or `notes="C E G"` instead of both (first note = root); `frets=A-B` (default `0-15`); `labels=notes\|intervals\|none` (default `notes`); `title`. Quote values containing spaces. |
| `{{grid: C \| Am \| F \| G}}` | An ad-hoc bar grid using the song bar syntax (symbols aren't checked against chord ids). Options after `;`: `{{grid: C \| G ; repeat=2 beats=3 title="Verse"}}`. |
| `{{song: in-my-life}}` | A song card: title link, meta, chord row, every section grid. |
| `{{try}} … {{/try}}` | Callout "Try it on the guitar". |
| `{{why}} … {{/why}}` | Callout "Why it's named that". |
| `{{tip}} … {{/tip}}` | Callout "Tip". Any callout takes a custom title: `{{try: Find every C}}`. Put HTML (`<p>…</p>`) inside; callouts can't nest. |
| `{{link:song:ID}}` | Inline link. Kinds: `learn:<slug>`, `song:<id>`, `level:<id>`, `chord:<id>` (its card in the chord library), `scale:<id>`, `page:home\|learn\|chords\|scales\|songs\|practice`. Custom text: `{{link:chord:Cmaj7_open \| the Cmaj7 shape}}`. |

Write `\{{…}}` to print a shortcode literally. Inside a shortcode, `|` is the
option separator (for `grid`, the bar separator; options go after `;`).

`content/learn/010-start-here.html` and `020-the-raw-material.html` between them use the chord, chords, scale, neck and grid shortcodes and every callout.

---

## 8. Site text

- `data/site.json`: `{"title": "...", "tagline": "..."}`. No personal details.
- Optional intro fragments (HTML + shortcodes, no front matter), placed at the
  top of generated pages: `content/pages/home.html`, `learn.html`,
  `chords.html`, `scales.html`, `songs.html`, `practice.html`. The home page
  also lists the level roadmap automatically.

---

## 9. Reading build errors

The build never stops at the first problem; it lists every error and exits
non-zero. Each line starts with where the problem is:

```
ERROR data/chords/open.json [chord 'C_open']: frets x 3 2 0 2 0 sound {C C#/Db E G}
      but root C + formula '1 3 5' needs {C E G}: C#/Db is not in the chord (from string 2 (B) fret 2)
ERROR data/chords/open.json [chord 'G_open']: lowest sounding note is B (string 5 (A) fret 2) but the
      bass should be G. Mute that string, or if the inversion is intended name it as a slash chord with "bass": "B"
ERROR data/scales/pent.json [scale 'A_minor_pent_pos1']: dot on string 5 (A) fret 6 is D#/Eb, which is
      not in A Minor pentatonic (A C D E G)
ERROR data/songs/x.json [song 'x'] section 'Verse': bar 3 uses chord symbol 'D9' which is not a key in the
      song's "chords" map (A7, D7, E7)
ERROR data/levels/level-02.json [level 'level-02'] session B: blocks add up to 50 minutes; a session must be
      exactly 45 (5 + 10 + 15 + 15 + 5)
ERROR data/levels/level-02.json [level 'level-02'] session A block #2 'Changes': unknown chord id 'E7_opn'
      — did you mean 'E7_open'?
ERROR content/learn/20-chords.html:14: unknown shortcode '{{chrd}}' (known: …)
ERROR data/songs/x.json [song 'x']: unknown field 'lyrics' (allowed: …)
```

How to act on the common ones:

- **"frets … sound {…} but … needs {…}"** — the message lists each extra note
  with the string and fret it comes from, and each missing note with its
  interval. Usually a wrong fret, a list written high-to-low, or a string that
  should be muted. If the voicing really drops a note, add it to `omits`.
- **"lowest sounding note is …"** — mute the low string(s) or declare `bass`.
- **"is fretted at N but has no finger"** — `fingers` doesn't line up with
  `frets` (often a missing `x`/`0`).
- **"fret N is below base_fret"** — frets are absolute; don't subtract the base.
- An entry with errors is skipped, and references to it are not reported again
  (fix the entry's own error first).

Warnings (`warning: …`) don't fail the build: long sessions, unused song
chord symbols, non-standard chord groups.

---

## 10. Recipes

**Add a chord.** Append an object to any `data/chords/*.json` (or a new file).
Fill `id`, `name`, `root`, `quality`, `frets`, `fingers`, `tags`. Run
`python3 build.py`. Look at it on the Chords page.

**Add a scale / position.** Add an object to `data/scales/*.json`. For a box,
list `dots` per string number; for "show all of these notes", use
`"layout": "neck"`. Build.

**Add a song.** Create `data/songs/<id>.json`. Make sure every chord it needs
exists in `data/chords/` (add shapes first). Map the symbols you write in the
bars to chord ids in `chords`. No lyrics. Build, then check the song page fits
one page with `python3 build.py pdf`.

**Add a chapter.** Create `content/learn/NN-slug.html` with front matter;
choose `order` to slot it between existing chapters (use gaps of 10). Build.

**Add a level.** Copy `data/levels/level-02.json` (hand-written) to
`data/levels/level-NN.json`, change `id`, `number`, text, sessions. (Levels
3–6 were generated once from a script and are now ordinary files: edit them
directly.) Keep every
session at 45 minutes. Run `python3 build.py`, then `python3 build.py pdf` and
open `out/pdf/level-NN.pdf` to confirm each session is one page.

---

## 11. Changing the engine (future evolution)

- New chord quality → `QUALITIES` in `engine/theory.py` (and `GROUP_ORDER` for
  a new library heading).
- New data field → add it to the schema in `SCHEMAS` (`engine/model.py`),
  normalise it in the matching `normalize_*` function, render it in
  `engine/pages.py`, and document it here. Unknown fields are rejected, so a
  field that isn't in `SCHEMAS` can't be used by authors.
- Level `reading` slugs are checked in `build.py` `validate()`, because chapters
  load after the data files.
- New shortcode → `BLOCK_CODES`/`INLINE_CODES` and `Renderer.block_code` /
  `inline_code` in `engine/content.py`.
- Diagram look → `engine/svg.py`. SVG colours are CSS classes (`.ink`, `.stk`,
  `.bgf`, `.mut`, `.mstk`, `.faint`) styled in `static/style.css`, so light,
  dark and print all follow the page palette. Never hard-code a colour that
  should change in dark mode, and never distinguish things by colour alone
  (roots are squares).
- Print layout → `@media print` in `static/style.css`; each `.sheet` is one
  printed page (`break-after: page`). After any change run
  `python3 build.py pdf` and look at the PDF.
- Constraints: Python standard library only; no JS frameworks, CDNs or web
  fonts (system font stacks); all links relative (the site must work from
  `file://` and under `https://USER.github.io/REPO/`).
