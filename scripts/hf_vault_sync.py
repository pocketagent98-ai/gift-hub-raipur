#!/usr/bin/env python3
"""
Hardened Hugging Face Private Vault & Keystore Continuity Manager (V2.0)
- Zero os.system() calls (uses subprocess.run with shell=False and shutil).
- Strict game_id validation against command injection & path traversal.
- Fail-closed restore for existing games and permanent Play Store keystores.
- Separates public client configuration (AdMob App/Unit IDs) from private server/signing secrets.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
from typing import Dict, Any

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
    subprocess.run(
        [
            "openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "100000",
            "-in", str(ks_enc), "-out", str(ks_plain), "-pass", "stdin",
        ],
        input=password.encode("utf-8"),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_public_client_config(raw_env_sec: str) -> Dict[str, str]:
    """
    Parses public client configuration entries (such as AdMob App ID and Ad Unit IDs)
    separated by commas, semicolons, or newlines.
    Rejects any string that resembles a private API key or backend secret.
    """
    config_dict: Dict[str, str] = {}
    cleaned = (raw_env_sec or "").strip()
    if not cleaned:
        return config_dict

    for pattern in FORBIDDEN_PRIVATE_KEY_PATTERNS:
        if pattern.search(cleaned):
            raise ValueError(
                "[SECURITY_BLOCK] Private API key or secret key detected in client config input! "
                "Never embed private API keys or backend secrets inside an APK/AAB."
            )

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

    # BUG 1 FIXED: Single-line properly escaped regex splitting on comma, semicolon, and newline
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
    """
    BUG 2 FIXED: Formats a valid GDScript Dictionary literal, safely handling empty and populated dicts.
    """
    if not entries_map:
        return "{}"
    encoded_entries = []
    for k, v in sorted(entries_map.items()):
        safe_k = json.dumps(str(k))
        safe_v = json.dumps(str(v))
        encoded_entries.append(f"\t{safe_k}: {safe_v}")
    dict_literal = "{\n" + ",\n".join(encoded_entries) + "\n}"
    return dict_literal


def get_hf_api():
    from huggingface_hub import HfApi, snapshot_download
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    hf_repo = os.environ.get("HF_PRIVATE_DATASET_REPO", "").strip()
    if not hf_token or not hf_repo:
        raise RuntimeError(
            "[FAIL_CLOSED] HF_TOKEN and HF_PRIVATE_DATASET_REPO environment variables are required."
        )
    if not re.fullmatch(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", hf_repo):
        raise ValueError(f"[SECURITY_BLOCK] Invalid HF_PRIVATE_DATASET_REPO format: '{hf_repo}'")
    return HfApi(token=hf_token), snapshot_download, hf_token, hf_repo



def parse_and_route_order_inputs(order_txt: str, research_dir: Path, ram_vault: Path) -> Dict[str, Any]:
    """
    Parses ORDER.md and discovers any attached APK, repo, video, screenshot, or research files
    so downstream tools (`deep_game_intelligence.py`, `apk_and_source_archaeologist.py`,
    `review_intelligence.py`, `ui_element_and_interaction_mapper.py`, and `rea-agents`)
    receive exact, verified paths without silent drops.
    """
    def extract_field(key: str, default_val: str = "") -> str:
        m = re.search(rf"^{key}[ \t]*:[ \t]*(.*)$", order_txt, re.M | re.I)
        return m.group(1).strip() if m and m.group(1).strip() else default_val

    raw_game_id = extract_field("GAME_ID", os.environ.get("INPUT_GAME_ID", "my_studio_game_01"))
    game_id = validate_game_id(raw_game_id)

    raw_mode = extract_field("MODE", os.environ.get("INPUT_ACTION_MODE", "new_game")).lower()
    if "update" in raw_mode:
        action_mode = "update_existing_game"
    elif "export" in raw_mode:
        action_mode = "export_only_apk_and_aab"
    else:
        action_mode = "new_game"

    game_cat = extract_field("CATEGORY", os.environ.get("INPUT_GAME_CATEGORY", "level_by_level")).lower()
    if game_cat not in ("level_by_level", "endless_map_chunks", "auto_detect_other"):
        game_cat = "level_by_level"

    genre = extract_field("GENRE", "default_3d").lower()
    use_rea = extract_field("USE_REA", "false").lower() == "true" or ("/rea" in order_txt.lower())
    ref_link = extract_field("PLAYSTORE_REFERENCE_LINK", extract_field("PACKAGE_ID", ""))
    apk_path_str = extract_field("REFERENCE_APK_PATH", "")
    repo_path_str = extract_field("AUTHORIZED_REPO_PATH", "")
    videos_str = extract_field("REFERENCE_VIDEOS", "")

    discovered_apks = []
    discovered_videos = [v.strip() for v in videos_str.split(",") if v.strip()]
    discovered_screenshots = []
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
    """Resolves ORDER.md locally when running outside Hugging Face network sync."""
    order_file = Path("ORDER.md")
    order_txt = order_file.read_text(encoding="utf-8") if order_file.exists() else ""
    repo_order_file = Path("ORDER.md")
    if repo_order_file.exists():
        repo_order_txt = repo_order_file.read_text(encoding="utf-8")
        if "GAME_ID:" in repo_order_txt and repo_order_txt.strip() != order_txt.strip():
            order_txt = repo_order_txt
            order_file.parent.mkdir(parents=True, exist_ok=True)
            order_file.write_text(repo_order_txt, encoding="utf-8")
            print("[HF-VAULT] Prioritized repository ORDER.md over stale HF inbox ORDER.md.")
    research_dir = Path("MY_RESEARCH_AND_FILES")
    res = parse_and_route_order_inputs(order_txt, research_dir, ram_vault)
    Path("docs/COMBINED_USER_RESEARCH.md").write_text(
        "# USER ORDER & MULTI-PAGE RESEARCH DOCUMENTS\n\n"
        f"## 1. ORDER.md INSTRUCTIONS:\n{order_txt}\n",
        encoding="utf-8",
    )
    print(f"[HF-VAULT] Resolved local ORDER.md for game_id='{res['game_id']}', use_rea={res['use_rea']}.")
    return res


def resolve_command(ram_vault: Path) -> None:
    api, snapshot_download, hf_token, hf_repo = get_hf_api()
    api.create_repo(repo_id=hf_repo, repo_type="dataset", private=True, exist_ok=True)

    inbox_dir = Path("/dev/shm/hf_inbox")
    inbox_dir.mkdir(parents=True, exist_ok=True)

    try:
        snapshot_download(
            repo_id=hf_repo,
            repo_type="dataset",
            allow_patterns=["MY_COMMANDS_AND_FILES/**"],
            local_dir=str(inbox_dir),
            token=hf_token,
        )
    except Exception as exc:
        raise RuntimeError(f"[FAIL_CLOSED] Failed to access Private HF Inbox in '{hf_repo}': {exc}") from exc

    order_file = inbox_dir / "MY_COMMANDS_AND_FILES" / "ORDER.md"
    config_file = inbox_dir / "MY_COMMANDS_AND_FILES" / "PUBLIC_AD_IDS.txt"
    research_dir = inbox_dir / "MY_COMMANDS_AND_FILES" / "MY_RESEARCH_AND_FILES"

    if not order_file.exists():
        init_base = Path("/dev/shm/hf_init_inbox")
        init_dir = init_base / "MY_COMMANDS_AND_FILES"
        (init_dir / "MY_RESEARCH_AND_FILES").mkdir(parents=True, exist_ok=True)

        order_template = (
            "# MY STUDIO ORDER FILE (V2.0)\n"
            "GAME_ID: my_studio_game_01\n"
            "MODE: new_game\n"
            "CATEGORY: level_by_level\n"
            "USE_REA: false\n"
            "PLAYSTORE_REFERENCE_LINK: \n\n"
            "## PROMPT:\n"
            "Build a polished 3D game with 10 progressive levels, interactive tutorial, "
            "3-4 hit armored targets, full audio mix, and responsive mobile UI.\n"
        )
        order_file_init = init_dir / "ORDER.md"
        repo_order = Path("ORDER.md")
        if repo_order.exists() and repo_order.read_text(encoding="utf-8").strip():
            shutil.copy2(repo_order, order_file_init)
            print("[HF-VAULT] Seeded HF inbox with the repository ORDER.md")
        else:
            order_file_init.write_text(order_template, encoding="utf-8")

        ad_template = (
            "# PUBLIC CLIENT IDENTIFIERS ONLY (Never put private API keys here)\n"
            "ADMOB_APP_ID=ca-app-pub-3940256099942544~3347511713\n"
            "REWARDED_AD_UNIT_ID=ca-app-pub-3940256099942544/5224354917\n"
            "INTERSTITIAL_AD_UNIT_ID=ca-app-pub-3940256099942544/1033173712\n"
            "USE_TEST_ADS=true\n"
        )
        (init_dir / "PUBLIC_AD_IDS.txt").write_text(ad_template, encoding="utf-8")
        (init_dir / "MY_RESEARCH_AND_FILES" / "README_DROP_FILES_HERE.md").write_text(
            "# Drop your multi-page research (.md, .txt, .pdf, .json) or custom assets here.\n",
            encoding="utf-8",
        )

        api.upload_folder(
            folder_path=str(init_base),
            path_in_repo=".",
            repo_id=hf_repo,
            repo_type="dataset",
            commit_message="Initialize V2.0 MY_COMMANDS_AND_FILES Private Inbox",
        )
        safe_copy_tree(init_base, inbox_dir)

    order_txt = order_file.read_text(encoding="utf-8") if order_file.exists() else ""
    repo_order_file = Path("ORDER.md")
    if repo_order_file.exists():
        repo_order_txt = repo_order_file.read_text(encoding="utf-8")
        # The checked-out repository ORDER is the auditable source for a workflow proof.
        # A stale private-inbox order must never silently switch the requested GAME_ID.
        if "GAME_ID:" in repo_order_txt and repo_order_txt.strip() != order_txt.strip():
            order_txt = repo_order_txt
            order_file.parent.mkdir(parents=True, exist_ok=True)
            order_file.write_text(repo_order_txt, encoding="utf-8")
            print("[HF-VAULT] Repository ORDER.md is authoritative for this run; stale inbox order ignored.")

    def extract_field(key: str, default_val: str) -> str:
        m = re.search(rf"^{key}[ \t]*:[ \t]*(.*)$", order_txt, re.M | re.I)
        return m.group(1).strip() if m and m.group(1).strip() else default_val

    raw_game_id = extract_field("GAME_ID", os.environ.get("INPUT_GAME_ID", "my_studio_game_01"))
    game_id = validate_game_id(raw_game_id)

    raw_mode = extract_field("MODE", os.environ.get("INPUT_ACTION_MODE", "new_game")).lower()
    if "update" in raw_mode:
        action_mode = "update_existing_game"
    elif "export" in raw_mode:
        action_mode = "export_only_apk_and_aab"
    else:
        action_mode = "new_game"

    game_cat = extract_field("CATEGORY", os.environ.get("INPUT_GAME_CATEGORY", "level_by_level")).lower()
    if game_cat not in ("level_by_level", "endless_map_chunks", "auto_detect_other"):
        game_cat = "level_by_level"

    use_rea = extract_field("USE_REA", "false").lower() == "true"
    ref_link = extract_field("PLAYSTORE_REFERENCE_LINK", "")

    Path("docs/user_research").mkdir(parents=True, exist_ok=True)
    Path("assets/custom").mkdir(parents=True, exist_ok=True)
    combined_research = []

    if research_dir.exists():
        for fpath in sorted(research_dir.rglob("*")):
            if fpath.is_dir() or fpath.name.startswith(".") or "README_DROP_FILES_HERE" in fpath.name:
                continue
            ext = fpath.suffix.lower()
            if ext in (".md", ".txt", ".json", ".csv"):
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                combined_research.append(f"\n--- RESEARCH FILE: {fpath.name} ---\n{content}\n")
                shutil.copy2(fpath, Path("docs/user_research") / fpath.name)
            elif ext == ".pdf":
                import pypdf
                reader = pypdf.PdfReader(str(fpath))
                pdf_txt = "\n".join((page.extract_text() or "") for page in reader.pages)
                combined_research.append(f"\n--- PDF RESEARCH FILE: {fpath.name} ---\n{pdf_txt}\n")
                shutil.copy2(fpath, Path("docs/user_research") / fpath.name)
            elif ext in (".png", ".jpg", ".jpeg", ".glb", ".gltf", ".wav", ".ogg", ".mp3"):
                shutil.copy2(fpath, Path("assets/custom") / fpath.name)

    Path("docs/COMBINED_USER_RESEARCH.md").write_text(
        "# USER ORDER & MULTI-PAGE RESEARCH DOCUMENTS\n\n"
        f"## 1. ORDER.md INSTRUCTIONS:\n{order_txt}\n\n"
        + ("## 2. ATTACHED RESEARCH FILES:\n" + "\n".join(combined_research) if combined_research else ""),
        encoding="utf-8",
    )

    raw_cfg_txt = config_file.read_text(encoding="utf-8") if config_file.exists() else ""
    env_cfg_txt = os.environ.get("PUBLIC_CLIENT_AD_CONFIG", "")
    client_cfg = parse_public_client_config(raw_cfg_txt + "\n" + env_cfg_txt)
    (ram_vault / "client_public_config.json").write_text(json.dumps(client_cfg, indent=2), encoding="utf-8")

    resolved = parse_and_route_order_inputs(order_txt, research_dir, ram_vault)
    print(f"[HF-VAULT] Resolved validated job for game_id='{game_id}', mode='{action_mode}'.")


def init_or_pull(ram_vault: Path) -> None:
    api, snapshot_download, hf_token, hf_repo = get_hf_api()
    job_file = ram_vault / "resolved_job.json"
    if not job_file.exists():
        raise RuntimeError("[FAIL_CLOSED] resolved_job.json missing. Run resolve_command first.")

    job_info = json.loads(job_file.read_text(encoding="utf-8"))
    game_id = validate_game_id(job_info["game_id"])
    action_mode = job_info["action_mode"]

    dl_dir = Path("/dev/shm/hf_download")
    dl_dir.mkdir(parents=True, exist_ok=True)

    try:
        snapshot_download(
            repo_id=hf_repo,
            repo_type="dataset",
            allow_patterns=[f"GAMES_VAULT/{game_id}/**"],
            local_dir=str(dl_dir),
            token=hf_token,
        )
    except Exception as exc:
        if action_mode in ("update_existing_game", "export_only_apk_and_aab"):
            raise RuntimeError(
                f"[FAIL_CLOSED] Failed to download GAMES_VAULT/{game_id} from '{hf_repo}': {exc}"
            ) from exc
        print(f"[HF-VAULT] No existing remote vault folder for new_game '{game_id}' ({exc}); initializing fresh vault.")

    proj_src = dl_dir / "GAMES_VAULT" / game_id / "project"
    ks_enc_src = dl_dir / "GAMES_VAULT" / game_id / "private_secrets" / "release.keystore.enc"
    ks_src = dl_dir / "GAMES_VAULT" / game_id / "private_secrets" / "release.keystore"
    cred_src = dl_dir / "GAMES_VAULT" / game_id / "private_secrets" / "keystore_meta.json"

    # RED FLAG 4 FIXED: Fail-Closed in Update/Export modes if project or keystore is missing!
    if action_mode in ("update_existing_game", "export_only_apk_and_aab"):
        if not (proj_src / "project.godot").exists():
            raise FileNotFoundError(
                f"[FAIL_CLOSED] Mode is '{action_mode}', but no existing Godot project was found at "
                f"GAMES_VAULT/{game_id}/project/project.godot in '{hf_repo}'. Refusing to overwrite with a blank project!"
            )
        if (not ks_enc_src.exists() and not ks_src.exists()) or not cred_src.exists():
            raise FileNotFoundError(
                f"[FAIL_CLOSED] Mode is '{action_mode}', but the permanent Play Store release.keystore "
                f"was not found for '{game_id}'. Refusing to generate a new keystore (would break Play Store updates)!"
            )
        safe_copy_tree(proj_src, Path("."))
        print(f"[HF-VAULT] Restored existing project for '{game_id}'.")

    ks_dest = ram_vault / "release.keystore"
    cred_dest = ram_vault / "keystore_meta.json"

    if (ks_enc_src.exists() or ks_src.exists()) and cred_src.exists():
        if ks_enc_src.exists():
            ks_pass_dl = os.environ.get("ANDROID_KEYSTORE_PASSWORD", "").strip()
            if len(ks_pass_dl) < 6:
                ks_pass_dl = "SkVault_" + hashlib.sha256((hf_token + ":" + game_id).encode("utf-8")).hexdigest()[:16]
            (ram_vault / "active_ks_pass.txt").write_text(ks_pass_dl, encoding="utf-8")
            decrypt_keystore_file(ks_enc_src, ks_dest, ks_pass_dl)
        else:
            shutil.copy2(ks_src, ks_dest)
        shutil.copy2(cred_src, cred_dest)
        meta = json.loads(cred_dest.read_text(encoding="utf-8"))
        actual_sha256 = compute_sha256(ks_dest)
        expected_sha256 = meta.get("keystore_sha256", "")
        if expected_sha256 and actual_sha256 != expected_sha256:
            raise RuntimeError(
                f"[FAIL_CLOSED] Keystore SHA-256 mismatch for '{game_id}'! "
                f"Expected {expected_sha256}, got {actual_sha256}."
            )
        if action_mode == "update_existing_game":
            meta["version_code"] = int(meta.get("version_code", 1)) + 1
            meta["version_name"] = f"2.0.{meta['version_code']}"
            cred_dest.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"[HF-VAULT] Verified existing Release Keystore (SHA256: {actual_sha256[:12]}..., vCode: {meta.get('version_code', 1)}).")
    else:
        ks_pass = os.environ.get("ANDROID_KEYSTORE_PASSWORD", "").strip()
        if len(ks_pass) < 6:
            ks_pass = "SkVault_" + hashlib.sha256((hf_token + ":" + game_id).encode("utf-8")).hexdigest()[:16]
            print("[HF-VAULT] ANDROID_KEYSTORE_PASSWORD not set in Secrets; derived deterministic vault keystore key.")
        (ram_vault / "active_ks_pass.txt").write_text(ks_pass, encoding="utf-8")
        ks_alias = os.environ.get("ANDROID_KEYSTORE_ALIAS", "").strip() or "playstore_upload_key"
        if not GAME_ID_PATTERN.fullmatch(ks_alias):
            raise ValueError(f"[SECURITY_BLOCK] Invalid ANDROID_KEYSTORE_ALIAS: '{ks_alias}'")

        subprocess.run(
            [
                "keytool", "-genkeypair", "-v",
                "-keystore", str(ks_dest),
                "-storepass", ks_pass,
                "-alias", ks_alias,
                "-keypass", ks_pass,
                "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
                "-dname", f"CN={game_id},O=AIStudio,C=IN",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        ks_sha256 = compute_sha256(ks_dest)
        os.environ["ACTIVE_KEYSTORE_PASS"] = ks_pass

        # Sanitized metadata (stores SHA-256 fingerprint & version; password is read from GitHub Secret or protected file)
        # NEVER store keystore_password in keystore_meta.json or upload plaintext passwords to HF!
        meta = {
            "game_id": game_id,
            "keystore_alias": ks_alias,
            "keystore_sha256": ks_sha256,
            "package_name": f"com.aistudio.{game_id.lower().replace('-', '_')}",
            "version_code": 1,
            "version_name": "3.0.1",
            "encrypted_keystore": True,
        }
        cred_dest.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        # RED FLAG 3 FIXED: Upload ONLY release.keystore and keystore_meta.json (never resolved_job.json or scratch files!)
        upload_stage = Path("/dev/shm/ks_upload_only")
        upload_stage.mkdir(parents=True, exist_ok=True)
        encrypt_keystore_file(ks_dest, upload_stage / "release.keystore.enc", ks_pass)
        shutil.copy2(cred_dest, upload_stage / "keystore_meta.json")
        api.upload_folder(
            folder_path=str(upload_stage),
            path_in_repo=f"GAMES_VAULT/{game_id}/private_secrets",
            repo_id=hf_repo,
            repo_type="dataset",
            commit_message=f"Lock permanent Play Store keystore for {game_id}",
        )
        shutil.rmtree(upload_stage, ignore_errors=True)
        print(f"[HF-VAULT] Created & locked permanent Release Keystore (SHA256: {ks_sha256[:12]}...).")


def inject_export_config(ram_vault: Path) -> None:
    cred_dest = ram_vault / "keystore_meta.json"
    ks_dest = ram_vault / "release.keystore"
    if not cred_dest.exists() or not ks_dest.exists():
        raise FileNotFoundError("[FAIL_CLOSED] Keystore or metadata missing in RAM vault.")

    meta = json.loads(cred_dest.read_text(encoding="utf-8"))
    cfg_path = Path("export_presets.cfg")
    cfg = cfg_path.read_text(encoding="utf-8")
    cfg = cfg.replace("__PRIVATE_KEYSTORE_PATH__", str(ks_dest))
    cfg = cfg.replace("__PRIVATE_KEYSTORE_USER__", meta["keystore_alias"])
    ks_pass_env = os.environ.get("ANDROID_KEYSTORE_PASSWORD", "").strip()
    if len(ks_pass_env) < 6 and (ram_vault / "active_ks_pass.txt").exists():
        ks_pass_env = (ram_vault / "active_ks_pass.txt").read_text(encoding="utf-8").strip()
    if not ks_pass_env:
        raise RuntimeError("[FAIL_CLOSED] ANDROID_KEYSTORE_PASSWORD must be set in GitHub Encrypted Secrets!")
    cfg = cfg.replace("__PRIVATE_KEYSTORE_PASS__", ks_pass_env)
    cfg = cfg.replace("com.aistudio.cleanroomgame", meta["package_name"])
    cfg = cfg.replace("version/code=1", f"version/code={meta.get('version_code', 1)}")
    cfg = cfg.replace('version/name="1.0.0"', f'version/name="{meta.get("version_name", "2.0.1")}"')
    cfg_path.write_text(cfg, encoding="utf-8")

    # Inject public client config (e.g., AdMob App ID / Unit IDs) into scripts/app_config.gd
    client_cfg_file = ram_vault / "client_public_config.json"
    client_cfg = json.loads(client_cfg_file.read_text(encoding="utf-8")) if client_cfg_file.exists() else {}
    dict_literal = format_gdscript_dictionary(client_cfg)

    app_cfg_path = Path("scripts/app_config.gd")
    if app_cfg_path.exists():
        gd_code = app_cfg_path.read_text(encoding="utf-8")
        gd_code = gd_code.replace(
            "const PUBLIC_CLIENT_CONFIG: Dictionary = {}",
            f"const PUBLIC_CLIENT_CONFIG: Dictionary = {dict_literal}",
        )
        app_cfg_path.write_text(gd_code, encoding="utf-8")
    print("[HF-VAULT] Injected verified signing config and public client IDs.")


def push_private_everything(ram_vault: Path) -> None:
    api, _, _, hf_repo = get_hf_api()
    job_info = json.loads((ram_vault / "resolved_job.json").read_text(encoding="utf-8"))
    game_id = validate_game_id(job_info["game_id"])

    if Path("export_presets.cfg.bak").exists():
        shutil.copy2("export_presets.cfg.bak", "export_presets.cfg")
    if Path("scripts/app_config.gd.bak").exists():
        shutil.copy2("scripts/app_config.gd.bak", "scripts/app_config.gd")

    # Upload only sanitized keystore files to private_secrets
    upload_ks = Path("/dev/shm/ks_upload_only")
    upload_ks.mkdir(parents=True, exist_ok=True)
    ks_pass_up = os.environ.get("ANDROID_KEYSTORE_PASSWORD", "").strip()
    if len(ks_pass_up) < 6 and (ram_vault / "active_ks_pass.txt").exists():
        ks_pass_up = (ram_vault / "active_ks_pass.txt").read_text(encoding="utf-8").strip()
    if ks_pass_up:
        encrypt_keystore_file(ram_vault / "release.keystore", upload_ks / "release.keystore.enc", ks_pass_up)
    shutil.copy2(ram_vault / "keystore_meta.json", upload_ks / "keystore_meta.json")
    api.upload_folder(
        folder_path=str(upload_ks),
        path_in_repo=f"GAMES_VAULT/{game_id}/private_secrets",
        repo_id=hf_repo,
        repo_type="dataset",
        commit_message=f"Sync keystore metadata for {game_id}",
    )
    shutil.rmtree(upload_ks, ignore_errors=True)

    api.upload_folder(
        folder_path=".",
        path_in_repo=f"GAMES_VAULT/{game_id}/project",
        repo_id=hf_repo,
        repo_type="dataset",
        ignore_patterns=[".git/*", "/tmp/*", "build/*", "__pycache__/*", "*.bak"],
        commit_message=f"Verified V2.0 Release ({job_info['action_mode']}) for {game_id}",
    )
    if Path("build").exists():
        api.upload_folder(
            folder_path="build",
            path_in_repo=f"GAMES_VAULT/{game_id}/builds_apk_and_aab",
            repo_id=hf_repo,
            repo_type="dataset",
            commit_message=f"Verified APK & Play Store AAB for {game_id}",
        )
    if Path("/tmp/qa_videos").exists():
        api.upload_folder(
            folder_path="/tmp/qa_videos",
            path_in_repo=f"GAMES_VAULT/{game_id}/qa_videos",
            repo_id=hf_repo,
            repo_type="dataset",
            commit_message=f"QA Videos for {game_id}",
        )
    print(f"[HF-VAULT] Synced verified release to https://huggingface.co/datasets/{hf_repo}/tree/main/GAMES_VAULT/{game_id}")


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
    else:
        raise ValueError(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
