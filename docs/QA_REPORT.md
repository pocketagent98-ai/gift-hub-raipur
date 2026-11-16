# 🧪 DEEP GAMEPLAY & LIFECYCLE QA REPORT (V2.0)

## 1. Fail-Closed QA Architecture (Part 3 #5 & #8)
- All `|| true` error-suppression masks have been removed from the QA and export steps in `.github/workflows/ai-game-studio.yml`.
- `scripts/multi_video_inspector.py` enforces a **2-Stage Fail-Closed Gate**:
  1. **Stage A (Deterministic Engine Telemetry Gate)**: Parses `telemetry_<suite>.txt` and rejects the build immediately (`sys.exit(1)`) if `Status=COMPLETED` is absent, if any `QA_FAIL_` or `CRITICAL_ERROR` is logged, or if the 4-hit armored target fails its `4 -> 3 -> 2 -> 1 -> 0 (popped)` state transition contract.
  2. **Stage B (Multimodal High-Thinking Video + Audio Gate)**: Uploads the 720p H.264 AAC gameplay recording to `gemini-3.5-flash-lite` / `gemini-3.1-flash-lite` (`thinking_level="high"`) and rejects the build if `VERDICT: PASS` is not returned.

---

## 2. Coverage of Android Lifecycle, Touch, Resolutions & Edge Cases (`scripts/deep_game_verifier_bot.gd`)

| Test Category | Verification Mechanism Implemented | Gate Rule |
| :--- | :--- | :--- |
| **Touch Controls** | Generates synthetic `InputEventScreenTouch` press/release events via `Input.parse_input_event()` at each button's global rect center. | Every button must respond and have size >= 44x44 px (`56px` enforced by theme). |
| **Multi-Resolution & Safe Areas** | Dynamically switches viewport across `1080x1920` (Portrait), `1080x2400` (20:9 Tall Notch), and `2400x1080` (Landscape). | Zero `Control` or `Button` nodes clipped outside viewport bounds. |
| **Pause/Resume & Focus Loss** | Propagates `NOTIFICATION_APPLICATION_PAUSED`, `NOTIFICATION_WM_WINDOW_FOCUS_OUT`, `NOTIFICATION_WM_WINDOW_FOCUS_IN`, and `NOTIFICATION_APPLICATION_RESUMED`. | Zero state corruption or audio lockups across lifecycle transitions. |
| **Save/Load Persistence** | Executes `SaveManager.run_self_test()` performing a write/clear/read round-trip to `user://savegame.json`. | Exact coin and progression state restored from disk. |
| **Offline Mode Resilience** | Executes `MonetizationManager.run_offline_resilience_test()` simulating network loss (`offline_mode = true`). | Graceful fallback without crash when ads/billing are unreachable. |
| **Memory Leak & Orphan Nodes** | Monitors `Performance.OBJECT_ORPHAN_NODE_COUNT` and `Performance.OBJECT_NODE_COUNT` across 4 levels and 5 endless chunks. | Fails if orphan nodes > 50 or active nodes grow > 1,500. |
| **FPS & ANR Frame Spikes** | Monitors `Engine.get_frames_per_second()` and frame delta (`ms`). | Fails if FPS < 24 or single frame delta > 150 ms. |
