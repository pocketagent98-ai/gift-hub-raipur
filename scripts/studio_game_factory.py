#!/usr/bin/env python3
"""Deterministic clean-room genre factory for the AI Game Studio V5.0 pipeline.

The factory turns the resolved ORDER.md + Stage 1 blueprints into a complete,
self-contained Godot 4.7 project. It never copies reference game files; every
scene, script, shader value, and gameplay rule is authored from the studio
templates in `templates/`.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict

GENRE_TEMPLATES = {
    "match_3": "game_manager_match3.gd.tmpl",
    "screw_puzzle": "game_manager_screw.gd.tmpl",
}

GENRE_ALIASES = {
    "match_3": "match_3",
    "match3": "match_3",
    "match-3": "match_3",
    "candy": "match_3",
    "screw_puzzle": "screw_puzzle",
    "screw": "screw_puzzle",
    "screw_jam": "screw_puzzle",
    "bolt": "screw_puzzle",
    "puzzle": "screw_puzzle",
}

GENRE_TITLES = {
    "match_3": "Sugar Cascade",
    "screw_puzzle": "Bolt Master",
}

GENRE_DESCRIPTIONS = {
    "match_3": "Clean-room match-3 crystal cascade with armored crystals, combos, and 30 levels.",
    "screw_puzzle": "Clean-room layered screw puzzle with colored tools, rusted bolts, and 30 levels.",
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
}

GENERATED_FILES = [
    "project.godot",
    "main.tscn",
    "export_presets.cfg",
    "scenes/ui_root.tscn",
    "scenes/qa_bootstrap.tscn",
    "scripts/app_config.gd",
    "scripts/game_manager.gd",
    *SHARED_TEMPLATES.values(),
]


def _read_order(project_root: Path) -> str:
    order = project_root / "ORDER.md"
    return order.read_text(encoding="utf-8") if order.exists() else ""


def _field(order_txt: str, key: str, default: str = "") -> str:
    m = re.search(rf"^{re.escape(key)}[ \t]*:[ \t]*(.*)$", order_txt, re.M | re.I)
    return m.group(1).strip() if m and m.group(1).strip() else default


def resolve_job(project_root: Path) -> Dict[str, str]:
    order_txt = _read_order(project_root)
    job_path = project_root / "docs" / "resolved_job.json"
    job = json.loads(job_path.read_text(encoding="utf-8")) if job_path.exists() else {}

    game_id = _field(order_txt, "GAME_ID", str(job.get("game_id", "studio_game_01")))
    raw_genre = _field(order_txt, "GENRE", str(job.get("genre", "match_3"))).strip().lower()
    genre = GENRE_ALIASES.get(raw_genre, "match_3")
    if genre not in GENRE_TEMPLATES:
        genre = "match_3"
    version = _field(order_txt, "GAME_VERSION", "v1.0.0")
    category = _field(order_txt, "CATEGORY", str(job.get("game_category", "level_by_level")))
    title = _field(order_txt, "GAME_TITLE", GENRE_TITLES[genre])
    return {
        "game_id": game_id,
        "genre": genre,
        "version": version,
        "category": category,
        "title": title,
        "reference_link": str(job.get("ref_link", "")),
    }


def _template(project_root: Path, name: str) -> str:
    path = project_root / "templates" / name
    if not path.exists():
        raise FileNotFoundError(f"[FACTORY_FAIL] Missing template: {path}")
    return path.read_text(encoding="utf-8")


def _substitute(text: str, job: Dict[str, str]) -> str:
    replacements = {
        "__GAME_ID__": job["game_id"],
        "__GAME_TITLE__": job["title"],
        "__GENRE__": job["genre"],
        "__GAME_VERSION__": job["version"],
        "__VERSION__": job["version"].lstrip("v"),
        "__CATEGORY__": job["category"],
        "__GAME_DESCRIPTION__": GENRE_DESCRIPTIONS[job["genre"]],
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def _export_presets(job: Dict[str, str]) -> str:
    package_name = "com.aistudio.cleanroomgame"
    version_name = job["version"].lstrip("v")
    exclude = "scripts/deep_game_verifier_bot.gd, scripts/qa_bootstrap.gd, scenes/qa_bootstrap.tscn, test/*, docs/*"
    common = f'''gradle_build/use_gradle_build=true
gradle_build/min_sdk=24
gradle_build/target_sdk=36
version/min_sdk=24
version/target_sdk=36
architectures/arm64-v8a=true
architectures/armeabi-v7a=false
permissions/internet=false
keystore/release="__PRIVATE_KEYSTORE_PATH__"
keystore/release_user="__PRIVATE_KEYSTORE_USER__"
keystore/release_password="__PRIVATE_KEYSTORE_PASS__"
package/unique_name="{package_name}"
package/name="{job["title"]}"
package/signed=true
version/code=1
version/name="1.0.0"
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


def _icon_svg(job: Dict[str, str]) -> str:
    if job["genre"] == "match_3":
        inner = (
            '<circle cx="128" cy="128" r="78" fill="#2b6cf6"/>'
            '<circle cx="104" cy="104" r="26" fill="#ffffff" opacity="0.55"/>'
            '<rect x="66" y="180" width="124" height="20" rx="10" fill="#ffd447"/>'
        )
    else:
        inner = (
            '<circle cx="128" cy="128" r="80" fill="#ff5b6e"/>'
            '<rect x="84" y="120" width="88" height="16" rx="8" fill="#1b2333"/>'
            '<rect x="120" y="84" width="16" height="88" rx="8" fill="#1b2333"/>'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">'
        '<rect width="256" height="256" rx="48" fill="#0d1730"/>'
        f'{inner}'
        '</svg>\n'
    )


def build_game(project_root: Path) -> Dict[str, Any]:
    job = resolve_job(project_root)
    genre = job["genre"]

    for relative in GENERATED_FILES:
        target = project_root / relative
        if target.exists() and target.is_file():
            target.unlink()

    for directory in ("scripts", "scenes", "build"):
        (project_root / directory).mkdir(parents=True, exist_ok=True)

    for template_name, relative in SHARED_TEMPLATES.items():
        text = _template(project_root, template_name)
        (project_root / relative).write_text(_substitute(text, job), encoding="utf-8")

    manager_text = _template(project_root, GENRE_TEMPLATES[genre])
    (project_root / "scripts/game_manager.gd").write_text(_substitute(manager_text, job), encoding="utf-8")

    app_config = _substitute(_template(project_root, "app_config.gd.tmpl"), job)
    (project_root / "scripts/app_config.gd").write_text(app_config, encoding="utf-8")

    (project_root / "project.godot").write_text(_substitute(_template(project_root, "project.godot.tmpl"), job), encoding="utf-8")
    (project_root / "main.tscn").write_text(_substitute(_template(project_root, "main.tscn"), job), encoding="utf-8")
    (project_root / "scenes/ui_root.tscn").write_text(_template(project_root, "ui_root.tscn"), encoding="utf-8")
    (project_root / "scenes/qa_bootstrap.tscn").write_text(_template(project_root, "qa_bootstrap.tscn"), encoding="utf-8")
    (project_root / "export_presets.cfg").write_text(_export_presets(job), encoding="utf-8")
    (project_root / "icon.svg").write_text(_icon_svg(job), encoding="utf-8")

    manifest = {
        "status": "GENERATED",
        "game_id": job["game_id"],
        "genre": genre,
        "title": job["title"],
        "version": job["version"],
        "category": job["category"],
        "reference_link": job["reference_link"],
        "engine": "Godot 4.7.2 Stable GUI (gl_compatibility)",
        "android": {"target_sdk": 36, "min_sdk": 24, "abi": ["arm64-v8a"]},
        "screens": 12,
        "levels": 30,
        "mechanics": {
            "match_3": {
                "board": "8x8",
                "min_match": 3,
                "armored_hits": 4,
                "scoring": "20 per cleared cell x cascade multiplier; armored hit 15 x cascade",
            },
            "screw_puzzle": {
                "plates": "3..9 layered plates",
                "tools": 3,
                "temp_capacity": 3,
                "rusted_hits": 4,
                "scoring": "screw 100, plate 500, rusted hit 25",
            },
        }[genre],
        "generated_files": GENERATED_FILES,
        "clean_room": True,
    }
    docs = project_root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "GAME_GENERATION_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[STUDIO_FACTORY] Generated {genre} game '{job['game_id']}' ({job['title']}) with {len(GENERATED_FILES)} files.")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    build_game(Path(args.project_root).resolve())
