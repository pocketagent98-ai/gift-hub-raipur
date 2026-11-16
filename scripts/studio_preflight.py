#!/usr/bin/env python3
"""
STUDIO PREFLIGHT & INVARIANTS GUARD (V5.1)

Purpose
-------
Every time you drop a new game idea into `ORDER.md` and push, the studio must be able to
build it without a human fixing configuration first. This script is the single place that
knows the *hard invariants* the Android export and the QA gates depend on, and it repairs
the ones that are safe to repair automatically.

It runs as Step 0b of `.github/workflows/ai-game-studio.yml`, so a broken studio fails in
seconds with a readable reason instead of failing 10 minutes later inside Godot.

Modes
-----
  python3 scripts/studio_preflight.py            # repair (idempotent) then verify
  python3 scripts/studio_preflight.py --check     # verify only, never writes

Invariants enforced
-------------------
1. Required GitHub Actions secrets are present (values are never printed).
2. `project.godot` declares an icon and stays on Godot 4.7 GL Compatibility.
3. The QA bot (`DeepGameVerifierBot`) never leaks into production autoloads.
4. `export_presets.cfg`:
   - a non-Gradle Android preset must NOT override Min/Target SDK (Godot refuses to export);
   - at least one preset declares the Target SDK required by the compatibility policy;
   - `scripts/deep_game_verifier_bot.gd` stays excluded from production exports.
5. `ORDER.md` exists and carries a GAME_ID, so the factory knows what to build.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

REQUIRED_SECRETS = [
    "GEMINI_API_KEY",
    "NVIDIA_API_KEY",
    "HF_TOKEN",
    "HF_PRIVATE_DATASET_REPO",
    "ANDROID_KEYSTORE_PASSWORD",
]

SDK_OVERRIDE_KEYS = (
    "gradle_build/min_sdk",
    "gradle_build/target_sdk",
    "version/min_sdk",
    "version/target_sdk",
)


def load_target_sdk() -> int:
    pol_path = Path("config/android_compatibility_policy.json")
    if pol_path.exists():
        pol = json.loads(pol_path.read_text(encoding="utf-8"))
        return int(pol.get("android_requirements", {}).get("new_apps_and_updates_target_sdk", 36))
    return 36


def load_min_sdk() -> int:
    pol_path = Path("config/android_compatibility_policy.json")
    if pol_path.exists():
        pol = json.loads(pol_path.read_text(encoding="utf-8"))
        return int(pol.get("android_requirements", {}).get("min_sdk", 24))
    return 24


def check_secrets(errors: List[str], notes: List[str]) -> None:
    missing = [name for name in REQUIRED_SECRETS if not os.environ.get(name, "").strip()]
    if missing:
        errors.append(
            "Missing GitHub Actions secret(s): " + ", ".join(missing) +
            " — add them in Settings > Secrets and variables > Actions (values are never read by this script)."
        )
    else:
        notes.append(f"All {len(REQUIRED_SECRETS)} required studio secrets are present.")


def repair_project_godot(repair: bool, errors: List[str], notes: List[str]) -> None:
    path = Path("project.godot")
    if not path.exists():
        errors.append("project.godot is missing — the studio cannot export without it.")
        return

    txt = path.read_text(encoding="utf-8")
    original = txt

    if 'config/features=PackedStringArray("4.7", "GL Compatibility")' not in txt:
        errors.append(
            'project.godot is not locked to config/features=PackedStringArray("4.7", "GL Compatibility").'
        )

    if "DeepGameVerifierBot" in txt:
        errors.append(
            "CRITICAL: DeepGameVerifierBot is registered in project.godot — QA code must never ship in production."
        )

    icon_missing = "config/icon=" not in txt
    if icon_missing:
        icon_file = Path("icon.svg")
        if not icon_file.exists():
            errors.append("project.godot has no icon and icon.svg is missing — Android export would fail.")
        elif repair:
            if "[application]" in txt:
                txt = txt.replace("[application]", '[application]\nconfig/icon="res://icon.svg"', 1)
            else:
                txt = '[application]\nconfig/icon="res://icon.svg"\n\n' + txt
            notes.append('REPAIRED project.godot: added config/icon="res://icon.svg".')
        else:
            errors.append('project.godot has no config/icon (Android export fails without one).')

    if txt != original:
        path.write_text(txt, encoding="utf-8")


def _iter_preset_blocks(txt: str):
    """Yields (preset_name, block_text) for every [preset.N.options] section."""
    names: Dict[str, str] = {}
    for m in re.finditer(r"^\[preset\.(\d+)\]\s*$([\s\S]*?)(?=^\[|\Z)", txt, re.M):
        nm = re.search(r'^name="([^"]+)"', m.group(2), re.M)
        if nm:
            names[m.group(1)] = nm.group(1)
    for m in re.finditer(r"^\[preset\.(\d+)\.options\]\s*$([\s\S]*?)(?=^\[|\Z)", txt, re.M):
        yield names.get(m.group(1), f"preset.{m.group(1)}"), m.group(2)


def repair_export_presets(repair: bool, target_sdk: int, min_sdk: int,
                          errors: List[str], notes: List[str]) -> None:
    path = Path("export_presets.cfg")
    if not path.exists():
        errors.append("export_presets.cfg is missing — nothing can be exported.")
        return

    txt = path.read_text(encoding="utf-8")
    if "deep_game_verifier_bot.gd" not in txt:
        errors.append("export_presets.cfg must exclude scripts/deep_game_verifier_bot.gd from production exports.")

    names: Dict[str, str] = {}
    for m in re.finditer(r"^\[preset\.(\d+)\]\s*$([\s\S]*?)(?=^\[|\Z)", txt, re.M):
        nm = re.search(r'^name="([^"]+)"', m.group(2), re.M)
        if nm:
            names[m.group(1)] = nm.group(1)

    gradle_presets = 0
    removals: List[tuple] = []
    for m in re.finditer(r"^\[preset\.(\d+)\.options\]\s*$([\s\S]*?)(?=^\[|\Z)", txt, re.M):
        preset_name = names.get(m.group(1), f"preset.{m.group(1)}")
        body, body_start = m.group(2), m.start(2)
        if re.search(r"^gradle_build/use_gradle_build=true\s*$", body, re.M):
            gradle_presets += 1
            continue
        # Godot refuses to export a non-Gradle Android preset that overrides Min/Target SDK.
        offending = []
        for key in SDK_OVERRIDE_KEYS:
            for hit in re.finditer(rf"^{re.escape(key)}=.*\n?", body, re.M):
                offending.append(key)
                removals.append((body_start + hit.start(), body_start + hit.end()))
        if offending:
            if repair:
                notes.append(
                    f"REPAIRED export_presets.cfg: removed SDK override(s) {', '.join(offending)} "
                    f"from non-Gradle preset '{preset_name}' (Godot rejects those without Gradle build)."
                )
            else:
                errors.append(
                    f"Preset '{preset_name}' uses no Gradle build but overrides {', '.join(offending)} — "
                    "Godot will refuse to export it."
                )

    if repair and removals:
        for start_pos, end_pos in sorted(removals, reverse=True):
            txt = txt[:start_pos] + txt[end_pos:]

    if gradle_presets and repair:
        # Only Gradle presets keep SDK overrides, so align those with the compatibility policy.
        for key in ("gradle_build/min_sdk", "version/min_sdk"):
            txt = re.sub(rf"^{re.escape(key)}=\d+", f"{key}={min_sdk}", txt, flags=re.M)
        for key in ("gradle_build/target_sdk", "version/target_sdk"):
            txt = re.sub(rf"^{re.escape(key)}=\d+", f"{key}={target_sdk}", txt, flags=re.M)

    if f"version/target_sdk={target_sdk}" not in txt and f"gradle_build/target_sdk={target_sdk}" not in txt:
        errors.append(
            f"export_presets.cfg does not target SDK {target_sdk} required by the Google Play policy."
        )

    path.write_text(txt, encoding="utf-8")
    if gradle_presets:
        notes.append(f"Target SDK {target_sdk} / Min SDK {min_sdk} aligned for {gradle_presets} Gradle preset(s).")


def check_order(errors: List[str], notes: List[str]) -> None:
    path = Path("ORDER.md")
    if not path.exists():
        errors.append("ORDER.md is missing — the studio has no game idea to build.")
        return
    txt = path.read_text(encoding="utf-8")
    gid = re.search(r"^GAME_ID\s*:\s*(\S+)", txt, re.M | re.I)
    if not gid:
        errors.append("ORDER.md has no 'GAME_ID:' line — the factory cannot name the game.")
    else:
        notes.append(f"ORDER.md targets game_id='{gid.group(1)}'.")


def main() -> int:
    repair = "--check" not in sys.argv
    errors: List[str] = []
    notes: List[str] = []

    check_secrets(errors, notes)
    check_order(errors, notes)
    repair_project_godot(repair, errors, notes)
    repair_export_presets(repair, load_target_sdk(), load_min_sdk(), errors, notes)

    for note in notes:
        print(f"[PREFLIGHT] {note}")

    if errors:
        for err in errors:
            print(f"[PREFLIGHT_FAIL] {err}")
        print("\n[PREFLIGHT_FAIL] Studio is not build-ready. Fix the items above, then push again.")
        return 1

    mode = "REPAIRED_AND_VERIFIED" if repair and any(n.startswith("REPAIRED") for n in notes) else "VERIFIED"
    print(f"\n[PREFLIGHT_PASS] Studio invariants {mode}: secrets, ORDER.md, project.godot and export_presets.cfg are build-ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
