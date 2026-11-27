# Studio V7.0 Mandatory Engineering & Clean-Room Rules

1. **100% Clean-Room Originality:** Never download, decompile, or copy code, sprites, sounds, or trademarks from third-party APKs. Use only public genre conventions, public Play Store player review insights, and original procedural/AI assets.
2. **Godot 4.7.2 Syntax Strictness:** All generated GDScript must compile cleanly under Godot 4.7.2 GUI (`--editor --import --quit`) with zero `SCRIPT ERROR` or `Parse Error`.
3. **Zero UI Clipping & Mobile Ergonomics:** Portrait `720x1280` with `canvas_items` + `expand`. Wrap all screens in `SafeAreaMargin` (24px sides, 44px top, 32px bottom). Every descriptive `Label` must use `TextServer.AUTOWRAP_WORD_SMART`. Minimum interactive touch target: `56x56` px.
4. **Anti-429 API Discipline:** Every LLM call passes through `scripts/llm_router.py` with 3.5s pacing and exponential backoff (`15s -> 30s -> 60s`).
5. **Release Safety:** CI test driver (`test_driver.gd`) must never execute when `OS.has_feature("release")` is true or when `--qa-mode=true` is absent.
6. **Disk Hygiene:** Every stage runs on a clean GitHub Actions runner and persists outputs to the private Hugging Face Dataset Vault (`HF_PRIVATE_DATASET_REPO`).
