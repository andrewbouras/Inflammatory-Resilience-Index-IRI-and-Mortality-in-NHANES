#!/usr/bin/env python3
"""
Generate manuscript/IRI_Manuscript_TrackedChanges.docx — the brahiri.docx
starting point with our edits applied as Word's native tracked changes.

This wraps Microsoft Word's Compare Documents feature (the same one available
under Review > Compare in the Word UI) via AppleScript. Word's Compare
produces a docx with proper <w:ins> / <w:del> / <w:moveFrom> / <w:moveTo>
XML that Word, Google Docs, and Pages all render correctly with accept/reject
controls. Banach's original comments in brahiri.docx are preserved.

Inputs (must already exist):
  - IRI/brahiri.docx  (the version PI Banach reviewed, with comments)
  - manuscript/IRI_Manuscript_Final.docx  (current canonical, built by
    scripts/build_manuscript_docx.py from the .md)

Output:
  - manuscript/IRI_Manuscript_TrackedChanges.docx

Requirements:
  - macOS with Microsoft Word installed (uses osascript / AppleScript)

If Word is not available, see the legacy text-only redline at the bottom
of this file (kept as a fallback for headless environments).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ORIGINAL = PROJECT / "IRI" / "brahiri.docx"
REVISED = PROJECT / "manuscript" / "IRI_Manuscript_Final.docx"
OUTPUT = PROJECT / "manuscript" / "IRI_Manuscript_TrackedChanges.docx"

APPLESCRIPT = f"""
tell application "Microsoft Word"
    activate
    open file name "{ORIGINAL}"
    delay 2
    compare active document path "{REVISED}"
    delay 3
    save as active document file name "{OUTPUT}" file format format document
    delay 1
    close active document saving no
    try
        close active document saving no
    end try
end tell
"""


def main() -> int:
    if not ORIGINAL.exists():
        sys.exit(f"missing input: {ORIGINAL}")
    if not REVISED.exists():
        sys.exit(f"missing input: {REVISED} — run scripts/build_manuscript_docx.py first")
    if not shutil.which("osascript"):
        sys.exit("osascript not found; this helper requires macOS with Microsoft Word")

    # Run the AppleScript Compare
    print(f"Comparing:")
    print(f"  original: {ORIGINAL}")
    print(f"  revised:  {REVISED}")
    print(f"  output:   {OUTPUT}")

    if OUTPUT.exists():
        OUTPUT.unlink()  # Word's "save as" sometimes balks at overwrite

    result = subprocess.run(
        ["osascript", "-e", APPLESCRIPT],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout + "\n" + result.stderr + "\n")
        sys.exit(f"AppleScript failed (exit {result.returncode})")

    if not OUTPUT.exists():
        sys.exit("Word compare reported success but output file is missing")

    size = OUTPUT.stat().st_size
    print(f"Wrote {OUTPUT} ({size:,} bytes)")

    # Quick verification: count tracked-change XML elements
    import zipfile
    with zipfile.ZipFile(OUTPUT) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    n_ins = xml.count("<w:ins ")
    n_del = xml.count("<w:del ")
    n_movefrom = xml.count("<w:moveFrom ")
    n_moveto = xml.count("<w:moveTo ")
    print(f"  <w:ins>      runs: {n_ins}")
    print(f"  <w:del>      runs: {n_del}")
    print(f"  <w:moveFrom> runs: {n_movefrom}")
    print(f"  <w:moveTo>   runs: {n_moveto}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
