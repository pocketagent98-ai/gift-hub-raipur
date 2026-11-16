#!/usr/bin/env python3
"""
DEEP GAME INTELLIGENCE & RESEARCH ENGINE (V5.0)
Reads Play Store link/package ID from CLI arguments OR `docs/resolved_job.json` / `/dev/shm/private_studio_vault/resolved_job.json`.
Collects Play Store metadata, publisher details, release history, screenshots,
and official repository/docs references with strict confidence tagging:
[VERIFIED], [OBSERVED], [INFERRED], [UNKNOWN].
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, Optional


def extract_package_id(text_or_url: str) -> Optional[str]:
    m = re.search(r"id=([a-zA-Z0-9._]+)", text_or_url or "")
    if m:
        return m.group(1)
    if re.fullmatch(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z0-9_]+){1,}$", (text_or_url or "").strip()):
        return text_or_url.strip()
    return None


def load_routed_ref_link(cli_arg: str, order_json_path: str = "") -> str:
    if cli_arg and not cli_arg.startswith("-"):
        return cli_arg.strip()
    for candidate in [order_json_path, "/dev/shm/private_studio_vault/resolved_job.json", "docs/resolved_job.json"]:
        if candidate and Path(candidate).exists():
            try:
                data = json.loads(Path(candidate).read_text(encoding="utf-8"))
                if data.get("ref_link"):
                    return str(data["ref_link"]).strip()
            except Exception:
                pass
    if Path("ORDER.md").exists():
        m = re.search(r"^PLAYSTORE_REFERENCE_LINK\s*:\s*(.*)$", Path("ORDER.md").read_text(encoding="utf-8"), re.M | re.I)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return ""


def gather_play_store_intelligence(url_or_pkg: str) -> Dict[str, Any]:
    pkg_id = extract_package_id(url_or_pkg)
    timestamp = datetime.now(timezone.utc).isoformat()

    if not pkg_id:
        return {
            "timestamp_utc": timestamp,
            "package_id": None,
            "confidence": "UNKNOWN",
            "status": "NO_PACKAGE_ID_SUPPLIED",
            "active_skills": ["Jakeschincariol/replica-skill (replica-recon, replica-brand)", "storytold/craft-anything"],
            "limitations": [
                "No Play Store package ID or URL was provided in ORDER.md or CLI input. "
                "Operating in 100% Original Clean-Room IP mode without external store scraping."
            ],
        }

    try:
        from google_play_scraper import app as gp_app
        info = gp_app(pkg_id, lang="en", country="us")
        return {
            "timestamp_utc": timestamp,
            "status": "FETCHED_LIVE",
            "package_id": pkg_id,
            "confidence": "VERIFIED",
            "active_skills": ["Jakeschincariol/replica-skill (replica-recon, replica-brand)", "storytold/craft-anything"],
            "identity": {
                "title": {"value": info.get("title"), "confidence": "VERIFIED"},
                "package_id": {"value": pkg_id, "confidence": "VERIFIED"},
                "publisher": {"value": info.get("developer"), "confidence": "VERIFIED"},
                "version": {"value": info.get("version"), "confidence": "VERIFIED"},
                "genre": {"value": info.get("genre"), "confidence": "VERIFIED"},
                "released": {"value": info.get("released"), "confidence": "VERIFIED"},
                "updated": {"value": info.get("updated"), "confidence": "VERIFIED"},
                "installs": {"value": info.get("installs"), "confidence": "OBSERVED"},
                "developer_website": {"value": info.get("developerWebsite"), "confidence": "VERIFIED"},
            },
            "screenshots": info.get("screenshots", [])[:8],
            "video_url": info.get("video"),
            "description": info.get("description", ""),
            "recent_changes": info.get("recentChanges", ""),
            "forbidden_trademarks": [t for t in (info.get("title", ""), info.get("developer", "")) if t],
            "source_url": f"https://play.google.com/store/apps/details?id={pkg_id}",
        }
    except Exception as exc:
        return {
            "timestamp_utc": timestamp,
            "status": "BLOCKED_OFFLINE_OR_UNREACHABLE",
            "package_id": pkg_id,
            "confidence": "UNKNOWN",
            "active_skills": ["Jakeschincariol/replica-skill (replica-recon, replica-brand)", "storytold/craft-anything"],
            "identity": {
                "package_id": {"value": pkg_id, "confidence": "VERIFIED"},
                "title": {"value": "Unavailable offline (Requires online runner)", "confidence": "UNKNOWN"},
                "publisher": {"value": "Unavailable offline (Requires online runner)", "confidence": "UNKNOWN"},
            },
            "forbidden_trademarks": [pkg_id],
            "limitations": [f"Live Play Store network lookup blocked/unreachable in current environment: {exc}"],
            "source_url": f"https://play.google.com/store/apps/details?id={pkg_id}",
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("pos_ref", nargs="?", default="")
    parser.add_argument("--order", default="")
    parser.add_argument("--out", default="docs/game_identity_report.json")
    args, _ = parser.parse_known_args()

    routed_ref = load_routed_ref_link(args.pos_ref, args.order)
    out = gather_play_store_intelligence(routed_ref)
    Path("docs").mkdir(parents=True, exist_ok=True)
    Path("docs/game_identity_report.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    if args.out and args.out != "docs/game_identity_report.json":
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
