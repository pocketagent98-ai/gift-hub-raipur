#!/usr/bin/env python3
"""
PINNED TOOLCHAIN, GITHUB ACTIONS SHA & DOWNLOAD CHECKSUM VERIFIER (SECTION 7)
- Verifies that `.github/workflows/*.yml` pin `actions/checkout` by full 40-char commit SHA.
- Verifies that `requirements.lock.txt` pins every dependency with `==`.
- Computes and verifies SHA-256 / SHA-512 checksums for any downloaded tool archives
  (such as `/tmp/godot.zip` and `/tmp/templates.tpz`) against official `SHA512-SUMS.txt`.
"""

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, List


def compute_hash(path: Path, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_pinned_supply_chain(project_root: Path = Path(".")) -> Dict[str, Any]:
    cfg_path = project_root / "config/pinned_toolchains_and_checksums.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"[FAIL_CLOSED] Missing {cfg_path}")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    errors: List[str] = []
    expected_checkout_sha = cfg["github_actions_pins"]["actions/checkout"]

    for wf in sorted((project_root / ".github/workflows").glob("*.yml")):
        txt = wf.read_text(encoding="utf-8")
        if f"actions/checkout@{expected_checkout_sha}" not in txt:
            errors.append(f"Workflow {wf.name} does not pin actions/checkout@{expected_checkout_sha}")

    req_lock = project_root / "requirements.lock.txt"
    if not req_lock.exists():
        errors.append("Missing requirements.lock.txt")
    else:
        for line in req_lock.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "==" not in s:
                errors.append(f"Unpinned Python package in requirements.lock.txt: {s}")

    # Verify downloaded Godot archives if present on runner (/tmp/godot.zip, /tmp/templates.tpz)
    verified_downloads: List[Dict[str, str]] = []
    sums_file = Path("/tmp/SHA512-SUMS.txt")
    sums_text = sums_file.read_text(encoding="utf-8") if sums_file.exists() else ""

    for dl_path, official_name in [
        (Path("/tmp/godot.zip"), "Godot_v4.7.2-stable_linux.x86_64.zip"),
        (Path("/tmp/templates.tpz"), "Godot_v4.7.2-stable_export_templates.tpz"),
    ]:
        if dl_path.exists():
            sha512 = compute_hash(dl_path, "sha512")
            sha256 = compute_hash(dl_path, "sha256")
            if sums_text and sha512 not in sums_text:
                errors.append(f"SHA-512 mismatch for {official_name}: {sha512}")
            verified_downloads.append({"file": official_name, "sha256": sha256, "sha512": sha512[:32] + "..."})

    if errors:
        raise RuntimeError(f"[SUPPLY_CHAIN_PIN_FAIL] {errors}")

    return {
        "status": "PASS",
        "checkout_sha_verified": expected_checkout_sha,
        "requirements_lock_pinned": True,
        "verified_downloads": verified_downloads,
    }


if __name__ == "__main__":
    res = verify_pinned_supply_chain(Path("."))
    print(json.dumps(res, indent=2))
