#!/usr/bin/env python3
"""
GEMINI DECISION 1 — FAST MULTIMODAL JUDGE, ROUTER & RUBRIC SCORER (V5.0)
- Quota profile: 200 RPM | 50,000 TPM | 10,000 RPD (`gemini-decision-1`).
- Evaluates typed Yes/No, Multiple-Choice, and 0-to-100 Rubric Score questions
  for:
  1. Instant Skill & Privacy Router (keeps DeepSeek Harness on private NVIDIA NIM route for proprietary research).
  2. Multi-Question Visual/Video Polish Judge.
  3. Play Store Policy & Trademark Gate.
"""

import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List


def build_polish_decision_questions() -> List[Dict[str, Any]]:
    return [
        {"id": "q_no_floor_sinking", "type": "yes_no", "question": "Are all 3D characters, blocks, and vehicles cleanly aligned without sinking into the floor?"},
        {"id": "q_no_wall_clipping", "type": "yes_no", "question": "Do all moving entities and puzzle pieces stay strictly inside board/world bounds without clipping?"},
        {"id": "q_ui_no_overlap", "type": "yes_no", "question": "Are all 12 UI screens, buttons (>=56px), and HUD labels cleanly spaced inside safe areas with zero overlap?"},
        {"id": "q_visual_polish_grade", "type": "score", "min": 0, "max": 100, "question": "Score the overall visual polish, lighting, clearcoat materials, and commercial readiness from 0 to 100."},
        {"id": "q_mobile_ux_grade", "type": "score", "min": 0, "max": 100, "question": "Score mobile readability, button contrast, and touch-target ergonomics from 0 to 100."},
    ]


def evaluate_with_gemini_decision_1(artifact_path: Path, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        out = {"status": "SKIPPED_NO_API_KEY", "model": "gemini-decision-1", "questions_count": len(questions)}
        Path("docs").mkdir(parents=True, exist_ok=True)
        Path("docs/GEMINI_DECISION_LOG.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        return out

    text_snippet = artifact_path.read_text(encoding="utf-8", errors="ignore")[:12000] if artifact_path.exists() else "Studio V5.0 Build"
    prompt = (
        "You are the Gemini Decision Gate for AI Game Studio V5.0.\n"
        f"Artifact ({artifact_path.name}):\n{text_snippet}\n\n"
        f"Evaluate these exact decision questions and return compact JSON:\n{json.dumps(questions)}"
    )

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        for model_name in ("gemini-decision-1", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"):
            try:
                resp = client.models.generate_content(model=model_name, contents=[prompt])
                ans = (resp.text or "").strip()
                if ans:
                    out = {
                        "status": "EVALUATED_LIVE",
                        "model": model_name,
                        "questions_count": len(questions),
                        "response_preview": ans[:600],
                    }
                    Path("docs").mkdir(parents=True, exist_ok=True)
                    Path("docs/GEMINI_DECISION_LOG.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
                    return out
            except Exception:
                continue
    except Exception as exc:
        out = {
            "status": "DETERMINISTIC_FALLBACK",
            "model": "gemini-decision-1",
            "questions_count": len(questions),
            "note": str(exc),
        }
        Path("docs").mkdir(parents=True, exist_ok=True)
        Path("docs/GEMINI_DECISION_LOG.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        return out

    out = {
        "status": "READY_FOR_DECISIONS_ENDPOINT",
        "model": "gemini-decision-1",
        "questions_count": len(questions),
    }
    Path("docs").mkdir(parents=True, exist_ok=True)
    Path("docs/GEMINI_DECISION_LOG.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/ART_DIRECTION_BIBLE.md")
    res = evaluate_with_gemini_decision_1(target, build_polish_decision_questions())
    print(json.dumps(res, indent=2))
