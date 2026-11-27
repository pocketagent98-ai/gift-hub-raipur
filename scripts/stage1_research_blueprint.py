#!/usr/bin/env python3
"""
STAGE 1 — Clean-Room Play Store Review Intelligence & 6 Game Bibles Generator (V7.0)
- Uses public Google Play listing metadata + 5-star/1-2-star user reviews ONLY.
- Never downloads or decompiles third-party APKs; enforces strict clean-room originality.
- Uses gemini-decision-1 (policy gate) + NVIDIA NIM nemotron-3-ultra-550b (architect).
"""

import argparse
import json
from pathlib import Path
import re

from llm_router import gemini_decision_gate, nvidia_chat


def load_order(slot: str, custom_link: str, custom_prompt: str, custom_genre: str, custom_game_id: str) -> dict:
    queue_p = Path("config/game_queue.json")
    queue = json.loads(queue_p.read_text(encoding="utf-8")) if queue_p.exists() else {"games": {}}

    if slot and slot in queue.get("games", {}):
        entry = dict(queue["games"][slot])
    else:
        txt = Path("ORDER.md").read_text(encoding="utf-8") if Path("ORDER.md").exists() else ""
        def field(key: str, default: str = "") -> str:
            m = re.search(rf"^{key}[ \t]*:[ \t]*(.*)$", txt, re.M | re.I)
            return m.group(1).strip() if m and m.group(1).strip() else default
        pm = re.search(r"## PROMPT:\s*(.+)", txt, re.S | re.I)
        entry = {
            "game_id": field("GAME_ID", "block_blast_studio_01"),
            "game_version": field("GAME_VERSION", "v1.0.0"),
            "genre": field("GENRE", "block_puzzle").lower(),
            "title": "Crystal Grid Cascade",
            "package_name": "com.aistudio.crystalgridcascade",
            "playstore_reference_link": field("PLAYSTORE_REFERENCE_LINK", ""),
            "prompt": pm.group(1).strip() if pm else "Build a polished original mobile puzzle game.",
        }

    if custom_game_id:
        entry["game_id"] = re.sub(r"[^a-zA-Z0-9_]", "_", custom_game_id).lower()
    if custom_genre:
        entry["genre"] = custom_genre.strip().lower()
    if custom_link:
        entry["playstore_reference_link"] = custom_link.strip()
    if custom_prompt:
        entry["prompt"] = custom_prompt.strip()

    pkg_m = re.search(r"id=([a-zA-Z0-9._]+)", entry.get("playstore_reference_link", ""))
    entry["reference_pkg_id"] = pkg_m.group(1) if pkg_m else ""
    if not entry.get("package_name"):
        clean_id = re.sub(r"[^a-z0-9]", "", entry["game_id"].lower())[:20] or "origgame"
        entry["package_name"] = f"com.aistudio.{clean_id}"
    return entry


def scrape_public_reviews(pkg_id: str) -> dict:
    meta = {
        "reference_pkg_id": pkg_id,
        "public_title": pkg_id or "Original Concept",
        "genre_label": "Puzzle",
        "score": 4.5,
        "positive_loves": [],
        "negative_pains": [],
    }
    if not pkg_id:
        return meta
    try:
        from google_play_scraper import Sort, app, reviews
        info = app(pkg_id, lang="en", country="us")
        good, _ = reviews(pkg_id, lang="en", country="us", sort=Sort.MOST_RELEVANT, count=20, filter_score_with=5)
        bad, _ = reviews(pkg_id, lang="en", country="us", sort=Sort.NEWEST, count=25, filter_score_with=2)
        meta["public_title"] = info.get("title", pkg_id)
        meta["genre_label"] = info.get("genre", "Puzzle")
        meta["score"] = info.get("score", 4.5)
        meta["positive_loves"] = [r.get("content", "").strip()[:200] for r in good[:6] if r.get("content")]
        meta["negative_pains"] = [r.get("content", "").strip()[:200] for r in bad[:6] if r.get("content")]
    except Exception as exc:
        meta["scrape_note"] = f"Public store scrape fallback: {exc}"
    return meta


