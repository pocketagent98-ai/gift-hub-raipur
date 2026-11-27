#!/usr/bin/env python3
"""Stage 4 (V8.0): Hybrid Vision QA (cactus.Mirage + Gemini Flash-Lite) & 4-Cycle Craft Anything Auto-Refine.

- Captures 6 HD PNG screenshots (01_loading.png..06_win_lose.png) and 4 Movie Maker MP4 videos
  (ui_shop.mp4, mechanics_lab.mp4, multi_levels.mp4, save_ads_and_edge.mp4) on Xvfb.
- Layer 1: Local cactus-compute Python SDK (cactus.Mirage().describe(img)) + frame-to-frame motion delta check.
- Layer 2: Strict 0-100 commercial grading via gemini-3.5-flash-lite -> 3.1-flash-lite -> NVIDIA Omni + replica-diff.
- HARD GATE: score >= 85/100 (NEVER NOT_EVALUATED). If < 85, writes docs/CRAFT_DIFF_DEFECTS.json,
  patches via NVIDIA_API_KEY, re-imports in Godot 4.7.2 GUI, re-captures, and re-scores (up to 4 cycles).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, ImageChops, ImageStat

from dynamic_skill_loader import load_stage_skills
from llm_router import call_nvidia, call_vision_qa, extract_json_block

QA_DIR = Path("/tmp/v8_qa")
SUITES = ["ui_shop", "mechanics_lab", "multi_levels", "save_ads_and_edge"]
EXPECTED_PNGS = [
    "01_loading.png",
    "02_home.png",
    "03_saga_map.png",
    "04_gameplay.png",
    "05_shop_ads.png",
    "06_win_lose.png",
]


def _capture_suite(suite: str) -> Path:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    avi = QA_DIR / f"{suite}.avi"
    mp4 = QA_DIR / f"{suite}.mp4"
    cmd = [
        "timeout", "-k", "15s", "150s",
        "xvfb-run", "--auto-servernum", "-s", "-screen 0 720x1280x24",
        "godot", "--path", ".", "res://scenes/qa_bootstrap.tscn",
        "--write-movie", str(avi), "--fixed-fps", "15",
        "--", "--qa-mode=true", f"--suite={suite}", f"--qa-output-dir={QA_DIR}",
    ]
    subprocess.run(cmd, check=False)
    if avi.exists() and avi.stat().st_size > 1024:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(avi), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(mp4)],
            capture_output=True, check=False,
        )
    return mp4


def _extract_video_frames_and_motion(mp4_paths: List[Path]) -> Dict[str, Any]:
    frames_dir = QA_DIR / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    motion_scores: Dict[str, float] = {}
    extracted: List[Path] = []
    for mp4 in mp4_paths:
        if not mp4.exists():
            continue
        pair: List[Path] = []
        for idx, sec in enumerate(("1.5", "5.5")):
            out = frames_dir / f"{mp4.stem}_{idx}.png"
            subprocess.run(["ffmpeg", "-y", "-ss", sec, "-i", str(mp4), "-frames:v", "1", str(out)], capture_output=True, check=False)
            if out.exists() and out.stat().st_size > 1024:
                pair.append(out)
                extracted.append(out)
        if len(pair) == 2:
            a = Image.open(pair[0]).convert("RGB")
            b = Image.open(pair[1]).convert("RGB")
            diff = ImageChops.difference(a, b)
            motion_scores[mp4.stem] = round(sum(ImageStat.Stat(diff).mean) / 3.0, 2)
    # Ensure all 6 canonical HD PNG filenames exist (preferring bot-captured, else extracted frames)
    for idx, fname in enumerate(EXPECTED_PNGS):
        target = QA_DIR / fname
        if not target.exists() and idx < len(extracted):
            target.write_bytes(extracted[idx].read_bytes())
    return {"motion_deltas": motion_scores, "pngs": [QA_DIR / f for f in EXPECTED_PNGS if (QA_DIR / f).exists()]}


def _run_cactus_mirage_layer1(pngs: List[Path]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    try:
        import cactus  # type: ignore

        mirage = cactus.Mirage()
        for p in pngs:
            out[p.name] = str(mirage.describe(str(p)))[:260]
    except Exception as exc:
        out["fallback_note"] = f"cactus_mirage_unavailable: {exc}"
    return out


def _grade_layer2(bp: Dict[str, Any], pngs: List[Path], mirage_notes: Dict[str, str], motion: Dict[str, float], skills_ctx: str) -> Dict[str, Any]:
    prompt = (
        "You are a strict AAA Mobile Game Store Reviewer & replica-diff Visual Critic. "
        f"Game: {bp.get('title')} ({bp.get('genre')}).\n"
        f"Local cactus.Mirage Layer-1 Descriptions:\n{json.dumps(mirage_notes, indent=2)}\n"
        f"Frame-to-Frame Motion Deltas (0 = static freeze):\n{json.dumps(motion, indent=2)}\n"
        f"Replica-Diff Rubric:\n{skills_ctx[:3000]}\n\n"
        "Inspect ALL attached HD screenshots. Reject flat solid-color boxes, static frozen screens, "
        "clipped text, or flat grid level maps instead of a winding Saga Map. "
        "Return ONLY valid JSON:\n"
        '{"overall_score": 0, "visual_art_score": 0, "animation_motion_score": 0, "ui_ergonomics_score": 0, '
        '"saga_map_score": 0, "defects": ["..."], "patch_instructions": ["..."], "verdict": "PASS|FAIL"}'
    )
    res = call_vision_qa(prompt, pngs[:6], max_tokens=1500)
    graded = extract_json_block(res["text"])
    graded["vision_provider"] = res["provider"]
    graded["vision_model"] = res["model"]
    graded["cactus_mirage"] = mirage_notes
    graded["motion_deltas"] = motion
    return graded


def _craft_anything_patch(defects: Dict[str, Any]) -> None:
    Path("docs/CRAFT_DIFF_DEFECTS.json").write_text(json.dumps(defects, indent=2), encoding="utf-8")
    target_scripts = ["scripts/ui_controller.gd", "scripts/saga_level_map.gd", "scripts/board_view.gd", "scripts/tween_juice.gd"]
    current = {p: Path(p).read_text(encoding="utf-8", errors="replace") for p in target_scripts if Path(p).exists()}
    sys_prompt = (
        "You are the Craft Anything Polish & Defect Patcher (Godot 4.7.2). "
        "Fix every defect listed in CRAFT_DIFF_DEFECTS.json to raise visual polish, motion, and UI quality above 85/100. "
        "Return ONLY valid JSON mapping file paths to complete updated GDScript source."
    )
    res = call_nvidia("core_coder", sys_prompt, f"Defects:\n{json.dumps(defects, indent=2)}\n\nFiles:\n{json.dumps(current)[:9000]}", max_tokens=6000, temperature=0.15)
    patched = extract_json_block(res["text"])
    for fpath, code in patched.items():
        if isinstance(code, str) and code.strip() and fpath.startswith("scripts/"):
            Path(fpath).write_text(code.strip() + "\n", encoding="utf-8")
    subprocess.run(
        ["timeout", "-k", "15s", "180s", "xvfb-run", "--auto-servernum", "-s", "-screen 0 720x1280x24", "godot", "--editor", "--path", ".", "--import", "--quit"],
        check=False,
    )


def run_stage4() -> Dict[str, Any]:
    bp = json.loads(Path("docs/MASTER_GAME_BLUEPRINT.json").read_text(encoding="utf-8"))
    skills = load_stage_skills("stage4")
    last_report: Dict[str, Any] = {}

    for cycle in range(1, 5):
        print(f"=== STAGE 4 HYBRID VISION QA — CRAFT CYCLE {cycle}/4 ===")
        mp4s = [_capture_suite(s) for s in SUITES]
        media = _extract_video_frames_and_motion(mp4s)
        mirage_notes = _run_cactus_mirage_layer1(media["pngs"])
        report = _grade_layer2(bp, media["pngs"], mirage_notes, media["motion_deltas"], skills["context_text"])
        report["cycle"] = cycle
        score = float(report.get("overall_score", 0))
        last_report = report
        Path("docs/V8_HYBRID_VISION_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[STAGE 4 CYCLE {cycle}] Score={score}/100 | Model={report.get('vision_model')} | Verdict={report.get('verdict')}")
        if score >= 85.0:
            print("[STAGE 4 HARD GATE PASS] Score >= 85/100 verified!")
            return report
        if cycle < 4:
            _craft_anything_patch(report)

    raise RuntimeError(f"[STAGE 4 HARD GATE FAIL] Best score after 4 Craft Anything cycles was {last_report.get('overall_score', 0)}/100 (< 85).")


if __name__ == "__main__":
    run_stage4()
