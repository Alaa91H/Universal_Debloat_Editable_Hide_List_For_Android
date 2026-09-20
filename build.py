#!/usr/bin/env python3
"""Package the Universal Debloat flashable zip.

Usage:
    python build.py                      # builds with bundled hide_list.txt
    python build.py --cleanrom           # also add the clean-ROM marker file
    python build.py --list mylist.txt    # replace the bundled hide_list.txt
"""
import argparse
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DEFAULT = "Universal_Debloat_v3.1.2.zip"

ENTRIES = [
    ("module/blank.apk", "blank.apk", 0o644),
    ("module/customize.sh", "customize.sh", 0o755),
    ("module/hide_list.txt", "hide_list.txt", 0o644),
    ("module/module.prop", "module.prop", 0o644),
    ("module/post-fs-data.sh", "post-fs-data.sh", 0o755),
    ("module/service.sh", "service.sh", 0o755),
    ("module/uninstall.sh", "uninstall.sh", 0o755),
    ("presets/safe.txt", "presets/safe.txt", 0o644),
    ("presets/default.txt", "presets/default.txt", 0o644),
    ("presets/max.txt", "presets/max.txt", 0o644),
    ("META-INF/com/google/android/update-binary", "META-INF/com/google/android/update-binary", 0o755),
    ("META-INF/com/google/android/updater-script", "META-INF/com/google/android/updater-script", 0o644),
]


def norm(data: bytes, arcname: str) -> bytes:
    if not arcname.endswith(".apk"):
        data = data.replace(b"\r\n", b"\n")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the Universal Debloat flashable zip")
    ap.add_argument("--cleanrom", action="store_true", help="include the clean-ROM marker")
    ap.add_argument("--preset", choices=("safe", "default", "max"),
                    help="use a preset list as hide_list.txt (and @mode action)")
    ap.add_argument("--mode", choices=("uninstall", "disable"), default="uninstall",
                    help="action mode written into the list (with --preset)")
    ap.add_argument("--list", dest="list_file", help="use this file as hide_list.txt")
    ap.add_argument("--out", default=OUT_DEFAULT, help="output zip path")
    args = ap.parse_args()

    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    blank = os.path.join(ROOT, "module", "blank.apk")
    if not os.path.exists(blank):
        open(blank, "wb").close()

    entries = list(ENTRIES)
    extra = {}
    if args.list_file:
        with open(args.list_file, "rb") as f:
            extra["hide_list.txt"] = f.read().replace(b"\r\n", b"\n")
    elif args.preset:
        src = os.path.join(ROOT, "presets", args.preset + ".txt")
        with open(src, "rb") as f:
            data = f.read().replace(b"\r\n", b"\n")
        data = re.sub(rb"(?m)^@mode=.*$", b"@mode=" + args.mode.encode(), data)
        extra["hide_list.txt"] = data

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for src, arc, mode in entries:
            path = os.path.join(ROOT, src)
            with open(path, "rb") as f:
                payload = norm(extra.get(arc, f.read()), arc)
            zi = zipfile.ZipInfo(arc, date_time=(2026, 9, 20, 12, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = mode << 16
            z.writestr(zi, payload)
        if args.cleanrom:
            zi = zipfile.ZipInfo("cleanrom", date_time=(2026, 9, 20, 12, 0, 0))
            zi.external_attr = 0o644 << 16
            z.writestr(zi, b"")

    print("built:", out, os.path.getsize(out), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
