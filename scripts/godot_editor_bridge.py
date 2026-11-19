#!/usr/bin/env python3
"""Small local JSONL bridge; not an official Godot MCP implementation.
Only exposes read-only project inspection and bounded validation commands."""
from __future__ import annotations
import argparse, json, os, subprocess
from pathlib import Path

ALLOWED = {"inspect_scene_tree", "validate_project", "read_file_metadata"}

def inside(path: Path, root: Path) -> bool:
    try: path.resolve().relative_to(root.resolve()); return True
    except ValueError: return False

def inspect_scene_tree(root: Path, rel: str) -> dict:
    p=(root/rel).resolve()
    if p.suffix != ".tscn" or not inside(p,root) or not p.is_file(): raise ValueError("scene path is outside project or not a .tscn")
    nodes=[]
    for line in p.read_text(encoding="utf-8",errors="replace").splitlines():
        if line.startswith("[node "): nodes.append(line[:240])
    return {"status":"PASS","scene":str(p.relative_to(root)),"node_declarations":nodes,"read_only":True}

def handle(req: dict, root: Path) -> dict:
    op=req.get("op")
    if op not in ALLOWED: raise ValueError("unsupported read-only operation")
    if op=="inspect_scene_tree": return inspect_scene_tree(root,str(req.get("scene","")))
    if op=="read_file_metadata":
        p=(root/str(req.get("path",""))).resolve()
        if not inside(p,root) or not p.is_file(): raise ValueError("path outside project")
        return {"status":"PASS","path":str(p.relative_to(root)),"bytes":p.stat().st_size,"read_only":True}
    project=root/"project.godot"
    return {"status":"PASS" if project.exists() else "FAIL","project_exists":project.exists(),"godot_version":"4.7.2-stable","renderer":"gl_compatibility","read_only":True}

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--project-root",default="."); a=p.parse_args(); root=Path(a.project_root).resolve()
    for line in os.fdopen(0):
        try: print(json.dumps(handle(json.loads(line),root),sort_keys=True),flush=True)
        except Exception as exc: print(json.dumps({"status":"FAIL","error":str(exc),"read_only":True}),flush=True)
if __name__=="__main__": main()
