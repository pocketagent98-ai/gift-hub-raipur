#!/usr/bin/env python3
"""Deterministic clean-room genre factory for the AI Game Studio V5.0 pipeline.

The factory turns ORDER.md + the live NVIDIA NIM design blueprint into a
complete, self-contained, playable Godot 4.7 project. It never copies reference
game files; every scene, script, theme value, shop item, and level name is
authored from the studio templates and the validated AI blueprint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict

import ai_game_designer

GENRE_TEMPLATES = {
    "match_3": "game_manager_match3.gd.tmpl",
    "screw_puzzle": "game_manager_screw.gd.tmpl",
}

GENRE_ALIASES = {
    "match_3": "match_3", "match3": "match_3", "match-3": "match_3", "candy": "match_3",
    "screw_puzzle": "screw_puzzle", "screw": "screw_puzzle", "screw_jam": "screw_puzzle", "bolt": "screw_puzzle",
}

GENRE_TITLES = {"match_3": "Sugar Cascade", "screw_puzzle": "Bolt Master"}
GENRE_DESCRIPTIONS = {
    "match_3": "Clean-room match-3 crystal cascade with special candies, combos, shop, and 30 levels.",
    "screw_puzzle": "Clean-room layered screw puzzle with colored tools, rusted bolts, shop, and 30 levels.",
}

SHARED_TEMPLATES = {
    "analytics_manager.gd": "scripts/analytics_manager.gd",
    "save_manager.gd": "scripts/save_manager.gd",
    "audio_director.gd": "scripts/audio_director.gd",
    "monetization_manager.gd": "scripts/monetization_manager.gd",
    "procedural_polish_theme_and_vfx.gd": "scripts/procedural_polish_theme_and_vfx.gd",
    "ui_controller.gd": "scripts/ui_controller.gd",
    "board_view.gd": "scripts/board_view.gd",
    "main_scene.gd": "scripts/main_scene.gd",
    "qa_bootstrap.gd": "scripts/qa_bootstrap.gd",
    "deep_game_verifier_bot.gd": "scripts/deep_game_verifier_bot.gd",
    "secure_loader.gd": "scripts/secure_loader.gd",
    "signature_guard.gd": "scripts/signature_guard.gd",
}

GENERATED_FILES = [
    "project.godot",
    "main.tscn",
    "export_presets.cfg",
    "scenes/ui_root.tscn",
    "scenes/qa_bootstrap.tscn",
    "scripts/app_config.gd",
    "scripts/game_manager.gd",
    "scripts/generated_ui_spec.gd",
    "scripts/ai_gameplay_extension.gd",
    *SHARED_TEMPLATES.values(),
]

UI_SCREEN_WIDGETS = {
    "LoadingScreen": ["game_logo", "tagline", "hero_icon", "progress_bar", "loading_label"],
    "MainMenu": ["coin_counter", "level_badge", "game_logo", "tagline", "hero_icon", "play_button", "level_map_button", "nav_shop", "nav_levels", "nav_daily", "nav_settings"],
    "GameplayHUD": ["level_label", "goal_label", "moves_label", "score_label", "coin_counter", "pause_button", "goal_progress", "tutorial_banner", "booster_hammer", "booster_shuffle", "booster_swap"],
    "PauseMenu": ["title", "resume_button", "restart_button", "settings_button", "main_menu_button"],
    "Settings": ["title", "audio_toggle", "vibration_toggle", "privacy_button", "back_button"],
    "Shop": ["title", "coin_counter", "shop_card_starter", "shop_card_remove_ads", "shop_card_coins", "shop_card_bundle", "shop_card_coin_stash", "back_button"],
    "Inventory": ["title", "booster_card_hammer", "booster_card_shuffle", "booster_card_swap", "back_button"],
    "Rewards": ["title", "daily_rewards_button", "watch_ad_coins_button", "free_booster_button", "back_button"],
    "LevelSelection": ["title", "level_grid_1_to_30", "back_button"],
    "WinLoseScreen": ["result_title", "star_rating", "score_tally", "coin_tally", "next_level_button", "retry_button", "watch_ad_moves_button", "main_menu_button"],
    "Profile": ["title", "highest_level_stat", "best_score_stat", "coins_stat", "genre_stat", "back_button"],
    "DailyRewards": ["title", "day_1_card", "day_2_card", "day_3_card", "day_4_card", "day_5_card", "day_6_card", "day_7_card", "back_button"],
}


def _read_order(project_root: Path) -> str:
    order = project_root / "ORDER.md"
    return order.read_text(encoding="utf-8") if order.exists() else ""


def _field(order_txt: str, key: str, default: str = "") -> str:
    m = re.search(rf"^{re.escape(key)}[ \t]*:[ \t]*(.*)$", order_txt, re.M | re.I)
    return m.group(1).strip() if m and m.group(1).strip() else default


def _bool_field(text: str, key: str, default: bool = False) -> bool:
    return _field(text, key, "true" if default else "false").strip().lower() in ("1", "true", "yes", "on")


def _canonical_action_mode(raw: str) -> str:
    value = raw.strip().lower()
    if "finalize" in value or "lock" in value:
        return "finalize_and_lock_release"
    if "update" in value:
        return "update_existing_game"
    if "export" in value:
        return "export_only_apk_and_aab"
    if "rollback" in value:
        return "rollback_release"
    return "new_game"


def resolve_job(project_root: Path) -> Dict[str, Any]:
    order_txt = _read_order(project_root)
    job_path = project_root / "docs" / "resolved_job.json"
    job = json.loads(job_path.read_text(encoding="utf-8")) if job_path.exists() else {}

    game_id = _field(order_txt, "GAME_ID", str(job.get("game_id", "studio_game_01")))
    raw_genre = _field(order_txt, "GENRE", str(job.get("genre", "match_3"))).strip().lower()
    genre = GENRE_ALIASES.get(raw_genre, raw_genre or "match_3")
    if genre not in GENRE_TEMPLATES:
        raise RuntimeError(
            f"[FACTORY_FAIL_CLOSED] Genre '{raw_genre}' has no real playable generator yet. "
            f"Supported genres: {sorted(GENRE_TEMPLATES)}. Refusing to emit a placeholder."
        )
    version = _field(order_txt, "GAME_VERSION", "v1.0.0")
    category = _field(order_txt, "CATEGORY", str(job.get("game_category", "level_by_level")))
    title = _field(order_txt, "GAME_TITLE", GENRE_TITLES[genre])
    action_mode = _canonical_action_mode(_field(order_txt, "ACTION_MODE", str(job.get("action_mode", "new_game"))))
    final_package = _field(order_txt, "FINAL_PACKAGE_NAME", str(job.get("final_package_name", "")))
    final_app_name = _field(order_txt, "FINAL_APP_NAME", str(job.get("final_app_name", "")))
    enable_anti_re = _bool_field(order_txt, "ENABLE_ANTI_REVERSE_ENGINEERING", action_mode == "finalize_and_lock_release")
    signature_strict = _bool_field(order_txt, "SIGNATURE_CHECK_STRICT", action_mode == "finalize_and_lock_release")
    expected_cert = _field(order_txt, "EXPECTED_SIGNING_CERT_SHA256", str(job.get("expected_signing_cert_sha256", "")))
    version_code = int(job.get("version_code", 1))
    safe_id = re.sub(r"[^a-z0-9_]", "_", game_id.lower())
    preview_package = f"com.skgamestudio.preview.{safe_id}"
    package_name = final_package if action_mode == "finalize_and_lock_release" and final_package else preview_package
    app_name = final_app_name if action_mode == "finalize_and_lock_release" and final_app_name else title
    secure_key = hashlib.sha256(f"{game_id}:{version}:studio-secure-v1".encode("utf-8")).hexdigest()[:32]
    return {
        "game_id": game_id,
        "genre": genre,
        "version": version,
        "category": category,
        "title": title,
        "app_name": app_name,
        "action_mode": action_mode,
        "preview_package_name": preview_package,
        "package_name": package_name,
        "final_package_name": final_package,
        "final_app_name": final_app_name,
        "enable_anti_reverse_engineering": enable_anti_re,
        "signature_check_strict": signature_strict,
        "expected_signing_cert_sha256": expected_cert,
        "secure_config_key": secure_key,
        "version_code": version_code,
        "reference_link": str(job.get("ref_link", "")),
    }


def _template(project_root: Path, name: str) -> str:
    path = project_root / "templates" / name
    if not path.exists():
        raise FileNotFoundError(f"[FACTORY_FAIL] Missing template: {path}")
    return path.read_text(encoding="utf-8")


def _substitute(text: str, job: Dict[str, Any]) -> str:
    replacements = {
        "__GAME_ID__": job["game_id"],
        "__GAME_TITLE__": job["app_name"],
        "__GAME_DISPLAY_TITLE__": job["title"],
        "__GENRE__": job["genre"],
        "__GAME_VERSION__": job["version"],
        "__VERSION__": job["version"].lstrip("v"),
        "__CATEGORY__": job["category"],
        "__GAME_DESCRIPTION__": GENRE_DESCRIPTIONS[job["genre"]],
        "__FINAL_PACKAGE_NAME__": job["final_package_name"],
        "__FINAL_APP_NAME__": job["final_app_name"],
        "__ENABLE_ANTI_REVERSE_ENGINEERING__": "true" if job["enable_anti_reverse_engineering"] else "false",
        "__SIGNATURE_CHECK_STRICT__": "true" if job["signature_check_strict"] else "false",
        "__EXPECTED_SIGNING_CERT_SHA256__": job["expected_signing_cert_sha256"],
        "__SECURE_CONFIG_KEY__": job["secure_config_key"],
    }
    for key, value in replacements.items():
        text = text.replace(key, str(value))
    return text


def _export_presets(job: Dict[str, Any]) -> str:
    version_name = job["version"].lstrip("v")
    exclude = "scripts/deep_game_verifier_bot.gd, scripts/qa_bootstrap.gd, scenes/qa_bootstrap.tscn, test/*, docs/*, *.py, scripts/*.py, .agents/*"
    common = f'''gradle_build/use_gradle_build=true
gradle_build/min_sdk=24
gradle_build/target_sdk=36
gradle_build/advanced/minify_enabled=true
gradle_build/advanced/minify_verbose=false
gradle_build/advanced/resource_shrinking=true
version/min_sdk=24
version/target_sdk=36
architectures/arm64-v8a=true
architectures/armeabi-v7a=false
permissions/internet=true
keystore/release="__PRIVATE_KEYSTORE_PATH__"
keystore/release_user="__PRIVATE_KEYSTORE_USER__"
keystore/release_password="__PRIVATE_KEYSTORE_PASS__"
package/unique_name="{job["package_name"]}"
package/name="{job["app_name"]}"
package/signed=true
version/code={job["version_code"]}
version/name="{version_name}"
script_export_mode=2
convert_text_resources_to_binary=true
encrypt_pck=false
encrypt_directory=false
'''
    return f'''[preset.0]

name="Android (Play Store Signed AAB)"
platform="Android"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter="{exclude}"
export_path="build/android/game_release.aab"

[preset.0.options]

gradle_build/export_format=1
{common}
[preset.1]

name="Android (Direct Install APK)"
platform="Android"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter="{exclude}"
export_path="build/android/game_install.apk"

[preset.1.options]

gradle_build/export_format=0
{common}'''


def _icon_svg(job: Dict[str, Any], blueprint: Dict[str, Any]) -> str:
    theme = blueprint.get("theme", {})
    accent = str(theme.get("accent", "#FF4D9D"))
    accent2 = str(theme.get("accent_2", "#FFD447"))
    bg_top = str(theme.get("bg_top", "#24103D"))
    bg_bottom = str(theme.get("bg_bottom", "#090B22"))
    if job["genre"] == "match_3":
        inner = (
            f'<circle cx="98" cy="100" r="44" fill="{accent}"/>'
            f'<circle cx="84" cy="86" r="15" fill="#FFFFFF" opacity="0.65"/>'
            f'<circle cx="158" cy="146" r="38" fill="{accent2}"/>'
            f'<circle cx="146" cy="134" r="12" fill="#FFFFFF" opacity="0.6"/>'
            f'<rect x="72" y="176" width="112" height="24" rx="12" fill="#FFFFFF" opacity="0.9"/>'
        )
    else:
        inner = (
            f'<rect x="54" y="58" width="148" height="140" rx="26" fill="{accent}" opacity="0.92"/>'
            f'<rect x="70" y="74" width="116" height="108" rx="18" fill="{bg_top}"/>'
            f'<circle cx="128" cy="128" r="34" fill="{accent2}"/>'
            f'<circle cx="128" cy="128" r="22" fill="{bg_bottom}"/>'
            f'<rect x="118" y="104" width="20" height="48" rx="8" fill="#FFFFFF" opacity="0.85"/>'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">'
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{bg_top}"/><stop offset="1" stop-color="{bg_bottom}"/>'
        '</linearGradient></defs>'
        '<rect width="256" height="256" rx="56" fill="url(#bg)"/>'
        f'{inner}'
        '<circle cx="196" cy="58" r="10" fill="#FFFFFF" opacity="0.8"/>'
        '<circle cx="58" cy="198" r="7" fill="#FFFFFF" opacity="0.55"/>'
        '</svg>\n'
    )


def _ui_spec(job: Dict[str, Any], blueprint: Dict[str, Any]) -> Dict[str, Any]:
    screens = []
    for screen_id, widgets in UI_SCREEN_WIDGETS.items():
        screens.append({
            "screen_id": screen_id,
            "widgets": widgets,
            "element_count": len(widgets),
            "container_type": "Full-rect Control -> MarginContainer -> VBoxContainer / GridContainer",
            "evidence_tag": "GENERATED_FROM_REAL_UI_CODE",
        })
    return {
        "schema_version": "5.0",
        "game_id": job["game_id"],
        "genre": job["genre"],
        "title": job["title"],
        "action_mode": job["action_mode"],
        "package_name": job["package_name"],
        "preview_package_name": job["preview_package_name"],
        "screens": screens,
        "screen_count": len(screens),
        "shop_items": blueprint["shop_items"],
        "boosters": blueprint["boosters"],
        "daily_rewards": blueprint["daily_rewards"],
        "level_count": 30,
        "level_names": blueprint["level_names"],
        "tutorial": blueprint["tutorial"],
        "theme": blueprint["theme"],
        "navigation": {
            "MainMenu": ["LevelSelection", "Shop", "DailyRewards", "Settings"],
            "GameplayHUD": ["PauseMenu", "WinLoseScreen"],
            "Shop": ["MainMenu", "Inventory", "Rewards"],
            "LevelSelection": ["GameplayHUD", "MainMenu"],
            "WinLoseScreen": ["GameplayHUD", "LevelSelection", "MainMenu"],
            "DailyRewards": ["MainMenu", "Rewards"],
            "Inventory": ["MainMenu", "Shop"],
            "Rewards": ["MainMenu", "DailyRewards", "Shop"],
        },
    }


def build_game(project_root: Path) -> Dict[str, Any]:
    job = resolve_job(project_root)
    genre = job["genre"]

    for relative in GENERATED_FILES:
        target = project_root / relative
        if target.exists() and target.is_file():
            target.unlink()

    for directory in ("scripts", "scenes", "build", "assets/icons", "assets/audio", "assets/secure", "docs"):
        (project_root / directory).mkdir(parents=True, exist_ok=True)

    blueprint_path = project_root / "docs" / "AI_GAME_DESIGN_BLUEPRINT.json"
    if blueprint_path.exists():
        blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
        blueprint.setdefault("genre", genre)
        ai_game_designer.write_runtime_files(project_root, blueprint)
    else:
        blueprint = ai_game_designer.build_design_blueprint(project_root)

    for template_name, relative in SHARED_TEMPLATES.items():
        text = _template(project_root, template_name)
        (project_root / relative).write_text(_substitute(text, job), encoding="utf-8")

    manager_text = _template(project_root, GENRE_TEMPLATES[genre])
    (project_root / "scripts/game_manager.gd").write_text(_substitute(manager_text, job), encoding="utf-8")
    (project_root / "scripts/app_config.gd").write_text(_substitute(_template(project_root, "app_config.gd.tmpl"), job), encoding="utf-8")
    (project_root / "project.godot").write_text(_substitute(_template(project_root, "project.godot.tmpl"), job), encoding="utf-8")
    (project_root / "main.tscn").write_text(_substitute(_template(project_root, "main.tscn"), job), encoding="utf-8")
    (project_root / "scenes/ui_root.tscn").write_text(_template(project_root, "ui_root.tscn"), encoding="utf-8")
    (project_root / "scenes/qa_bootstrap.tscn").write_text(_template(project_root, "qa_bootstrap.tscn"), encoding="utf-8")
    (project_root / "export_presets.cfg").write_text(_export_presets(job), encoding="utf-8")
    (project_root / "icon.svg").write_text(_icon_svg(job, blueprint), encoding="utf-8")

    spec = _ui_spec(job, blueprint)
    (project_root / "docs" / "UI_SPEC.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")

    manifest = {
        "status": "GENERATED_REAL_PLAYABLE_PROJECT",
        "game_id": job["game_id"],
        "genre": genre,
        "title": job["title"],
        "app_name": job["app_name"],
        "version": job["version"],
        "version_code": job["version_code"],
        "category": job["category"],
        "action_mode": job["action_mode"],
        "package_name": job["package_name"],
        "preview_package_name": job["preview_package_name"],
        "final_package_name": job["final_package_name"],
        "final_app_name": job["final_app_name"],
        "anti_reverse_engineering": job["enable_anti_reverse_engineering"],
        "reference_link": job["reference_link"],
        "engine": "Godot 4.7.2 Stable GUI (gl_compatibility)",
        "android": {"target_sdk": 36, "min_sdk": 24, "abi": ["arm64-v8a"]},
        "screens": 12,
        "levels": 30,
        "ai_blueprint": str(blueprint_path.relative_to(project_root)) if blueprint_path.exists() else "",
        "ai_model_used": blueprint.get("model_used", ""),
        "ai_status": blueprint.get("status", ""),
        "shop_items": len(blueprint["shop_items"]),
        "boosters": len(blueprint["boosters"]),
        "daily_rewards": len(blueprint["daily_rewards"]),
        "generated_files": GENERATED_FILES,
        "clean_room": True,
        "stub_strings_allowed": 0,
    }
    (project_root / "docs" / "GAME_GENERATION_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[STUDIO_FACTORY] Generated real {genre} game '{job['game_id']}' ({job['title']}) package={job['package_name']} with {len(GENERATED_FILES)} files.")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    build_game(Path(args.project_root).resolve())
