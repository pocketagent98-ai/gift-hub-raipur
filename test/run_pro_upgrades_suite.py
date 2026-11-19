#!/usr/bin/env python3
import json, tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fusion_engine, godot_editor_bridge, godot_version_migrator, stage_cleanup_guard, zero_bug_sentinel


def main():
    passed=[]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); (root/"docs").mkdir(); (root/"config").mkdir(); (root/"scripts").mkdir()
        (root/"config/pinned_toolchains_and_checksums.json").write_text('{"godot_official_release":{"version":"4.7.2-stable"}}')
        (root/"scripts/godot_legacy_code_scanner.py").write_text('# scanner')
        for name,data in (("REFERENCE_INTELLIGENCE_DOSSIER.json",{"confidence":"UNKNOWN"}),("UI_ELEMENT_AND_INTERACTION_MAP.json",{"screens":[1,2]}),("UNIQUE_GAME_UPGRADE_SPEC.json",{"features":[]})):
            (root/"docs"/name).write_text(json.dumps(data))
        r=stage_cleanup_guard.isolate_game(root,"new_game","old_game"); assert r["status"]=="PASS"; passed.append("cleanup boundary")
        f=fusion_engine.build(root); assert len(f["unique_upgrade_proposals"])==3; passed.append("fusion schema")
        s=zero_bug_sentinel.run(root,"test_game","block_puzzle"); assert s["status"]=="PASS" and len(s["tests"]["monte_carlo_balance"])==5; passed.append("sentinel oracle")
        m=godot_version_migrator.migrate(root,simulate_failure=True); assert m["status"]=="FAILED_AND_REVERTED"; passed.append("migrator rollback")
        q=godot_editor_bridge.handle({"op":"validate_project"},root); assert q["status"]=="FAIL"; passed.append("bridge read-only gate")
    print(json.dumps({"status":"PASS","passed":len(passed),"checks":passed,"failed":0},indent=2))

if __name__=="__main__": main()