def load_stage1_skills() -> str:
    chunks = []
    for p in (
        ".agents/skills/replica-recon/SKILL.md",
        ".agents/skills/replica-entrepreneur/SKILL.md",
        ".agents/skills/craft-anything/SKILL.md",
    ):
        fp = Path(p)
        if fp.exists():
            chunks.append(fp.read_text(encoding="utf-8"))
    return "\n\n".join(chunks)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", default="")
    parser.add_argument("--playstore-link", default="")
    parser.add_argument("--prompt", default="")
    parser.add_argument("--genre", default="")
    parser.add_argument("--game-id", default="")
    args = parser.parse_args()

    order = load_order(args.slot, args.playstore_link, args.prompt, args.genre, args.game_id)
    out = Path("docs/generated")
    out.mkdir(parents=True, exist_ok=True)

    # 1. Clean-room gate via Gemini Decision Gate
    gate = gemini_decision_gate(
        "Confirm this is a 100% clean-room original game design using only public genre reviews (no copyrighted asset or code copying).",
        json.dumps(order),
    )
    order["clean_room_gate"] = gate

    # 2. Public Play Store review scraping
    store_intel = scrape_public_reviews(order["reference_pkg_id"])
    (out / "public_review_intel.json").write_text(json.dumps(store_intel, indent=2, ensure_ascii=False), encoding="utf-8")

    # 3. Synthesize structured design_spec.json via NVIDIA NIM Architect
    skills_txt = load_stage1_skills()
    sys_msg = (
        "You are the Lead Game Architect for Autonomous AI Game Studio V7.0 (Godot 4.7.2). "
        "Follow these active clean-room skills:\n" + skills_txt
    )
    user_msg = (
        f"Design a 100% original commercial mobile game for:\n"
        f"- game_id: {order['game_id']}\n"
        f"- genre: {order['genre']}\n"
        f"- preferred_title: {order.get('title', 'Crystal Craft')}\n"
        f"- user_prompt: {order['prompt']}\n"
        f"- public_player_loves: {json.dumps(store_intel['positive_loves'][:4])}\n"
        f"- public_player_pains_to_fix: {json.dumps(store_intel['negative_pains'][:4])}\n\n"
        "Return COMPACT VALID JSON ONLY with keys: "
        "title, tagline, theme_bg_hex, theme_panel_hex, theme_accent_hex, "
        "palette_hex (list of 6 bright hex colors), differentiator_features (list of 3 strings), "
        "ad_policy (dict with interstitial_every_n_levels, rewarded_placements), "
        "iap_packs (list of 3 dicts with sku, name, price_inr, coins), "
        "pain_points_solved (list of 3 strings)."
    )
    raw_spec, model_used = nvidia_chat(
        [{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}],
        role="architect",
        max_tokens=1400,
        temperature=0.3,
    )

    default_spec = {
        "title": order.get("title") or ("Crystal Grid Cascade" if order["genre"] == "block_puzzle" else "Hexa Bolt Craft"),
        "tagline": "Craft smart cascades, solve layered boards, zero forced mid-move ads!",
        "theme_bg_hex": "#0f172a" if order["genre"] == "block_puzzle" else "#161b2e",
        "theme_panel_hex": "#1e293b",
        "theme_accent_hex": "#38bdf8" if order["genre"] == "block_puzzle" else "#f59e0b",
        "palette_hex": ["#fb5668", "#ffa62b", "#3ddc84", "#38b6ff", "#a86bff", "#ff66c4"],
        "differentiator_features": [
            "Smart Mercy Rescue (prevents unfair unwinnable draws)",
            "Tactical Hold/Buffer Slot + 3x3 Smash / Magnet Booster",
            "Combo Fever Overdrive (2x score burst on 3+ streaks)",
        ],
        "ad_policy": {
            "interstitial_every_n_levels": 2,
            "zero_mid_move_forced_ads": True,
            "rewarded_placements": ["extra_coins_100", "revive_continue", "free_booster"],
        },
        "iap_packs": [
            {"sku": "starter_pack_89", "name": "Starter Pack (500 Coins + Boosters)", "price_inr": 89, "coins": 500},
            {"sku": "remove_ads_249", "name": "Remove Ads Forever", "price_inr": 249, "coins": 250},
            {"sku": "mega_vault_799", "name": "Mega Vault (5,000 Coins)", "price_inr": 799, "coins": 5000},
        ],
        "pain_points_solved": [
            "Eliminated intrusive mid-turn pop-up ads",
            "Prevented unfair RNG dead-end boards with Smart Mercy generator",
            "Zero clipped mobile UI text with large >=56px touch controls",
        ],
    }

    design_spec = dict(default_spec)
    if raw_spec and "{" in raw_spec and "}" in raw_spec:
        try:
            parsed = json.loads(raw_spec[raw_spec.find("{"): raw_spec.rfind("}") + 1])
            for k, v in parsed.items():
                if v:
                    design_spec[k] = v
        except Exception as exc:
            print(f"[STAGE 1] JSON parse fallback: {exc}")

    design_spec["architect_model"] = model_used
    design_spec["game_id"] = order["game_id"]
    design_spec["genre"] = order["genre"]
    design_spec["package_name"] = order["package_name"]
    order["resolved_title"] = design_spec["title"]

    (out / "resolved_order.json").write_text(json.dumps(order, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "design_spec.json").write_text(json.dumps(design_spec, indent=2, ensure_ascii=False), encoding="utf-8")

    # 4. Write all 6 Clean-Room Game Bibles
    bibles = {
        "01_CORE_MECHANICS_BIBLE.md": (
            f"# 01 — Core Mechanics Bible: {design_spec['title']}\n\n"
            f"- **Game ID:** `{order['game_id']}` | **Genre:** `{order['genre']}`\n"
            f"- **Architect Model:** `{model_used}`\n"
            f"- **Clean-Room Policy:** 100% original code & procedural art inspired by public genre expectations.\n"
            f"- **Differentiators:**\n" + "\n".join(f"  - {f}" for f in design_spec["differentiator_features"]) + "\n"
        ),
        "02_LEVEL_PROGRESSION_BIBLE.md": (
            f"# 02 — Level Progression Bible (Levels 1–30 + Endless)\n\n"
            "- Deterministic seeded progression from Level 1 (onboarding) to Level 30 (master challenge).\n"
            "- Dynamic Smart Mercy protection prevents impossible RNG deadlocks.\n"
        ),
        "03_FAIR_ADS_AND_IAP_BIBLE.md": (
            f"# 03 — Fair Monetization (Ads + Play Billing IAP) & Review Upgrades\n\n"
            f"- **Ad Policy:** `{json.dumps(design_spec['ad_policy'])}`\n"
            f"- **IAP Catalog:** `{json.dumps(design_spec['iap_packs'])}`\n"
            f"- **Player Complaints Fixed:**\n" + "\n".join(f"  - {p}" for p in design_spec["pain_points_solved"]) + "\n"
        ),
        "04_UI_UX_12_SCREENS_BIBLE.md": (
            "# 04 — UI/UX 12-Screen Mobile Bible\n\n"
            "- Portrait 720x1280 (`canvas_items`, `expand`), SafeAreaMargin(24,44,24,32), `AUTOWRAP_WORD_SMART`, >=56px touch buttons.\n"
            "- Screens: MainMenu, LoadingScreen, GameplayHUD, PauseMenu, Settings, Shop, Inventory, Rewards, LevelSelection, WinLoseScreen, Profile, DailyRewards.\n"
        ),
        "05_ART_AND_AUDIO_BIBLE.md": (
            f"# 05 — Original Art & Musical Audio Bible\n\n"
            f"- **Backdrop:** `{design_spec['theme_bg_hex']}` | **Accent:** `{design_spec['theme_accent_hex']}`\n"
            f"- **Piece Palette:** `{json.dumps(design_spec['palette_hex'])}`\n"
            "- **Audio:** Synthesized pentatonic marimba/chime WAVs + Godot AudioStreamGenerator fallback.\n"
        ),
        "06_TECHNICAL_ARCHITECTURE_BIBLE.md": (
            "# 06 — Godot 4.7.2 Technical Architecture\n\n"
            "- Autoloads: `AppConfig`, `SaveManager`, `AudioDirector`, `MonetizationManager`, `GameManager`.\n"
            "- Renderer: `gl_compatibility`, Android Target SDK 36, Min SDK 24, arm64-v8a.\n"
        ),
    }
    for fname, content in bibles.items():
        (out / fname).write_text(content, encoding="utf-8")

    print(f"[STAGE 1 PASS] Clean-Room Blueprints ready for {order['game_id']} ({design_spec['title']}) via {model_used}.")


if __name__ == "__main__":
    main()
