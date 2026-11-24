#!/usr/bin/env python3
"""Live NVIDIA NIM game-design blueprint + runtime extension generator.

The designer asks the private NVIDIA NIM coding route for a strict JSON design
blueprint (theme, shop, boosters, level names, daily rewards, tutorial copy),
validates it, and writes:

  docs/AI_GAME_DESIGN_BLUEPRINT.json
  docs/AI_GENERATION_PROOF.json
  scripts/generated_ui_spec.gd
  scripts/ai_gameplay_extension.gd

The generated GDScript is deliberately small and import-validated by the
workflow. If the live model is unavailable or returns invalid JSON, the
deterministic genre fallback is used so the build never silently degrades into
a placeholder game.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

NVIDIA_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-4-340b-instruct",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia/nemotron-nano-3-30b-a3b",
    "nvidia/kimi-k3.1-pro",
    "google/gemma-4-31b-it",
]

GENRE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "match_3": {
        "game_title": "Sugar Cascade",
        "tagline": "Swap. Match. Cascade into sweetness.",
        "theme": {
            "bg_top": "#24103D",
            "bg_bottom": "#090B22",
            "accent": "#FF4D9D",
            "accent_2": "#FFD447",
            "panel": "#1B1238",
            "panel_alt": "#2A1A52",
            "text": "#FFF7FF",
            "text_dim": "#C9B8E8",
            "success": "#54E39A",
            "danger": "#FF5D6C",
            "board": "#160D2D",
            "gem_colors": ["#FF4D6D", "#4DA3FF", "#54E39A", "#FFD447", "#B36BFF", "#33E0E8"],
        },
        "tutorial": "Swap two neighboring candies to match 3 or more. Match 4+ to create a power candy!",
        "boosters": [
            {"id": "hammer", "name": "Hammer", "desc": "Smash one candy instantly.", "price_coins": 150, "icon": "bomb_hazard"},
            {"id": "shuffle", "name": "Shuffle", "desc": "Re-mix the whole board.", "price_coins": 120, "icon": "shield_armor"},
            {"id": "swap", "name": "Swap", "desc": "Swap any two candies.", "price_coins": 100, "icon": "btn_play"},
        ],
        "shop_items": [
            {"sku": "starter_pack", "title": "Starter Pack", "desc": "1,200 coins + 3 hammers", "price_label": "₹89", "kind": "iap", "icon": "coin_badge", "reward_coins": 1200, "reward_booster": "hammer"},
            {"sku": "remove_ads", "title": "Remove Ads", "desc": "Play forever without interstitials.", "price_label": "₹249", "kind": "iap", "icon": "shield_armor", "reward_coins": 0, "reward_booster": ""},
            {"sku": "coins_small", "title": "Coin Pack", "desc": "2,600 shiny coins.", "price_label": "₹199", "kind": "iap", "icon": "coin_badge", "reward_coins": 2600, "reward_booster": ""},
            {"sku": "booster_bundle", "title": "Booster Bundle", "desc": "2 hammers + 2 shuffles + 2 swaps", "price_label": "₹149", "kind": "iap", "icon": "bomb_hazard", "reward_coins": 0, "reward_booster": "bundle"},
            {"sku": "coins_150", "title": "Mega Vault", "desc": "7,500 coins + 2 boosters", "price_label": "₹499", "kind": "iap", "icon": "coin_badge", "reward_coins": 7500, "reward_booster": "hammer"},
        ],
        "level_names": [
            "Sugar Meadow", "Jelly Grove", "Cocoa Cove", "Lollipop Lane", "Gumdrop Gate",
            "Marshmallow Bay", "Caramel Creek", "Frosting Falls", "Taffy Terrace", "Sherbet Shore",
            "Bonbon Bluff", "Toffee Tower", "Mint Hollow", "Candy Canyon", "Licorice Loop",
            "Peach Plateau", "Vanilla Vale", "Berry Bazaar", "Cinnamon Spire", "Honey Harbor",
            "Fudge Fortress", "Praline Peak", "Nougat Nexus", "Truffle Temple", "Marzipan Maze",
            "Sorbet Summit", "Dulce Depot", "Gelato Garden", "Fondant Foundry", "Royal Sugar Palace",
        ],
        "daily_rewards": [
            {"day": 1, "coins": 50, "booster": ""}, {"day": 2, "coins": 75, "booster": ""},
            {"day": 3, "coins": 100, "booster": "hammer"}, {"day": 4, "coins": 125, "booster": ""},
            {"day": 5, "coins": 150, "booster": "shuffle"}, {"day": 6, "coins": 200, "booster": ""},
            {"day": 7, "coins": 300, "booster": "swap"},
        ],
        "visual_motifs": ["glossy candy gems", "chocolate board frame", "sprinkle particles", "neon candy trail"],
        "special_rule": "Match 4 creates a striped candy; match 5 creates a color bomb.",
    },
    "screw_puzzle": {
        "game_title": "Bolt Master",
        "tagline": "Unscrew the layers. Free the plates.",
        "theme": {
            "bg_top": "#10243A",
            "bg_bottom": "#071018",
            "accent": "#FF9F1C",
            "accent_2": "#38BDF8",
            "panel": "#132C44",
            "panel_alt": "#1B3D5C",
            "text": "#F2FBFF",
            "text_dim": "#A9C7DD",
            "success": "#54E39A",
            "danger": "#FF5D6C",
            "board": "#0A1A28",
            "gem_colors": ["#FF5D6C", "#4DA3FF", "#54E39A", "#FFD447", "#B36BFF", "#33E0E8"],
        },
        "tutorial": "Tap a screw that matches one of your three tools. Wrong colors fill the holding slots. Free every plate!",
        "boosters": [
            {"id": "hammer", "name": "Power Wrench", "desc": "Remove one screw instantly.", "price_coins": 150, "icon": "bomb_hazard"},
            {"id": "shuffle", "name": "Tool Refresh", "desc": "Re-roll the three tools.", "price_coins": 120, "icon": "shield_armor"},
            {"id": "swap", "name": "Extra Slot", "desc": "Clear one holding slot.", "price_coins": 100, "icon": "btn_play"},
        ],
        "shop_items": [
            {"sku": "starter_pack", "title": "Starter Crate", "desc": "1,200 bolts + 3 power wrenches", "price_label": "₹89", "kind": "iap", "icon": "coin_badge", "reward_coins": 1200, "reward_booster": "hammer"},
            {"sku": "remove_ads", "title": "Remove Ads", "desc": "Play forever without interstitials.", "price_label": "₹249", "kind": "iap", "icon": "shield_armor", "reward_coins": 0, "reward_booster": ""},
            {"sku": "coins_small", "title": "Bolt Pack", "desc": "2,600 bolts.", "price_label": "₹199", "kind": "iap", "icon": "coin_badge", "reward_coins": 2600, "reward_booster": ""},
            {"sku": "booster_bundle", "title": "Power Tool Bundle", "desc": "2 wrenches + 2 refreshes + 2 slots", "price_label": "₹149", "kind": "iap", "icon": "bomb_hazard", "reward_coins": 0, "reward_booster": "bundle"},
            {"sku": "coins_150", "title": "Bolt Vault", "desc": "7,500 bolts + 2 power tools", "price_label": "₹499", "kind": "iap", "icon": "coin_badge", "reward_coins": 7500, "reward_booster": "hammer"},
        ],
        "level_names": [
            "Rusty Workshop", "Copper Clamp", "Steel Shelf", "Brass Bracket", "Iron Hinge",
            "Chrome Crate", "Titanium Tray", "Alloy Alcove", "Cobalt Cabinet", "Nickel Nook",
            "Zinc Zone", "Silver Stack", "Bronze Bay", "Magnet Mill", "Piston Plant",
            "Gear Garage", "Bolt Bunker", "Cog Castle", "Rivet Ridge", "Anvil Alley",
            "Wrench Works", "Clamp Canyon", "Screw Summit", "Plate Plateau", "Torque Tower",
            "Drill Depot", "Fastener Fort", "Metal Maze", "Tool Temple", "Master Machine",
        ],
        "daily_rewards": [
            {"day": 1, "coins": 50, "booster": ""}, {"day": 2, "coins": 75, "booster": ""},
            {"day": 3, "coins": 100, "booster": "hammer"}, {"day": 4, "coins": 125, "booster": ""},
            {"day": 5, "coins": 150, "booster": "shuffle"}, {"day": 6, "coins": 200, "booster": ""},
            {"day": 7, "coins": 300, "booster": "swap"},
        ],
        "visual_motifs": ["brushed metal plates", "glowing screws", "orange sparks", "industrial toolbox"],
        "special_rule": "Rusted bolts need four hits; blocked layers unlock only when the plate above falls.",
    },
}

GENRE_ALIASES = {
    "match_3": "match_3", "match3": "match_3", "match-3": "match_3", "candy": "match_3",
    "screw_puzzle": "screw_puzzle", "screw": "screw_puzzle", "screw_jam": "screw_puzzle", "bolt": "screw_puzzle",
}


def _field(text: str, key: str, default: str = "") -> str:
    m = re.search(rf"^{re.escape(key)}[ \t]*:[ \t]*(.*)$", text, re.M | re.I)
    return m.group(1).strip() if m and m.group(1).strip() else default


def _canonical_genre(raw: str) -> str:
    value = raw.strip().lower()
    return GENRE_ALIASES.get(value, value or "match_3")


def _defaults(genre: str) -> Dict[str, Any]:
    return json.loads(json.dumps(GENRE_DEFAULTS.get(genre, GENRE_DEFAULTS["match_3"])))


def _merge(defaults: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    merged = json.loads(json.dumps(defaults))
    for key, value in candidate.items():
        if key in ("theme",) and isinstance(value, dict):
            merged["theme"].update({k: v for k, v in value.items() if isinstance(v, (str, int, float, list))})
        elif key in ("shop_items", "boosters", "daily_rewards", "level_names", "visual_motifs") and isinstance(value, list) and value:
            merged[key] = value
        elif isinstance(value, (str, int, float, bool)):
            merged[key] = value
    # Keep the generated UI safe: exactly 30 level names and 7 daily rewards.
    names = [str(x) for x in merged.get("level_names", []) if str(x).strip()]
    while len(names) < 30:
        names.append(f"Level {len(names) + 1}")
    merged["level_names"] = names[:30]
    rewards = [x for x in merged.get("daily_rewards", []) if isinstance(x, dict)]
    merged["daily_rewards"] = (rewards + defaults["daily_rewards"])[:7]
    if len(merged.get("shop_items", [])) < 4:
        merged["shop_items"] = defaults["shop_items"]
    if len(merged.get("boosters", [])) < 3:
        merged["boosters"] = defaults["boosters"]
    for key in ("game_title", "tagline", "tutorial", "special_rule"):
        if not str(merged.get(key, "")).strip():
            merged[key] = defaults[key]
    theme = merged.get("theme", {})
    for key, value in defaults["theme"].items():
        theme.setdefault(key, value)
    merged["theme"] = theme
    return merged


def _call_nim(prompt: str, nv_key: str) -> tuple[str, str]:
    for model_id in NVIDIA_MODELS:
        try:
            payload = json.dumps({
                "model": model_id,
                "messages": [
                    {"role": "system", "content": "You are a senior commercial mobile game designer. Reply with JSON only."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 3000,
                "temperature": 0.35,
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {nv_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                text = body["choices"][0]["message"]["content"].strip()
                if text:
                    return text, model_id
        except Exception as exc:
            print(f"[AI_DESIGNER] NVIDIA model {model_id} failed: {exc}")
    return "", ""


def _parse_json(text: str) -> Dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("model response contained no JSON object")
    parsed = json.loads(cleaned[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("model response JSON is not an object")
    return parsed


def _prompt(project_root: Path, genre: str, game_id: str) -> str:
    order = (project_root / "ORDER.md").read_text(encoding="utf-8") if (project_root / "ORDER.md").exists() else ""
    fusion = ""
    for name in ("FUSION_BLUEPRINT.json", "COMPLETE_GAME_BIBLE.json", "playstore_reference_blueprint.json"):
        p = project_root / "docs" / name
        if p.exists():
            try:
                fusion += f"\n--- {name} ---\n{p.read_text(encoding='utf-8')[:6000]}"
            except Exception:
                pass
    return f"""Create a 100% original, commercial-quality {genre} mobile game design for GAME_ID {game_id}.
