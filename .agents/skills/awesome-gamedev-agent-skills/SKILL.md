# Skill: Awesome GameDev Agent Skills (Curated Godot 4 Mobile Core)
Source: `gamedev-skills/awesome-gamedev-agent-skills`

Active rules loaded on-demand for Stage 3:
- Use typed GDScript 4.7.2 (`var score: int = 0`, `func load_level(lvl: int) -> void`).
- Separate game state (`GameManager` autoload), visual presentation (`BoardView`), UI navigation (`StudioUI`), persistence (`SaveManager`), audio (`AudioDirector`), and monetization (`MonetizationManager`).
- Guarantee responsive touch controls (`InputEventScreenTouch`, `InputEventScreenDrag`, plus mouse fallback for desktop/CI testing).
- Keep draw calls low and particle counts bounded for smooth 60 FPS on entry-level Android devices.
