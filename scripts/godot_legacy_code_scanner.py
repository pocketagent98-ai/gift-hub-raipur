#!/usr/bin/env python3
"""
GODOT 4.7.2 LEGACY-CODE & ANTI-VIBE-CODING SCANNER (V4.0)
Inspired by Google/Chrome/MDN `modern-web-guidance` legacy scan:
Flags outdated Godot 3.x or C#-hallucinated GDScript patterns with zero LLM tokens
so AI agents never ship legacy/broken code.
"""

import json
from pathlib import Path
import re
import sys
from typing import List, Dict

LEGACY_PATTERNS: Dict[str, str] = {
    r"\bKinematicBody(2D|3D)?\b": "Godot 3.x KinematicBody is deprecated; use CharacterBody2D/CharacterBody3D.",
    r"\bSpatial\b": "Godot 3.x Spatial is deprecated; use Node3D.",
    r"\byield\s*\(": "Godot 3.x yield() is removed; use `await`.",
    r"\.Lerp\(": "C# PascalCase .Lerp() invalid in GDScript 4.7.2; use .lerp().",
    r"\.Position\b": "C# PascalCase .Position invalid in GDScript 4.7.2; use .position.",
    r"\bexport\s+var\b": "Godot 3.x `export var` is invalid; use `@export var`.",
    r"\bonready\s+var\b": "Godot 3.x `onready var` is invalid; use `@onready var`.",
}


def scan_gdscript_files() -> Dict[str, object]:
    findings: List[Dict[str, object]] = []
    scanned = 0
    for gd in sorted(Path("scripts").glob("*.gd")):
        scanned += 1
        lines = gd.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, 1):
            code = line.split("#", 1)[0]
            for pattern, msg in LEGACY_PATTERNS.items():
                if re.search(pattern, code):
                    findings.append({"file": str(gd), "line": idx, "message": msg, "code": line.strip()})

    status = "PASS" if not findings else "FAIL"
    report = {"status": status, "files_scanned": scanned, "legacy_findings": findings}
    print(json.dumps(report, indent=2))
    if status != "PASS":
        sys.exit(1)
    return report


if __name__ == "__main__":
    scan_gdscript_files()
