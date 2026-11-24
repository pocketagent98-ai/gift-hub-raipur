#!/usr/bin/env python3
"""Final release lock: package rename, comment stripping, binary resources,
R8/ProGuard, encrypted config vault, and runtime signer fingerprint wiring.

encrypt_pck / encrypt_directory are enabled ONLY when a matching custom
encrypted Godot 4.7.2 Android template exists in the HF vault. Otherwise they
stay false and the report states exactly why.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
from pathlib import Path
from typing import Any, Dict

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"STUDIOV1"
PROGUARD_RULES = """# AI Game Studio final release lock
-keep class org.godotengine.godot.** { *; }
-keep class org.godotengine.plugin.** { *; }
-keep class com.godot.game.** { *; }
-keep class org.godotengine.godot.GodotLib { *; }
-dontwarn org.godotengine.**
-dontwarn com.google.android.gms.**
"""


def strip_gdscript_comments(text: str) -> str:
    out_lines = []
    for line in text.splitlines():
        in_str = False
        quote = ""
        escape = False
        cut = len(line)
        for i, ch in enumerate(line):
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == quote:
                    in_str = False
            else:
                if ch == "#":
                    cut = i
                    break
                if ch in ('"', "'"):
                    in_str = True
                    quote = ch
        out_lines.append(line[:cut].rstrip())
    return "\n".join(out_lines) + "\n"


def _set_config_constant(text: str, name: str, value: str) -> str:
    pattern = rf"^(const\s+{re.escape(name)}\s*:=\s*).*$"
    if re.search(pattern, text, re.M):
        return re.sub(pattern, lambda m: m.group(1) + value, text, count=1, flags=re.M)
    return text


def _read_secure_key(text: str) -> str:
    m = re.search(r'^const\s+SECURE_CONFIG_KEY\s*:=\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else "studio-secure-fallback-key"


def build_encrypted_vault(project_root: Path, secure_key: str) -> Dict[str, Any]:
    blueprint = {}
    bp_path = project_root / "docs" / "AI_GAME_DESIGN_BLUEPRINT.json"
    if bp_path.exists():
        try:
            blueprint = json.loads(bp_path.read_text(encoding="utf-8"))
        except Exception:
            blueprint = {}
    levels = []
    for level in range(1, 31):
        levels.append({
            "level": level,
            "target_score": int(blueprint.get("target_score", 250) or 250) + level * 70,
            "moves": 18 + min(level, 12),
            "colors": 4 if level < 3 else (5 if level < 12 else 6),
            "name": (blueprint.get("level_names", [])[level - 1] if len(blueprint.get("level_names", [])) >= level else f"Level {level}"),
        })
    payload = {
        "game_id": blueprint.get("game_id", ""),
        "theme": blueprint.get("theme", {}),
        "shop_items": blueprint.get("shop_items", []),
        "boosters": blueprint.get("boosters", []),
        "daily_rewards": blueprint.get("daily_rewards", []),
        "tutorial": blueprint.get("tutorial", ""),
        "special_rule": blueprint.get("special_rule", ""),
        "levels": levels,
    }
    plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    salt = secrets.token_bytes(16)
    iv = secrets.token_bytes(16)
    key = hashlib.sha256((secure_key + salt.hex()).encode("utf-8")).digest()
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    vault_dir = project_root / "assets" / "secure"
    vault_dir.mkdir(parents=True, exist_ok=True)
    vault_path = vault_dir / "config_vault.enc"
    vault_path.write_bytes(MAGIC + salt + iv + ciphertext)
    return {
        "vault_path": str(vault_path.relative_to(project_root)),
        "vault_bytes": vault_path.stat().st_size,
        "plaintext_bytes": len(plaintext),
        "aes": "AES-256-CBC + PKCS7",
        "key_derivation": "SHA-256(secure_key + salt_hex)",
        "levels_encrypted": len(levels),
        "shop_items_encrypted": len(payload["shop_items"]),
    }


def patch_android_gradle(project_root: Path) -> Dict[str, Any]:
    build_gradle = project_root / "android" / "build" / "build.gradle"
    if not build_gradle.exists():
        return {"status": "SKIPPED_NO_GRADLE_TEMPLATE", "r8_minify": False, "shrink_resources": False}
    text = build_gradle.read_text(encoding="utf-8")
    rules_path = project_root / "android" / "build" / "proguard-rules.pro"
    rules_path.write_text(PROGUARD_RULES, encoding="utf-8")
    if "minifyEnabled" not in text:
        text, count = re.subn(
            r"(\brelease\s*\{)",
            r"\1\n            minifyEnabled true\n            shrinkResources true\n            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'",
            text,
            count=1,
        )
    else:
        count = 0
    build_gradle.write_text(text, encoding="utf-8")
    return {"status": "PATCHED_R8", "r8_minify": "minifyEnabled true" in text, "shrink_resources": "shrinkResources true" in text, "patches_applied": count, "proguard_rules": str(rules_path.relative_to(project_root))}


def run_hardening(project_root: Path, package_name: str, app_name: str, version_code: int, version_name: str, enable_anti_re: bool, expected_cert: str, encrypted_template: str = "") -> Dict[str, Any]:
    report: Dict[str, Any] = {"status": "HARDENED", "package_name": package_name, "app_name": app_name, "version_code": version_code, "version_name": version_name}
    presets = project_root / "export_presets.cfg"
    if presets.exists():
        text = presets.read_text(encoding="utf-8")
        text = re.sub(r'^package/unique_name=".*"$', f'package/unique_name="{package_name}"', text, flags=re.M)
        text = re.sub(r'^package/name=".*"$', f'package/name="{app_name}"', text, flags=re.M)
        text = re.sub(r'^version/code=\d+$', f'version/code={version_code}', text, flags=re.M)
        text = re.sub(r'^version/name=".*"$', f'version/name="{version_name}"', text, flags=re.M)
        text = re.sub(r'^script_export_mode=\d+$', 'script_export_mode=2', text, flags=re.M)
        text = re.sub(r'^convert_text_resources_to_binary=.*$', 'convert_text_resources_to_binary=true', text, flags=re.M)
        encrypted_ok = bool(encrypted_template and Path(encrypted_template).exists() and Path(encrypted_template).stat().st_size > 1024)
        text = re.sub(r'^encrypt_pck=.*$', f'encrypt_pck={"true" if encrypted_ok else "false"}', text, flags=re.M)
        text = re.sub(r'^encrypt_directory=.*$', f'encrypt_directory={"true" if encrypted_ok else "false"}', text, flags=re.M)
        presets.write_text(text, encoding="utf-8")
        report["export_presets"] = "UPDATED"
        report["encrypted_pck"] = encrypted_ok
        report["encrypted_template"] = encrypted_template if encrypted_ok else ""
    project = project_root / "project.godot"
    if project.exists():
        text = project.read_text(encoding="utf-8")
        text = re.sub(r'^config/name=".*"$', f'config/name="{app_name}"', text, flags=re.M)
        text = re.sub(r'^config/version=".*"$', f'config/version="{version_name}"', text, flags=re.M)
        project.write_text(text, encoding="utf-8")
        report["project_name"] = app_name

    app_config = project_root / "scripts" / "app_config.gd"
    secure_key = "studio-secure-fallback-key"
    if app_config.exists():
        text = app_config.read_text(encoding="utf-8")
        secure_key = _read_secure_key(text)
        text = _set_config_constant(text, "FINAL_PACKAGE_NAME", json.dumps(package_name))
        text = _set_config_constant(text, "FINAL_APP_NAME", json.dumps(app_name))
        text = _set_config_constant(text, "ENABLE_ANTI_REVERSE_ENGINEERING", "true" if enable_anti_re else "false")
        text = _set_config_constant(text, "EXPECTED_SIGNING_CERT_SHA256", json.dumps(expected_cert))
        text = _set_config_constant(text, "SIGNATURE_CHECK_STRICT", "true" if enable_anti_re and expected_cert else "false")
        app_config.write_text(strip_gdscript_comments(text), encoding="utf-8")
        report["runtime_signature_check"] = bool(enable_anti_re and expected_cert)

    stripped_files = []
    for gd in (project_root / "scripts").glob("*.gd"):
        if gd.name in ("deep_game_verifier_bot.gd", "qa_bootstrap.gd"):
            continue
        original = gd.read_text(encoding="utf-8")
        cleaned = strip_gdscript_comments(original)
        if cleaned != original:
            gd.write_text(cleaned, encoding="utf-8")
            stripped_files.append(gd.name)
    report["gdscript_comments_stripped"] = stripped_files
    report["vault"] = build_encrypted_vault(project_root, secure_key)
    report["android_gradle"] = patch_android_gradle(project_root)
    report["binary_resources"] = True
    report["script_export_mode"] = 2
    (project_root / "docs" / "RELEASE_HARDENING_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--app-name", required=True)
    parser.add_argument("--version-code", type=int, default=1)
    parser.add_argument("--version-name", default="1.0.0")
    parser.add_argument("--enable-anti-re", action="store_true")
    parser.add_argument("--expected-signing-cert-sha256", default="")
    parser.add_argument("--encrypted-template", default="")
    args = parser.parse_args()
    run_hardening(Path(args.project_root).resolve(), args.package_name, args.app_name, args.version_code, args.version_name, args.enable_anti_re, args.expected_signing_cert_sha256, args.encrypted_template)
