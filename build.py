#!/usr/bin/env python3
"""GuitarPractice build.

    python3 build.py            validate everything, then build the site into site/
    python3 build.py check      validate only (no output written)
    python3 build.py pdf        build, then print every level packet and song chart
                                to out/pdf/*.pdf (and copy them into site/pdf/)
    python3 build.py serve [PORT]   serve site/ at http://localhost:8000/
    python3 build.py samples    list entries still marked "sample": true
    python3 build.py clean      delete site/ and out/

Python 3 standard library only. See AUTHORING.md.
"""

import functools
import http.server
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from engine import content, model, pdf  # noqa: E402
from engine.pages import SiteWriter, layout  # noqa: E402

SITE = os.path.join(ROOT, "site")
OUT = os.path.join(ROOT, "out")


def validate():
    proj = model.Project(ROOT)
    chapters = content.load_chapters(ROOT, proj.rep)
    slugs = [c["slug"] for c in chapters]
    for lv in proj.levels.values():  # a level's reading list names Learn chapters by slug
        for r in lv["reading"]:
            if r["chapter"] not in slugs:
                proj.rep.error(lv["where"], "reading: no Learn chapter with slug '%s' (have: %s)"
                               % (r["chapter"], ", ".join(slugs)))
    renderer = content.Renderer(proj, chapters)
    return proj, chapters, renderer


def report(proj, stage):
    rep = proj.rep
    for w in rep.warnings:
        print("warning: " + w)
    rep.warnings = []
    if rep.errors:
        print("\n%d error(s) found during %s:\n" % (len(rep.errors), stage), file=sys.stderr)
        for e in rep.errors:
            print("  ERROR " + e, file=sys.stderr)
        print("\nBuild failed. Nothing is published until these are fixed.", file=sys.stderr)
        sys.exit(1)


def build(pdf_links=False):
    proj, chapters, renderer = validate()
    report(proj, "validation")
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    w = SiteWriter(ROOT, proj, chapters, renderer, pdf_links=pdf_links)
    w.build_all()  # shortcode errors are found while rendering
    report(proj, "rendering content")
    shutil.copy(os.path.join(ROOT, "static", "style.css"), os.path.join(SITE, "style.css"))
    open(os.path.join(SITE, ".nojekyll"), "w").close()
    print("OK  %d chords, %d scales, %d songs, %d levels, %d chapters -> %d pages in site/"
          % (len(proj.chords), len(proj.scales), len(proj.songs), len(proj.levels), len(chapters), len(w.written)))
    samples = proj.samples() + ["chapter %s (%s)" % (c["slug"], c["file"]) for c in chapters if c["sample"]]
    if samples:
        kinds = {}
        for s in samples:
            kinds[s.split()[0]] = kinds.get(s.split()[0], 0) + 1
        print("note: SAMPLE entries still present (%s); `python3 build.py samples` lists them"
              % ", ".join("%d %s%s" % (n, k, "s" if n > 1 else "") for k, n in kinds.items()))
    return proj, w


def build_pdfs():
    try:
        browser = pdf.find_browser()
    except pdf.PdfError as e:
        print("ERROR " + str(e), file=sys.stderr)
        sys.exit(1)
    proj, w = build(pdf_links=True)
    print("printing with %s" % browser)
    out_dir = os.path.join(OUT, "pdf")
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    errors = []
    try:
        for lv in proj.levels.values():
            target = os.path.join(out_dir, lv["id"] + ".pdf")
            pdf.print_pdf(browser, os.path.join(SITE, "practice", lv["id"] + ".html"), target)
            print("  %s  (%d pages)" % (os.path.relpath(target, ROOT), pdf.page_count(target)))
            errors += check_sessions(browser, w, lv)
        for s in proj.songs.values():
            target = os.path.join(out_dir, "song-%s.pdf" % s["id"])
            pdf.print_pdf(browser, os.path.join(SITE, "songs", s["id"] + ".html"), target)
            n = pdf.page_count(target)
            print("  %s  (%d page%s)" % (os.path.relpath(target, ROOT), n, "" if n == 1 else "s"))
            if n != 1:
                print("warning: song chart '%s' prints on %d pages; aim for one" % (s["id"], n))
    except pdf.PdfError as e:
        print("ERROR " + str(e), file=sys.stderr)
        sys.exit(1)
    if errors:
        for e in errors:
            print("  ERROR " + e, file=sys.stderr)
        print("\nPDF check failed: shorten the text of the sessions above.", file=sys.stderr)
        sys.exit(1)
    shutil.copytree(out_dir, os.path.join(SITE, "pdf"))
    print("OK  PDFs in out/pdf/ and copied to site/pdf/")


def check_sessions(browser, w, lv):
    """Every session must print on exactly one Letter page."""
    tmp_html = os.path.join(SITE, "practice", ".check-%s.html" % lv["id"])
    tmp_pdf = os.path.join(OUT, "check", lv["id"] + "-sessions.pdf")
    errors = []

    def pages_for(sessions_body):
        with open(tmp_html, "w", encoding="utf-8") as fh:
            fh.write(layout(w.site, "check", sessions_body, 1, "practice", "wide packet"))
        pdf.print_pdf(browser, tmp_html, tmp_pdf)
        return pdf.page_count(tmp_pdf)

    try:
        n = pages_for(w.level_body(lv, sessions_only=True))
        if n != len(lv["sessions"]):
            kicker = "Level %d" % lv["number"]
            for s in lv["sessions"]:
                k = pages_for(w.session_sheet(lv, s, kicker))
                if k != 1:
                    errors.append("%s session %s prints on %d pages (must be 1)" % (lv["where"], s["name"], k))
            if not errors:
                errors.append("%s: sessions print on %d pages instead of %d" % (lv["where"], n, len(lv["sessions"])))
    finally:
        if os.path.exists(tmp_html):
            os.remove(tmp_html)
        shutil.rmtree(os.path.join(OUT, "check"), ignore_errors=True)
    return errors


def serve(port):
    if not os.path.isdir(SITE):
        build()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=SITE)
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print("Serving site/ at http://localhost:%d/  (Ctrl+C to stop)" % port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "build"
    if cmd == "build":
        build()
    elif cmd == "check":
        proj, chapters, renderer = validate()
        # render content in memory too, so shortcode errors are caught
        for c in chapters:
            renderer.render(c["body"], c["file"], 1, c["line_offset"])
        report(proj, "validation")
        print("OK  everything validates")
    elif cmd == "samples":
        proj, chapters, _ = validate()
        for s in proj.samples() + ["chapter %s (%s)" % (c["slug"], c["file"]) for c in chapters if c["sample"]]:
            print(s)
    elif cmd == "pdf":
        build_pdfs()
    elif cmd == "serve":
        serve(int(argv[2]) if len(argv) > 2 else 8000)
    elif cmd == "clean":
        shutil.rmtree(SITE, ignore_errors=True)
        shutil.rmtree(OUT, ignore_errors=True)
        print("removed site/ and out/")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
