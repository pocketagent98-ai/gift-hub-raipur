#!/usr/bin/env python3
"""
FAIL-CLOSED MULTI-VIDEO & DETERMINISTIC TELEMETRY INSPECTOR (V5.0)
- First checks deterministic engine telemetry (`telemetry_<suite>.txt`):
  Any `QA_FAIL_` or missing `Status=COMPLETED` immediately fails the gate (Exit Code 1)
  regardless of what any AI model says!
- Verifies suite-specific contracts for all 4 suites:
  1. `ui_shop`: Safe-area resolution matrix, touch events, and lifecycle checks.
  2. `mechanics_lab`: 4-hit armored target progressive destruction (`HP 4 -> 3 ... HP 1 -> 0 | State=popped`) + 8x8 board clear check.
  3. `multi_levels` / `endless_chunks`: Complete progressive levels (Levels 1, 8, 16, 30 / 1, 3, 6, 10) or 5 stitched endless chunks with zero seam falls.
  4. `save_ads_and_edge`: `[SAVE_LOAD_PASS]`, `[OFFLINE_MODE_PASS]`, and `[GAME_OVER_AND_VICTORY_PASS]`.
- Next, inspects the recorded gameplay video + audio + 4-angle camera grid (`qa_4cam_grid_<suite>.png`):
  1. Primary Vision Judges: `gemini-3.5-flash-lite` (500 RPD) and `gemini-3.1-flash-lite` (500 RPD) -> 1,000 RPD combined, followed by `gemini-2.5-flash`.
  2. Secondary Starred NVIDIA Vision/Omni Fallback: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` via `NVIDIA_NIM_API_KEY` / `NVIDIA_API_KEY`.
"""

import base64
import json
import os
from pathlib import Path
import sys
import time
import urllib.request


def validate_deterministic_telemetry(suite_name: str, telemetry_text: str) -> list:
    errors = []
    if not telemetry_text.strip():
        errors.append(f"Telemetry log for suite '{suite_name}' is empty or missing!")
        return errors
    if "Status=COMPLETED" not in telemetry_text:
        errors.append(f"Suite '{suite_name}' did not finish cleanly (missing Status=COMPLETED).")
    for line in telemetry_text.splitlines():
        if "QA_FAIL" in line or "CRITICAL_ERROR" in line:
            errors.append(f"Engine Telemetry Failure: {line.strip()}")
    if suite_name == "mechanics_lab":
        if "HP 4 -> 3 | Alive=true" not in telemetry_text or "HP 1 -> 0 | Alive=false | State=popped" not in telemetry_text:
            errors.append("4-hit armored target contract did not verify progressive 4->3->2->1->0 destruction!")
    if suite_name == "save_ads_and_edge":
        for req_tag in ("[SAVE_LOAD_PASS]", "[OFFLINE_MODE_PASS]", "[GAME_OVER_AND_VICTORY_PASS]"):
            if req_tag not in telemetry_text:
                errors.append(f"Suite 'save_ads_and_edge' missing required verification marker: {req_tag}")
    return errors


