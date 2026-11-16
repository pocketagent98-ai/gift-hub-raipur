#!/usr/bin/env python3
"""
IDEA → GAME BLUEPRINT GENERATOR (V5.2)

Turns the free-text game idea in `ORDER.md` into a validated, machine-readable
blueprint that the rest of the studio actually consumes:

  * theme + colour palette      -> asset factory (icons, launcher icon, 3D tint)
  * difficulty curve            -> mercy rescue threshold, Crystal Fever threshold
  * level / economy / ad policy -> docs, monetisation manifest, Play listing copy

Design rules
------------
1. Honest scope: this studio ships ONE gameplay engine (8x8 block-puzzle cascade).
   A genre it cannot build is refused loudly instead of silently producing the
   wrong game. Extend SUPPORTED_GENRES only together with real engine code.
2. Deterministic: the same ORDER.md always yields the same blueprint, so CI is
   reproducible and diffs are reviewable.
3. Never invents gameplay code — it only produces configuration + documentation.

Outputs
-------
  config/game_blueprint.json   machine-readable, consumed by scripts/*
  docs/GAME_BLUEPRINT.md       human-readable, shows exactly how the idea mapped
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BLUEPRINT_PATH = Path("config/game_blueprint.json")
DOC_PATH = Path("docs/GAME_BLUEPRINT.md")

# Genres this studio can genuinely build today. Everything here maps onto the
# verified 8x8 crystal-grid cascade engine.
SUPPORTED_GENRES = {
    "block_puzzle": "block_puzzle",
    "block_puzzle_3d": "block_puzzle",
    "puzzle": "block_puzzle",
    "blocks": "block_puzzle",
    "match3": "block_puzzle",
    "match_3": "block_puzzle",
    "crystal": "block_puzzle",
    "cascade": "block_puzzle",
}

THEMES: Dict[str, Dict[str, Any]] = {
    "candy": {
        "keywords": ("candy", "sweet", "sugar", "chocolate", "dessert", "mithai", "toffee"),
        "palette": {"background": "#2A0E2E", "surface": "#3D1543", "primary": "#FF5FA2",
                    "accent": "#FFD166", "reward": "#FFB703", "danger": "#EF476F"},
        "piece_names": ["Candy Cube", "Jelly Block", "Toffee Tile", "Mint Crystal"],
    },
    "space": {
        "keywords": ("space", "galaxy", "star", "cosmic", "astro", "planet", "rocket", "nebula"),
        "palette": {"background": "#070B1F", "surface": "#131A38", "primary": "#6C8CFF",
                    "accent": "#4DE1C1", "reward": "#FFD166", "danger": "#FF5C7A"},
        "piece_names": ["Star Shard", "Nebula Block", "Comet Tile", "Void Crystal"],
    },
    "ocean": {
        "keywords": ("ocean", "sea", "bubble", "water", "coral", "fish", "aqua", "beach"),
        "palette": {"background": "#04222E", "surface": "#0A3547", "primary": "#37C2E0",
                    "accent": "#7BF1A8", "reward": "#FFD166", "danger": "#FF6B6B"},
        "piece_names": ["Bubble Block", "Coral Tile", "Pearl Crystal", "Wave Cube"],
    },
    "jungle": {
        "keywords": ("jungle", "forest", "nature", "leaf", "garden", "animal", "green", "tree"),
        "palette": {"background": "#0B2016", "surface": "#143324", "primary": "#4ADE80",
                    "accent": "#FACC15", "reward": "#FDE047", "danger": "#F97316"},
        "piece_names": ["Leaf Block", "Moss Tile", "Seed Crystal", "Bark Cube"],
    },
    "crystal": {
        "keywords": ("crystal", "gem", "jewel", "diamond", "ice", "frost", "glass", "prism"),
        "palette": {"background": "#0F172A", "surface": "#1E293B", "primary": "#38BDF8",
                    "accent": "#00E676", "reward": "#FBBF24", "danger": "#F43F5E"},
        "piece_names": ["Crystal Cube", "Frost Block", "Prism Tile", "Shard Crystal"],
    },
}

DEFAULT_THEME = "crystal"

DIFFICULTY_PRESETS = {
    "relaxed": {
        "keywords": ("easy", "chill", "relax", "casual", "kids", "calm", "simple", "aaram"),
        "mercy_rescue_threshold": 3, "fever_combo_threshold": 3, "starting_hints": 3,
    },
    "standard": {
        "keywords": (),
        "mercy_rescue_threshold": 2, "fever_combo_threshold": 3, "starting_hints": 1,
    },
    "hardcore": {
        "keywords": ("hard", "difficult", "hardcore", "expert", "brutal", "competitive"),
        "mercy_rescue_threshold": 1, "fever_combo_threshold": 4, "starting_hints": 0,
    },
}

ECONOMY_SKUS: List[Dict[str, Any]] = [
    {"sku": "starter_gem_pouch", "price_inr": 89, "contents": "120 crystals"},
    {"sku": "handful_of_gems", "price_inr": 169, "contents": "260 crystals"},
    {"sku": "gem_jar", "price_inr": 299, "contents": "500 crystals + 1 hammer"},
    {"sku": "gem_chest", "price_inr": 499, "contents": "900 crystals + 3 hammers"},
    {"sku": "mega_crystal_bundle", "price_inr": 699, "contents": "1500 crystals + 5 juggles"},
    {"sku": "vault_of_plenty", "price_inr": 849, "contents": "2500 crystals + all boosters"},
]


def parse_order(txt: str) -> Dict[str, str]:
    def field(key: str, default: str = "") -> str:
        m = re.search(rf"^{key}\s*:\s*(.*)$", txt, re.M | re.I)
        return m.group(1).strip() if m else default

    prompt = ""
    m = re.search(r"^##\s*PROMPT\s*:\s*$([\s\S]*)$", txt, re.M | re.I)
    if m:
        prompt = m.group(1).strip()

    return {
        "game_id": field("GAME_ID"),
        "genre": field("GENRE", "block_puzzle").lower(),
        "category": field("CATEGORY", "level_by_level").lower(),
        "reference_link": field("PLAYSTORE_REFERENCE_LINK"),
        "prompt": prompt,
    }


def pick_theme(prompt: str) -> str:
    low = prompt.lower()
    scores = {name: sum(low.count(k) for k in cfg["keywords"]) for name, cfg in THEMES.items()}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else DEFAULT_THEME


def pick_difficulty(prompt: str) -> str:
    low = prompt.lower()
    for name, cfg in DIFFICULTY_PRESETS.items():
        if any(k in low for k in cfg["keywords"]):
            return name
    return "standard"


def build_blueprint(order_txt: str) -> Dict[str, Any]:
    order = parse_order(order_txt)

    if not order["game_id"]:
        raise ValueError("[BLUEPRINT_FAIL] ORDER.md has no 'GAME_ID:' line — nothing to name the game.")

    raw_genre = order["genre"]
    if raw_genre not in SUPPORTED_GENRES:
        supported = ", ".join(sorted({v for v in SUPPORTED_GENRES.values()}))
        raise ValueError(
            f"[BLUEPRINT_FAIL] GENRE '{raw_genre}' is not supported by this studio. "
            f"This factory builds one verified engine family: {supported}. "
            "Set GENRE to a supported value, or add the new engine (code + QA suites) first — "
            "silently shipping the wrong game would be worse than stopping here."
        )

    if not order["prompt"]:
        raise ValueError(
            "[BLUEPRINT_FAIL] ORDER.md has no '## PROMPT:' section — the studio needs the idea in words."
        )

    theme = pick_theme(order["prompt"])
    difficulty = pick_difficulty(order["prompt"])
    theme_cfg = THEMES[theme]
    diff_cfg = {k: v for k, v in DIFFICULTY_PRESETS[difficulty].items() if k != "keywords"}

    return {
        "schema_version": "5.2.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "order_file": "ORDER.md",
            "order_sha256": hashlib.sha256(order_txt.encode("utf-8")).hexdigest(),
        },
        "game_id": order["game_id"],
        "engine": {
            "family": SUPPORTED_GENRES[raw_genre],
            "requested_genre": raw_genre,
            "board_size": 8,
            "tray_pieces": 3,
            "categories": ["level_by_level", "endless_map_chunks"],
            "active_category": order["category"] if order["category"] in
                               ("level_by_level", "endless_map_chunks") else "level_by_level",
        },
        "theme": {
            "name": theme,
            "palette": theme_cfg["palette"],
            "piece_names": theme_cfg["piece_names"],
        },
        "difficulty": dict(diff_cfg, preset=difficulty),
        "levels": {
            "total": 30,
            "milestones": [1, 3, 6, 8, 10, 16, 30],
            "endless_chunks": 5,
            "armored_hit_points": 4,
        },
        "economy": {"currency": "crystals", "skus": ECONOMY_SKUS},
        "ad_policy": {
            "mid_move_interstitials": 0,
            "interstitial_min_level": 3,
            "interstitial_cooldown_seconds": 180,
            "rewarded_optional_only": True,
        },
        "idea_prompt": order["prompt"],
        "reference_link": order["reference_link"],
    }


def render_doc(bp: Dict[str, Any]) -> str:
    pal = bp["theme"]["palette"]
    skus = "\n".join(f"| `{s['sku']}` | ₹{s['price_inr']} | {s['contents']} |" for s in bp["economy"]["skus"])
    return f"""# GAME BLUEPRINT — {bp['game_id']}

