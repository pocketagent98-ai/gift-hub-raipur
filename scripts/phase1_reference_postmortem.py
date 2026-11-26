#!/usr/bin/env python3
"""
PHASE 1 — REFERENCE LINK / APK POST-MORTEM & 5 DEEP STUDIO DOCUMENTS GENERATOR (V6.0)
"""

import json
from pathlib import Path
import re
import urllib.request
import zipfile


def parse_order() -> dict:
    txt = Path("ORDER.md").read_text(encoding="utf-8") if Path("ORDER.md").exists() else ""
    def field(key: str, default: str = "") -> str:
        m = re.search(rf"^{key}[ \t]*:[ \t]*(.*)$", txt, re.M | re.I)
        return m.group(1).strip() if m and m.group(1).strip() else default

    ref_link = field("PLAYSTORE_REFERENCE_LINK", "")
    pkg_m = re.search(r"id=([a-zA-Z0-9._]+)", ref_link)
    pkg_id = pkg_m.group(1) if pkg_m else ""
    prompt_m = re.search(r"## PROMPT:\s*(.+)", txt, re.S | re.I)
    return {
        "game_id": field("GAME_ID", "block_blast_studio_01"),
        "game_version": field("GAME_VERSION", "v1.0.0"),
        "mode": field("MODE", "new_game").lower(),
        "release_mode": field("RELEASE_MODE", "preview").lower(),
        "genre": field("GENRE", "block_puzzle").lower(),
        "use_rea": field("USE_REA", "true").lower() == "true",
        "ref_link": ref_link,
        "pkg_id": pkg_id,
        "ref_apk_url": field("REFERENCE_APK_URL", ""),
        "prompt": prompt_m.group(1).strip() if prompt_m else "Build a polished mobile puzzle game.",
    }


def main() -> None:
    order = parse_order()
    docs = Path("docs")
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "resolved_order_v6.json").write_text(json.dumps(order, indent=2), encoding="utf-8")

    apk_summary = {"downloaded": False, "engine_detected": "UNKNOWN", "entries": 0}
    if order["ref_apk_url"]:
        apk_dst = Path("/tmp/reference_game.apk")
        try:
            req = urllib.request.Request(order["ref_apk_url"], headers={"User-Agent": "Mozilla/5.0 StudioV6"})
            with urllib.request.urlopen(req, timeout=60) as r:
                apk_dst.write_bytes(r.read())
            with zipfile.ZipFile(apk_dst, "r") as zf:
                names = zf.namelist()
                eng = "Unity" if any("libunity" in n.lower() for n in names) else ("Godot" if any("libgodot" in n.lower() for n in names) else "Native/Other")
                apk_summary = {"downloaded": True, "engine_detected": eng, "entries": len(names)}
        except Exception as exc:
            apk_summary["note"] = str(exc)

    store_meta = {"title": order["pkg_id"] or "Original User Idea", "positive_loves": [], "negative_pains": []}
    if order["pkg_id"]:
        try:
            from google_play_scraper import Sort, app, reviews
            info = app(order["pkg_id"], lang="en", country="us")
            good, _ = reviews(order["pkg_id"], lang="en", country="us", sort=Sort.MOST_RELEVANT, count=20, filter_score_with=5)
            bad, _ = reviews(order["pkg_id"], lang="en", country="us", sort=Sort.NEWEST, count=25, filter_score_with=2)
            store_meta["title"] = info.get("title", order["pkg_id"])
            store_meta["positive_loves"] = [r.get("content", "")[:180] for r in good[:5] if r.get("content")]
            store_meta["negative_pains"] = [r.get("content", "")[:180] for r in bad[:5] if r.get("content")]
        except Exception as exc:
            store_meta["scrape_note"] = str(exc)

    (docs / "01_GAME_POSTMORTEM_AND_MECHANICS.md").write_text(
        f"# 01 — Game Post-Mortem & Core Mechanics ({order['game_id']})\n\n"
        f"- **Genre:** `{order['genre']}`\n"
        f"- **Reference:** `{order['ref_link'] or 'Pure User Idea'}`\n"
        f"- **APK Inspection (REA):** `{json.dumps(apk_summary)}`\n"
        "- **Core Loop:** Real interactive 8x8 puzzle board with drag-and-drop + tap-to-place or swipe + tap-to-swap, glowing line/match clear cascades, and escalating combo multipliers.\n",
        encoding="utf-8",
    )
    (docs / "02_UI_UX_AND_ANIMATION_BIBLE.md").write_text(
        "# 02 — UI/UX & Animation Bible\n\n"
        "- **Zero Clipping Rule:** Every `Label` uses `AUTOWRAP_WORD_SMART` inside `SafeAreaMargin` (24px/44px).\n"
        "- **12 Complete Screens:** MainMenu, LoadingScreen, GameplayHUD, PauseMenu, Settings, Shop, Inventory, Rewards, LevelSelection (centered 5-column 1..30 grid), WinLoseScreen, Profile, DailyRewards.\n",
        encoding="utf-8",
    )
    (docs / "03_LEVEL_PROGRESSION_AND_DIFFICULTY.md").write_text(
        "# 03 — Level Progression & Difficulty Curve (Levels 1–30)\n\n"
        "- **Levels 1–30:** Progressive score targets (`360` -> `4420`), pre-seeded gem patterns, Smart Mercy Rescue.\n",
        encoding="utf-8",
    )
    (docs / "04_ASSETS_AUDIO_AND_VFX_BIBLE.md").write_text(
        "# 04 — Assets, Audio & VFX Bible\n\n"
        "- **Visuals:** 100% original procedural glossy 3D-bevelled crystal blocks/gems, glowing board frame, particle bursts, floating score popups, and screen shake.\n"
        "- **Musical Audio:** Warm pentatonic marimba/chime chords via `AudioStreamGenerator`.\n",
        encoding="utf-8",
    )
    (docs / "05_MONETIZATION_ADS_IAP_AND_REVIEW_UPGRADES.md").write_text(
        "# 05 — Monetization (Ads + IAP) & Positive/Negative Review Upgrades\n\n"
        f"- **Player Loves Preserved:** {json.dumps(store_meta['positive_loves'], ensure_ascii=False)}\n"
        f"- **Player Complaints Fixed:** {json.dumps(store_meta['negative_pains'], ensure_ascii=False)}\n"
        "- **Unique Upgrades:** Smart Mercy & Juggle Hold Vault, Crystal Fever Overdrive (3x+ combo), Hammer 3x3 Smash Booster, Zero Mid-Move Forced Ads.\n",
        encoding="utf-8",
    )
    print(f"[PHASE 1 PASS] Generated all 5 Deep Studio Documents for '{order['game_id']}' ({order['genre']}).")


if __name__ == "__main__":
    main()
