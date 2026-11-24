#!/usr/bin/env python3
"""Prepare the final approved release: package rename, version bump, hardening.

The workflow exports and signs the APK/AAB with the full Godot GUI after this
script prepares the project. This script never changes GitHub Secrets.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import release_hardening
import studio_game_factory


def _field(text: str, key: str, default: str = "") -> str:
    m = re.search(rf"^{re.escape(key)}[ \t]*:[ \t]*(.*)$", text, re.M | re.I)
    return m.group(1).strip() if m and m.group(1).strip() else default


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--vault-dir", default="/dev/shm/private_studio_vault")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    vault = Path(args.vault_dir)
    order = (root / "ORDER.md").read_text(encoding="utf-8") if (root / "ORDER.md").exists() else ""
    job = studio_game_factory.resolve_job(root)
    if job["action_mode"] != "finalize_and_lock_release":
        raise SystemExit(f"[FINALIZE_FAIL_CLOSED] ACTION_MODE is '{job['action_mode']}', expected 'FINALIZE_AND_LOCK_RELEASE'.")
    final_package = _field(order, "FINAL_PACKAGE_NAME", job.get("final_package_name", ""))
    final_app_name = _field(order, "FINAL_APP_NAME", job.get("final_app_name", job["title"]))
    if not final_package or not re.fullmatch(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$", final_package):
        raise SystemExit("[FINALIZE_FAIL_CLOSED] FINAL_PACKAGE_NAME must be a valid reverse-domain Android package.")
    version_name = job["version"].lstrip("v")
    meta_path = vault / "keystore_meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
    version_code = int(meta.get("version_code", job.get("version_code", 2)))
    if version_code < 2:
        version_code = 2
    encrypted_template = str(vault / "encrypted_android_release.apk")
    report = release_hardening.run_hardening(
        root,
        final_package,
        final_app_name,
        version_code,
        version_name,
        bool(job.get("enable_anti_reverse_engineering", True)),
        str(job.get("expected_signing_cert_sha256", "")),
        encrypted_template,
    )
    lock = {
        "status": "FINAL_RELEASE_LOCK_READY",
        "game_id": job["game_id"],
        "genre": job["genre"],
        "final_package_name": final_package,
        "final_app_name": final_app_name,
        "version_name": version_name,
        "version_code": version_code,
        "hardening": report,
        "keystore_meta": str(meta_path),
        "approval": "ACTION_MODE=FINALIZE_AND_LOCK_RELEASE",
    }
    (root / "docs" / "FINAL_RELEASE_LOCK.json").write_text(json.dumps(lock, indent=2), encoding="utf-8")
    print(json.dumps(lock, indent=2))


if __name__ == "__main__":
    main()
