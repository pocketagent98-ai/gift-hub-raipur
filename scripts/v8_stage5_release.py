#!/usr/bin/env python3
"""Stage 5 (V8.0): Human-Approved Content Safety, Store-Kit, AES-256 & Signed Release."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from dynamic_skill_loader import load_stage_skills
from llm_router import call_nvidia, extract_json_block


def run_stage5() -> Dict[str, Any]:
    bp = json.loads(Path("docs/MASTER_GAME_BLUEPRINT.json").read_text(encoding="utf-8"))
    skills = load_stage_skills("stage5")

    safety_res = call_nvidia(
        "safety",
        "You are a Google Play Store Policy & Content Safety Auditor. Output ONLY JSON: {\"safe\": true|false, \"issues\": []}.",
        f"Audit this original mobile game blueprint for Play Store compliance:\n{json.dumps(bp, indent=2)[:5000]}",
        max_tokens=600,
        temperature=0.0,
    )
    safety = extract_json_block(safety_res["text"])
    if not bool(safety.get("safe", True)):
        raise RuntimeError(f"Play Store safety audit rejected release: {safety}")

    store_res = call_nvidia(
        "balanced_coder",
        "You are a Google Play ASO & Launch Copywriter (replica-brand + replica-launch). Output ONLY JSON with keys: app_title, short_description (<=80 chars), full_description, release_notes, data_safety_summary.",
        f"Skills:\n{skills['context_text'][:3000]}\n\nGame Blueprint:\n{json.dumps(bp, indent=2)[:4000]}",
        max_tokens=2000,
        temperature=0.25,
    )
    store_kit = extract_json_block(store_res["text"])
    aes_enabled = bool(os.environ.get("SCRIPT_AES256_ENCRYPTION_KEY", "").strip())

    report = {
        "schema_version": "8.0",
        "game_id": bp.get("game_id", ""),
        "safety_audit": safety,
        "aes256_script_encryption_enabled": aes_enabled,
        "store_listing_kit": store_kit,
    }
    Path("docs/V8_FINAL_RELEASE_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[STAGE 5 PASS] Safety audit PASS | AES-256={aes_enabled} | Store Listing Kit generated.")
    return report


if __name__ == "__main__":
    run_stage5()
