"""Print pages to PDF with a headless Chromium-family browser."""

import os
import platform
import re
import shutil
import subprocess
import tempfile

MAC_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
PATH_CANDIDATES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"]


class PdfError(Exception):
    pass


def find_browser():
    """$CHROME (if set) -> Google Chrome on macOS -> PATH names -> Chromium/Edge."""
    env = os.environ.get("CHROME")
    if env:
        if os.path.exists(env) or shutil.which(env):
            return shutil.which(env) or env
        raise PdfError("CHROME is set to %r but that file does not exist" % env)
    if os.path.exists(MAC_CANDIDATES[0]):
        return MAC_CANDIDATES[0]
    for name in PATH_CANDIDATES:
        p = shutil.which(name)
        if p:
            return p
    for p in MAC_CANDIDATES[1:]:
        if os.path.exists(p):
            return p
    raise PdfError(
        "No Chrome/Chromium found for PDF printing.\n  Looked for: %s\n  and on PATH: %s\n"
        "  Install Google Chrome, or set CHROME=/path/to/chrome-compatible-browser."
        % ("\n              ".join(MAC_CANDIDATES), ", ".join(PATH_CANDIDATES)))


def print_pdf(browser, html_path, pdf_path):
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    url = "file://" + os.path.abspath(html_path)
    with tempfile.TemporaryDirectory() as profile:
        cmd = [browser, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
               "--disable-extensions", "--user-data-dir=" + profile,
               "--no-pdf-header-footer", "--print-to-pdf-no-header",
               "--print-to-pdf=" + os.path.abspath(pdf_path), url]
        if platform.system() == "Linux":
            cmd.insert(1, "--no-sandbox")  # CI runners block the Chrome sandbox
        # Headless Edge/Chrome occasionally hangs on one page out of dozens;
        # a fresh attempt almost always succeeds, so retry before giving up.
        for attempt in range(3):
            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
                break
            except subprocess.TimeoutExpired:
                if attempt == 2:
                    raise PdfError("browser timed out printing %s (3 attempts)" % html_path)
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        raise PdfError("browser did not write %s\n%s" % (pdf_path, res.stderr.decode("utf-8", "replace")[-2000:]))


def page_count(pdf_path):
    with open(pdf_path, "rb") as fh:
        data = fh.read()
    m = re.findall(rb"/Type\s*/Pages\b[^>]*?/Count\s+(\d+)", data)
    if m:
        return max(int(x) for x in m)
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", data))
