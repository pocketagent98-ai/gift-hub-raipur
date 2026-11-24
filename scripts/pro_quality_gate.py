#!/usr/bin/env python3
"""Fail-closed anti-stub and commercial-quality gate.

Stage 1 rejects empty / generic blueprints.
Stage 2 rejects placeholder UI, static non-interactive menus, missing genre
mechanics, and screens with fewer than three real widgets.
Stage 3 additionally requires the Zero-Bug Sentinel, four Movie Maker videos,
deterministic telemetry, and the strict Gemini visual critic (>= 85/100).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

FORBIDDEN_PATTERNS = [
    r"STUDIO\s*V2\.0",
    r"STUDIO\s*V5\.0\s*[-—]\s*",
    r"\bOpen\s+(GameplayHUD|PauseMenu|WinLoseScreen|DailyRewards|Inventory|Shop|MainMenu|LevelSelection|Settings|Profile|Rewards)\b",
    r"TUTORIAL:\s*Tap targets to fire",
    r"Purple Armored Bubbles",
]

REQUIRED_SCREENS = [
    "LoadingScreen", "MainMenu", "GameplayHUD", "PauseMenu", "Settings", "Shop",
    "Inventory", "Rewards", "LevelSelection", "WinLoseScreen", "Profile", "DailyRewards",
]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def scan_stub_strings(project_root: Path, genre: str) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    roots = [project_root / "scripts", project_root / "scenes"]
    files: List[Path] = []
    for root in roots:
        if root.exists():
            files.extend(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in (".gd", ".tscn", ".tres", ".json", ".cfg"))
    for name in ("main.tscn", "project.godot", "export_presets.cfg", "ORDER.md"):
        p = project_root / name
        if p.exists():
            files.append(p)
    docs = project_root / "docs"
    if docs.exists():
        files.extend(p for p in docs.glob("*") if p.is_file() and p.suffix.lower() == ".json")
    for path in sorted(set(files)):
        if any(part in {".git", "build", "android", "__pycache__", "user_research"} for part in path.parts):
            continue
        text = _read(path)
        for pattern in FORBIDDEN_PATTERNS:
            for m in re.finditer(pattern, text, re.I):
                if "Purple Armored Bubbles" in pattern and genre == "bubble_shooter":
                    continue
                line = text[:m.start()].count("\n") + 1
                findings.append({
                    "file": str(path.relative_to(project_root)),
                    "line": str(line),
                    "pattern": pattern,
                    "snippet": text[max(0, m.start() - 40):m.end() + 60].replace("\n", " "),
                })
    return findings


def check_stage1(project_root: Path, game_id: str, genre: str) -> List[str]:
    errors: List[str] = []
    fusion = _load_json(project_root / "docs/FUSION_BLUEPRINT.json")
    bible = _load_json(project_root / "docs/COMPLETE_GAME_BIBLE.json")
    blueprint = _load_json(project_root / "docs/AI_GAME_DESIGN_BLUEPRINT.json")
    if not fusion:
        errors.append("Stage 1 missing docs/FUSION_BLUEPRINT.json")
    if not bible:
        errors.append("Stage 1 missing docs/COMPLETE_GAME_BIBLE.json")
    if not blueprint:
        errors.append("Stage 1 missing docs/AI_GAME_DESIGN_BLUEPRINT.json")
    if blueprint:
        if len(blueprint.get("shop_items", [])) < 4:
            errors.append("AI blueprint has fewer than 4 real shop items")
        if len(blueprint.get("boosters", [])) < 3:
            errors.append("AI blueprint has fewer than 3 real boosters")
        if len(blueprint.get("level_names", [])) != 30:
            errors.append("AI blueprint must define exactly 30 level names")
        if len(blueprint.get("daily_rewards", [])) != 7:
            errors.append("AI blueprint must define exactly 7 daily rewards")
        theme = blueprint.get("theme", {})
        for key in ("bg_top", "bg_bottom", "accent", "panel", "text"):
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(theme.get(key, ""))):
                errors.append(f"AI blueprint theme.{key} is not a valid #RRGGBB color")
        if not str(blueprint.get("tutorial", "")).strip():
            errors.append("AI blueprint tutorial copy is empty")
    return errors


def check_stage2(project_root: Path, game_id: str, genre: str) -> tuple[List[str], List[Dict[str, str]]]:
    errors: List[str] = []
    stubs = scan_stub_strings(project_root, genre)
    if stubs:
        errors.append(f"Anti-stub ban: {len(stubs)} forbidden placeholder strings found")
    spec = _load_json(project_root / "docs/UI_SPEC.json")
    if not spec:
        errors.append("Missing docs/UI_SPEC.json (no declarative real-UI contract)")
    else:
        screens = {str(s.get("screen_id")): s for s in spec.get("screens", []) if isinstance(s, dict)}
        for screen in REQUIRED_SCREENS:
            if screen not in screens:
                errors.append(f"UI spec missing required screen '{screen}'")
            elif int(screens[screen].get("element_count", 0)) < 3:
                errors.append(f"UI screen '{screen}' has fewer than 3 real widgets")
        if len(spec.get("shop_items", [])) < 4:
            errors.append("UI spec shop has fewer than 4 real item cards")
        if len(spec.get("boosters", [])) < 3:
            errors.append("UI spec has fewer than 3 real boosters")
        if int(spec.get("level_count", 0)) != 30:
            errors.append("UI spec must expose a 30-level map")
        if len(spec.get("daily_rewards", [])) != 7:
            errors.append("UI spec must expose a 7-day reward calendar")
    ui = _read(project_root / "scripts/ui_controller.gd")
    gm = _read(project_root / "scripts/game_manager.gd")
    board = _read(project_root / "scripts/board_view.gd")
    project = _read(project_root / "project.godot")
    for builder in ("_build_loading", "_build_main_menu", "_build_gameplay_hud", "_build_shop", "_build_level_selection", "_build_daily_rewards", "_build_inventory", "_build_win_lose", "_build_pause_menu", "_build_settings", "_build_profile", "_build_rewards"):
        if builder not in ui:
            errors.append(f"ui_controller.gd missing real screen builder {builder}")
    for token in ("Spec.SHOP_ITEMS", "Spec.BOOSTERS", "Spec.DAILY_REWARDS", "GameManager.load_level", "GameManager.use_booster", "set_result", "update_hud"):
        if token not in ui:
            errors.append(f"ui_controller.gd missing real interactive hook {token}")
    for token in ("func load_level(", "func use_booster(", "func add_moves(", "func get_snapshot(", "target_score", "moves_left", "state = \"won\"", "state = \"lost\"", "handle_tap" if genre == "match_3" else "handle_screw_tap"):
        if token not in gm:
            errors.append(f"game_manager.gd missing gameplay substance token {token}")
    if genre == "match_3":
        for token in ("find_match_groups", "swap_cells", "_apply_gravity_and_refill", "specials", "armor"):
            if token not in gm:
                errors.append(f"match_3 manager missing real mechanic {token}")
    elif genre == "screw_puzzle":
        for token in ("is_screw_tappable", "handle_screw_tap", "_check_plate_completion", "plates", "screws", "tools"):
            if token not in gm:
                errors.append(f"screw manager missing real mechanic {token}")
    for token in ("_draw", "_gui_input", "cell_center" if genre == "match_3" else "handle_screw_tap"):
        if token not in board:
            errors.append(f"board_view.gd missing real interactive renderer token {token}")
    for token in ('window/stretch/mode="canvas_items"', 'window/stretch/aspect="expand"', 'run/main_scene="res://main.tscn"', 'StudioUI="*res://scenes/ui_root.tscn"', 'SecureLoader="*res://scripts/secure_loader.gd"'):
        if token not in project:
            errors.append(f"project.godot missing mobile viewport/autoload token {token}")
    manifest = _load_json(project_root / "docs/GAME_GENERATION_MANIFEST.json")
    if manifest.get("status") != "GENERATED_REAL_PLAYABLE_PROJECT":
        errors.append("GAME_GENERATION_MANIFEST.json does not certify a real playable project")
    if int(manifest.get("stub_strings_allowed", 1)) != 0:
        errors.append("GAME_GENERATION_MANIFEST.json allows stub strings")
    return errors, stubs


def _video_duration(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, timeout=20, check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            return float(out.stdout.strip())
    except Exception:
        pass
    try:
        import imageio_ffmpeg  # type: ignore
        return float(imageio_ffmpeg.count_frames_and_secs(str(path))[1])
    except Exception:
        return 0.0


def check_stage3(project_root: Path, game_id: str, genre: str, qa_dir: Path, video_dir: Path) -> List[str]:
    errors: List[str] = []
    sentinel = _load_json(project_root / "docs/ZERO_BUG_SENTINEL_REPORT.json")
    if sentinel.get("status") != "PASS":
        errors.append("Zero-Bug Sentinel report is not PASS")
    critic = _load_json(project_root / "docs/VISUAL_CRITIC_REPORT.json")
    if not critic:
        errors.append("Missing docs/VISUAL_CRITIC_REPORT.json")
    else:
        if float(critic.get("overall_score", 0)) < 85.0:
            errors.append(f"Visual critic score {critic.get('overall_score')} < 85")
        for flag in ("placeholder_art_detected", "empty_menus_detected", "static_noninteractive_detected", "broken_aspect_ratio_detected"):
            if bool(critic.get(flag, False)):
                errors.append(f"Visual critic rejected build: {flag}=true")
        for suite in ("ui_shop", "mechanics_lab", "multi_levels", "save_ads_and_edge"):
            item = critic.get("suites", {}).get(suite, {})
            if not item:
                errors.append(f"Visual critic missing suite '{suite}'")
            elif float(item.get("score", 0)) < 85.0:
                errors.append(f"Visual critic suite '{suite}' score {item.get('score')} < 85")
    expected_suites = ["ui_shop", "mechanics_lab", "multi_levels", "save_ads_and_edge"]
    if (project_root / "docs/GAME_GENERATION_MANIFEST.json").exists():
        manifest = _load_json(project_root / "docs/GAME_GENERATION_MANIFEST.json")
        if manifest.get("category") == "endless_map_chunks":
            expected_suites = ["ui_shop", "mechanics_lab", "endless_chunks", "save_ads_and_edge"]
    for suite in expected_suites:
        telemetry = qa_dir / f"telemetry_{suite}.txt"
        if not telemetry.exists() or telemetry.stat().st_size == 0:
            errors.append(f"Missing telemetry for suite '{suite}'")
        else:
            text = _read(telemetry)
            if "Status=COMPLETED" not in text:
                errors.append(f"Suite '{suite}' telemetry missing Status=COMPLETED")
            if "QA_FAIL" in text or "CRITICAL_ERROR" in text:
                errors.append(f"Suite '{suite}' telemetry contains a failure marker")
        video = video_dir / f"{suite}.mp4"
        if not video.exists() or video.stat().st_size < 10_000:
            errors.append(f"Missing or empty QA video '{suite}.mp4'")
        elif _video_duration(video) < 8.0:
            errors.append(f"QA video '{suite}.mp4' is shorter than 8 seconds")
    return errors


def run_gate(project_root: Path, stage: str, game_id: str, genre: str, qa_dir: Path, video_dir: Path) -> Dict[str, Any]:
    errors: List[str] = []
    stubs: List[Dict[str, str]] = []
    if stage == "stage1":
        errors.extend(check_stage1(project_root, game_id, genre))
    else:
        stage2_errors, stubs = check_stage2(project_root, game_id, genre)
        errors.extend(stage2_errors)
        if stage == "stage3":
            errors.extend(check_stage3(project_root, game_id, genre, qa_dir, video_dir))
    report = {
        "schema_version": "5.0",
        "status": "PASS" if not errors else "FAIL",
        "stage": stage,
        "game_id": game_id,
        "genre": genre,
        "checks": {
            "anti_stub_ban": "PASS" if not stubs else "FAIL",
            "real_ui_contract": "PASS" if not any("UI spec" in e or "ui_controller" in e for e in errors) else "FAIL",
            "gameplay_substance": "PASS" if not any("game_manager" in e or "board_view" in e for e in errors) else "FAIL",
            "visual_critic_85_plus": "PASS" if stage == "stage3" and not any("Visual critic" in e for e in errors) else ("NOT_EVALUATED" if stage != "stage3" else "FAIL"),
        },
        "stub_strings_found": stubs,
        "errors": errors,
        "repair_requests": errors,
        "evidence": {
            "ui_spec": str(project_root / "docs/UI_SPEC.json"),
            "generation_manifest": str(project_root / "docs/GAME_GENERATION_MANIFEST.json"),
            "visual_critic": str(project_root / "docs/VISUAL_CRITIC_REPORT.json"),
            "sentinel": str(project_root / "docs/ZERO_BUG_SENTINEL_REPORT.json"),
        },
    }
    out = project_root / "docs/PRO_QUALITY_GATE_REPORT.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    Path("/tmp/pro_quality_feedback.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--stage", choices=["stage1", "stage2", "stage3"], required=True)
    parser.add_argument("--game-id", default="unknown_game")
    parser.add_argument("--genre", default="match_3")
    parser.add_argument("--qa-dir", default="/tmp/studio_qa")
    parser.add_argument("--video-dir", default="/tmp/qa_videos")
    args = parser.parse_args()
    report = run_gate(Path(args.project_root).resolve(), args.stage, args.game_id, args.genre, Path(args.qa_dir), Path(args.video_dir))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