Do NOT copy any brand, character, level layout, or protected expression. Preserve only unprotectable genre mechanics.

ORDER.md:
{order[:5000]}

Clean-room research:
{fusion[:9000]}

Return ONLY a JSON object with exactly these keys:
{{
  "game_title": "short original title",
  "tagline": "one-line marketing hook",
  "theme": {{
    "bg_top": "#RRGGBB", "bg_bottom": "#RRGGBB", "accent": "#RRGGBB", "accent_2": "#RRGGBB",
    "panel": "#RRGGBB", "panel_alt": "#RRGGBB", "text": "#RRGGBB", "text_dim": "#RRGGBB",
    "success": "#RRGGBB", "danger": "#RRGGBB", "board": "#RRGGBB",
    "gem_colors": ["#RRGGBB", "#RRGGBB", "#RRGGBB", "#RRGGBB", "#RRGGBB", "#RRGGBB"]
  }},
  "tutorial": "one actionable sentence shown in the HUD",
  "boosters": [{{"id":"hammer","name":"...","desc":"...","price_coins":150,"icon":"bomb_hazard"}}, ... exactly 3],
  "shop_items": [{{"sku":"starter_pack","title":"...","desc":"...","price_label":"₹89","kind":"iap","icon":"coin_badge","reward_coins":1200,"reward_booster":"hammer"}}, ... at least 4],
  "level_names": ["...", ... exactly 30],
  "daily_rewards": [{{"day":1,"coins":50,"booster":""}}, ... exactly 7],
  "visual_motifs": ["...", "...", "...", "..."],
  "special_rule": "one genre-specific power-up or layer rule"
}}
The game must be genuinely playable on a 1080x2400 Android screen with a full-screen board, real shop cards, 30 level map, daily rewards, and win/lose flow. No placeholders, no empty menus, no generic 'Open X' buttons."""


def _gd_value(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_gd_value(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{json.dumps(str(k))}: {_gd_value(v)}" for k, v in value.items()) + "}"
    return "null"


def write_runtime_files(project_root: Path, blueprint: Dict[str, Any]) -> None:
    scripts = project_root / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    theme = blueprint["theme"]
    gd = f'''extends Node
# Generated by the live NVIDIA NIM design agent. Do not hand-edit.
const GAME_TITLE := {_gd_value(blueprint["game_title"])}
const TAGLINE := {_gd_value(blueprint["tagline"])}
const GENRE := {_gd_value(blueprint.get("genre", "match_3"))}
const TUTORIAL := {_gd_value(blueprint["tutorial"])}
const SPECIAL_RULE := {_gd_value(blueprint["special_rule"])}
const THEME := {_gd_value(theme)}
const SHOP_ITEMS := {_gd_value(blueprint["shop_items"])}
const BOOSTERS := {_gd_value(blueprint["boosters"])}
const LEVEL_NAMES := {_gd_value(blueprint["level_names"])}
const DAILY_REWARDS := {_gd_value(blueprint["daily_rewards"])}
const VISUAL_MOTIFS := {_gd_value(blueprint.get("visual_motifs", []))}

func theme_color(key: String, fallback: String = "#FFFFFF") -> Color:
    return Color(str(THEME.get(key, fallback)))

func level_name(level_num: int) -> String:
    var idx := clampi(level_num - 1, 0, LEVEL_NAMES.size() - 1)
    return str(LEVEL_NAMES[idx]) if LEVEL_NAMES.size() > 0 else "Level %d" % level_num
'''
    (scripts / "generated_ui_spec.gd").write_text(gd, encoding="utf-8")

    tuning: List[Dict[str, Any]] = []
    for level in range(1, 31):
        tuning.append({
            "level": level,
            "target_score": 250 + level * 70,
            "moves": 18 + min(level, 12),
            "colors": 4 if level < 3 else (5 if level < 12 else 6),
        })
    ext = f'''extends Node
# Generated by the live NVIDIA NIM design agent + validated studio schema.
const GENRE := {_gd_value(blueprint.get("genre", "match_3"))}
const SPECIAL_RULE := {_gd_value(blueprint["special_rule"])}
const LEVEL_TUNING := {_gd_value(tuning)}

static func get_level_tuning(level_num: int) -> Dictionary:
    var idx := clampi(level_num - 1, 0, LEVEL_TUNING.size() - 1)
    return LEVEL_TUNING[idx].duplicate(true)

static func get_special_rule() -> String:
    return SPECIAL_RULE

static func get_theme_accent() -> Color:
    return Color({_gd_value(theme.get("accent", "#FF4D9D"))})
'''
    (scripts / "ai_gameplay_extension.gd").write_text(ext, encoding="utf-8")


def build_design_blueprint(project_root: Path, force: bool = False) -> Dict[str, Any]:
    order = (project_root / "ORDER.md").read_text(encoding="utf-8") if (project_root / "ORDER.md").exists() else ""
    game_id = _field(order, "GAME_ID", "studio_game_01")
    genre = _canonical_genre(_field(order, "GENRE", "match_3"))
    out = project_root / "docs" / "AI_GAME_DESIGN_BLUEPRINT.json"
    if out.exists() and not force:
        try:
            existing = json.loads(out.read_text(encoding="utf-8"))
            existing.setdefault("genre", genre)
            write_runtime_files(project_root, existing)
            return existing
        except Exception:
            pass

    defaults = _defaults(genre)
    nv_key = (os.environ.get("NVIDIA_NIM_API_KEY", "") or os.environ.get("NVIDIA_API_KEY", "")).strip()
    raw = ""
    model_used = ""
    status = "DETERMINISTIC_FALLBACK"
    if nv_key:
        raw, model_used = _call_nim(_prompt(project_root, genre, game_id), nv_key)
    candidate: Dict[str, Any] = {}
    parse_error = ""
    if raw:
        try:
            candidate = _parse_json(raw)
            status = "LIVE_NVIDIA_NIM_BLUEPRINT"
        except Exception as exc:
            parse_error = str(exc)
            status = "LIVE_NVIDIA_INVALID_JSON_FALLBACK"
    blueprint = _merge(defaults, candidate)
    blueprint["genre"] = genre
    blueprint["game_id"] = game_id
    blueprint["generated_by"] = "nvidia-nim" if status.startswith("LIVE") else "deterministic-fallback"
    blueprint["model_used"] = model_used
    blueprint["status"] = status
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(blueprint, indent=2), encoding="utf-8")
    write_runtime_files(project_root, blueprint)
    proof = {
        "status": status,
        "model_used": model_used,
        "game_id": game_id,
        "genre": genre,
        "prompt_sha256": hashlib.sha256(_prompt(project_root, genre, game_id).encode("utf-8")).hexdigest(),
        "raw_response_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest() if raw else "",
        "raw_response_preview": raw[:1200],
        "parse_error": parse_error,
        "blueprint_sha256": hashlib.sha256(json.dumps(blueprint, sort_keys=True).encode("utf-8")).hexdigest(),
        "runtime_files": ["scripts/generated_ui_spec.gd", "scripts/ai_gameplay_extension.gd"],
    }
    (project_root / "docs" / "AI_GENERATION_PROOF.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print(f"[AI_DESIGNER] {status} model={model_used or 'none'} genre={genre} game={game_id}")
    return blueprint


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    build_design_blueprint(Path(args.project_root).resolve(), force=args.force)