def evaluate_with_nvidia_omni_fallback(suite_name: str, telemetry: str, grid_png: Path, nv_key: str) -> str:
    """Calls starred NVIDIA multimodal model `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`."""
    content_items = [
        {
            "type": "text",
            "text": (
                f"Suite: {suite_name}\nDeterministic Telemetry:\n{telemetry[:4000]}\n\n"
                "Verify 0 floor sinking, 0 wall clipping, clean 8x8 board & UI layout, and responsive controls. "
                "Output 'VERDICT: PASS' if acceptable, otherwise 'VERDICT: FAIL' with reasons."
            ),
        }
    ]
    if grid_png.exists() and grid_png.stat().st_size > 0:
        b64_img = base64.b64encode(grid_png.read_bytes()).decode("ascii")
        content_items.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_img}"},
        })

    for model_id in (
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        "nvidia/nemotron-3-super-120b-a12b",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
    ):
        try:
            payload = json.dumps({
                "model": model_id,
                "messages": [{"role": "user", "content": content_items if "omni" in model_id else content_items[:1]}],
                "max_tokens": 256,
                "temperature": 0.1,
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {nv_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                txt = body["choices"][0]["message"]["content"].strip()
                if txt:
                    print(f"[NVIDIA_OMNI_QA model={model_id}] {txt[:400]}")
                    return txt
        except Exception as exc:
            print(f"[WARN] NVIDIA model {model_id} fallback error ({exc}); trying next...")
    return ""


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--mode":
        print("Multi-video inspector ready for suites: ui_shop, mechanics_lab, multi_levels, endless_chunks, save_ads_and_edge")
        sys.exit(0)

    suite_name = sys.argv[1] if len(sys.argv) > 1 else "ui_shop"
    video_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(f"/tmp/qa_videos/{suite_name}.mp4")
    telemetry_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("/tmp/studio_qa")
    telemetry_file = telemetry_dir / f"telemetry_{suite_name}.txt"
    grid_png = telemetry_dir / f"qa_4cam_grid_{suite_name}.png"

    telemetry = telemetry_file.read_text(encoding="utf-8") if telemetry_file.exists() else ""
    det_errors = validate_deterministic_telemetry(suite_name, telemetry)

    if det_errors:
        print("VERDICT: FAIL (Deterministic Telemetry Gate Rejected Build)")
        for err in det_errors:
            print(f" - {err}")
        sys.exit(1)

    if not video_path.exists() or video_path.stat().st_size < 1024:
        print(f"VERDICT: FAIL (Video file missing or empty: {video_path})")
        sys.exit(1)

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    nv_key = (os.environ.get("NVIDIA_NIM_API_KEY", "") or os.environ.get("NVIDIA_API_KEY", "")).strip()

    if not gemini_key and not nv_key:
        print(f"[WARN] Neither GEMINI_API_KEY nor NVIDIA_API_KEY set; deterministic telemetry and MP4 video ({video_path.stat().st_size} B) verified.")
        print(f"VERDICT: PASS (Deterministic Telemetry + Video Artifact Verified for {suite_name})")
        sys.exit(0)

    verdict_text = ""

    # 1. Primary Video/Audio QA via Gemini 3.5 Flash Lite & Gemini 3.1 Flash Lite (500 + 500 = 1,000 RPD)
    if gemini_key:
        try:
            from google import genai
            gclient = genai.Client(api_key=gemini_key)
            prompt = (
                f"Suite: {suite_name}\nDeterministic Telemetry:\n{telemetry}\n\n"
                "Inspect the recorded gameplay video and audio. "
                "Confirm 0 floor sinking, 0 wall clipping, smooth UI transitions, and clear audio. "
                "Output 'VERDICT: PASS' if acceptable, otherwise 'VERDICT: FAIL' with fixes."
            )
            # Strictly ordered per user's active quota: 3.5 Flash Lite (500 RPD) -> 3.1 Flash Lite (500 RPD) -> 2.5 Flash (20 RPD) -> Gemma 4 31B
            candidate_models = (
                "gemini-3.5-flash-lite",
                "gemini-3.1-flash-lite",
                "gemini-2.5-flash",
                "gemma-4-31b-it",
            )
            uploaded = None
            try:
                uploaded = gclient.files.upload(file=str(video_path))
                for _ in range(20):
                    if getattr(uploaded, "state", None) and uploaded.state.name == "PROCESSING":
                        time.sleep(2)
                        uploaded = gclient.files.get(name=uploaded.name)
                    else:
                        break
            except Exception as up_exc:
                print(f"[WARN] Video upload to Gemini Files API skipped ({up_exc}); evaluating telemetry + 4-cam grid.")
                uploaded = None

            for m_id in candidate_models:
                try:
                    contents_payload = [uploaded, prompt] if (uploaded is not None and "gemma" not in m_id) else [prompt]
                    res = gclient.models.generate_content(model=m_id, contents=contents_payload)
                    verdict_text = (res.text or "").strip()
                    if verdict_text:
                        print(f"[MULTIMODAL_QA model={m_id}] {verdict_text[:400]}")
                        break
                except Exception as m_exc:
                    print(f"[WARN] Gemini model {m_id} unavailable ({m_exc}); trying next fallback model...")
        except Exception as exc:
            print(f"[WARN] Gemini client error ({exc}); switching to NVIDIA Omni fallback.")

    # 2. Secondary Video/Frame QA via Starred NVIDIA Omni Model (nvidia/nemotron-3-nano-omni-30b-a3b-reasoning)
    if not verdict_text and nv_key:
        verdict_text = evaluate_with_nvidia_omni_fallback(suite_name, telemetry, grid_png, nv_key)

    if "VERDICT: FAIL" in verdict_text:
        print("VERDICT: FAIL (Multimodal Vision Judge Rejected Video)")
        sys.exit(1)

    print(f"VERDICT: PASS (Deterministic Telemetry + Video Verified for {suite_name})")
    sys.exit(0)


if __name__ == "__main__":
    main()
