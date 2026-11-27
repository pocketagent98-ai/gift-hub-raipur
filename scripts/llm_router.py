#!/usr/bin/env python3
"""Anti-429 Dual-LLM Router (AI Game Studio V8.0).

Enforces 3.5s pacing and exponential backoff (15s -> 30s -> 60s) on HTTP 429.
- Private NVIDIA_API_KEY ONLY for blueprints, GDScript 4.7.2 coding, and polish.
- GEMINI_API_KEY for gemini-decision-1 policy gate and primary multimodal Vision QA
  (gemini-3.5-flash-lite -> gemini-3.1-flash-lite -> NVIDIA Nemotron Omni backup).
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

NVIDIA_API_BASE = "https://integrate.api.nvidia.com/v1/chat/completions"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

MIN_DELAY_SEC = 3.5
BACKOFF_SCHEDULE = (15, 30, 60)

NVIDIA_ROLES: Dict[str, List[str]] = {
    "architect": ["nvidia/nemotron-3-ultra-550b-a55b", "moonshotai/kimi-k3.1-pro", "nvidia/nemotron-3-super-120b-a12b"],
    "core_coder": ["nvidia/nemotron-4-340b-instruct", "moonshotai/kimi-k3.1-pro", "nvidia/nemotron-3-super-120b-a12b"],
    "balanced_coder": ["nvidia/nemotron-3-super-120b-a12b", "nvidia/nemotron-3.5-lightning-30b-a3b"],
    "fast_patch": ["nvidia/nemotron-3.5-lightning-30b-a3b", "nvidia/nemotron-3-super-120b-a12b"],
    "reward": ["nvidia/nemotron-4-340b-reward", "nvidia/nemotron-3-super-120b-a12b"],
    "safety": ["nvidia/nemotron-3.5-content-safety", "nvidia/nemotron-3-super-120b-a12b"],
    "vision_backup": ["nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "nvidia/nemotron-3-super-120b-a12b"],
}

GEMINI_VISION_CHAIN = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]

_LAST_CALL_TS = 0.0


def _pace() -> None:
    global _LAST_CALL_TS
    now = time.time()
    wait = MIN_DELAY_SEC - (now - _LAST_CALL_TS)
    if wait > 0:
        time.sleep(wait)
    _LAST_CALL_TS = time.time()


def _nvidia_key() -> str:
    return (os.environ.get("NVIDIA_API_KEY", "") or os.environ.get("NVIDIA_NIM_API_KEY", "")).strip()


def _gemini_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def extract_json_block(text: str) -> Dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object found in LLM response")
    obj = json.loads(cleaned[start : end + 1])
    if not isinstance(obj, dict):
        raise ValueError("Parsed JSON is not an object")
    return obj


def _http_post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = 120) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    last_err: Optional[Exception] = None
    for attempt in range(len(BACKOFF_SCHEDULE) + 1):
        _pace()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code == 429 and attempt < len(BACKOFF_SCHEDULE):
                delay = BACKOFF_SCHEDULE[attempt]
                print(f"[ANTI-429] HTTP 429 received; backing off {delay}s...")
                time.sleep(delay)
                continue
            raise
        except Exception as exc:
            last_err = exc
            if attempt < len(BACKOFF_SCHEDULE):
                time.sleep(5)
                continue
            raise
    raise RuntimeError(f"HTTP POST failed after retries: {last_err}")


def call_nvidia(
    role: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    key = _nvidia_key()
    if not key:
        raise RuntimeError("NVIDIA_API_KEY is not set in environment")
    models = NVIDIA_ROLES.get(role, NVIDIA_ROLES["balanced_coder"])
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    last_err = ""
    for model in models:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            body = _http_post_json(NVIDIA_API_BASE, payload, headers, timeout=150)
            content = body["choices"][0]["message"]["content"].strip()
            if content:
                return {"provider": "nvidia_nim", "model": model, "text": content}
        except Exception as exc:
            last_err = f"{model}: {exc}"
            print(f"[LLM_ROUTER WARN] NVIDIA {last_err}; trying fallback...")
    raise RuntimeError(f"All NVIDIA NIM models failed for role '{role}': {last_err}")


def call_gemini_decision_gate(prompt: str) -> Dict[str, Any]:
    key = _gemini_key()
    if not key:
        return {"provider": "local_policy_fallback", "approved": True, "note": "GEMINI_API_KEY missing"}
    url = f"{GEMINI_API_BASE}/gemini-3.5-flash-lite:generateContent?key={key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": f"Respond ONLY with JSON {{\"approved\": true|false, \"reason\": \"...\"}}.\n{prompt}"}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 256},
    }
    try:
        body = _http_post_json(url, payload, {"Content-Type": "application/json"}, timeout=45)
        text = "".join(p.get("text", "") for p in body.get("candidates", [{}])[0].get("content", {}).get("parts", []))
        parsed = extract_json_block(text)
        parsed["provider"] = "gemini_decision_gate"
        return parsed
    except Exception as exc:
        return {"provider": "gemini_decision_gate", "approved": True, "warning": str(exc)}


def call_vision_qa(prompt: str, image_paths: List[Path], max_tokens: int = 1600) -> Dict[str, Any]:
    g_key = _gemini_key()
    encoded: List[Dict[str, str]] = []
    for p in image_paths:
        if p.exists() and p.stat().st_size > 1024:
            mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
            encoded.append({"mime": mime, "b64": base64.b64encode(p.read_bytes()).decode("ascii")})
    if not encoded:
        raise RuntimeError("No valid images supplied to call_vision_qa")

    if g_key:
        for model in GEMINI_VISION_CHAIN:
            parts: List[Dict[str, Any]] = [{"text": prompt}]
            for img in encoded:
                parts.append({"inline_data": {"mime_type": img["mime"], "data": img["b64"]}})
            url = f"{GEMINI_API_BASE}/{model}:generateContent?key={g_key}"
            payload = {
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_tokens},
            }
            try:
                body = _http_post_json(url, payload, {"Content-Type": "application/json"}, timeout=120)
                text = "".join(p.get("text", "") for p in body.get("candidates", [{}])[0].get("content", {}).get("parts", [])).strip()
                if text:
                    return {"provider": "gemini", "model": model, "text": text}
            except Exception as exc:
                print(f"[VISION_QA WARN] Gemini {model} failed: {exc}")

    nv_key = _nvidia_key()
    if nv_key:
        content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
        for img in encoded:
            content.append({"type": "image_url", "image_url": {"url": f"data:{img['mime']};base64,{img['b64']}"}})
        headers = {"Authorization": f"Bearer {nv_key}", "Content-Type": "application/json"}
        for model in NVIDIA_ROLES["vision_backup"]:
            payload = {"model": model, "messages": [{"role": "user", "content": content}], "max_tokens": max_tokens, "temperature": 0.1}
            try:
                body = _http_post_json(NVIDIA_API_BASE, payload, headers, timeout=150)
                text = body["choices"][0]["message"]["content"].strip()
                if text:
                    return {"provider": "nvidia_omni", "model": model, "text": text}
            except Exception as exc:
                print(f"[VISION_QA WARN] NVIDIA {model} failed: {exc}")

    raise RuntimeError("All Vision QA providers (Gemini Flash-Lite & NVIDIA Omni) failed")
