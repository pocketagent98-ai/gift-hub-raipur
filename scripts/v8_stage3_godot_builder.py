#!/usr/bin/env python3
"""Stage 3 (V8.0): Autonomous Multi-Agent Godot 4.7.2 Game Builder + 3-Cycle Self-Heal.

Uses ONLY private NVIDIA_API_KEY + dynamically loaded multi-studio skills
(bullish0x/GameStudio, everything-game-dev-code, awesome-gamedev-agent-skills,
htdt/godogen) to generate the complete animated Godot 4.7.2 project, then
imports it in FULL Godot 4.7.2 GUI under Xvfb with up to 3 autonomous
self-heal passes on any SCRIPT ERROR / Parse Error.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from dynamic_skill_loader import load_stage_skills
from llm_router import call_nvidia, extract_json_block

TARGET_FILES = [
    "scripts/tween_juice.gd",
    "scripts/save_manager.gd",
    "scripts/audio_director.gd",
    "scripts/monetization_manager.gd",
    "scripts/game_manager.gd",
    "scripts/board_view.gd",
    "scripts/saga_level_map.gd",
    "scripts/ui_controller.gd",
    "scripts/test_driver.gd",
]


def _write_project_scaffolding(bp: Dict[str, Any]) -> None:
    title = bp.get("title", "AI Studio Game")
    project_godot = f"""config_version=5

[application]
config/name="{title}"
run/main_scene="res://main.tscn"
config/features=PackedStringArray("4.7", "GL Compatibility")
config/icon="res://assets/art/icon_512x512.png"

[autoload]
SaveManager="*res://scripts/save_manager.gd"
AudioDirector="*res://scripts/audio_director.gd"
MonetizationManager="*res://scripts/monetization_manager.gd"
TweenJuice="*res://scripts/tween_juice.gd"
GameManager="*res://scripts/game_manager.gd"
StudioUI="*res://scripts/ui_controller.gd"

[display]
window/size/viewport_width=720
window/size/viewport_height=1280
window/stretch/mode="canvas_items"
window/stretch/aspect="expand"
window/handheld/orientation=1

[gui]
theme/custom="res://assets/theme/studio_theme.tres"

[physics]
common/physics_ticks_per_second=60

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
"""
    Path("project.godot").write_text(project_godot, encoding="utf-8")

    Path("main.tscn").write_text(
        """[gd_scene format=3]

