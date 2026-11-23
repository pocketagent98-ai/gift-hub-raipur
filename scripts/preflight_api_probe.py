#!/usr/bin/env python3
"""Bounded 10-second pre-flight probe for NVIDIA NIM, Gemini, and HF endpoints."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def probe(name: str, url: str, headers: dict | None = None, redact: bool = False) -> dict:
    started = time.time()
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read(256).decode("utf-8", "replace")
            sample = "authenticated" if redact else body[:120]
            return {"name": name, "ok": 200 <= response.status < 300, "status": response.status, "elapsed_ms": int((time.time() - started) * 1000), "sample": sample}
    except urllib.error.HTTPError as exc:
        return {"name": name, "ok": False, "status": exc.code, "elapsed_ms": int((time.time() - started) * 1000), "error": exc.reason}
    except Exception as exc:
        return {"name": name, "ok": False, "status": 0, "elapsed_ms": int((time.time() - started) * 1000), "error": str(exc)[:160]}


def main() -> int:
    nvidia = os.environ.get("NVIDIA_NIM_API_KEY", "").strip() or os.environ.get("NVIDIA_API_KEY", "").strip()
    gemini = os.environ.get("GEMINI_API_KEY", "").strip()
    hf = os.environ.get("HF_TOKEN", "").strip()
    results = []
    if nvidia:
        results.append(probe("nvidia_nim_models", "https://integrate.api.nvidia.com/v1/models", {"Authorization": f"Bearer {nvidia}", "Accept": "application/json"}))
    else:
        results.append({"name": "nvidia_nim_models", "ok": False, "status": 0, "error": "NVIDIA key not configured"})
    if gemini:
        results.append(probe("gemini_models", "https://generativelanguage.googleapis.com/v1beta/models", {"x-goog-api-key": gemini}))
    else:
        results.append({"name": "gemini_models", "ok": False, "status": 0, "error": "GEMINI_API_KEY not configured"})
    if hf:
        results.append(probe("huggingface_whoami", "https://huggingface.co/api/whoami-v2", {"Authorization": f"Bearer {hf}"}, redact=True))
    else:
        results.append({"name": "huggingface_whoami", "ok": False, "status": 0, "error": "HF_TOKEN not configured"})
    report = {"status": "PASS" if any(r.get("ok") for r in results) else "WARN", "probes": results, "note": "Probe is advisory; deterministic clean-room generation does not depend on live model calls."}
    out = Path("docs/PREFLIGHT_API_PROBE.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
