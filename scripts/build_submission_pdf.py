"""Build the Round 2 submission PDF from docs/ROUND-2-SUBMISSION.md.

Usage:
    python scripts/build_submission_pdf.py
    python scripts/build_submission_pdf.py --demo-url https://... --repo-url https://github.com/...

Requires: markdown (installed via backend/requirements-dev.txt) and Microsoft Edge or Chrome.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "ROUND-2-SUBMISSION.md"
HTML_OUT = ROOT / "docs" / "BrandGuard-AI-Round-2-Submission.html"
PDF_OUT = ROOT / "docs" / "BrandGuard-AI-Round-2-Submission.pdf"

EDGE_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]

CSS = """
@page { size: A4; margin: 17mm 15mm 16mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  margin: 0;
  font-family: "Segoe UI", -apple-system, "Helvetica Neue", Arial, sans-serif;
  font-size: 9.4pt;
  line-height: 1.48;
  color: #1b2430;
}
h1, h2, h3, h4 { color: #0b1424; line-height: 1.2; page-break-after: avoid; }
h1 { font-size: 26pt; margin: 0 0 4mm; letter-spacing: -0.02em; }
h2 {
  font-size: 15pt;
  margin: 8mm 0 3mm;
  padding-bottom: 1.6mm;
  border-bottom: 1.2pt solid #2f6bff;
}
h3 { font-size: 11.2pt; margin: 5mm 0 2mm; color: #12305e; }
h4 { font-size: 9.8pt; margin: 4mm 0 1.5mm; }
p { margin: 0 0 2.6mm; }
strong { color: #0b1424; }
a { color: #1f5be0; text-decoration: none; }
ul, ol { margin: 0 0 2.8mm; padding-left: 5.2mm; }
li { margin: 0 0 1.1mm; }
hr { border: 0; border-top: 0.8pt solid #d8e0ec; margin: 6mm 0; }
blockquote {
  margin: 3mm 0 4mm;
  padding: 3mm 4mm;
  background: #eef4ff;
  border-left: 3pt solid #2f6bff;
  border-radius: 1.5mm;
  color: #13233a;
}
blockquote p { margin: 0; }
code {
  font-family: "Cascadia Mono", Consolas, monospace;
  font-size: 8.1pt;
  background: #f1f4f9;
  padding: 0.3mm 1mm;
  border-radius: 1mm;
}
pre {
  font-family: "Cascadia Mono", Consolas, monospace;
  font-size: 7.8pt;
  line-height: 1.4;
  background: #0e1726;
  color: #dbe7ff;
  padding: 3.2mm 4mm;
  border-radius: 2mm;
  overflow: hidden;
  white-space: pre-wrap;
  page-break-inside: avoid;
}
pre code { background: none; color: inherit; padding: 0; font-size: inherit; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 2.5mm 0 4mm;
  font-size: 8.2pt;
  page-break-inside: auto;
}
thead { display: table-header-group; }
tr { page-break-inside: avoid; }
th {
  background: #e8effd;
  color: #0b1424;
  text-align: left;
  font-weight: 600;
  padding: 1.7mm 2mm;
  border: 0.6pt solid #c7d4ea;
}
td {
  padding: 1.6mm 2mm;
  border: 0.6pt solid #d7dfec;
  vertical-align: top;
}
tbody tr:nth-child(even) { background: #f8fafd; }

.cover {
  height: 255mm;
  display: flex;
  flex-direction: column;
  justify-content: center;
  page-break-after: always;
  break-after: page;
}
.cover .band {
  display: inline-block;
  align-self: flex-start;
  font-size: 8pt;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: #1f5be0;
  background: #e8effd;
  border: 0.7pt solid #b9ccf3;
  border-radius: 10mm;
  padding: 1.6mm 4mm;
  margin-bottom: 10mm;
}
.cover h1 { font-size: 38pt; margin: 0 0 3mm; }
.cover h3 { font-size: 14pt; color: #44536b; font-weight: 500; margin: 0 0 10mm; }
.cover table { width: 100%; font-size: 9pt; margin-top: 4mm; }
.cover th { width: 28%; background: #f2f6fd; }
.cover .foot { margin-top: 18mm; font-size: 8.2pt; color: #6b7a91; }
.page-break { page-break-after: always; }
main { page-break-before: always; break-before: page; }
"""


def find_browser() -> Path:
    for candidate in EDGE_CANDIDATES:
        if candidate.exists():
            return candidate
    raise SystemExit("Could not find Microsoft Edge or Google Chrome. Pass a browser path or print the HTML manually.")


def build_html(text: str) -> str:
    if "\n---\n" not in text:
        raise SystemExit("Submission markdown is missing the cover separator ('---').")
    cover_md, body_md = text.split("\n---\n", 1)

    extensions = ["tables", "fenced_code", "sane_lists", "attr_list"]
    cover = markdown.markdown(cover_md, extensions=extensions)
    body = markdown.markdown(body_md, extensions=extensions)

    # Wrap the cover heading block so it gets a full title page.
    cover = cover.replace("<h1>", '<div class="band">CODEX 48 · ROUND 2 · THE BUILD</div><h1>', 1)
    cover = cover.replace("</table>", '</table><div class="foot">Confidential submission · CHOOSE AS U WISH CYBER SQUAD · Codex 48</div>')

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>BrandGuard AI — Codex 48 Round 2 Submission</title>
<style>{CSS}</style>
</head>
<body>
<section class="cover">
{cover}
</section>
<main>
{body}
</main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo-url", default="", help="Public live demo URL")
    parser.add_argument("--repo-url", default="", help="Public source repository URL")
    parser.add_argument("--out", default=str(PDF_OUT))
    args = parser.parse_args()

    text = SOURCE.read_text(encoding="utf-8")
    demo = args.demo_url.strip() or "Pending deployment — add public URL"
    repo = args.repo_url.strip() or "Pending push — add public repository URL"
    text = text.replace("{{DEMO_URL}}", demo).replace("{{REPO_URL}}", repo)

    if not args.demo_url or not args.repo_url:
        print("WARNING: generating with placeholder links. Re-run with --demo-url and --repo-url before submitting.")

    HTML_OUT.write_text(build_html(text), encoding="utf-8")

    browser = find_browser()
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=4000",
        f"--print-to-pdf={out_path}",
        HTML_OUT.resolve().as_uri(),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)

    if result.returncode != 0 or not out_path.exists():
        print(result.stdout)
        print(result.stderr)
        raise SystemExit(f"PDF generation failed (exit {result.returncode}).")

    head = out_path.read_bytes()[:5]
    if head != b"%PDF-":
        raise SystemExit("Generated file is not a valid PDF.")

    print(f"HTML: {HTML_OUT}")
    print(f"PDF : {out_path} ({out_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    sys.exit(main())
