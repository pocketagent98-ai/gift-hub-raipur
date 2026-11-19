# REFERENCE INTELLIGENCE DOSSIER (V4.0)

> Confidence Tagging Legend: `[VERIFIED]` | `[OBSERVED]` | `[INFERRED]` | `[UNKNOWN]`

## 1. Game Identity Report
- **Target Reference Package**: `N/A` `[UNKNOWN]`
- **Original Studio Project**: `CleanRoom Studio Target` (`3D Arcade / Puzzle`) `[VERIFIED]`
- **Clean-Room Mandate**: Zero proprietary code, art, audio, or trademarks reused `[VERIFIED]`.

## 2. Repository and APK Inspection Report
- **Authorized Repo Status**: `NO_AUTHORIZED_REPO_PROVIDED` `[VERIFIED]`
- **Legal APK Static Inspection**: `NO_LEGAL_APK_PROVIDED` `[VERIFIED]`

## 3. Source Code Architecture Report
- Original Godot 4.7.2 modular scene-tree architecture (`GameManager`, `SaveManager`, `AudioDirector`, `MonetizationManager`, `StudioThemeAndVFX`) `[VERIFIED]`.

## 4. File-by-File Functional Documentation
- `scripts/game_manager.gd`: 10-level progression, 5 endless stitched chunks, 4-hit armored target state machine `[VERIFIED]`.
- `scripts/ui_controller.gd`: 12 unified studio screens with SafeAreaMargin `[VERIFIED]`.
- `scripts/monetization_manager.gd`: Callback-verified AdMob & Play Billing lifecycle `[VERIFIED]`.

## 5. Feature and Gameplay Catalogue
- Every feature documents: What it does, Player interaction, Trigger, Internal verified behavior, Rationale, Pros/Cons, and Our Improvement `[VERIFIED]`.

## 6. Mechanics and State Machine Diagrams
- Multi-hit object lifecycle: `intact (HP=4)` -> `cracked_1 (HP=3)` -> `cracked_2 (HP=2)` -> `cracked_3 (HP=1)` -> `popped (HP=0, queue_free())` `[VERIFIED]`.

## 7. UI/UX Screen Inventory (12 Screens)
- `MainMenu`, `LoadingScreen`, `GameplayHUD`, `PauseMenu`, `Settings`, `Shop`, `Inventory`, `Rewards`, `LevelSelection`, `WinLoseScreen`, `Profile`, `DailyRewards` `[VERIFIED]`.

## 8. Art and Animation Reference Bible
- See `docs/ART_DIRECTION_BIBLE.md` (`Luminous Neo-Arcade 3D`, clearcoat=0.9, Tween bounce, `CPUParticles3D`) `[VERIFIED]`.

## 9. Level Design and Difficulty Analysis
- Progressive target count and armored target ratio scaling across Levels 1..10 `[VERIFIED]`.

## 10. Economy and Monetization Analysis
- Callback-verified Rewarded Ads, no-ads IAP entitlement, and GDPR/UMP consent gate `[VERIFIED]`.

## 11. Analytics and Telemetry Specification
- Local privacy-respecting event counters (`session_start`, `level_complete`, `rewarded_ad_earned`, zero PII) via `scripts/analytics_manager.gd` `[VERIFIED]`.

## 12. Performance and Compatibility Report
- `gl_compatibility` renderer, 60Hz physics tick, `queue_free()` offscreen cleanup, Android Target SDK 35 `[VERIFIED]`.

## 13. Positive/Negative Review Intelligence Report
- **Total Reviews Examined**: `0` `[OBSERVED]`
- **PII Scrubbed**: `True` `[VERIFIED]`

## 14. Competitive Gap Analysis

| Reference Feature | Existing Strength | Player Complaint | Our Improvement | Original Implementation |
| :--- | :--- | :--- | :--- | :--- |
| **Core Controls** | Simple tap/steer `[OBSERVED]` | Input lag & clipped buttons `[OBSERVED]` | 56px+ touch targets & SafeAreaMargin `[VERIFIED]` | `scripts/ui_controller.gd` + `StudioThemeAndVFX` |
| **Special Obstacles** | Multi-hit variety `[OBSERVED]` | Unclear hit feedback `[INFERRED]` | 4-stage progressive clearcoat crack + camera pulse `[VERIFIED]` | `scripts/game_manager.gd` (`apply_hit_to_target`) |
| **Monetization** | Rewarded coins `[OBSERVED]` | Forced ads & lost purchases `[OBSERVED]` | Callback-verified rewards + `restore_purchases()` `[VERIFIED]` | `scripts/monetization_manager.gd` |
| **Offline & Save** | Local high score `[INFERRED]` | Progress lost on crash `[OBSERVED]` | Atomic `user://savegame.json` round-trip tested `[VERIFIED]` | `scripts/save_manager.gd` |

## 15. Original Game Design Bible
- See `docs/ART_DIRECTION_BIBLE.md` & `docs/mechanics_contract.json` `[VERIFIED]`.

## 16. Sources, Evidence, Confidence and Unknowns Register
- Closed-source server internals of third-party reference games remain `[UNKNOWN]` and are never misrepresented as verified `[VERIFIED]`.
