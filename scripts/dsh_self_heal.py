#!/usr/bin/env python3
"""Autonomous self-heal loop driven by the fail-closed quality gate.

The deterministic factory remains the source of truth. This agent reads the
gate's repair requests, asks the private NVIDIA NIM route to revise the design
blueprint, repairs any missing schema fields deterministically, and rewrites
the runtime UI/gameplay spec. The workflow then rebuilds and re-gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import ai_game_designer


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _repair_blueprint(project_root: Path, feedback: Dict[str, Any], attempt: int) -> Dict[str, Any]:
    order = (project_root / "ORDER.md").read_text(encoding="utf-8") if (project_root / "ORDER.md").exists() else ""
    game_id = ai_game_designer._field(order, "GAME_ID", "studio_game_01")
    genre = ai_game_designer._canonical_genre(ai_game_designer._field(order, "GENRE", "match_3"))
    blueprint_path = project_root / "docs" / "AI_GAME_DESIGN_BLUEPRINT.json"
    blueprint = _load_json(blueprint_path) or ai_game_designer.build_design_blueprint(project_root)
    defaults = ai_game_designer._defaults(genre)
    errors = feedback.get("errors", []) or feedback.get("repair_requests", [])
    if not isinstance(errors, list):
        errors = [str(errors)]

    nv_key = (os.environ.get("NVIDIA_NIM_API_KEY", "") or os.environ.get("NVIDIA_API_KEY", "")).strip()
    revised: Dict[str, Any] = {}
    model_used = ""
    status = "DETERMINISTIC_REPAIR"
    if nv_key:
        prompt = f"""The studio quality gate rejected this {genre} game design for GAME_ID {game_id}.
Defects:
{json.dumps(errors[:40], indent=2)}

Current blueprint:
{json.dumps(blueprint, indent=2)[:12000]}

Return ONLY a corrected complete JSON blueprint with the same schema. It must have:
- a real original game_title and tagline
- theme colors as #RRGGBB
- 3 real boosters
- at least 4 real shop items
- exactly 30 original level names
- exactly 7 daily rewards
- a concrete tutorial sentence
- a genre-specific special_rule
No placeholders, no empty menus, no generic 'Open X' buttons."""
        raw, model_used = ai_game_designer._call_nim(prompt, nv_key)
        if raw:
            try:
                revised = ai_game_designer._parse_json(raw)
                status = "LIVE_NVIDIA_NIM_SELF_HEAL"
            except Exception as exc:
                print(f"[SELF_HEAL] NIM JSON invalid: {exc}")
    merged = ai_game_designer._merge(defaults, revised if revised else blueprint)
    merged["genre"] = genre
    merged["game_id"] = game_id
    merged["status"] = status
    merged["model_used"] = model_used or str(blueprint.get("model_used", ""))
    merged["self_heal_attempt"] = attempt
    merged["self_heal_defects"] = errors[:40]
    # Deterministic fail-closed repairs for anything the model missed.
    if len(merged.get("shop_items", [])) < 4:
        merged["shop_items"] = defaults["shop_items"]
    if len(merged.get("boosters", [])) < 3:
        merged["boosters"] = defaults["boosters"]
    if len(merged.get("level_names", [])) != 30:
        merged["level_names"] = defaults["level_names"]
    if len(merged.get("daily_rewards", [])) != 7:
        merged["daily_rewards"] = defaults["daily_rewards"]
    if not str(merged.get("tutorial", "")).strip():
        merged["tutorial"] = defaults["tutorial"]
    if not str(merged.get("special_rule", "")).strip():
        merged["special_rule"] = defaults["special_rule"]
    for key, value in defaults["theme"].items():
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(merged.get("theme", {}).get(key, ""))):
            merged.setdefault("theme", {})[key] = value
    blueprint_path.parent.mkdir(parents=True, exist_ok=True)
    blueprint_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    ai_game_designer.write_runtime_files(project_root, merged)
    return merged


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--stage", default="stage2")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    feedback = _load_json(Path("/tmp/pro_quality_feedback.json"))
    if not feedback:
        feedback = _load_json(root / "docs/PRO_QUALITY_GATE_REPORT.json")
    errors = feedback.get("errors", []) if isinstance(feedback, dict) else []
    if not errors:
        print("[SELF_HEAL] No defects to repair.")
        return

    if args.stage == "stage1":
        import subprocess
        for cmd in (
            ["python3", "scripts/generate_intelligence_dossier.py"],
            ["python3", "scripts/fusion_engine.py", "--project-root", "."],
            ["python3", "scripts/generate_complete_game_bible.py"],
        ):
            try:
                subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=120, check=False)
            except Exception as exc:
                print(f"[SELF_HEAL] Optional stage1 repair {cmd[1]} failed: {exc}")

    blueprint = _repair_blueprint(root, feedback, args.attempt)
    report = {
        "status": "SELF_HEALED",
        "stage": args.stage,
        "attempt": args.attempt,
        "defects_received": errors,
        "blueprint_sha256": hashlib.sha256(json.dumps(blueprint, sort_keys=True).encode("utf-8")).hexdigest(),
        "model_used": blueprint.get("model_used", ""),
        "repair_mode": blueprint.get("status", ""),
        "next_action": "rebuild_project_then_re_run_quality_gate",
    }
    (root / "docs/SELF_HEAL_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
