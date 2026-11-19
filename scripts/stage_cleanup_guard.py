#!/usr/bin/env python3
"""Bounded, allowlisted disk cleanup and cross-game workspace guard."""
from __future__ import annotations
import argparse, json, os, shutil, time
from pathlib import Path

SAFE_TEMP_ROOTS = (Path("/tmp/studio_qa"), Path("/tmp/qa_videos"), Path("/tmp/research_dumps"), Path("/tmp/skill_checkouts"), Path("/tmp/studio_transient"))
SAFE_CACHE_ROOTS = (Path.home()/".cache/pip", Path.home()/".npm/_cacache")
GENERATED_DIRS = ("generated", "build", "games")

def free_bytes(path: Path = Path(".")) -> int:
    return shutil.disk_usage(path.resolve()).free

def _safe_child(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve()); return True
    except ValueError:
        return False

def _remove_contents(root: Path) -> list[str]:
    removed = []
    if not root.exists(): return removed
    for child in root.iterdir():
        if not _safe_child(child, root): raise RuntimeError(f"[SECURITY_BLOCK] cleanup path escaped allowlist: {child}")
        if child.is_symlink(): child.unlink()
        elif child.is_dir(): shutil.rmtree(child)
        else: child.unlink()
        removed.append(str(child))
    return removed

def cleanup(stage: str, project_root: Path, min_free_gb: float = 5.0) -> dict:
    before = free_bytes(project_root)
    removed = []
    for root in SAFE_TEMP_ROOTS + SAFE_CACHE_ROOTS: removed.extend(_remove_contents(root))
    after = free_bytes(project_root)
    result = {"schema_version":"1.0", "stage":stage, "timestamp_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "free_bytes_before":before, "free_bytes_after":after, "free_gb_before":round(before/1024**3,3), "free_gb_after":round(after/1024**3,3), "removed_count":len(removed), "removed_allowlisted_paths":removed, "minimum_free_gb":min_free_gb, "minimum_free_space_met":after >= int(min_free_gb*1024**3), "source_preserved":project_root.resolve().exists()}
    print(json.dumps(result, indent=2))
    if not result["minimum_free_space_met"]: raise RuntimeError(f"[DISK_GUARD_FAIL] free space below configured minimum: {result['free_gb_after']} GB")
    return result

def isolate_game(project_root: Path, game_id: str, previous_game_id: str | None = None) -> dict:
    if not game_id or "/" in game_id or ".." in game_id or game_id in (".", ".."): raise ValueError("invalid game_id")
    removed = []
    if previous_game_id and previous_game_id != game_id:
        for base in GENERATED_DIRS:
            candidate = (project_root/base/previous_game_id).resolve(); allowed = (project_root/base).resolve()
            if _safe_child(candidate, allowed) and candidate.exists():
                shutil.rmtree(candidate) if candidate.is_dir() else candidate.unlink(); removed.append(str(candidate))
    return {"game_id":game_id, "previous_game_id":previous_game_id, "removed":removed, "status":"PASS"}

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--stage",default="step_zero"); p.add_argument("--project-root",default="."); p.add_argument("--min-free-gb",type=float,default=float(os.getenv("MIN_FREE_GB","5"))); p.add_argument("--isolate-game",nargs=2,metavar=("GAME_ID","PREVIOUS_GAME_ID")); a=p.parse_args()
    root=Path(a.project_root).resolve(); result=cleanup(a.stage,root,a.min_free_gb)
    if a.isolate_game: result["isolation"]=isolate_game(root,*a.isolate_game)
    out=root/"docs"/"STAGE_CLEANUP_REPORT.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2),encoding="utf-8")
if __name__ == "__main__": main()
