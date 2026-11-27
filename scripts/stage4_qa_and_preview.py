#!/usr/bin/env python3
"""
STAGE 4 — Xvfb Automated Playtesting, 4 Movie Maker MP4 Videos & Multimodal Vision QA (V7.0)
- Records ui_shop.mp4, mechanics_lab.mp4, multi_levels.mp4, save_ads_and_edge.mp4.
- Uses bundled imageio-ffmpeg (fast, zero apt stalls).
- Runs fallback Vision QA: gemini-3.5-flash-lite -> gemini-3.1-flash-lite -> nvidia/nemotron-3-nano-omni.
"""

import json
from pathlib import Path
import subprocess
import sys

import imageio_ffmpeg
from llm_router import gemini_video_qa

SUITES = (
    ("ui_shop", 115),
    ("mechanics_lab", 100),
    ("multi_levels", 155),
    ("save_ads_and_edge", 95),
)


def main() -> None:
    qa_dir = Path("/tmp/studio_qa")
    vid_dir = Path("/tmp/qa_videos")
    qa_dir.mkdir(parents=True, exist_ok=True)
    vid_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()

    results = []
    for suite, quit_frames in SUITES:
        avi = vid_dir / f"{suite}.avi"
        mp4 = vid_dir / f"{suite}.mp4"
        tel = qa_dir / f"telemetry_{suite}.txt"
        for p in (avi, mp4, tel):
            p.unlink(missing_ok=True)

        print(f"[STAGE 4] Recording Movie Maker QA suite: {suite} ({quit_frames} frames)...")
        subprocess.run(
            [
                "xvfb-run", "--auto-servernum", "-s", "-screen 0 720x1280x24",
                "godot", "--rendering-method", "gl_compatibility", "--rendering-driver", "opengl3",
                "--write-movie", str(avi), "--fixed-fps", "15", "--quit-after", str(quit_frames),
                "res://scenes/qa_bootstrap.tscn", "--", "--qa-mode=true", f"--suite={suite}", f"--qa-output-dir={qa_dir}",
            ],
            timeout=180,
            check=False,
        )

        if not tel.exists():
            raise RuntimeError(f"[QA_FAIL] Missing telemetry for suite {suite}")
        tel_txt = tel.read_text(encoding="utf-8")
        print(tel_txt)

        if "Status=COMPLETED" not in tel_txt or "QA_FAIL" in tel_txt:
            raise RuntimeError(f"[QA_FAIL] Telemetry check failed for {suite}")
        if suite == "multi_levels" and "[REAL_GAMEPLAY_VERIFIED]" not in tel_txt:
            raise RuntimeError("[QA_FAIL] multi_levels did not prove real interactive scoring!")
        if not avi.exists() or avi.stat().st_size < 1024:
            raise RuntimeError(f"[QA_FAIL] Missing Movie Maker AVI for {suite}")

        subprocess.run(
            [ffmpeg_bin, "-y", "-i", str(avi), "-vf", "scale=720:1280", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-c:a", "aac", "-b:a", "96k", str(mp4)],
            capture_output=True, timeout=90, check=True,
        )
        avi.unlink(missing_ok=True)

        qa_prompt = (
            f"Suite: {suite}\nTelemetry:\n{tel_txt}\n"
            "Verify real gameplay/UI transitions, zero horizontal clipping, and clean readability. "
            "Reply VERDICT: PASS or VERDICT: FAIL with a 1-sentence note."
        )
        verdict, model = gemini_video_qa(mp4, qa_prompt)
        print(f"[VISION_QA {suite} via {model}] {verdict[:240]}")
        if "VERDICT: FAIL" in verdict.upper():
            raise RuntimeError(f"[QA_FAIL] Vision Judge rejected {suite}: {verdict}")

        results.append({
            "suite": suite,
            "mp4": str(mp4),
            "size_bytes": mp4.stat().st_size,
            "vision_model": model,
            "verdict": verdict[:240],
        })

    out = Path("docs/generated")
    out.mkdir(parents=True, exist_ok=True)
    (out / "QA_REPORT.json").write_text(json.dumps({"status": "PASS", "suites": results}, indent=2), encoding="utf-8")
    md = ["# Stage 4 Automated Playtest & Movie Maker QA Report\n"]
    for r in results:
        md.append(f"- **{r['suite']}** (`{r['size_bytes']} bytes`, model `{r['vision_model']}`): {r['verdict']}")
    (out / "QA_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("[STAGE 4 PASS] All 4 Movie Maker QA videos & anti-demo checks verified!")


if __name__ == "__main__":
    main()
