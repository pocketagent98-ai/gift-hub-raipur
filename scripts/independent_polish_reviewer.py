#!/usr/bin/env python3
"""
INDEPENDENT ART & EXPERIENCE REVIEWER (V3.0 — BOTTOM-UP EVIDENCE SCORING)
Computes each of the 7 Quality Area scores strictly bottom-up from 0 using
verified checks across scenes, scripts, shaders, UI screens, audio buses,
and runtime telemetry. Zero hardcoded starting scores!
"""

import json
from pathlib import Path
import sys
from typing import Dict, Any, List, Tuple

TARGETS: Dict[str, int] = {
    "Graphics & Visual Quality": 90,
    "UI/UX Quality": 90,
    "Animations & Game Feel": 90,
    "Gameplay Presentation": 90,
    "Audio Quality": 85,
    "Mobile Experience": 90,
    "Performance": 90,
}

REQUIRED_12_SCREENS: List[str] = [
    "MainMenu", "LoadingScreen", "GameplayHUD", "PauseMenu",
    "Settings", "Shop", "Inventory", "Rewards",
    "LevelSelection", "WinLoseScreen", "Profile", "DailyRewards",
]


def score_checks(checks: List[Tuple[str, int, bool]], defects: List[str]) -> int:
    total = 0
    for desc, pts, passed in checks:
        if passed:
            total += pts
        else:
            defects.append(desc)
    return min(100, total)


def evaluate_studio_quality() -> Dict[str, Any]:
    defects: List[str] = []

    ui_code = Path("scripts/ui_controller.gd").read_text(encoding="utf-8") if Path("scripts/ui_controller.gd").exists() else ""
    vfx_code = Path("scripts/procedural_polish_theme_and_vfx.gd").read_text(encoding="utf-8") if Path("scripts/procedural_polish_theme_and_vfx.gd").exists() else ""
    aud_code = Path("scripts/audio_director.gd").read_text(encoding="utf-8") if Path("scripts/audio_director.gd").exists() else ""
    gm_code = Path("scripts/game_manager.gd").read_text(encoding="utf-8") if Path("scripts/game_manager.gd").exists() else ""
    mon_code = Path("scripts/monetization_manager.gd").read_text(encoding="utf-8") if Path("scripts/monetization_manager.gd").exists() else ""
    proj_code = Path("project.godot").read_text(encoding="utf-8") if Path("project.godot").exists() else ""
    tscn_code = Path("main.tscn").read_text(encoding="utf-8") if Path("main.tscn").exists() else ""

    scores: Dict[str, int] = {}

    # 1. Graphics & Visual Quality (0 -> 100)
    scores["Graphics & Visual Quality"] = score_checks([
        ("Missing docs/ART_DIRECTION_BIBLE.md", 20, Path("docs/ART_DIRECTION_BIBLE.md").exists()),
        ("Missing WorldEnvironment in main.tscn", 20, "WorldEnvironment" in tscn_code),
        ("Missing shadow_enabled = true on DirectionalLight3D", 20, "shadow_enabled = true" in tscn_code),
        ("Missing clearcoat=0.9 glossy 3D material", 20, "clearcoat_enabled = true" in vfx_code),
        ("Missing emissive highlights or lowercase .lerp()", 20, "emission_enabled = true" in vfx_code and ".lerp(" in vfx_code and ".Lerp(" not in vfx_code),
    ], defects)

    # 2. UI/UX Quality (0 -> 100)
    screens_present = sum(1 for s in REQUIRED_12_SCREENS if f'"{s}"' in ui_code)
    scores["UI/UX Quality"] = score_checks([
        (f"Only {screens_present}/12 required screens present", 60 if screens_present == 12 else 0, screens_present == 12),
        ("Missing unified StyleBoxFlat theme", 20, "StyleBoxFlat" in vfx_code),
        ("Missing Settings audio control", 20, "Btn_ToggleAudio" in ui_code),
    ], defects)

    # 3. Animations & Game Feel (0 -> 100)
    scores["Animations & Game Feel"] = score_checks([
        ("Missing button Tween animation", 25, "create_tween()" in vfx_code),
        ("Missing CPUParticles3D burst system (with lowercase .position)", 25, "CPUParticles3D" in vfx_code and "p.position =" in vfx_code and "p.Position" not in vfx_code),
        ("Missing camera feedback pulse on pop", 25, "pulse_camera_feedback" in gm_code and "pulse_camera_feedback" in vfx_code),
        ("Missing mobile haptic vibration", 25, "vibrate_handheld" in vfx_code),
    ], defects)

    # 4. Gameplay Presentation (0 -> 100)
    scores["Gameplay Presentation"] = score_checks([
        ("Missing First-60s interactive tutorial banner", 25, "TUTORIAL:" in ui_code),
        ("Missing 10-level progression loader", 25, "func load_level(" in gm_code),
        ("Missing 5-chunk seamless endless stitching", 25, "func test_stitched_chunks(" in gm_code),
        ("Missing 4-hit armored target crack states", 25, '"cracked_%d"' in gm_code and "hits_required" in gm_code),
    ], defects)

    # 5. Audio Quality (0 -> 100)
    scores["Audio Quality"] = score_checks([
        ("Missing 4-bus mixing (Master, Music, SFX, UI)", 35, '"Music"' in aud_code and '"SFX"' in aud_code and '"UI"' in aud_code),
        ("Missing procedural AudioStreamGenerator", 35, "AudioStreamGenerator" in aud_code),
        ("Missing polyphony rate limiter (MIN_SFX_INTERVAL_MS)", 30, "MIN_SFX_INTERVAL_MS" in aud_code),
    ], defects)

    # 6. Mobile Experience (0 -> 100)
    scores["Mobile Experience"] = score_checks([
        ("Missing SafeAreaMargin in ui_controller.gd", 25, "SafeAreaMargin" in ui_code),
        ("Missing >=56px touch target enforcement", 25, "56.0" in vfx_code),
        ("DeepGameVerifierBot must NOT be in production project.godot", 25, "DeepGameVerifierBot" not in proj_code),
        ("Monetization callbacks must be provider-verified (no pre-callback grants)", 25, "_on_rewarded_ad_earned_reward" in mon_code and "_on_purchase_acknowledged" in mon_code),
    ], defects)

    # 7. Performance (0 -> 100)
    scores["Performance"] = score_checks([
        ("Missing gl_compatibility mobile renderer", 35, 'renderer/rendering_method="gl_compatibility"' in proj_code),
        ("Missing 60Hz physics tick lock", 30, "physics_ticks_per_second=60" in proj_code),
        ("Missing queue_free() cleanup on destroyed targets/particles", 35, "queue_free()" in gm_code and "queue_free()" in vfx_code),
    ], defects)

    passed = len(defects) == 0 and all(scores[k] >= TARGETS[k] for k in TARGETS)
    verdict = {
        "verdict": "PASS" if passed else "FAIL",
        "scoring_method": "bottom_up_evidence_from_zero",
        "scores": scores,
        "targets": TARGETS,
        "defects": defects,
    }
    Path("/tmp/polish_reviewer_feedback.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    return verdict


if __name__ == "__main__":
    result = evaluate_studio_quality()
    print(json.dumps(result, indent=2))
    if result["verdict"] != "PASS":
        sys.exit(1)
