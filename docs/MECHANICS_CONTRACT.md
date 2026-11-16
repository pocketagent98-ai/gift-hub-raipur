# ⚙️ MECHANICS CONTRACT (`block_juggle_cleanroom_01`)

- **Engine**: Godot `4.7.2` (`gl_compatibility`, 60Hz Physics) `[VERIFIED]`
- **4-Hit Armored Target State Machine**: `HP=4 (intact)` -> `HP=3 (cracked_1)` -> `HP=2 (cracked_2)` -> `HP=1 (cracked_3)` -> `HP=0 (popped + queue_free)` `[VERIFIED]`
- **10 Progressive Levels**: `load_level(1..10)` (`target_count = 4 + level * 2`) `[VERIFIED]`
- **5 Seamless Endless Chunks**: `30.0m` length per chunk, `0.000m` seam gap `[VERIFIED]`
- **All 4 Unrushed QA Video Suites**: `ui_shop`, `mechanics_lab`, `multi_levels`/`endless_chunks`, `save_ads_and_edge` `[VERIFIED]`
