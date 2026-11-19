#!/usr/bin/env python3
"""Deterministic Fusion output contract for research and UI evidence."""
from __future__ import annotations
import argparse,json
from pathlib import Path

def build(project_root: Path) -> dict:
    docs=project_root/"docs"; docs.mkdir(exist_ok=True)
    dossier=json.loads((docs/"REFERENCE_INTELLIGENCE_DOSSIER.json").read_text()) if (docs/"REFERENCE_INTELLIGENCE_DOSSIER.json").exists() else {}
    ui=json.loads((docs/"UI_ELEMENT_AND_INTERACTION_MAP.json").read_text()) if (docs/"UI_ELEMENT_AND_INTERACTION_MAP.json").exists() else {}
    upgrades=json.loads((docs/"UNIQUE_GAME_UPGRADE_SPEC.json").read_text()) if (docs/"UNIQUE_GAME_UPGRADE_SPEC.json").exists() else {}
    out={"schema_version":"1.0","engine":"replica-craft-clean-room-fusion","source_evidence":{"reference_dossier":bool(dossier),"ui_map":bool(ui),"review_confidence":dossier.get("confidence","UNKNOWN")},"mechanics_summary":{"genre":"original_mobile_puzzle","preserved_player_benefits":["responsive placement","legible combo feedback","short offline sessions"],"proprietary_expression_excluded":True},"ui_map_summary":{"screen_count":len(ui.get("screens",ui.get("screen_map",{}))) if isinstance(ui,dict) else 0,"minimum_touch_target_px":56,"layout_source":"repository-generated interaction map"},"unique_upgrade_proposals":[{"name":"Smart Mercy & Juggle Vault","originality":"new rescue-piece and hold-slot rule"},{"name":"Crystal Fever Overdrive","originality":"new combo reward state"},{"name":"Streak Booster Forge","originality":"new progression reward cadence"}],"clean_room_constraints":["no copied assets, source code, branding, levels, or distinctive protected expression","procedural/original assets only","record licenses and attribution in ASSET_LICENSE_MANIFEST"]}
    (docs/"FUSION_BLUEPRINT.json").write_text(json.dumps(out,indent=2),encoding="utf-8"); return out
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--project-root",default="."); a=p.parse_args(); print(json.dumps(build(Path(a.project_root).resolve()),indent=2))