[node name="Main" type="Node2D"]
""",
        encoding="utf-8",
    )

    Path("scenes").mkdir(parents=True, exist_ok=True)
    Path("scenes/qa_bootstrap.tscn").write_text(
        """[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://scripts/test_driver.gd" id="1"]

[node name="QABootstrap" type="Node"]
script = ExtResource("1")
""",
        encoding="utf-8",
    )


def _generate_batch(bp: Dict[str, Any], skills_ctx: str, files_subset: List[str], role: str) -> Dict[str, str]:
    sys_prompt = (
        "You are a Senior Godot 4.7.2 Mobile Game Engineer. Write clean, strictly typed GDScript 4.7.2 "
        "(avoid Variant-inferred ':=' warnings; use explicit types like 'var x: float = floor(...)'). "
        "NEVER use ThemeDB.fallback_font (the project theme loads Fredoka-Bold.ttf). "
        "Use generated HD art textures in res://assets/art/ (bg_home.png, bg_map.png, bg_gameplay.png, piece_1..6.png), "
        "custom shaders in res://assets/shaders/ (animated_backdrop.gdshader, button_shine.gdshader, piece_gloss_pulse.gdshader), "
        "and audio in res://assets/audio/ (bgm_loop.wav, sfx_tap.wav, sfx_clear.wav, sfx_combo.wav, sfx_victory.wav). "
        "SagaLevelMap MUST use a curved winding Curve2D + Line2D path with pulsing level nodes — NEVER a flat 5x6 grid. "
        "test_driver.gd MUST exit immediately if OS.has_feature('release') or '--qa-mode=true' is absent, and must capture "
        "6 HD PNGs (01_loading.png..06_win_lose.png) and support Movie Maker suites (ui_shop, mechanics_lab, multi_levels, save_ads_and_edge). "
        "Return ONLY valid JSON mapping each requested file path to its complete GDScript source string."
    )
    user_prompt = (
        f"Studio Skills:\n{skills_ctx[:5500]}\n\n"
        f"Master Blueprint:\n{json.dumps(bp, indent=2)[:5500]}\n\n"
        f"Generate these exact GDScript files as a JSON object {{path: code}}:\n{json.dumps(files_subset)}"
    )
    res = call_nvidia(role, sys_prompt, user_prompt, max_tokens=6000, temperature=0.15)
    parsed = extract_json_block(res["text"])
    written: Dict[str, str] = {}
    for fpath in files_subset:
        code = parsed.get(fpath)
        if isinstance(code, str) and code.strip():
            dest = Path(fpath)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(code.strip() + "\n", encoding="utf-8")
            written[fpath] = res["model"]
    return written


def _run_godot_import_check() -> str:
    cmd = [
        "timeout", "-k", "15s", "180s",
        "xvfb-run", "--auto-servernum", "-s", "-screen 0 720x1280x24",
        "godot", "--editor", "--path", ".", "--import", "--quit",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    Path("/tmp/godot_v8_import.log").write_text(combined, encoding="utf-8")
    err_lines = [ln for ln in combined.splitlines() if re.search(r"SCRIPT ERROR|Parse Error|Failed to load script", ln)]
    return "\n".join(err_lines[:40])


def _self_heal_scripts(error_log: str, bp: Dict[str, Any]) -> None:
    mentioned = sorted(set(re.findall(r"res://(scripts/[A-Za-z0-9_]+\.gd)", error_log)))
    if not mentioned:
        mentioned = ["scripts/ui_controller.gd", "scripts/game_manager.gd", "scripts/board_view.gd"]
    current_code = {p: Path(p).read_text(encoding="utf-8", errors="replace") for p in mentioned if Path(p).exists()}
    sys_prompt = (
        "You are a Godot 4.7.2 Compiler Repair Agent. Fix ALL Parse Errors and SCRIPT ERRORs shown below. "
        "Return ONLY valid JSON mapping each file path to its complete fixed GDScript source."
    )
    user_prompt = (
        f"Godot 4.7.2 Import Errors:\n{error_log}\n\n"
        f"Current Files:\n{json.dumps(current_code)[:9000]}"
    )
    res = call_nvidia("fast_patch", sys_prompt, user_prompt, max_tokens=6000, temperature=0.1)
    patched = extract_json_block(res["text"])
    for fpath, code in patched.items():
        if isinstance(code, str) and code.strip() and fpath.startswith("scripts/"):
            Path(fpath).write_text(code.strip() + "\n", encoding="utf-8")
            print(f"[SELF_HEAL] Patched {fpath} via {res['model']}")


def run_stage3() -> None:
    bp = json.loads(Path("docs/MASTER_GAME_BLUEPRINT.json").read_text(encoding="utf-8"))
    skills = load_stage_skills("stage3")
    _write_project_scaffolding(bp)

    # Batch 1: Core systems & gameplay (nemotron-4-340b / kimi-k3.1-pro)
    _generate_batch(bp, skills["context_text"], TARGET_FILES[:6], role="core_coder")
    # Batch 2: Winding Saga Map, Animated UI & QA Driver (nemotron-3-super-120b)
    _generate_batch(bp, skills["context_text"], TARGET_FILES[6:], role="balanced_coder")

    # 3-cycle autonomous Godot 4.7.2 GUI import + self-heal loop
    for attempt in range(1, 4):
        errors = _run_godot_import_check()
        if not errors:
            print(f"[STAGE 3 PASS] Godot 4.7.2 GUI import succeeded with 0 script errors (attempt {attempt}).")
            return
        print(f"[STAGE 3 HEAL {attempt}/3] Godot script errors detected:\n{errors}")
        _self_heal_scripts(errors, bp)

    final_errors = _run_godot_import_check()
    if final_errors:
        raise RuntimeError(f"Godot 4.7.2 import still has script errors after 3 self-heal cycles:\n{final_errors}")


if __name__ == "__main__":
    run_stage3()
