# Skill: Godogen — Godot 4 Scene & Visual QA Standards
Source: `htdt/godogen`

Active rules:
- Use `gl_compatibility` renderer for universal Android & Xvfb CI compatibility.
- Validate scenes via full Godot GUI import (`xvfb-run godot --editor --path . --import --quit`) before QA.
- Record deterministic Movie Maker QA clips (`--write-movie`, `--fixed-fps 15`) covering UI, mechanics, live gameplay, and save/offline edge cases.
