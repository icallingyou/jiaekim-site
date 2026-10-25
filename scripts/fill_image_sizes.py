#!/usr/bin/env python3
"""Fill in missing image pixel sizes (w/h) in _data/*.yml.

Pages CMS writes `image: /images/foo.jpg` lines; this script reads the JPEG/PNG/WebP/GIF
header of each referenced file and inserts `w:` and `h:` lines right after the `image:`
line when the surrounding mapping does not already have both. It edits the YAML as text so
formatting and comments are preserved. No third-party dependencies.

Usage: python3 scripts/fill_image_sizes.py [repo_root]
Exit code 0 always; prints the files it changed.
"""
import os
import re
import struct
import sys
import urllib.parse

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT, "_data")


def image_size(path):
    """Return (width, height) for JPEG, PNG, GIF or WebP files, else None."""
    try:
        with open(path, "rb") as f:
            head = f.read(32)
            if head.startswith(b"\x89PNG\r\n\x1a\n"):
                w, h = struct.unpack(">II", head[16:24])
                return w, h
            if head[:6] in (b"GIF87a", b"GIF89a"):
                w, h = struct.unpack("<HH", head[6:10])
                return w, h
            if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                chunk = head[12:16]
                f.seek(12)
                data = f.read(30)
                if chunk == b"VP8X":
                    w = 1 + int.from_bytes(data[12:15], "little")
                    h = 1 + int.from_bytes(data[15:18], "little")
                    return w, h
                if chunk == b"VP8L":
                    b = data[9:13]
                    w = 1 + (((b[1] & 0x3F) << 8) | b[0])
                    h = 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
                    return w, h
                if chunk == b"VP8 ":
                    w = int.from_bytes(data[14:16], "little") & 0x3FFF
                    h = int.from_bytes(data[16:18], "little") & 0x3FFF
                    return w, h
                return None
            if head[:2] == b"\xff\xd8":  # JPEG: walk the segments to a SOF marker
                f.seek(2)
                while True:
                    marker = f.read(2)
                    if len(marker) < 2 or marker[0] != 0xFF:
                        return None
                    m = marker[1]
                    while m == 0xFF:  # padding
                        nxt = f.read(1)
                        if not nxt:
                            return None
                        m = nxt[0]
                    if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                        continue
                    seg = f.read(2)
                    if len(seg) < 2:
                        return None
                    (length,) = struct.unpack(">H", seg)
                    if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        body = f.read(5)
                        if len(body) < 5:
                            return None
                        h, w = struct.unpack(">HH", body[1:5])
                        return w, h
                    f.seek(length - 2, os.SEEK_CUR)
    except OSError:
        return None
    return None


def resolve_image(value):
    """Map a content value like /images/a.jpg (possibly percent-encoded or quoted) to a repo path."""
    v = value.strip().strip('"').strip("'")
    v = urllib.parse.unquote(v)
    if v.startswith("http://") or v.startswith("https://"):
        return None
    v = v.lstrip("/")
    return os.path.join(ROOT, v)


KEY_RE = re.compile(r"^(\s*)(- )?([A-Za-z_][A-Za-z0-9_]*):(.*)$")


def process(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    out = []
    changed = False
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        out.append(line)
        m = KEY_RE.match(line)
        if m and m.group(3) == "image":
            indent = len(m.group(1)) + (2 if m.group(2) else 0)  # column where sibling keys start
            value = m.group(4)
            # collect sibling keys of this mapping
            sib = set()
            j = i + 1
            while j < n:
                l2 = lines[j]
                if l2.strip() == "" or l2.lstrip().startswith("#"):
                    j += 1
                    continue
                m2 = KEY_RE.match(l2)
                cur_indent = len(l2) - len(l2.lstrip(" "))
                if m2 and not m2.group(2) and cur_indent == indent:
                    sib.add(m2.group(3))
                    j += 1
                    continue
                if cur_indent > indent and not (m2 and m2.group(2) and cur_indent == indent):
                    j += 1
                    continue
                break
            if "w" in sib and "h" in sib:
                i += 1
                continue
            target = resolve_image(value)
            size = image_size(target) if target and os.path.isfile(target) else None
            if size:
                pad = " " * indent
                if "w" not in sib:
                    out.append(f"{pad}w: {size[0]}")
                if "h" not in sib:
                    out.append(f"{pad}h: {size[1]}")
                changed = True
        i += 1
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(out))
        print(f"updated {os.path.relpath(path, ROOT)}")
    return changed


def main():
    if not os.path.isdir(DATA_DIR):
        return
    any_changed = False
    for name in sorted(os.listdir(DATA_DIR)):
        if name.endswith((".yml", ".yaml")):
            any_changed |= process(os.path.join(DATA_DIR, name))
    if not any_changed:
        print("nothing to fill")


if __name__ == "__main__":
    main()
