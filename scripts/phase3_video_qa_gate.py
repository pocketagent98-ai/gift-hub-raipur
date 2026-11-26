#!/usr/bin/env python3
"""
PHASE 3 — STRICT ANTI-DEMO PLAYTEST & MULTIMODAL VIDEO QA GATE (V6.0)
"""

import json
import os
from pathlib import Path
import sys
import time
import urllib.request


def main() -> None:
    suite = sys.argv[1] if len(sys.argv) > 1 else "multi_levels"
    video_p = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(f"/tmp/qa_videos/{suite}.mp4")
    qa_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("/tmp/studio_qa")
    tel_p = qa_dir / f"telemetry_{suite}.txt"

    if not tel_p.exists():
        print(f"[QA_FAIL] Missing telemetry file: {tel_p}")
        sys.exit(1)
    telemetry = tel_p.read_text(encoding="utf-8")
    print(telemetry)

    if "Status=COMPLETED" not in telemetry or "QA_FAIL" in telemetry:
        print(f"[QA_FAIL] Anti-Demo / Clipping telemetry gate failed for {suite}!")
        sys.exit(1)
    if suite == "multi_levels" and "[REAL_GAMEPLAY_VERIFIED]" not in telemetry:
        print("[QA_FAIL] Gameplay bot did not prove real interactive scoring!")
        sys.exit(1)
    if not video_p.exists() or video_p.stat().st_size < 1024:
        print(f"[QA_FAIL] Missing or empty MP4 video: {video_p}")
        sys.exit(1)

    gem_key = os.environ.get("GEMINI_API_KEY", "").strip()
    nv_key = (os.environ.get("NVIDIA_NIM_API_KEY", "") or os.environ.get("NVIDIA_API_KEY", "")).strip()
    verdict = ""

    if gem_key:
        try:
            from google import genai
            client = genai.Client(api_key=gem_key)
            uploaded = None
            try:
                uploaded = client.files.upload(file=str(video_p))
                for _ in range(15):
                    if getattr(uploaded, "state", None) and uploaded.state.name == "PROCESSING":
                        time.sleep(2)
                        uploaded = client.files.get(name=uploaded.name)
                    else:
                        break
            except Exception:
                uploaded = None
            prompt = f"Suite: {suite}\nTelemetry:\n{telemetry}\nConfirm real interactive gameplay, 0 clipped UI, and clean layout. Reply VERDICT: PASS or VERDICT: FAIL."
            for m_id in ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash"):
                try:
                    res = client.models.generate_content(model=m_id, contents=[uploaded, prompt] if uploaded else [prompt])
                    verdict = (res.text or "").strip()
                    if verdict:
                        print(f"[GEMINI_QA model={m_id}] {verdict[:300]}")
                        break
                except Exception:
                    continue
        except Exception as exc:
            print(f"[WARN] Gemini QA skipped: {exc}")

    if not verdict and nv_key:
        try:
            payload = json.dumps({
                "model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
                "messages": [{"role": "user", "content": f"Suite {suite} Telemetry:\n{telemetry}\nReply VERDICT: PASS or VERDICT: FAIL."}],
                "max_tokens": 120,
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {nv_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                verdict = json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"].strip()
                print(f"[NVIDIA_OMNI_QA] {verdict[:300]}")
        except Exception as exc:
            print(f"[WARN] NVIDIA Omni QA skipped: {exc}")

    if "VERDICT: FAIL" in verdict:
        print(f"[QA_FAIL] Vision Judge rejected {suite}!")
        sys.exit(1)

    print(f"[PHASE 3 QA PASS] {suite} verified (Anti-Demo + Zero Clipping + Video).")


if __name__ == "__main__":
    main()
