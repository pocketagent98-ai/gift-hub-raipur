# 📦 ANDROID BUILD, SIGNING & GOOGLE PLAY COMPLIANCE REPORT (V2.0)

## 1. Google Play Release Compliance Checklist (Part 3 #11)

| Requirement | V2.0 Configuration | Verification Script | Status |
| :--- | :--- | :--- | :--- |
| **Target API Level** | `version/target_sdk=35` & `gradle_build/target_sdk=35` (`min_sdk=24`) in `export_presets.cfg` | `scripts/studio_healer_and_compliance.py` | **VERIFIED** |
| **Dual Output Formats** | Preset 1: `build/android/game_release.aab` (Google Play AAB)<br>Preset 2: `build/android/game_install.apk` (Universal APK) | `scripts/verify_android_builds.py --post-build` | **VERIFIED** |
| **Persistent App Signing Keystore** | RSA-2048 `release.keystore` with SHA-256 continuity check in `scripts/hf_vault_sync.py` | `scripts/hf_vault_sync.py` & `keytool` | **VERIFIED** |
| **Production QA-Bot Exclusion** | Removed from `project.godot` `[autoload]` AND excluded via `exclude_filter="scripts/deep_game_verifier_bot.gd, test/*, docs/*"` | `scripts/verify_android_builds.py` | **VERIFIED** |
| **AdMob & Play Billing Lifecycle** | GDPR/UMP Consent + Test/Prod Ad Unit switching + `restore_purchases()` in `scripts/monetization_manager.gd` | `scripts/monetization_manager.gd` | **VERIFIED** |
| **Privacy Policy & Data Safety** | Auto-generated and audited in `docs/PRIVACY_POLICY.md` | `scripts/studio_healer_and_compliance.py` | **VERIFIED** |
| **Software Bill of Materials (SBOM)** | CycloneDX 1.5 JSON (`docs/SBOM.cdx.json`) with SHA-256 hashes of APK, AAB, and pinned libraries | `scripts/verify_android_builds.py` | **VERIFIED** |
