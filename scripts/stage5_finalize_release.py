#!/usr/bin/env python3
"""
STAGE 4/5 — Android Gradle Export, Signing, Optional AES-256 Hardening & Store-Kit Builder (V7.0)
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from llm_router import nvidia_chat


def _configure_export_presets(pkg: str, app_name: str, ks_path: str, ks_pass: str, mode: str, enc_key: str) -> tuple[str, str]:
    cfg_p = Path("export_presets.cfg")
    txt = cfg_p.read_text(encoding="utf-8")
    Path("export_presets.cfg.bak").write_text(txt, encoding="utf-8")

    # Find preset names dynamically so we preserve proven Godot 4.7.2 SDK 36 Gradle config
    blocks = re.split(r"(?=\[preset\.\d+\])", txt)
    apk_preset = "Android (Direct Install APK)"
    aab_preset = "Android (Google Play AAB)"

    updated = []
    for blk in blocks:
        m_name = re.search(r'^name="([^"]+)"', blk, re.M)
        m_path = re.search(r'^export_path="([^"]+)"', blk, re.M)
        if m_name and m_path:
            ep = m_path.group(1)
            if ep.endswith(".apk"):
                apk_preset = m_name.group(1)
            elif ep.endswith(".aab"):
                aab_preset = m_name.group(1)
            blk = re.sub(r'^package/unique_name="[^"]*"', f'package/unique_name="{pkg}"', blk, flags=re.M)
            blk = re.sub(r'^package/name="[^"]*"', f'package/name="{app_name}"', blk, flags=re.M)
            blk = re.sub(r'^keystore/release="[^"]*"', f'keystore/release="{ks_path}"', blk, flags=re.M)
            blk = re.sub(r'^keystore/release_user="[^"]*"', 'keystore/release_user="studio_release"', blk, flags=re.M)
            blk = re.sub(r'^keystore/release_password="[^"]*"', f'keystore/release_password="{ks_pass}"', blk, flags=re.M)
            if mode == "final" and enc_key and len(enc_key) == 64:
                blk = re.sub(r'^encrypt_pck=(true|false)', "encrypt_pck=true", blk, flags=re.M)
                blk = re.sub(r'^encrypt_directory=(true|false)', "encrypt_directory=true", blk, flags=re.M)
                if "encryption_key=" in blk:
                    blk = re.sub(r'^encryption_key="[^"]*"', f'encryption_key="{enc_key}"', blk, flags=re.M)
        updated.append(blk)

    cfg_p.write_text("".join(updated), encoding="utf-8")
    return apk_preset, aab_preset


def _build_store_kit(order: dict, spec: dict) -> None:
    kit = Path("build/store_kit")
    kit.mkdir(parents=True, exist_ok=True)
    for name in ("icon_512x512.png", "feature_graphic_1024x500.png"):
        src = Path("assets/generated/store") / name
        if src.exists():
            shutil.copy2(src, kit / name)

    # Play Store safety audit via nemotron-3.5-content-safety
    safety_txt, safety_model = nvidia_chat(
        [{"role": "user", "content": f"Audit this mobile puzzle game for Google Play Store content safety: Title={spec.get('title')}, Genre={order['genre']}, Tagline={spec.get('tagline')}. Reply SAFE or UNSAFE with 1 line."}],
        role="safety",
        max_tokens=100,
    )

    # Store listing copy via replica-brand + replica-launch
    listing_txt, listing_model = nvidia_chat(
        [{"role": "user", "content": f"Write a crisp Google Play Store listing for original mobile game '{spec.get('title')}' ({order['genre']}). Include Short Description (<=80 chars), Full Description, and 5 Feature Bullets."}],
        role="balanced",
        max_tokens=500,
    )
    if not listing_txt:
        listing_txt = f"# {spec.get('title')}\n\n{spec.get('tagline')}\n\n- 30 Handcrafted Levels\n- Zero Forced Mid-Move Ads\n- Offline Play Ready\n"

    (kit / "PLAY_STORE_LISTING.md").write_text(
        f"<!-- Safety Audit ({safety_model}): {safety_txt[:180]} -->\n"
        f"<!-- Listing Author: {listing_model} -->\n\n{listing_txt}\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preview", "final"), default="preview")
    parser.add_argument("--package-name", default="")
    parser.add_argument("--app-name", default="")
    args = parser.parse_args()

    order = json.loads(Path("docs/generated/resolved_order.json").read_text(encoding="utf-8"))
    spec = json.loads(Path("docs/generated/design_spec.json").read_text(encoding="utf-8"))

    pkg = args.package_name.strip() or order.get("package_name", "com.aistudio.origgame")
    app_name = args.app_name.strip() or spec.get("title", "AI Studio Game")
    ks_path = "/tmp/studio_release.jks"
    ks_pass = os.environ["ANDROID_KEYSTORE_PASSWORD"]
    enc_key = os.environ.get("SCRIPT_AES256_ENCRYPTION_KEY", "").strip()

    if args.mode == "final":
        # Switch AD_MODE to PRODUCTION
        cfg = Path("scripts/app_config.gd")
        if cfg.exists():
            cfg.write_text(cfg.read_text(encoding="utf-8").replace('AD_MODE: String = "TEST"', 'AD_MODE: String = "PRODUCTION"'), encoding="utf-8")
        _build_store_kit(order, spec)

    apk_preset, aab_preset = _configure_export_presets(pkg, app_name, ks_path, ks_pass, args.mode, enc_key)
    Path("build/android").mkdir(parents=True, exist_ok=True)

    # Export signed APK
    print(f"[EXPORT] Building signed APK using preset '{apk_preset}'...")
    subprocess.run(
        ["xvfb-run", "--auto-servernum", "-s", "-screen 0 720x1280x24", "godot", "--editor", "--path", ".", "--export-release", apk_preset, "build/android/game_install.apk"],
        timeout=600, check=True,
    )

    if args.mode == "final":
        print(f"[EXPORT] Building signed Play Store AAB using preset '{aab_preset}'...")
        subprocess.run(
            ["xvfb-run", "--auto-servernum", "-s", "-screen 0 720x1280x24", "godot", "--editor", "--path", ".", "--export-release", aab_preset, "build/android/game_release.aab"],
            timeout=600, check=True,
        )

    print(f"[EXPORT PASS] Mode={args.mode} | Package={pkg} | App={app_name}")


if __name__ == "__main__":
    main()
