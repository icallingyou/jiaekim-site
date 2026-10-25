#!/usr/bin/env python3
"""Record the pixel size of every photo referenced from _data/*.yml.

Pages CMS writes lines such as `image: /images/foo.jpg` into the content files. This
script reads the JPEG/PNG/GIF/WebP header of each referenced file and writes one map,
`_data/image_sizes.yml`, keyed by the exact path value found in the content files:

    "/images/foo.jpg":
      w: 1600
      h: 1200

The templates look sizes up in that map, so the content files the owner edits are never
touched by automation. The map is fully regenerated on every run, so a replaced or
re-uploaded photo always gets its current size. No third-party dependencies.

Usage: python3 scripts/fill_image_sizes.py [repo_root]
Prints "updated" when the map changed, "no change" otherwise. Exit code 0 always.
"""
import os
import re
import struct
import sys
import urllib.parse

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT, "_data")
OUT = os.path.join(DATA_DIR, "image_sizes.yml")
KEYS = ("image", "image_mobile", "og_image")
LINE_RE = re.compile(r"^\s*(?:-\s+)?(" + "|".join(KEYS) + r"):\s*(.+?)\s*$")
HEADER = "# 자동 생성 파일 — 사진의 가로·세로 픽셀 크기. GitHub Action(scripts/fill_image_sizes.py)이 채웁니다. 직접 고치지 마세요.\n"


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
                    return 1 + int.from_bytes(data[12:15], "little"), 1 + int.from_bytes(data[15:18], "little")
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
                    while m == 0xFF:
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


def unquote_value(raw):
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v


def resolve(value):
    """Map a content value like /images/a.jpg (possibly percent-encoded) to a repo path."""
    if value.startswith(("http://", "https://", "data:")):
        return None
    return os.path.join(ROOT, urllib.parse.unquote(value).lstrip("/"))


def referenced_paths():
    found = []
    if not os.path.isdir(DATA_DIR):
        return found
    for name in sorted(os.listdir(DATA_DIR)):
        if not name.endswith((".yml", ".yaml")) or name == os.path.basename(OUT):
            continue
        with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
            for line in f:
                m = LINE_RE.match(line)
                if not m:
                    continue
                v = unquote_value(m.group(2))
                if v and v not in found:
                    found.append(v)
    return found


def yaml_key(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    entries = []
    for value in sorted(referenced_paths()):
        path = resolve(value)
        if not path or not os.path.isfile(path):
            continue
        size = image_size(path)
        if size:
            entries.append((value, size))
    text = HEADER + "".join(f"{yaml_key(v)}:\n  w: {w}\n  h: {h}\n" for v, (w, h) in entries)
    old = None
    if os.path.isfile(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = f.read()
    if old == text:
        print(f"no change ({len(entries)} images)")
        return
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"updated {os.path.relpath(OUT, ROOT)} ({len(entries)} images)")


if __name__ == "__main__":
    main()
