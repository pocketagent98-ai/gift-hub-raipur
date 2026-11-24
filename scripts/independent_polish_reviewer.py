#!/usr/bin/env python3
"""Independent 7-dimension commercial polish reviewer.

Scores are computed bottom-up from real generated code, the declarative UI
contract, the AI blueprint, and the strict visual-critic report. Any dimension
below target (90, or 85 for audio/visual evidence) fails the stage.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

TARGETS: Dict[str, int] = {
    "Graphics & Visual Quality": 85,
    "UI/UX Quality": 90,
    "Animations & Game Feel": 90,
    "Gameplay Presentation": 90,
    "Audio Quality": 85,
    "Mobile Experience": 90,
    "Performance": 90,
}

REQUIRED_12_SCREENS = [
    "MainMenu", "LoadingScreen", "GameplayHUD", "PauseMenu",
    "Settings", "Shop", "Inventory", "Rewards",
    "LevelSelection", "WinLoseScreen", "Profile", "DailyRewards",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def score_checks(checks: List[Tuple[str, int, bool]], defects: List[str]) -> int:
    total = 0
    for desc, pts, passed in checks:
        if passed:
            total += pts
        else:
            defects.append(desc)
    return min(100, total)


def evaluate_studio_quality(project_root: Path = Path(".")) -> Dict[str, Any]:
    defects: List[str] = []
    ui = _read(project_root / "scripts/ui_controller.gd")
    vfx = _read(project_root / "scripts/procedural_polish_theme_and_vfx.gd")
    aud = _read(project_root / "scripts/audio_director.gd")
    gm = _read(project_root / "scripts/game_manager.gd")
    board = _read(project_root / "scripts/board_view.gd")
    main_scene = _read(project_root / "scripts/main_scene.gd")
    mon = _read(project_root / "scripts/monetization_manager.gd")
    project = _read(project_root / "project.godot")
    tscn = _read(project_root / "main.tscn")
    spec = _json(project_root / "docs/UI_SPEC.json")
    blueprint = _json(project_root / "docs/AI_GAME_DESIGN_BLUEPRINT.json")
    critic = _json(project_root / "docs/VISUAL_CRITIC_REPORT.json")
    manifest = _json(project_root / "docs/GAME_GENERATION_MANIFEST.json")

    visual_score = float(critic.get("overall_score", 0)) if critic else 0.0
    visual_suites = critic.get("suites", {}) if critic else {}
    screens = {str(s.get("screen_id")): s for s in spec.get("screens", []) if isinstance(s, dict)}
    screens_present = sum(1 for s in REQUIRED_12_SCREENS if s in screens and int(screens[s].get("element_count", 0)) >= 3)
    shop_cards = len(spec.get("shop_items", []))
    boosters = len(spec.get("boosters", []))
    daily = len(spec.get("daily_rewards", []))
    genre = str(manifest.get("genre", blueprint.get("genre", "match_3")))

    scores: Dict[str, int] = {}

    graphics_points = score_checks([
        ("Missing generated AI theme palette", 15, bool(blueprint.get("theme"))),
        ("Missing glossy beveled 3D decor in main_scene.gd", 20, "clearcoat" in main_scene and "SphereMesh" in main_scene or "TorusMesh" in main_scene),
        ("Missing real custom board renderer", 25, "func _draw(" in board and "draw_circle" in board and "draw_style_box" in board),
        ("Missing VFX burst/particles", 20, "burst_at_screen" in vfx and "CPUParticles3D" in vfx),
        ("Missing WorldEnvironment / lighting", 10, "WorldEnvironment" in tscn and "DirectionalLight3D" in tscn),
        ("Missing 12-screen theme consistency", 10, "Spec.THEME" in ui and "_theme_color" in ui),
    ], defects)
    if visual_score > 0:
        graphics_points = min(graphics_points, int(visual_score))
    scores["Graphics & Visual Quality"] = graphics_points

    scores["UI/UX Quality"] = score_checks([
        (f"Only {screens_present}/12 screens have >=3 real widgets", 40 if screens_present == 12 else 0, screens_present == 12),
        ("Missing full-rect safe-area layout", 15, "SafeAreaMargin" in ui and "PRESET_FULL_RECT" in ui),
        ("Missing >=56px touch targets", 15, "TOUCH_MIN" in ui and "Vector2(96, 56)" in ui),
        ("Missing real shop cards", 10, shop_cards >= 4),
        ("Missing 30-level map", 10, len(spec.get("level_names", [])) == 30),
        ("Missing 7-day daily rewards", 10, daily == 7),
    ], defects)

    scores["Animations & Game Feel"] = score_checks([
        ("Missing button Tween animation", 20, "create_tween()" in ui and "lightened(" in ui),
        ("Missing screen fade transitions", 15, "tween_property(screens[screen_name], \"modulate\"" in ui),
        ("Missing CPUParticles2D menu atmosphere", 15, "CPUParticles2D" in ui),
        ("Missing camera feedback pulse", 20, "pulse_camera_feedback" in gm and "pulse_camera_feedback" in vfx),
        ("Missing mobile haptic vibration", 15, "vibrate_handheld" in ui),
        ("Missing board animation loop", 15, "_process" in board and "queue_redraw" in board),
    ], defects)

    genre_tokens = ("find_match_groups", "specials", "armor") if genre == "match_3" else ("is_screw_tappable", "plates", "screws", "tools")
    scores["Gameplay Presentation"] = score_checks([
        ("Missing real level loader", 20, "func load_level(" in gm),
        ("Missing boosters", 15, "func use_booster(" in gm and boosters >= 3),
        ("Missing genre-specific mechanics", 25, all(t in gm for t in genre_tokens)),
        ("Missing win/lose state machine", 15, "state = \"won\"" in gm and "state = \"lost\"" in gm),
        ("Missing 30-level tuning", 10, len(blueprint.get("level_names", [])) == 30),
        ("Missing touch input handler", 15, "handle_tap" in gm or "handle_screw_tap" in gm),
    ], defects)

    audio_score = score_checks([
        ("Missing 4-bus mixing (Master, Music, SFX, UI)", 35, '"Music"' in aud and '"SFX"' in aud and '"UI"' in aud),
        ("Missing procedural AudioStreamGenerator", 25, "AudioStreamGenerator" in aud or "_tone(" in aud),
        ("Missing polyphony rate limiter", 20, "MIN_SFX_INTERVAL_MS" in aud),
        ("Missing generated 44.1kHz WAV assets", 20, len(list((project_root / "assets/audio").glob("*.wav"))) >= 4 if (project_root / "assets/audio").exists() else False),
    ], defects)
    audio_critic = float(visual_suites.get("mechanics_lab", {}).get("audio_vfx_feedback", 0)) if visual_suites else 0.0
    if 0 < audio_critic < 60:
        audio_score = min(audio_score, int(audio_critic))
    scores["Audio Quality"] = audio_score

    scores["Mobile Experience"] = score_checks([
        ("Missing 720x1280 canvas_items stretch", 20, 'window/size/viewport_width=720' in project and 'window/stretch/mode="canvas_items"' in project),
        ("Missing expand aspect", 15, 'window/stretch/aspect="expand"' in project),
        ("Missing safe-area margins", 15, "margin_left" in ui and "margin_right" in ui),
        ("DeepGameVerifierBot must NOT be in production project.godot", 20, "DeepGameVerifierBot" not in project),
        ("Missing provider-gated monetization callbacks", 30, "_on_rewarded_ad_earned_reward" in mon and "_on_purchase_acknowledged" in mon),
    ], defects)

    scores["Performance"] = score_checks([
        ("Missing gl_compatibility renderer", 30, 'renderer/rendering_method="gl_compatibility"' in project),
        ("Missing 60Hz physics tick lock", 25, "physics_ticks_per_second=60" in project),
        ("Missing queue_free cleanup", 20, "queue_free()" in gm or "queue_free()" in vfx),
        ("Missing sprite/candy batching draw loop", 25, "queue_redraw" in board and "draw_circle" in board),
    ], defects)

    if critic:
        if critic.get("status") != "PASS":
            defects.append("Strict visual critic report status is not PASS")
        for flag in ("placeholder_art_detected", "empty_menus_detected", "static_noninteractive_detected", "broken_aspect_ratio_detected"):
            if bool(critic.get(flag, False)):
                defects.append(f"Strict visual critic rejected: {flag}")

    passed = len(defects) == 0 and all(scores[k] >= TARGETS[k] for k in TARGETS)
    verdict = {
        "verdict": "PASS" if passed else "FAIL",
        "scoring_method": "bottom_up_evidence_from_zero_with_strict_visual_critic",
        "game_id": manifest.get("game_id", ""),
        "genre": genre,
        "scores": scores,
        "targets": TARGETS,
        "defects": defects,
        "anti_stub": {
            "screen_widget_contract": f"{screens_present}/12",
            "shop_cards": shop_cards,
            "boosters": boosters,
            "daily_rewards": daily,
            "stub_strings_allowed": 0,
        },
        "visual_critic": {
            "overall_score": visual_score,
            "status": critic.get("status", "NOT_EVALUATED"),
            "suites": {k: v.get("score") for k, v in visual_suites.items() if isinstance(v, dict)},
        },
    }
    (project_root / "docs/INDEPENDENT_POLISH_REVIEW.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    Path("/tmp/polish_reviewer_feedback.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    return verdict


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    result = evaluate_studio_quality(root)
    print(json.dumps(result, indent=2))
    if result["verdict"] != "PASS":
        sys.exit(1)
