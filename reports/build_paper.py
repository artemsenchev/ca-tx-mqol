"""Render reports/paper.md to PDF and HTML.

    python reports/build_paper.py

Uses pandoc via pypandoc-binary, so no system pandoc install is required.
Citations are resolved from references.bib with APA formatting; the PDF route
additionally needs a LaTeX engine (MiKTeX or TeX Live) on PATH.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "paper.md"
BIB = HERE / "references.bib"
CSL = HERE / "apa.csl"

COMMON = [
    "--standalone",
    "--citeproc",
    f"--bibliography={BIB}",
    "--metadata=link-citations=true",
    # Image paths in paper.md are relative to paper.md, not to wherever the
    # build is invoked from. Without this, pandoc silently drops the figure
    # and replaces it with its alt text -- and still exits 0.
    f"--resource-path={HERE}",
]

PDF_ARGS = COMMON + [
    "--pdf-engine=pdflatex",
    "-V", "geometry:margin=1in",
    "-V", "fontsize=11pt",
    "-V", "linkcolor=blue",
    "-V", "urlcolor=blue",
]

HTML_ARGS = COMMON + ["--embed-resources", "--toc", "--toc-depth=2"]


def main() -> int:
    import pypandoc

    if not SOURCE.exists():
        print(f"missing {SOURCE}", file=sys.stderr)
        return 1

    args_pdf = list(PDF_ARGS)
    if CSL.exists():
        args_pdf.append(f"--csl={CSL}")
        html_args = HTML_ARGS + [f"--csl={CSL}"]
    else:
        # APA style is optional; pandoc falls back to its default author-date
        # style rather than failing the build.
        print(f"note: {CSL.name} not found, using pandoc's default citation style")
        html_args = list(HTML_ARGS)

    ok = True
    for fmt, out, extra in (("html", HERE / "paper.html", html_args),
                            ("pdf", HERE / "paper.pdf", args_pdf)):
        try:
            pypandoc.convert_file(str(SOURCE), fmt, outputfile=str(out),
                                  extra_args=extra)
            print(f"wrote {out}  ({out.stat().st_size / 1024:.0f} KB)")
        except Exception as exc:  # noqa: BLE001 - report and continue
            ok = False
            print(f"FAILED to build {fmt}: {exc}", file=sys.stderr)
            if fmt == "pdf":
                print("  a LaTeX engine (MiKTeX / TeX Live) must be on PATH",
                      file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
