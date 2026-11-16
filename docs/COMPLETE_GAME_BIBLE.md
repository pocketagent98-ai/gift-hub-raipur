# 📖 COMPLETE ORIGINAL GAME DESIGN BIBLE (`block_juggle_cleanroom_01`)

- **Game ID**: `block_juggle_cleanroom_01` | **Genre**: `block_puzzle` | **Category**: `level_by_level` `[VERIFIED]`
- **Engine & Dynamic SDK Policy**: `Godot 4.7.2 Stable (gl_compatibility, Dynamic Target SDK 36)` (`config/android_compatibility_policy.json`) `[VERIFIED]`
- **Companion Bibles Generated**:
  1. `docs/REFERENCE_INTELLIGENCE_DOSSIER.md` (`.json`)
  2. `docs/UI_UX_BIBLE.md` (`.json`)
  3. `docs/MECHANICS_CONTRACT.md` (`docs/mechanics_contract.json`)
  4. `docs/TECHNICAL_ARCHITECTURE.md` (`.json`)
  5. `docs/ART_DIRECTION_BIBLE.md` (`.json`)
  6. `docs/ASSET_LICENSE_MANIFEST.md` (`.json`)

## 1. Core Gameplay Loop
- **Second-to-Second**: Aim/steer with responsive mobile touch -> strike 1-hit and 4-hit armored targets -> trigger clearcoat crack, particle burst, camera pulse, and combo chime.
- **Minute-to-Minute**: Clear progressive waves across 10 handcrafted levels or 5 seamless endless 30m chunks while maintaining combo multiplier and shield integrity.
- **Session-to-Session**: Spend earned coins in the Shop screen, unlock new visual skins in Inventory, claim DailyRewards, and beat high scores saved in user://savegame.json (schema v5).

## 2. Retention Architecture (0–60s, 5–15m, 15–30m, 30m+)
- **First 60 Seconds**: Instant main menu load (<2.5s), interactive tutorial banner explaining 4-hit purple armored targets, and immediate tactile hit feedback.
- **5–15 Minutes**: Introduction of 3-hit and 4-hit armored targets at Levels 3 and 6, plus first Shop skin/reward unlock.
- **15–30 Minutes**: Mastery of high-density Level 6–10 patterns and seamless 5-chunk Endless mode.
- **30+ Minutes**: Completionist progression, streak milestones, and zero-paywall high-score mastery.
