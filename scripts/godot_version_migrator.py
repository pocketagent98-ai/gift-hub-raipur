#!/usr/bin/env python3
"""Only stable Godot migration; never accepts beta/dev releases."""
from __future__ import annotations
import argparse,json,shutil
from pathlib import Path

def migrate(root: Path, target: str="4.8-stable", simulate_failure: bool=False) -> dict:
    if target != "4.8-stable": raise ValueError("only verified 4.8-stable candidate is supported")
    pin=root/"config/pinned_toolchains_and_checksums.json"; backup=root/".migration_vault/pre_godot48/pinned_toolchains_and_checksums.json"; backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(pin,backup)
    scanner=root/"scripts/godot_legacy_code_scanner.py"
    try:
        if simulate_failure: raise RuntimeError("simulated migration failure")
        data=json.loads(pin.read_text()); data["migration_candidate"]={"version":target,"status":"PROPOSAL_ONLY","official_checksum_verified":False}; pin.write_text(json.dumps(data,indent=2)+"\n")
        return {"status":"PROPOSAL_ONLY","target":target,"vault_snapshot":str(backup),"scanner_present":scanner.exists(),"production_pin_changed":False}
    except Exception as exc:
        shutil.copy2(backup,pin); return {"status":"FAILED_AND_REVERTED","target":target,"error":str(exc),"restored":True}
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--project-root",default="."); p.add_argument("--target",default="4.8-stable"); p.add_argument("--simulate-failure",action="store_true"); a=p.parse_args(); print(json.dumps(migrate(Path(a.project_root).resolve(),a.target,a.simulate_failure),indent=2))