Generated from `ORDER.md` (sha256 `{bp['source']['order_sha256'][:16]}…`) at {bp['generated_at_utc']}.
This file is generated, not hand-written: edit `ORDER.md` and push to change it.

## Your idea, as the studio understood it
> {bp['idea_prompt']}

## Mapping
| Idea signal | Studio decision |
| :--- | :--- |
| Requested genre | `{bp['engine']['requested_genre']}` → engine family `{bp['engine']['family']}` |
| Theme detected | `{bp['theme']['name']}` |
| Difficulty detected | `{bp['difficulty']['preset']}` (mercy rescue at {bp['difficulty']['mercy_rescue_threshold']} placements, Crystal Fever at {bp['difficulty']['fever_combo_threshold']}x combo) |
| Category | `{bp['engine']['active_category']}` |

## Theme palette (drives icons, launcher art and 3D tint)
| Role | Hex |
| :--- | :--- |
| Background | `{pal['background']}` |
| Surface | `{pal['surface']}` |
| Primary | `{pal['primary']}` |
| Accent | `{pal['accent']}` |
| Reward | `{pal['reward']}` |
| Danger | `{pal['danger']}` |

Piece names: {", ".join(bp['theme']['piece_names'])}

## Board & progression
- Board {bp['engine']['board_size']}x{bp['engine']['board_size']}, {bp['engine']['tray_pieces']}-piece tray, Juggle Hold slot
- {bp['levels']['total']} levels (milestones {bp['levels']['milestones']}), {bp['levels']['endless_chunks']} endless chunks
- Armored blocks take {bp['levels']['armored_hit_points']} hits

## Monetisation catalog
| SKU | Price | Contents |
| :--- | :--- | :--- |
{skus}

## Ad policy
- Mid-move interstitials: **{bp['ad_policy']['mid_move_interstitials']}**
- Interstitials only from level {bp['ad_policy']['interstitial_min_level']}, {bp['ad_policy']['interstitial_cooldown_seconds']}s cooldown
- Rewarded ads are opt-in only
"""


def main() -> int:
    order_path = Path("ORDER.md")
    if not order_path.exists():
        print("[BLUEPRINT_FAIL] ORDER.md is missing.")
        return 1

    try:
        bp = build_blueprint(order_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(str(exc))
        return 1

    BLUEPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    BLUEPRINT_PATH.write_text(json.dumps(bp, indent=2) + "\n", encoding="utf-8")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(render_doc(bp), encoding="utf-8")

    print(
        f"[BLUEPRINT] {bp['game_id']}: engine={bp['engine']['family']} "
        f"theme={bp['theme']['name']} difficulty={bp['difficulty']['preset']} "
        f"-> {BLUEPRINT_PATH} + {DOC_PATH}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
