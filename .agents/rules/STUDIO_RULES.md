# 🛡️ IRONCLAD AI GAME STUDIO RULES (GODOT 4.7.2 EDITION)

Every AI agent (`studio-architect`, `studio-coder`, `Godogen`, `OpenCode Game Studios`) MUST obey these 9 non-negotiable engineering and legal rules on every file edit:

## 1. Target Engine: Godot 4.7.2 (`gl_compatibility`)
- Write all GDScript and shaders strictly for **Godot 4.7.2**.
- Keep `renderer/rendering_method="gl_compatibility"` so the game runs at 60 FPS on all Android devices, Web browsers, and GitHub Actions software OpenGL3 runners.

## 2. Dual Android Packaging (`game_install.apk` + `game_release.aab`)
- Never delete or break `export_presets.cfg`. Both `Android (Direct Install APK)` (`build/android/game_install.apk`) and `Android (Play Store Signed AAB)` (`build/android/game_release.aab`) must remain valid and signed.

## 3. 100% Clean-Room & Copyright Immunity
- NEVER copy any 3D model, texture, sound file, logo, character name, or trademarked title from `docs/playstore_reference_blueprint.json`.
- Use Play Store references strictly to understand high-level gameplay loops and to fix the 1-star user complaints listed in `user_complaints_to_fix_in_our_game`.
- Generate ALL 3D characters, vehicles, weapons, and props procedurally inside Godot 4.7.2 using `Procedural3DFactory` (`scripts/procedural_3d_factory.gd`), `CSGMesh3D`, `ArrayMesh`, and `.gdshader`.

## 4. Zero 3D Floor Sinking & Wall Penetration
- Every 3D character (`CharacterBody3D`) and vehicle (`VehicleBody3D`) MUST have its lowest mesh vertex (`AABB.position.y`) aligned to `y = 0.0` relative to its root collision shape.
- Enable `continuous_cd = true` on fast-moving bodies so objects never tunnel through walls at high speed.

## 5. Mandatory Hooks for Deep Multi-Video Verification
To allow `scripts/deep_game_verifier_bot.gd` to inspect every level, mechanic, and endless chunk without getting stuck at `0:00`, the main game manager MUST expose:
- `load_level(level_number: int)`: Immediately loads and starts the specified level (`1..10`) for Level-by-Level games.
- `load_single_chunk(chunk_id: int)` and `test_stitched_chunks(chunk_order: Array)`: Loads individual map chunks (`1..5`) and stitched seam sequences (`[1, 3, 2, 5, 4, 1]`) for Endless games.
- `on_hit(damage: int)` and `hit_points: int`: On all multi-hit objects (e.g., 3-to-4 hit bubbles, shields, destructible armor) so the Mechanics Lab video can verify progressive damage on hits 1, 2, 3 and destruction on hit 4.

## 6. Memory Leak Prevention (`queue_free()`)
- Any obstacle, bullet, particle, enemy, or map chunk that moves more than 60 meters behind the active camera MUST call `queue_free()` or return to an Object Pool so `Performance.OBJECT_NODE_COUNT` never grows unbounded.

## 7. Android Read-Only Storage Protection (`user://` ONLY)
- NEVER open files for writing in `res://` (`FileAccess.open("res://...", FileAccess.WRITE)` crashes on Android!).
- Always store save data, high scores, unlocked levels, and purchased shop items/cards in `user://savegame.json`.

## 8. Mobile Safe-Area & Multi-Resolution UI
- Anchor all UI `Control` and `Button` nodes using full-rect or margin containers with at least `32px` padding from screen edges so buttons are never cut off by mobile camera notches or aspect ratio shifts.

## 9. Cloudflare Security Hygiene
- Never hardcode API keys, tokens, or insecure `http://` endpoints inside any `.gd` or `.tscn` file.
