#!/usr/bin/env python3
"""Prepare release notes for the GitHub release from CHANGELOG.md.

Extracts the section for the version passed as the first argument
(e.g. 3.1.0) and prints it to stdout.
"""
import re
import sys
import io
from pathlib import Path

# Windows consoles default to a legacy codepage; force UTF-8 output.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

def main() -> int:
    if len(sys.argv) != 2:
        print("usage: make_release_notes.py <version>", file=sys.stderr)
        return 2
    version = sys.argv[1].lstrip("v")
    changelog = Path(__file__).with_name("CHANGELOG.md").read_text(encoding="utf-8")
    pattern = re.compile(
        rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}\n(.*?)(?=^## \[|\Z)",
        re.M | re.S,
    )
    m = pattern.search(changelog)
    if not m:
        print(f"no changelog section for {version}", file=sys.stderr)
        return 1
    print(f"# Universal Debloat v{version}\n")
    print(m.group(1).strip())
    return 0

if __name__ == "__main__":
    sys.exit(main())
