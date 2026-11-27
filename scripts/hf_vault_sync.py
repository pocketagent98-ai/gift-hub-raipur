#!/usr/bin/env python3
"""
Hugging Face Private Dataset Vault Sync — Studio V7.0
Relays compact .tar.gz stage bundles, persistent Android keystores, and versioned releases.
"""

import os
from pathlib import Path
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi, hf_hub_download


def _get_api() -> tuple[HfApi, str, str]:
    token = os.environ.get("HF_TOKEN", "").strip()
    repo_id = os.environ.get("HF_PRIVATE_DATASET_REPO", "").strip()
    if not token or not repo_id:
        raise RuntimeError("Missing HF_TOKEN or HF_PRIVATE_DATASET_REPO environment variables.")
    api = HfApi(token=token)
    return api, repo_id, token


def push_stage(game_id: str, stage: str, paths: list[str]) -> None:
    api, repo_id, _ = _get_api()
    bundle = Path(f"/tmp/hf_v7_{game_id}_{stage}.tar.gz")
    if bundle.exists():
        bundle.unlink()

    added = 0
    with tarfile.open(bundle, "w:gz") as tf:
        for p_str in paths:
            p = Path(p_str)
            if p.exists():
                tf.add(p, arcname=p_str)
                added += 1
    if added == 0:
        raise RuntimeError(f"No paths found to archive for stage {stage}: {paths}")

    remote_path = f"GAMES_VAULT/{game_id}/relay/{stage}/bundle.tar.gz"
    api.upload_file(
        path_or_fileobj=str(bundle),
        path_in_repo=remote_path,
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=f"Studio V7 relay {game_id}/{stage}",
    )
    bundle.unlink(missing_ok=True)
    print(f"[HF-VAULT] Uploaded {remote_path} ({added} root paths).")


def pull_stage(game_id: str, stage: str, dest_dir: str = ".") -> None:
    _, repo_id, token = _get_api()
    remote_path = f"GAMES_VAULT/{game_id}/relay/{stage}/bundle.tar.gz"
    local_tar = hf_hub_download(
        repo_id=repo_id,
        filename=remote_path,
        repo_type="dataset",
        token=token,
    )
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(local_tar, "r:gz") as tf:
        tf.extractall(path=dest, filter="data")
    print(f"[HF-VAULT] Pulled and extracted {remote_path} into {dest}.")


def ensure_keystore(game_id: str, keystore_path: str, password: str, alias: str = "studio_release") -> None:
    api, repo_id, token = _get_api()
    ks = Path(keystore_path)
    ks.parent.mkdir(parents=True, exist_ok=True)
    remote_path = f"GAMES_VAULT/{game_id}/keystore/release.jks"

    try:
        downloaded = hf_hub_download(
            repo_id=repo_id,
            filename=remote_path,
            repo_type="dataset",
            token=token,
        )
        ks.write_bytes(Path(downloaded).read_bytes())
        # Quick verify with keytool
        chk = subprocess.run(
            ["keytool", "-list", "-keystore", str(ks), "-storepass", password],
            capture_output=True, text=True, check=False,
        )
        if chk.returncode == 0:
            print(f"[HF-VAULT] Restored persistent keystore for {game_id}.")
            return
        print("[HF-VAULT] Existing keystore password mismatch; regenerating clean game keystore.")
        ks.unlink(missing_ok=True)
    except Exception:
        print(f"[HF-VAULT] No existing keystore for {game_id}; generating new persistent keystore.")

    subprocess.run(
        [
            "keytool", "-genkeypair", "-v",
            "-keystore", str(ks),
            "-alias", alias,
            "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
            "-storepass", password, "-keypass", password,
            "-dname", f"CN={game_id}, O=AIStudio, C=IN",
        ],
        check=True,
    )
    api.upload_file(
        path_or_fileobj=str(ks),
        path_in_repo=remote_path,
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=f"Persist Android keystore for {game_id}",
    )
    print(f"[HF-VAULT] Created and vaulted persistent keystore at {remote_path}.")


def push_release(game_id: str, version: str, release_dir: str) -> None:
    api, repo_id, _ = _get_api()
    rdir = Path(release_dir)
    if not rdir.exists():
        raise RuntimeError(f"Release directory not found: {rdir}")
    for f in sorted(rdir.iterdir()):
        if f.is_file():
            remote_path = f"GAMES_VAULT/{game_id}/versions/{version}/{f.name}"
            api.upload_file(
                path_or_fileobj=str(f),
                path_in_repo=remote_path,
                repo_id=repo_id,
                repo_type="dataset",
                commit_message=f"Release {game_id} {version}: {f.name}",
            )
            print(f"[HF-VAULT] Uploaded release artifact: {remote_path}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: hf_vault_sync.py <push_stage|pull_stage|ensure_keystore|push_release> ...")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "push_stage":
        push_stage(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif cmd == "pull_stage":
        pull_stage(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else ".")
    elif cmd == "ensure_keystore":
        ensure_keystore(sys.argv[2], sys.argv[3], os.environ["ANDROID_KEYSTORE_PASSWORD"])
    elif cmd == "push_release":
        push_release(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        raise ValueError(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
