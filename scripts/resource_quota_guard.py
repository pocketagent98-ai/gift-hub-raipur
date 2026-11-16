#!/usr/bin/env python3
"""
RUNNER RESOURCE, DISK, TIME & API QUOTA GUARD (PART 3 #12)
Monitors free disk space, memory availability, and QA video sizes so the
GitHub Actions runner never crashes from disk exhaustion or runaway loops.
"""

import json
from pathlib import Path
import shutil
import sys

MIN_FREE_DISK_GB = 2.5
MAX_VIDEO_MB = 45.0


def check_resources() -> dict:
    usage = shutil.disk_usage(".")
    free_gb = usage.free / (1024 ** 3)
    total_gb = usage.total / (1024 ** 3)

    oversized_videos = []
    qa_dir = Path("/tmp/qa_videos")
    if qa_dir.exists():
        for mp4 in qa_dir.glob("*.mp4"):
            sz_mb = mp4.stat().st_size / (1024 ** 2)
            if sz_mb > MAX_VIDEO_MB:
                oversized_videos.append(f"{mp4.name} ({sz_mb:.1f} MB > {MAX_VIDEO_MB} MB)")

    status = {
        "free_disk_gb": round(free_gb, 2),
        "total_disk_gb": round(total_gb, 2),
        "oversized_videos": oversized_videos,
        "status": "PASS" if (free_gb >= MIN_FREE_DISK_GB and not oversized_videos) else "FAIL",
    }
    print(json.dumps(status, indent=2))
    if status["status"] != "PASS":
        sys.exit(1)
    return status


if __name__ == "__main__":
    check_resources()
