# Skill: Security Audit & Release Hardening
Active rules (Stage 5 ONLY):
- Verify no secrets, tokens, or debug QA bots remain active in release builds.
- Verify Android Target SDK 36, Min SDK 24, `arm64-v8a`, 16 KB page alignment, optional AES-256 Godot script/PCK encryption, and valid `apksigner` + `jarsigner` signatures.
