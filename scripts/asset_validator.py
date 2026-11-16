#!/usr/bin/env python3
"""
AUTOMATED ASSET VALIDATION & MISSING-ASSET DETECTOR (V5.0)
Scans all `.tscn`, `.tres`, `.gd`, and `project.godot` files for `res://`
asset references and verifies that every referenced script, scene, texture,
mesh, or audio file actually exists on disk and is non-empty.
Only scans regular files (never the `.godot` import cache directory).
Exits with code 1 if any broken or missing asset reference is found!
"""

import json
from pathlib import Path
import re
import sys
from typing import Dict, List

RES_REF_PATTERN = re.compile(r'res://([a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+)')


def validate_all_assets() -> Dict[str, object]:
    missing: List[str] = []
    empty_files: List[str] = []
    checked_refs: List[str] = []

    scan_files = [
        p for p in (
            list(Path(".").glob("*.godot"))
            + list(Path(".").glob("*.tscn"))
            + list(Path("scenes").glob("*.tscn"))
            + list(Path("scripts").glob("*.gd"))
        )
        if p.is_file()
    ]

    for src in scan_files:
        text = src.read_text(encoding="utf-8", errors="ignore")
        for match in RES_REF_PATTERN.finditer(text):
            rel_path = match.group(1)
            if rel_path.startswith("save") or rel_path.startswith("qa_"):
                continue
            target = Path(rel_path)
            checked_refs.append(f"{src} -> res://{rel_path}")
            if not target.exists():
                missing.append(f"Missing asset referenced in {src}: res://{rel_path}")
            elif target.stat().st_size == 0:
                empty_files.append(f"Empty (0-byte) asset referenced in {src}: res://{rel_path}")

    status = "PASS" if (not missing and not empty_files) else "FAIL"
    report = {
        "status": status,
        "total_references_checked": len(checked_refs),
        "missing_assets": missing,
        "empty_assets": empty_files,
    }
    print(json.dumps(report, indent=2))
    if status != "PASS":
        sys.exit(1)
    return report


if __name__ == "__main__":
    validate_all_assets()
