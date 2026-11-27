#!/usr/bin/env python3
"""Stage 1 (V8.0): Deep Play Store Deconstruction & 6 Game Bibles.

Scrapes live Play Store positive/negative reviews, loads morluto/rea +
replica-recon + replica-entrepreneur skills on demand, runs gemini-decision-1
clean-room check + private NVIDIA NIM architect, and writes
docs/MASTER_GAME_BLUEPRINT.json + 6 studio bibles for HF Vault relay.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from dynamic_skill_loader import load_stage_skills
from llm_router import call_gemini_decision_gate, call_nvidia, extract_json_block


def extract_package_id(playstore_url: str) -> str:
    m = re.search(r"id=([A-Za-z0-9._]+)", playstore_url or "")
    return m.group(1) if m else ""


def scrape_playstore_reviews(package_id: str) -> Dict[str, Any]:
    if not package_id:
        return {"status": "NO_PACKAGE_ID", "positive": [], "negative": [], "app_meta": {}}
    try:
        from google_play_scraper import Sort, app, reviews  # type: ignore

        meta = app(package_id, lang="en", country="us")
        pos_res, _ = reviews(package_id, lang="en", country="us", sort=Sort.MOST_RELEVANT, count=15, filter_score_with=5)
        neg_res, _ = reviews(package_id, lang="en", country="us", sort=Sort.MOST_RELEVANT, count=15, filter_score_with=1)
        return {
            "status": "LIVE_SCRAPED",
            "app_meta": {
                "title": meta.get("title", ""),
                "genre": meta.get("genre", ""),
                "score": meta.get("score", 0),
                "installs": meta.get("installs", ""),
                "summary": (meta.get("summary") or "")[:300],
            },
            "positive": [str(r.get("content", ""))[:220] for r in pos_res if r.get("content")][:10],
            "negative": [str(r.get("content", ""))[:220] for r in neg_res if r.get("content")][:10],
        }
    except Exception as exc:
        return {
            "status": f"FALLBACK_CLEANROOM ({exc})",
            "app_meta": {"package_id": package_id},
            "positive": ["Satisfying combo cascades", "Crisp tactile controls", "Short replayable sessions"],
            "negative": ["Too many forced interstitial ads", "Unfair RNG lockouts", "Static bland menus"],
        }


def run_stage1(game_slot: str) -> Dict[str, Any]:
    queue = json.loads(Path("config/game_queue.json").read_text(encoding="utf-8"))
    cfg = queue["games"][game_slot]
    pkg = extract_package_id(cfg.get("playstore_reference_link", ""))
    reviews_data = scrape_playstore_reviews(pkg)
    skills = load_stage_skills("stage1")

    gate = call_gemini_decision_gate(
        f"Confirm clean-room originality plan for game '{cfg['title']}' ({cfg['genre']}). "
        "Zero copyrighted assets or code from any third-party APK will be copied."
    )

    system_prompt = (
        "You are the Lead Game Director & Clean-Room Architect of an AAA Mobile Game Studio. "
        "Output ONLY valid JSON. Never copy copyrighted names, logos, or assets. "
        "Design a commercial-grade Godot 4.7.2 mobile game with rich illustrated art direction, "
        "a curved winding Saga Level Map (NEVER a flat grid), animated Shop & AdOfferModal, "
        "and 3-5 original advanced features directly fixing Play Store negative reviews."
    )
    user_prompt = (
        f"Loaded Studio Skills:\n{skills['context_text'][:6000]}\n\n"
        f"Target Game Slot: {json.dumps(cfg, indent=2)}\n"
        f"Play Store Review Intelligence: {json.dumps(reviews_data, indent=2)}\n\n"
        "Return a single JSON object with keys:\n"
        "game_id, title, genre, package_name, tagline, palette (bg_top, bg_bottom, accent, accent_2, panel, text),\n"
        "art_prompts (bg_home, bg_map, bg_gameplay, piece_style, icon_prompt, feature_graphic_prompt),\n"
        "screens (Loading, Home, WindingSagaMap, GameplayHUD, Shop, AdsIAP, WinLose — each with layout & animation specs),\n"
        "extra_advanced_features (list of 4 original features fixing negative reviews),\n"
        "level_progression (30 levels curve summary), economy_and_monetization (fair rewarded ads + IAP packs), audio_direction."
    )
    res = call_nvidia("architect", system_prompt, user_prompt, max_tokens=4096, temperature=0.25)
    blueprint = extract_json_block(res["text"])
    blueprint["game_id"] = cfg["game_id"]
    blueprint["game_slot"] = game_slot
    blueprint["genre"] = cfg["genre"]
    blueprint["title"] = cfg["title"]
    blueprint["package_name"] = cfg["package_name"]
    blueprint["playstore_reviews"] = reviews_data
    blueprint["decision_gate"] = gate
    blueprint["llm_model_used"] = res["model"]
    blueprint["skills_loaded"] = skills["files_loaded"]

    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "MASTER_GAME_BLUEPRINT.json").write_text(json.dumps(blueprint, indent=2), encoding="utf-8")

    # Emit 6 concise structured studio bibles derived from the master blueprint
    bibles = {
        "BIBLE_1_CORE_DESIGN.md": f"# Core Design Bible — {cfg['title']}\n\n- Genre: `{cfg['genre']}`\n- Tagline: {blueprint.get('tagline', '')}\n- Advanced Features:\n" + "\n".join(f"  - {f}" for f in blueprint.get("extra_advanced_features", [])),
        "BIBLE_2_ART_DIRECTION.md": f"# Art Direction Bible — {cfg['title']}\n\n```json\n{json.dumps(blueprint.get('art_prompts', {}), indent=2)}\n```",
        "BIBLE_3_UI_UX_SCREENS.md": f"# UI/UX Screen & Animation Bible — {cfg['title']}\n\n```json\n{json.dumps(blueprint.get('screens', {}), indent=2)}\n```",
        "BIBLE_4_LEVEL_PROGRESSION.md": f"# Level Progression Bible — {cfg['title']}\n\n```json\n{json.dumps(blueprint.get('level_progression', {}), indent=2)}\n```",
        "BIBLE_5_ECONOMY_MONETIZATION.md": f"# Economy & Fair Monetization Bible — {cfg['title']}\n\n```json\n{json.dumps(blueprint.get('economy_and_monetization', {}), indent=2)}\n```",
        "BIBLE_6_AUDIO_DIRECTION.md": f"# Audio Direction Bible — {cfg['title']}\n\n```json\n{json.dumps(blueprint.get('audio_direction', {}), indent=2)}\n```",
    }
    for fname, content in bibles.items():
        (docs_dir / fname).write_text(content + "\n", encoding="utf-8")

    print(f"[STAGE 1 PASS] Master blueprint + 6 bibles generated for {cfg['game_id']} using {res['model']}")
    return blueprint


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-slot", default="game_1")
    args = parser.parse_args()
    run_stage1(args.game_slot)
