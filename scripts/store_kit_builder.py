#!/usr/bin/env python3
"""Generate Play Store store-kit assets without external imaging libraries."""
from __future__ import annotations

import argparse
import json
import math
import struct
import zlib
from pathlib import Path
from typing import Callable, Tuple

RGB = Tuple[int, int, int]


def write_png(path: Path, width: int, height: int, pixel: Callable[[int, int], RGB]) -> None:
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            r, g, b = pixel(x, y)
            row.extend((r & 255, g & 255, b & 255))
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * max(0.0, min(1.0, t)))


def gradient_pixel(x: int, y: int, w: int, h: int) -> RGB:
    t = (x / max(w - 1, 1) + y / max(h - 1, 1)) * 0.5
    return (lerp(13, 60, t), lerp(23, 22, t), lerp(48, 110, t))


def draw_disc(pixel: Callable[[int, int], RGB], cx: float, cy: float, radius: float, color: RGB, shade: bool = True):
    def wrapped(x: int, y: int) -> RGB:
        base = pixel(x, y)
        dist = math.hypot(x - cx, y - cy)
        if dist <= radius:
            if shade and dist <= radius * 0.55 and (x - cx) + (y - cy) < 0:
                return (min(255, color[0] + 70), min(255, color[1] + 70), min(255, color[2] + 70))
            return color
        return base
    return wrapped


def draw_rect(pixel: Callable[[int, int], RGB], x0: int, y0: int, x1: int, y1: int, color: RGB):
    def wrapped(x: int, y: int) -> RGB:
        if x0 <= x <= x1 and y0 <= y <= y1:
            return color
        return pixel(x, y)
    return wrapped


def build_icon(genre: str, path: Path) -> None:
    size = 512
    pix: Callable[[int, int], RGB] = lambda x, y: gradient_pixel(x, y, size, size)
    if genre == "match_3":
        colors = [(246, 78, 96), (78, 160, 248), (86, 218, 132)]
        for i, color in enumerate(colors):
            pix = draw_disc(pix, 170 + i * 86, 250 + (i % 2) * 44, 74, color)
        pix = draw_rect(pix, 140, 400, 372, 432, (250, 202, 64))
    else:
        pix = draw_disc(pix, 256, 256, 150, (250, 92, 110))
        pix = draw_rect(pix, 150, 244, 362, 268, (27, 35, 51))
        pix = draw_rect(pix, 244, 150, 268, 362, (27, 35, 51))
        pix = draw_disc(pix, 256, 256, 34, (255, 214, 90))
    write_png(path, size, size, pix)


def build_feature(genre: str, title: str, path: Path) -> None:
    width, height = 1024, 500
    pix: Callable[[int, int], RGB] = lambda x, y: gradient_pixel(x, y, width, height)
    if genre == "match_3":
        colors = [(246, 78, 96), (78, 160, 248), (86, 218, 132), (250, 202, 64), (186, 112, 246)]
        for i, color in enumerate(colors):
            pix = draw_disc(pix, 260 + (i % 3) * 130, 150 + (i // 3) * 150, 64, color)
        pix = draw_rect(pix, 80, 430, 600, 456, (250, 202, 64))
    else:
        for i, color in enumerate([(250, 92, 110), (78, 160, 248), (86, 218, 132)]):
            pix = draw_disc(pix, 220 + i * 150, 240, 96, color)
        pix = draw_rect(pix, 120, 232, 720, 252, (27, 35, 51))
    # Decorative right-hand panel
    pix = draw_rect(pix, 760, 60, 964, 440, (18, 28, 54))
    write_png(path, width, height, pix)


def build_store_kit(project_root: Path, out_dir: Path) -> dict:
    manifest_path = project_root / "docs" / "GAME_GENERATION_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    genre = str(manifest.get("genre", "match_3"))
    title = str(manifest.get("title", "Studio Game"))
    game_id = str(manifest.get("game_id", "studio_game"))
    out_dir.mkdir(parents=True, exist_ok=True)
    build_icon(genre, out_dir / "icon_512x512.png")
    build_feature(genre, title, out_dir / "feature_graphic_1024x500.png")
    data_safety = {
        "game_id": game_id,
        "title": title,
        "data_collected": {
            "personal_info": False,
            "location": False,
            "financial_info": False,
            "app_activity": "Local-only analytics counters stored in user://analytics.json",
        },
        "data_shared_with_third_parties": False,
        "encrypted_in_transit": True,
        "data_deletion_request": "Delete app data from Android Settings or uninstall the app.",
        "ads": {
            "qa_mode": "Simulated templates only (zero real impressions)",
            "release_mode": "Publisher-provided Unity/AdMob IDs injected at export time",
        },
        "children_targeted": False,
    }
    (out_dir / "DATA_SAFETY_REPORT.json").write_text(json.dumps(data_safety, indent=2), encoding="utf-8")
    privacy = project_root / "docs" / "PRIVACY_POLICY.md"
    if privacy.exists():
        (out_dir / "PRIVACY_POLICY.md").write_text(privacy.read_text(encoding="utf-8"), encoding="utf-8")
    return {"status": "PASS", "genre": genre, "files": sorted(p.name for p in out_dir.iterdir() if p.is_file())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--out", default="build/store_kit")
    args = parser.parse_args()
    print(json.dumps(build_store_kit(Path(args.project_root).resolve(), Path(args.out).resolve()), indent=2))
