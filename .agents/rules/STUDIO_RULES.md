# 🛡️ IRONCLAD AI GAME STUDIO RULES (GODOT 4.7.2 + V7.0 CLEAN-ROOM EDITION)

Every AI agent (`studio-architect`, `studio-coder`, `Godogen`, `DeepSeek Harness`) MUST obey these non-negotiable engineering and legal rules on every file edit:

## 1. Target Engine: Godot 4.7.2 (`gl_compatibility`)
- Write all GDScript and shaders strictly for **Godot 4.7.2**.
- Keep `renderer/rendering_method="gl_compatibility"` so the game runs at 60 FPS on all Android devices, Web browsers, and GitHub Actions software OpenGL3 runners.
- All generated GDScript must compile cleanly under Godot 4.7.2 GUI (`--editor --import --quit`) with zero `SCRIPT ERROR` or `Parse Error`.

## 2. Dual Android Packaging (`game_install.apk` + `game_release.aab`)
- Never delete or break `export_presets.cfg`. Both `Android (Direct Install APK)` (`build/android/game_install.apk`) and `Android (Play Store Signed AAB)` (`build/android/game_release.aab`) must remain valid and signed (Target SDK 36, Min SDK 24, `arm64-v8a`, 16 KB aligned).

## 3. 100% Clean-Room & Copyright Immunity
- NEVER copy any 3D model, texture, sound file, logo, character name, or trademarked title from `docs/playstore_reference_blueprint.json` or any third-party APK.
- Use Play Store references strictly to understand high-level gameplay loops and to fix the 1-star user complaints listed in `user_complaints_to_fix_in_our_game`.
- Generate ALL 2D/3D characters, blocks, screws, props, and SFX procedurally inside Godot 4.7.2 or via original studio scripts (`scripts/stage2_asset_factory.py`, `scripts/procedural_3d_factory.gd`).

## 4. Zero 3D Floor Sinking & Wall Penetration
- Every 3D character (`CharacterBody3D`) and vehicle (`VehicleBody3D`) MUST have its lowest mesh vertex (`AABB.position.y`) aligned to `y = 0.0` relative to its root collision shape.
- Enable `continuous_cd = true` on fast-moving bodies so objects never tunnel through walls at high speed.

## 5. Mandatory Hooks for Deep Multi-Video Verification
- Expose `load_level(level_number: int)` and deterministic gameplay verification hooks so Movie Maker QA videos (`ui_shop.mp4`, `mechanics_lab.mp4`, `multi_levels.mp4`, `save_ads_and_edge.mp4`) prove real interactive gameplay.
- CI test drivers must never execute when `OS.has_feature("release")` is true or when `--qa-mode=true` is absent.

## 6. Memory Leak Prevention (`queue_free()`)
- Any transient obstacle, particle, or map chunk must call `queue_free()` or return to an Object Pool so `Performance.OBJECT_NODE_COUNT` never grows unbounded.

## 7. Android Read-Only Storage Protection (`user://` ONLY)
- NEVER open files for writing in `res://`. Always store save data, high scores, unlocked levels, and purchased shop items in `user://savegame.json`.

## 8. Mobile Safe-Area & Multi-Resolution UI (Zero Clipping)
- Portrait `720x1280` with `canvas_items` + `expand`. Wrap all 12 screens in `SafeAreaMargin` (24px+ sides, 44px top, 32px bottom). Every descriptive `Label` must use `TextServer.AUTOWRAP_WORD_SMART`. Minimum touch target: `56x56` px.

## 9. Security, Anti-429 API & Disk Hygiene
- Never hardcode API keys, tokens, or insecure `http://` endpoints inside any `.gd` or `.tscn` file.
- Every LLM call respects Anti-429 pacing (`>=3.5s` gap, exponential backoff `15s -> 30s -> 60s`) and persists stage bundles to the private Hugging Face Dataset Vault (`HF_PRIVATE_DATASET_REPO`).
