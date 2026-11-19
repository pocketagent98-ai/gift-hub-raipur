# 🏗️ TECHNICAL ARCHITECTURE SPECIFICATION (`block_juggle_cleanroom_01`)

- **Engine**: `Godot 4.7.2 Stable (gl_compatibility)` `[VERIFIED]`
- **Dynamic Android Compatibility Policy**: `config/android_compatibility_policy.json` (Currently configured Target SDK `36`, Min SDK `24`, with automated PR gate in `.github/workflows/android-future-compatibility-monitor.yml`) `[VERIFIED]`
- **Primary Coding Agent**: `DeepSeek Harness (dsh) + @ebony-vinyl/dsh-our-free-model@2.8.3` `[VERIFIED]`
- **Permanent Skills**: `gamedev-skills/awesome-gamedev-agent-skills, htdt/godogen, cloudflare/security-audit-skill, modern-web-guidance` `[VERIFIED]`
- **Temporary Research Skills**: `Jakeschincariol/replica-skill, storytold/craft-anything` `[VERIFIED]`
- **Standby Tools**: `morluto/rea (rea-agents — active only when USE_REA=true)` `[VERIFIED]`
- **Self-Healing & Rollback**: `git tag -f safe-AGENT_XX -> 3 attempts -> automatic git reset --hard safe-AGENT_XX` `[VERIFIED]`
