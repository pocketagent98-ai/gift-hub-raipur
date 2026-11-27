#!/usr/bin/env python3
"""
Unified Hugging Face Private Vault & Keystore Continuity Manager (Studio V7.0 + V5.0 Relay Compatible)
- Supports both V7.0 compact .tar.gz stage bundles AND live GitHub Actions workflow relay commands.
- Zero os.system() calls; strict game_id validation; persistent AES-256-CBC encrypted Play Store keystore.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time
from typing import Any, Dict

GAME_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,48}$")
FORBIDDEN_PRIVATE_KEY_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{16,}"),
    re.compile(r"hf_[a-zA-Z0-9]{16,}"),
    re.compile(r"nvapi-[a-zA-Z0-9_-]{16,}"),
    re.compile(r"AIza[0-9A-Za-z-_]{30,}"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
]


def validate_game_id(game_id: str) -> str:
    cleaned = (game_id or "").strip()
    if not GAME_ID_PATTERN.fullmatch(cleaned):
        raise ValueError(
            f"[SECURITY_BLOCK] Invalid game_id '{cleaned}'. "
            "Only ASCII letters, digits, underscores, and hyphens (3-48 chars) are allowed."
        )
    return cleaned


def safe_copy_tree(src: Path, dst: Path) -> None:
    src_resolved = src.resolve()
    dst_resolved = dst.resolve()
    if not src_resolved.exists() or not src_resolved.is_dir():
        raise FileNotFoundError(f"[FAIL_CLOSED] Source directory does not exist: {src_resolved}")
    dst_resolved.mkdir(parents=True, exist_ok=True)
    for item in src_resolved.iterdir():
        if item.name.startswith("."):
            continue
        target = dst_resolved / item.name
        if not target.resolve().is_relative_to(dst_resolved):
            raise PermissionError(f"[SECURITY_BLOCK] Path traversal blocked: {target}")
        if item.is_dir():
            shutil.copytree(
                item,
                target,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(".*", "__pycache__", "*.pyc", "*.bak"),
            )
        elif item.is_file():
            shutil.copy2(item, target)


def encrypt_keystore_file(ks_plain: Path, ks_enc: Path, password: str) -> None:
    subprocess.run(
        [
            "openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "100000", "-salt",
            "-in", str(ks_plain), "-out", str(ks_enc), "-pass", "stdin",
        ],
        input=password.encode("utf-8"),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def decrypt_keystore_file(ks_enc: Path, ks_plain: Path, password: str) -> None:
    result = subprocess.run(
        [
            "openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "100000",
            "-in", str(ks_enc), "-out", str(ks_plain), "-pass", "stdin",
        ],
        input=password.encode("utf-8"),
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"[KEYSTORE_DECRYPT_FAIL] {result.stderr.decode('utf-8', 'replace').strip()[:200]}")


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_public_client_config(raw_env_sec: str) -> Dict[str, str]:
    config_dict: Dict[str, str] = {}
    cleaned = (raw_env_sec or "").strip()
    if not cleaned:
        return config_dict
    for pattern in FORBIDDEN_PRIVATE_KEY_PATTERNS:
        if pattern.search(cleaned):
            raise ValueError("[SECURITY_BLOCK] Private API key detected in client config input!")
    if cleaned.startswith("{"):
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("[CONFIG_ERROR] JSON client config must be an object.")
        for k, v in parsed.items():
            key_str = str(k).strip()
            val_str = str(v).strip()
            if re.fullmatch(r"^[A-Z0-9_]{2,40}$", key_str):
                config_dict[key_str] = val_str
        return config_dict
    for pair in re.split(r"[,;\n]+", cleaned):
        pair_str = pair.strip()
        if not pair_str or pair_str.startswith("#"):
            continue
        if "=" in pair_str:
            k, v = pair_str.split("=", 1)
            key_str = k.strip()
            val_str = v.strip()
            if not re.fullmatch(r"^[A-Z0-9_]{2,40}$", key_str):
                raise ValueError(f"[SECURITY_BLOCK] Invalid config key name: '{key_str}'")
            config_dict[key_str] = val_str
    return config_dict


def format_gdscript_dictionary(entries_map: Dict[str, str]) -> str:
    if not entries_map:
        return "{}"
    encoded_entries = [f"\t{json.dumps(str(k))}: {json.dumps(str(v))}" for k, v in sorted(entries_map.items())]
    return "{\n" + ",\n".join(encoded_entries) + "\n}"


def get_hf_api():
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    hf_repo = os.environ.get("HF_PRIVATE_DATASET_REPO", "").strip()
    if not hf_token or not hf_repo:
        raise RuntimeError("[FAIL_CLOSED] HF_TOKEN and HF_PRIVATE_DATASET_REPO environment variables are required.")
    if not re.fullmatch(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", hf_repo):
        raise ValueError(f"[SECURITY_BLOCK] Invalid HF_PRIVATE_DATASET_REPO format: '{hf_repo}'")
    return HfApi(token=hf_token), snapshot_download, hf_hub_download, hf_token, hf_repo


def _order_field(order_txt: str, key: str, default: str = "") -> str:
    m = re.search(rf"^{re.escape(key)}[ \t]*:[ \t]*(.*)$", order_txt, re.M | re.I)
    return m.group(1).strip() if m and m.group(1).strip() else default


# --- V7.0 Compact Stage Relay Commands ---
def push_stage(game_id: str, stage: str, paths: list[str]) -> None:
    api, _, _, _, repo_id = get_hf_api()
    gid = validate_game_id(game_id)
    bundle = Path(f"/tmp/hf_v7_{gid}_{stage}.tar.gz")
    bundle.unlink(missing_ok=True)
    added = 0
    with tarfile.open(bundle, "w:gz") as tf:
        for p_str in paths:
            p = Path(p_str)
            if p.exists():
                tf.add(p, arcname=p_str)
                added += 1
    if added == 0:
        raise RuntimeError(f"No paths found to archive for stage {stage}: {paths}")
    remote_path = f"GAMES_VAULT/{gid}/relay/{stage}/bundle.tar.gz"
    api.upload_file(
        path_or_fileobj=str(bundle),
        path_in_repo=remote_path,
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=f"Studio V7 relay {gid}/{stage}",
    )
    bundle.unlink(missing_ok=True)
    print(f"[HF-VAULT] Uploaded {remote_path} ({added} root paths).")


def pull_stage(game_id: str, stage: str, dest_dir: str = ".") -> None:
    _, _, hf_hub_download, token, repo_id = get_hf_api()
    gid = validate_game_id(game_id)
    remote_path = f"GAMES_VAULT/{gid}/relay/{stage}/bundle.tar.gz"
    local_tar = hf_hub_download(repo_id=repo_id, filename=remote_path, repo_type="dataset", token=token)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(local_tar, "r:gz") as tf:
        tf.extractall(path=dest, filter="data")
    print(f"[HF-VAULT] Pulled and extracted {remote_path} into {dest}.")


def ensure_keystore(game_id: str, keystore_path: str, password: str, alias: str = "studio_release") -> None:
    api, _, hf_hub_download, token, repo_id = get_hf_api()
    gid = validate_game_id(game_id)
    ks = Path(keystore_path)
    ks.parent.mkdir(parents=True, exist_ok=True)
    remote_path = f"GAMES_VAULT/{gid}/keystore/release.jks"
    pw = (password or "").strip()
    if len(pw) < 6:
        pw = "SkVault_" + hashlib.sha256((token + ":" + gid).encode("utf-8")).hexdigest()[:16]
    try:
        downloaded = hf_hub_download(repo_id=repo_id, filename=remote_path, repo_type="dataset", token=token)
        ks.write_bytes(Path(downloaded).read_bytes())
        chk = subprocess.run(["keytool", "-list", "-keystore", str(ks), "-storepass", pw], capture_output=True, text=True, check=False)
        if chk.returncode == 0:
            print(f"[HF-VAULT] Restored persistent keystore for {gid}.")
            return
        ks.unlink(missing_ok=True)
    except Exception:
        print(f"[HF-VAULT] Generating new persistent keystore for {gid}.")
    subprocess.run(
        [
            "keytool", "-genkeypair", "-v", "-keystore", str(ks), "-alias", alias,
            "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
            "-storepass", pw, "-keypass", pw, "-dname", f"CN={gid}, O=AIStudio, C=IN",
        ],
        check=True,
    )
    api.upload_file(path_or_fileobj=str(ks), path_in_repo=remote_path, repo_id=repo_id, repo_type="dataset", commit_message=f"Persist keystore for {gid}")
    print(f"[HF-VAULT] Vaulted persistent keystore at {remote_path}.")


def push_release(game_id: str, version: str, release_dir: str) -> None:
    api, _, _, _, repo_id = get_hf_api()
    gid = validate_game_id(game_id)
    rdir = Path(release_dir)
    if not rdir.exists():
        raise RuntimeError(f"Release directory not found: {rdir}")
    for f in sorted(rdir.iterdir()):
        if f.is_file():
            remote_path = f"GAMES_VAULT/{gid}/versions/{version}/{f.name}"
            api.upload_file(path_or_fileobj=str(f), path_in_repo=remote_path, repo_id=repo_id, repo_type="dataset", commit_message=f"Release {gid} {version}: {f.name}")
            print(f"[HF-VAULT] Uploaded release artifact: {remote_path}")


# --- Live Workflow Relay Commands ---
def parse_and_route_order_inputs(order_txt: str, research_dir: Path, ram_vault: Path) -> Dict[str, Any]:
    raw_game_id = _order_field(order_txt, "GAME_ID", os.environ.get("INPUT_GAME_ID", "block_blast_studio_01"))
    game_id = validate_game_id(raw_game_id)
    raw_mode = _order_field(order_txt, "ACTION_MODE", _order_field(order_txt, "MODE", os.environ.get("INPUT_ACTION_MODE", "new_game"))).lower()
    if "finalize" in raw_mode or "lock" in raw_mode:
        action_mode = "finalize_and_lock_release"
    elif "update" in raw_mode:
        action_mode = "update_existing_game"
    elif "export" in raw_mode:
        action_mode = "export_only_apk_and_aab"
    elif "rollback" in raw_mode:
        action_mode = "rollback_release"
    else:
        action_mode = "new_game"

    game_cat = _order_field(order_txt, "CATEGORY", os.environ.get("INPUT_GAME_CATEGORY", "level_by_level")).lower()
    if game_cat not in ("level_by_level", "endless_map_chunks", "auto_detect_other"):
        game_cat = "level_by_level"
    genre = _order_field(order_txt, "GENRE", "block_puzzle").lower()
    use_rea = _order_field(order_txt, "USE_REA", "false").lower() == "true" or ("/rea" in order_txt.lower())
    ref_link = _order_field(order_txt, "PLAYSTORE_REFERENCE_LINK", _order_field(order_txt, "PACKAGE_ID", ""))
    apk_path_str = _order_field(order_txt, "REFERENCE_APK_PATH", "")
    repo_path_str = _order_field(order_txt, "AUTHORIZED_REPO_PATH", "")
    videos_str = _order_field(order_txt, "REFERENCE_VIDEOS", "")

    discovered_apks, discovered_screenshots = [], []
    discovered_videos = [v.strip() for v in videos_str.split(",") if v.strip()]
    discovered_repos = [repo_path_str] if repo_path_str else []

    Path("docs/user_research").mkdir(parents=True, exist_ok=True)
    Path("assets/custom").mkdir(parents=True, exist_ok=True)
    if research_dir.exists():
        for fpath in sorted(research_dir.rglob("*")):
            if fpath.is_dir() or fpath.name.startswith(".") or "README_DROP_FILES_HERE" in fpath.name:
                continue
            ext = fpath.suffix.lower()
            if ext in (".apk", ".aab"):
                dst = Path("docs/user_research") / fpath.name
                shutil.copy2(fpath, dst)
                discovered_apks.append(str(dst))
            elif ext in (".mp4", ".webm", ".mov", ".avi"):
                dst = Path("docs/user_research") / fpath.name
                shutil.copy2(fpath, dst)
                discovered_videos.append(str(dst))
            elif ext in (".png", ".jpg", ".jpeg", ".webp", ".svg"):
                dst = Path("assets/custom") / fpath.name
                shutil.copy2(fpath, dst)
                discovered_screenshots.append(str(dst))

    resolved_apk = apk_path_str if (apk_path_str and Path(apk_path_str).exists()) else (discovered_apks[0] if discovered_apks else "")
    resolved_repo = discovered_repos[0] if (discovered_repos and Path(discovered_repos[0]).exists()) else ""
    resolved = {
        "game_id": game_id,
        "action_mode": action_mode,
        "game_category": game_cat,
        "genre": genre,
        "final_package_name": _order_field(order_txt, "FINAL_PACKAGE_NAME", ""),
        "final_app_name": _order_field(order_txt, "FINAL_APP_NAME", ""),
        "enable_anti_reverse_engineering": _order_field(order_txt, "ENABLE_ANTI_REVERSE_ENGINEERING", "false").lower() == "true",
        "signature_check_strict": _order_field(order_txt, "SIGNATURE_CHECK_STRICT", "false").lower() == "true",
        "expected_signing_cert_sha256": _order_field(order_txt, "EXPECTED_SIGNING_CERT_SHA256", ""),
        "use_rea": use_rea,
        "ref_link": ref_link,
        "apk_path": resolved_apk,
        "authorized_repo_path": resolved_repo,
        "reference_videos": discovered_videos,
        "reference_screenshots": discovered_screenshots,
        "missing_optional_inputs": [
            k for k, v in {
                "play_store_reference_link": ref_link,
                "reference_apk_path": resolved_apk,
                "authorized_repo_path": resolved_repo,
                "reference_videos": discovered_videos,
            }.items() if not v
        ],
    }
    ram_vault.mkdir(parents=True, exist_ok=True)
    (ram_vault / "resolved_job.json").write_text(json.dumps(resolved, indent=2), encoding="utf-8")
    Path("docs").mkdir(parents=True, exist_ok=True)
    Path("docs/resolved_job.json").write_text(json.dumps(resolved, indent=2), encoding="utf-8")
    return resolved


def resolve_local_order(ram_vault: Path) -> Dict[str, Any]:
    order_file = Path("ORDER.md")
    order_txt = order_file.read_text(encoding="utf-8") if order_file.exists() else ""
    res = parse_and_route_order_inputs(order_txt, Path("MY_RESEARCH_AND_FILES"), ram_vault)
    Path("docs/COMBINED_USER_RESEARCH.md").write_text(
        f"# USER ORDER & MULTI-PAGE RESEARCH DOCUMENTS\n\n## 1. ORDER.md INSTRUCTIONS:\n{order_txt}\n",
        encoding="utf-8",
    )
    print(f"[HF-VAULT] Resolved local ORDER.md for game_id='{res['game_id']}'.")
    return res


def resolve_command(ram_vault: Path) -> None:
    api, snapshot_download, _, hf_token, hf_repo = get_hf_api()
    api.create_repo(repo_id=hf_repo, repo_type="dataset", private=True, exist_ok=True)
    inbox_dir = Path("/dev/shm/hf_inbox")
    inbox_dir.mkdir(parents=True, exist_ok=True)
    try:
        snapshot_download(repo_id=hf_repo, repo_type="dataset", allow_patterns=["MY_COMMANDS_AND_FILES/**"], local_dir=str(inbox_dir), token=hf_token)
    except Exception as exc:
        print(f"[HF-VAULT] Note accessing HF inbox ({exc}); using repository ORDER.md.")

    order_file = inbox_dir / "MY_COMMANDS_AND_FILES" / "ORDER.md"
    config_file = inbox_dir / "MY_COMMANDS_AND_FILES" / "PUBLIC_AD_IDS.txt"
    research_dir = inbox_dir / "MY_COMMANDS_AND_FILES" / "MY_RESEARCH_AND_FILES"

    order_txt = order_file.read_text(encoding="utf-8") if order_file.exists() else ""
    repo_order_file = Path("ORDER.md")
    if repo_order_file.exists():
        repo_order_txt = repo_order_file.read_text(encoding="utf-8")
        if "GAME_ID:" in repo_order_txt and repo_order_txt.strip() != order_txt.strip():
            order_txt = repo_order_txt
            print("[HF-VAULT] Repository ORDER.md is authoritative for this run.")

    Path("docs/COMBINED_USER_RESEARCH.md").write_text(
        f"# USER ORDER & MULTI-PAGE RESEARCH DOCUMENTS\n\n## 1. ORDER.md INSTRUCTIONS:\n{order_txt}\n",
        encoding="utf-8",
    )
    raw_cfg_txt = config_file.read_text(encoding="utf-8") if config_file.exists() else ""
    env_cfg_txt = os.environ.get("PUBLIC_CLIENT_AD_CONFIG", "")
    client_cfg = parse_public_client_config(raw_cfg_txt + "\n" + env_cfg_txt)
    ram_vault.mkdir(parents=True, exist_ok=True)
    (ram_vault / "client_public_config.json").write_text(json.dumps(client_cfg, indent=2), encoding="utf-8")
    resolved = parse_and_route_order_inputs(order_txt, research_dir, ram_vault)
    print(f"[HF-VAULT] Resolved validated job for game_id='{resolved['game_id']}', genre='{resolved['genre']}'.")


def init_or_pull(ram_vault: Path) -> None:
    api, snapshot_download, _, hf_token, hf_repo = get_hf_api()
    job_info = json.loads((ram_vault / "resolved_job.json").read_text(encoding="utf-8"))
    game_id = validate_game_id(job_info["game_id"])
    action_mode = job_info["action_mode"]

    dl_dir = Path("/dev/shm/hf_download")
    dl_dir.mkdir(parents=True, exist_ok=True)
    try:
        snapshot_download(repo_id=hf_repo, repo_type="dataset", allow_patterns=[f"GAMES_VAULT/{game_id}/**"], local_dir=str(dl_dir), token=hf_token)
    except Exception as exc:
        if action_mode in ("update_existing_game", "export_only_apk_and_aab", "finalize_and_lock_release"):
            raise RuntimeError(f"[FAIL_CLOSED] Failed to download GAMES_VAULT/{game_id}: {exc}") from exc
        print(f"[HF-VAULT] Fresh vault for new_game '{game_id}'.")

    vault_root = dl_dir / "GAMES_VAULT" / game_id
    proj_src = next((p for p in (vault_root / "project", vault_root / "latest" / "source") if (p / "project.godot").exists()), vault_root / "project")
    ks_enc_src = next((p for p in (vault_root / "private_secrets" / "release.keystore.enc", vault_root / "keystore" / "release.keystore.enc") if p.exists()), vault_root / "private_secrets" / "release.keystore.enc")
    ks_src = vault_root / "private_secrets" / "release.keystore"
    cred_src = next((p for p in (vault_root / "private_secrets" / "keystore_meta.json", vault_root / "keystore" / "keystore_meta.json") if p.exists()), vault_root / "private_secrets" / "keystore_meta.json")

    if action_mode in ("update_existing_game", "export_only_apk_and_aab", "finalize_and_lock_release"):
        if not (proj_src / "project.godot").exists():
            raise FileNotFoundError(f"[FAIL_CLOSED] No existing Godot project in GAMES_VAULT/{game_id}.")
        safe_copy_tree(proj_src, Path("."))

    ks_dest = ram_vault / "release.keystore"
    cred_dest = ram_vault / "keystore_meta.json"
    restored = False
    if (ks_enc_src.exists() or ks_src.exists()) and cred_src.exists():
        try:
            if ks_enc_src.exists():
                ks_pass_dl = os.environ.get("ANDROID_KEYSTORE_PASSWORD", "").strip()
                if len(ks_pass_dl) < 6:
                    ks_pass_dl = "SkVault_" + hashlib.sha256((hf_token + ":" + game_id).encode("utf-8")).hexdigest()[:16]
                (ram_vault / "active_ks_pass.txt").write_text(ks_pass_dl, encoding="utf-8")
                decrypt_keystore_file(ks_enc_src, ks_dest, ks_pass_dl)
            else:
                shutil.copy2(ks_src, ks_dest)
            shutil.copy2(cred_src, cred_dest)
            restored = True
            print(f"[HF-VAULT] Restored Release Keystore for '{game_id}'.")
        except Exception as exc:
            if action_mode in ("update_existing_game", "export_only_apk_and_aab", "finalize_and_lock_release"):
                raise
            print(f"[HF-VAULT] Regenerating keystore for new_game '{game_id}': {exc}")

    if not restored:
        ks_pass = os.environ.get("ANDROID_KEYSTORE_PASSWORD", "").strip()
        if len(ks_pass) < 6:
            ks_pass = "SkVault_" + hashlib.sha256((hf_token + ":" + game_id).encode("utf-8")).hexdigest()[:16]
        (ram_vault / "active_ks_pass.txt").write_text(ks_pass, encoding="utf-8")
        ks_alias = os.environ.get("ANDROID_KEYSTORE_ALIAS", "").strip() or "playstore_upload_key"
        subprocess.run(
            [
                "keytool", "-genkeypair", "-v", "-keystore", str(ks_dest), "-storepass", ks_pass,
                "-alias", ks_alias, "-keypass", ks_pass, "-keyalg", "RSA", "-keysize", "2048",
                "-validity", "10000", "-dname", f"CN={game_id},O=AIStudio,C=IN",
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        meta = {
            "game_id": game_id,
            "keystore_alias": ks_alias,
            "keystore_sha256": compute_sha256(ks_dest),
            "package_name": f"com.aistudio.{game_id.lower().replace('-', '_')}",
            "version_code": 1,
            "version_name": "1.0.0",
            "encrypted_keystore": True,
        }
        cred_dest.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        upload_stage = Path("/dev/shm/ks_upload_only")
        upload_stage.mkdir(parents=True, exist_ok=True)
        encrypt_keystore_file(ks_dest, upload_stage / "release.keystore.enc", ks_pass)
        shutil.copy2(cred_dest, upload_stage / "keystore_meta.json")
        api.upload_folder(folder_path=str(upload_stage), path_in_repo=f"GAMES_VAULT/{game_id}/private_secrets", repo_id=hf_repo, repo_type="dataset", commit_message=f"Lock keystore for {game_id}")
        shutil.rmtree(upload_stage, ignore_errors=True)
        print(f"[HF-VAULT] Created & locked permanent Release Keystore for '{game_id}'.")


def inject_export_config(ram_vault: Path) -> None:
    meta = json.loads((ram_vault / "keystore_meta.json").read_text(encoding="utf-8"))
    ks_dest = ram_vault / "release.keystore"
    cfg_path = Path("export_presets.cfg")
    cfg = cfg_path.read_text(encoding="utf-8")
    cfg = cfg.replace("__PRIVATE_KEYSTORE_PATH__", str(ks_dest))
    cfg = cfg.replace("__PRIVATE_KEYSTORE_USER__", meta["keystore_alias"])
    ks_pass_env = os.environ.get("ANDROID_KEYSTORE_PASSWORD", "").strip()
    if len(ks_pass_env) < 6 and (ram_vault / "active_ks_pass.txt").exists():
        ks_pass_env = (ram_vault / "active_ks_pass.txt").read_text(encoding="utf-8").strip()
    cfg = cfg.replace("__PRIVATE_KEYSTORE_PASS__", ks_pass_env)
    cfg = cfg.replace("com.aistudio.cleanroomgame", meta["package_name"])
    cfg = cfg.replace("version/code=1", f"version/code={meta.get('version_code', 1)}")
    cfg = cfg.replace('version/name="1.0.0"', f'version/name="{meta.get("version_name", "1.0.0")}"')
    cfg_path.write_text(cfg, encoding="utf-8")
    print("[HF-VAULT] Injected verified signing config into export_presets.cfg.")


def _copy_source_snapshot(src_root: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    blocked = {".git", ".agents", "build", "android", "__pycache__", ".godot", ".migration_vault", "MY_RESEARCH_AND_FILES", "docs/user_research"}
    for item in src_root.iterdir():
        if item.name in blocked or item.name.endswith(".bak"):
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.bak", ".godot", "user_research"))
        elif item.is_file():
            shutil.copy2(item, target)


def push_private_everything(ram_vault: Path) -> None:
    api, _, _, _, hf_repo = get_hf_api()
    job_info = json.loads((ram_vault / "resolved_job.json").read_text(encoding="utf-8"))
    game_id = validate_game_id(job_info["game_id"])
    order_txt = Path("ORDER.md").read_text(encoding="utf-8") if Path("ORDER.md").exists() else ""
    version_tag = _order_field(order_txt, "GAME_VERSION", "v1.0.0")
    stage = Path("/dev/shm/version_stage")
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True, exist_ok=True)
    _copy_source_snapshot(Path("."), stage / "source")
    artifacts = stage / "artifacts"
    artifacts.mkdir()
    for fname in ("build/android/game_install.apk", "build/android/game_release.aab"):
        p = Path(fname)
        if p.exists():
            shutil.copy2(p, artifacts / p.name)
    qa_dir = stage / "qa_videos"
    qa_dir.mkdir()
    if Path("/tmp/qa_videos").exists():
        for item in sorted(Path("/tmp/qa_videos").glob("*.mp4")):
            shutil.copy2(item, qa_dir / item.name)
    api.upload_folder(folder_path=str(stage), path_in_repo=f"GAMES_VAULT/{game_id}/versions/{version_tag}", repo_id=hf_repo, repo_type="dataset", commit_message=f"Versioned release {game_id} {version_tag}")
    shutil.rmtree(stage, ignore_errors=True)
    print(f"[HF-VAULT] Synced versioned release for {game_id} ({version_tag}).")


def push_final_release(ram_vault: Path) -> None:
    push_private_everything(ram_vault)


def push_stage1_blueprints(ram_vault: Path) -> None:
    api, _, _, _, hf_repo = get_hf_api()
    job_info = json.loads((ram_vault / "resolved_job.json").read_text(encoding="utf-8"))
    game_id = validate_game_id(job_info["game_id"])
    stage = Path("/dev/shm/stage1_blueprints")
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True, exist_ok=True)
    if Path("docs").exists():
        safe_copy_tree(Path("docs"), stage / "docs")
    if Path("ORDER.md").exists():
        shutil.copy2(Path("ORDER.md"), stage / "ORDER.md")
    (stage / "stage_manifest.json").write_text(json.dumps({"game_id": game_id, "stage": "stage1"}, indent=2), encoding="utf-8")
    api.upload_folder(folder_path=str(stage), path_in_repo=f"GAMES_VAULT/{game_id}/staging/stage1", repo_id=hf_repo, repo_type="dataset", commit_message=f"Stage 1 blueprints for {game_id}")
    print(f"[HF-VAULT] Uploaded stage1 relay for {game_id}")


def pull_stage1_blueprints(ram_vault: Path) -> None:
    _, snapshot_download, _, hf_token, hf_repo = get_hf_api()
    job_info = json.loads((ram_vault / "resolved_job.json").read_text(encoding="utf-8"))
    game_id = validate_game_id(job_info["game_id"])
    dl = Path("/dev/shm/hf_stage1")
    shutil.rmtree(dl, ignore_errors=True)
    snapshot_download(repo_id=hf_repo, repo_type="dataset", allow_patterns=[f"GAMES_VAULT/{game_id}/staging/stage1/**"], local_dir=str(dl), token=hf_token)
    source = dl / "GAMES_VAULT" / game_id / "staging" / "stage1"
    if (source / "docs").exists():
        safe_copy_tree(source / "docs", Path("docs"))
    print(f"[HF-VAULT] Pulled stage1 relay for {game_id}")


def push_stage2_project(ram_vault: Path) -> None:
    api, _, _, _, hf_repo = get_hf_api()
    job_info = json.loads((ram_vault / "resolved_job.json").read_text(encoding="utf-8"))
    game_id = validate_game_id(job_info["game_id"])
    api.upload_folder(
        folder_path=".",
        path_in_repo=f"GAMES_VAULT/{game_id}/staging/stage2_project",
        repo_id=hf_repo,
        repo_type="dataset",
        ignore_patterns=[".git/*", ".agents/*", ".godot/*", "build/*", "android/*", "/tmp/*", "__pycache__/*", ".migration_vault/*", "docs/user_research/*", "MY_RESEARCH_AND_FILES/*", "*.apk", "*.aab", "*.bak"],
        commit_message=f"Stage 2 project for {game_id}",
    )
    print(f"[HF-VAULT] Uploaded stage2 project relay for {game_id}")


def pull_stage2_project(ram_vault: Path) -> None:
    _, snapshot_download, _, hf_token, hf_repo = get_hf_api()
    job_info = json.loads((ram_vault / "resolved_job.json").read_text(encoding="utf-8"))
    game_id = validate_game_id(job_info["game_id"])
    dl = Path("/dev/shm/hf_stage2")
    shutil.rmtree(dl, ignore_errors=True)
    snapshot_download(repo_id=hf_repo, repo_type="dataset", allow_patterns=[f"GAMES_VAULT/{game_id}/staging/stage2_project/**"], local_dir=str(dl), token=hf_token)
    source = dl / "GAMES_VAULT" / game_id / "staging" / "stage2_project"
    if not (source / "project.godot").exists():
        raise RuntimeError("[FAIL_CLOSED] HF stage2 project is missing project.godot.")
    safe_copy_tree(source, Path("."))
    print(f"[HF-VAULT] Pulled stage2 project relay for {game_id}")


def main() -> None:
    ram_vault = Path("/dev/shm/private_studio_vault")
    ram_vault.mkdir(parents=True, exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "resolve_command"
    if cmd == "resolve_command":
        resolve_command(ram_vault)
    elif cmd == "resolve_local_order":
        resolve_local_order(ram_vault)
    elif cmd == "init_or_pull":
        init_or_pull(ram_vault)
    elif cmd == "inject_export_secrets":
        inject_export_config(ram_vault)
    elif cmd == "push_private_everything":
        push_private_everything(ram_vault)
    elif cmd == "push_final_release":
        push_final_release(ram_vault)
    elif cmd == "push_stage1_blueprints":
        push_stage1_blueprints(ram_vault)
    elif cmd == "pull_stage1_blueprints":
        pull_stage1_blueprints(ram_vault)
    elif cmd == "push_stage2_project":
        push_stage2_project(ram_vault)
    elif cmd == "pull_stage2_project":
        pull_stage2_project(ram_vault)
    elif cmd == "push_stage":
        push_stage(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif cmd == "pull_stage":
        pull_stage(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else ".")
    elif cmd == "ensure_keystore":
        ensure_keystore(sys.argv[2], sys.argv[3], os.environ.get("ANDROID_KEYSTORE_PASSWORD", ""))
    elif cmd == "push_release":
        push_release(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        raise ValueError(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
