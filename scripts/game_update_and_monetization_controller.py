#!/usr/bin/env python3
"""
FUTURE GAME UPDATE, AD/IAP EXPANSION & MOBILE CONTROLLER API BRIDGE (V5.0)
Allows updating an existing game (`MODE: update_existing_game`), adding new
AdMob Unit IDs or Google Play Billing IAP SKUs, dropping custom assets into
`MY_RESEARCH_AND_FILES/`, or starting a brand-new game from CLI or a mobile controller app.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def update_order_and_monetization(
    game_id: str,
    mode: str,
    genre: str,
    category: str,
    ref_link: str,
    prompt_notes: str,
    extra_sku: str = "",
) -> Dict[str, Any]:
    lines = [
        "# MY STUDIO ORDER FILE (V5.0 — PRODUCTION MASTER)",
        f"GAME_ID: {game_id}",
        f"MODE: {mode}",
        f"CATEGORY: {category}",
        f"GENRE: {genre}",
        "USE_REA: false",
        f"PLAYSTORE_REFERENCE_LINK: {ref_link}",
        "REFERENCE_APK_PATH:",
        "AUTHORIZED_REPO_PATH:",
        "REFERENCE_VIDEOS:",
        "",
        "## PROMPT:",
        prompt_notes,
        "",
    ]
    Path("ORDER.md").write_text("\n".join(lines), encoding="utf-8")
    result = {
        "status": "UPDATED_ORDER_MD",
        "game_id": game_id,
        "mode": mode,
        "genre": genre,
        "category": category,
        "ref_link": ref_link,
        "extra_sku_registered": extra_sku or None,
    }
    Path("docs").mkdir(parents=True, exist_ok=True)
    Path("docs/LAST_CONTROLLER_UPDATE.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update ORDER.md for new_game or update_existing_game")
    parser.add_argument("--game-id", default="block_juggle_cleanroom_01")
    parser.add_argument("--mode", default="new_game", choices=["new_game", "update_existing_game", "export_only_apk_and_aab"])
    parser.add_argument("--genre", default="block_puzzle")
    parser.add_argument("--category", default="level_by_level")
    parser.add_argument("--ref-link", default="https://play.google.com/store/apps/details?id=com.block.juggle")
    parser.add_argument("--prompt", default="Build or update Clean-Room 8x8 Crystal Grid Puzzle with Positive/Negative Review upgrades.")
    parser.add_argument("--add-sku", default="")
    args = parser.parse_args()
    res = update_order_and_monetization(
        game_id=args.game_id,
        mode=args.mode,
        genre=args.genre,
        category=args.category,
        ref_link=args.ref_link,
        prompt_notes=args.prompt,
        extra_sku=args.add_sku,
    )
    print(json.dumps(res, indent=2))
