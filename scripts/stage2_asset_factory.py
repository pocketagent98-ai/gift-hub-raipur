#!/usr/bin/env python3
"""
STAGE 2 — 100% Original Procedural HD Asset & Musical Audio Factory (V7.0)
- Synthesizes crisp bevelled PNG sprites, app icon (512x512), feature graphic (1024x500),
  and harmonic pentatonic WAV sound effects with zero third-party copyrighted material.
- Runs visual QA on generated icons via Gemini Flash-Lite.
"""

import json
import math
from pathlib import Path
import struct
import wave

from PIL import Image, ImageDraw
from llm_router import gemini_image_qa


def _hex_to_rgb(h: str, fallback: tuple[int, int, int] = (56, 189, 248)) -> tuple[int, int, int]:
    h = str(h).strip().lstrip("#")
    if len(h) != 6:
        return fallback
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except Exception:
        return fallback


def _shade(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * factor))) for c in rgb)


def _draw_glossy_tile(size: int, rgb: tuple[int, int, int], shape: str = "square") -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(4, size // 16)
    dark = _shade(rgb, 0.62) + (255,)
    mid = rgb + (255,)
    light = tuple(min(255, int(c + (255 - c) * 0.45)) for c in rgb) + (255,)

    if shape == "screw":
        d.ellipse([pad, pad, size - pad, size - pad], fill=dark, outline=light, width=max(2, size // 32))
        in_p = pad + size // 12
        d.ellipse([in_p, in_p, size - in_p, size - in_p], fill=mid)
        # Gloss highlight + screw cross slot
        d.ellipse([in_p + size // 10, in_p + size // 12, size // 2, size // 2 - size // 14], fill=light)
        c = size // 2
        arm = size // 5
        w = max(4, size // 16)
        d.line([c - arm, c, c + arm, c], fill=(20, 24, 34, 230), width=w)
        d.line([c, c - arm, c, c + arm], fill=(20, 24, 34, 230), width=w)
    else:
        r = size // 6
        d.rounded_rectangle([pad, pad, size - pad, size - pad], radius=r, fill=dark, outline=light, width=max(2, size // 32))
        in_p = pad + size // 14
        d.rounded_rectangle([in_p, in_p, size - in_p, size - in_p], radius=max(4, r - 4), fill=mid)
        d.rounded_rectangle(
            [in_p + 4, in_p + 4, size - in_p - 4, in_p + max(8, size // 4)],
            radius=max(3, r // 2),
            fill=light,
        )
    return img


def _make_icon_and_banner(out_dir: Path, spec: dict) -> None:
    bg = _hex_to_rgb(spec.get("theme_bg_hex", "#0f172a"), (15, 23, 42))
    accent = _hex_to_rgb(spec.get("theme_accent_hex", "#38bdf8"), (56, 189, 248))
    pal = [_hex_to_rgb(c) for c in spec.get("palette_hex", ["#fb5668", "#ffa62b", "#3ddc84", "#38b6ff"])]
    is_screw = spec.get("genre") == "screw_puzzle"

    # 512x512 App Icon
    icon = Image.new("RGBA", (512, 512), bg + (255,))
    draw = ImageDraw.Draw(icon)
    for y in range(512):
        t = y / 511.0
        col = tuple(int(bg[i] * (1.0 - t * 0.35) + accent[i] * (t * 0.25)) for i in range(3))
        draw.line([(0, y), (512, y)], fill=col + (255,))
    draw.rounded_rectangle([24, 24, 488, 488], radius=96, outline=accent + (255,), width=12)

    tile_shape = "screw" if is_screw else "square"
    coords = [(92, 92), (272, 92), (92, 272), (272, 272)]
    for idx, (x, y) in enumerate(coords):
        t_img = _draw_glossy_tile(148, pal[idx % len(pal)], tile_shape)
        icon.alpha_composite(t_img, (x, y))
    icon.convert("RGB").save(out_dir / "icon_512x512.png", "PNG")

    # 1024x500 Feature Graphic
    banner = Image.new("RGBA", (1024, 500), bg + (255,))
    bd = ImageDraw.Draw(banner)
    for y in range(500):
        t = y / 499.0
        col = tuple(int(bg[i] * (1.0 - t * 0.4) + accent[i] * (t * 0.28)) for i in range(3))
        bd.line([(0, y), (1024, y)], fill=col + (255,))
    bd.rounded_rectangle([18, 18, 1006, 482], radius=36, outline=accent + (220,), width=6)
    for idx in range(5):
        t_img = _draw_glossy_tile(136, pal[idx % len(pal)], tile_shape)
        banner.alpha_composite(t_img, (90 + idx * 176, 182))
    banner.convert("RGB").save(out_dir / "feature_graphic_1024x500.png", "PNG")


def _write_wav_chord(path: Path, freqs: list[float], duration: float = 0.24, gain: float = 0.35, rate: int = 22050) -> None:
    n = int(rate * duration)
    frames = bytearray()
    inv_f = 1.0 / max(1, len(freqs))
    for i in range(n):
        t = i / rate
        env = math.exp(-t * (6.0 / max(duration, 0.05)))
        val = 0.0
        for idx, f in enumerate(freqs):
            delay = idx * 0.025
            if t >= delay:
                dt = t - delay
                val += (math.sin(2.0 * math.pi * f * dt) * 0.78 + math.sin(4.0 * math.pi * f * dt) * 0.22) * inv_f
        sample = max(-1.0, min(1.0, val * env * gain))
        frames.extend(struct.pack("<h", int(sample * 32767)))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(bytes(frames))


def main() -> None:
    spec_p = Path("docs/generated/design_spec.json")
    spec = json.loads(spec_p.read_text(encoding="utf-8")) if spec_p.exists() else {}

    out = Path("assets/generated")
    sprites_dir = out / "sprites"
    audio_dir = out / "audio"
    store_dir = out / "store"
    for d in (sprites_dir, audio_dir, store_dir):
        d.mkdir(parents=True, exist_ok=True)

    pal = [_hex_to_rgb(c) for c in spec.get("palette_hex", ["#fb5668", "#ffa62b", "#3ddc84", "#38b6ff", "#a86bff", "#ff66c4"])]
    while len(pal) < 6:
        pal.append((56, 189, 248))

    # Original tile & screw sprites (128x128 HD)
    generated_files = []
    for i, rgb in enumerate(pal[:6], start=1):
        sq = sprites_dir / f"block_{i}.png"
        _draw_glossy_tile(128, rgb, "square").save(sq, "PNG")
        sc = sprites_dir / f"screw_{i}.png"
        _draw_glossy_tile(128, rgb, "screw").save(sc, "PNG")
        generated_files.extend([str(sq), str(sc)])

    _make_icon_and_banner(store_dir, spec)
    generated_files.extend([str(store_dir / "icon_512x512.png"), str(store_dir / "feature_graphic_1024x500.png")])

    # Original harmonic musical WAV SFX
    sfx_defs = {
        "ui_click.wav": ([659.25], 0.07, 0.28),
        "place_block.wav": ([440.0, 554.37], 0.11, 0.34),
        "line_clear.wav": ([523.25, 659.25, 783.99, 1046.5], 0.28, 0.36),
        "screw_turn.wav": ([587.33, 739.99], 0.12, 0.32),
        "plate_drop.wav": ([392.0, 523.25, 659.25], 0.25, 0.36),
        "victory.wav": ([523.25, 659.25, 783.99, 1046.5, 1318.51], 0.42, 0.38),
        "invalid.wav": ([220.0, 196.0], 0.13, 0.28),
    }
    for name, (freqs, dur, gain) in sfx_defs.items():
        wp = audio_dir / name
        _write_wav_chord(wp, freqs, dur, gain)
        generated_files.append(str(wp))

    # Visual QA on icon via Gemini Flash-Lite
    qa_verdict, qa_model = gemini_image_qa(
        store_dir / "icon_512x512.png",
        "Inspect this original mobile puzzle game app icon for sharpness, visual contrast, and cleanliness. Reply short VERDICT: PASS or VERDICT: WARN.",
    )

    manifest = {
        "schema_version": "7.0",
        "license": "100% Original Procedural Studio Asset (Zero Third-Party Copyright)",
        "file_count": len(generated_files),
        "files": generated_files,
        "visual_qa_model": qa_model,
        "visual_qa_verdict": qa_verdict[:240],
    }
    (out / "ASSET_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[STAGE 2 PASS] Generated {len(generated_files)} original HD sprites/icons/WAVs | Visual QA ({qa_model}): {qa_verdict[:120]}")


if __name__ == "__main__":
    main()
