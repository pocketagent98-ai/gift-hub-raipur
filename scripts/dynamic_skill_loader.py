#!/usr/bin/env python3
"""Dynamic On-Demand Multi-Studio Skill Loader (AI Game Studio V8.0).

Keeps the GitHub repository ultra-lightweight by shallow-cloning (--depth 1)
the 6 specialist studio repositories at runtime into /tmp/studio_hub/ inside
GitHub Actions and routing only stage-appropriate skills into each LLM prompt.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Dict, List

HUB_ROOT = Path("/tmp/studio_hub")

STUDIO_REPOS: Dict[str, str] = {
    "gamestudio": "https://github.com/bullish0x/GameStudio.git",
    "everything_gamedev": "https://github.com/MRCalderon3D/everything-game-dev-code.git",
    "awesome_skills": "https://github.com/gamedev-skills/awesome-gamedev-agent-skills.git",
    "rea": "https://github.com/morluto/rea.git",
    "replica": "https://github.com/Jakeschincariol/replica-skill.git",
    "godogen": "https://github.com/htdt/godogen.git",
}

ALLOWED_REPLICA_SKILLS = {
    "replica-recon",
    "replica-entrepreneur",
    "replica-diff",
    "replica-brand",
    "replica-launch",
}
BLOCKED_REPLICA_SKILLS = {"replica-build", "replica-backend"}

STAGE_ROUTES: Dict[str, List[str]] = {
    "stage1": ["rea", "replica"],
    "stage2": ["everything_gamedev", "gamestudio"],
    "stage3": ["gamestudio", "everything_gamedev", "awesome_skills", "godogen"],
    "stage4": ["godogen", "replica", "gamestudio"],
    "stage5": ["replica", "awesome_skills"],
}


def shallow_clone(name: str, url: str) -> Path:
    HUB_ROOT.mkdir(parents=True, exist_ok=True)
    target = HUB_ROOT / name
    if target.exists() and (target / ".git").exists():
        return target
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", url, str(target)],
            check=True,
            timeout=90,
        )
    except Exception as exc:
        print(f"[SKILL_LOADER WARN] Failed to clone {name} ({url}): {exc}")
    return target


def _collect_markdown_files(repo_dir: Path, repo_key: str, stage: str, max_files: int = 6) -> List[Path]:
    if not repo_dir.exists():
        return []
    candidates: List[Path] = []
    for p in sorted(repo_dir.rglob("*.md")):
        rel = str(p.relative_to(repo_dir)).lower()
        if any(skip in rel for skip in ("license", "changelog", "contributing", "node_modules")):
            continue
        if repo_key == "replica":
            if any(b in rel for b in BLOCKED_REPLICA_SKILLS):
                continue
            if stage == "stage1" and not any(k in rel for k in ("replica-recon", "replica-entrepreneur", "readme")):
                continue
            if stage == "stage4" and not any(k in rel for k in ("replica-diff", "readme")):
                continue
            if stage == "stage5" and not any(k in rel for k in ("replica-brand", "replica-launch")):
                continue
        if stage == "stage3" and repo_key in ("gamestudio", "everything_gamedev", "awesome_skills"):
            if not any(k in rel for k in ("godot", "ui", "shader", "audio", "polish", "mobile", "skill", "readme")):
                continue
        candidates.append(p)
        if len(candidates) >= max_files:
            break
    return candidates


def load_stage_skills(stage: str, max_chars: int = 12000) -> Dict[str, object]:
    repos = STAGE_ROUTES.get(stage, ["awesome_skills"])
    loaded_sources: List[str] = []
    chunks: List[str] = []
    total = 0
    for key in repos:
        repo_dir = shallow_clone(key, STUDIO_REPOS[key])
        for md_path in _collect_markdown_files(repo_dir, key, stage):
            try:
                text = md_path.read_text(encoding="utf-8", errors="replace").strip()
            except Exception:
                continue
            if not text:
                continue
            snippet = text[:1800]
            block = f"### [{key}] {md_path.relative_to(repo_dir)}\n{snippet}\n"
            if total + len(block) > max_chars:
                break
            chunks.append(block)
            loaded_sources.append(f"{key}:{md_path.relative_to(repo_dir)}")
            total += len(block)
    return {
        "stage": stage,
        "hub_root": str(HUB_ROOT),
        "repos_requested": repos,
        "files_loaded": loaded_sources,
        "context_text": "\n".join(chunks),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=sorted(STAGE_ROUTES.keys()))
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    bundle = load_stage_skills(args.stage)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print(json.dumps({"stage": bundle["stage"], "loaded_count": len(bundle["files_loaded"]), "files": bundle["files_loaded"]}, indent=2))


if __name__ == "__main__":
    main()
