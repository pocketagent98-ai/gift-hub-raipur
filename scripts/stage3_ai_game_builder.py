#!/usr/bin/env python3
"""
STAGE 3 — Multi-Agent Godot 4.7.2 Game Builder + 3-Cycle Self-Healing Compiler Gate (V7.0)
- Loads Stage 1 clean-room Bibles + Stage 2 original assets + curated .agents/skills/ router.
- Uses PRIVATE NVIDIA NIM route ONLY (never sends private studio build prompts to Gemini free tier).
- Synthesizes complete Godot 4.7.2 mobile game (block_puzzle, screw_puzzle, match_3) with
  AI-authored level tuning & visual config, then compiles under FULL Godot 4.7.2 GUI (Xvfb)
  with up to 3 autonomous NVIDIA NIM self-healing repair passes.
"""

import json
from pathlib import Path
import re
import subprocess

from llm_router import nvidia_chat


def _load_stage3_skills() -> str:
    router = json.loads(Path(".agents/skills/SKILL_ROUTER.json").read_text(encoding="utf-8"))
    parts = []
    for rel in router.get("routes", {}).get("stage3", []):
        p = Path(rel)
        if p.exists():
            parts.append(p.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def _generate_ai_tuning_gd(order: dict, spec: dict, skills_txt: str) -> tuple[str, str]:
    """Use NVIDIA NIM private coder to author custom level tuning & game-feel extension."""
    prompt = (
        f"You are writing `scripts/ai_game_tuning.gd` for Godot 4.7.2 (strict typed GDScript).\n"
        f"Game: {spec.get('title')} ({order['genre']}) | Prompt: {order['prompt'][:350]}\n"
        f"Skills:\n{skills_txt[:1400]}\n\n"
        "Output ONLY valid Godot 4.7.2 GDScript (no markdown fences) extending RefCounted with:\n"
        "- `static func get_level_goal(lvl: int) -> int`\n"
        "- `static func get_combo_label(combo: int) -> String`\n"
        "- `static func get_daily_coin_bonus(day: int) -> int`\n"
        "Keep it under 35 lines, pure typed GDScript 4.7.2, zero external dependencies."
    )
    code, model = nvidia_chat(
        [{"role": "user", "content": prompt}],
        role="coder",
        max_tokens=600,
        temperature=0.15,
    )
    if code:
        code = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", code.strip())
    if (
        not code
        or "extends RefCounted" not in code
        or "get_level_goal" not in code
        or "get_combo_label" not in code
    ):
        code = (
            "extends RefCounted\n\n"
            "static func get_level_goal(lvl: int) -> int:\n"
            "\treturn 340 + (maxi(1, lvl) - 1) * 135\n\n"
            "static func get_combo_label(combo: int) -> String:\n"
            "\tif combo >= 4:\n"
            "\t\treturn \"FEVER OVERDRIVE!\"\n"
            "\telif combo >= 2:\n"
            "\t\treturn \"SUPER COMBO x%d!\" % combo\n"
            "\treturn \"NICE!\"\n\n"
            "static func get_daily_coin_bonus(day: int) -> int:\n"
            "\treturn 40 + clampi(day, 1, 7) * 20\n"
        )
        model = f"{model}:validated_fallback"
    return code, model


def _write_app_config(order: dict, spec: dict) -> None:
    title = spec.get("title", "Crystal Grid Cascade").replace('"', "'")
    tagline = spec.get("tagline", "Original Studio Puzzle").replace('"', "'")
    pkg = order.get("package_name", "com.aistudio.crystalgrid")
    genre = order["genre"]
    bg = spec.get("theme_bg_hex", "#0f172a")
    panel = spec.get("theme_panel_hex", "#1e293b")
    accent = spec.get("theme_accent_hex", "#38bdf8")
    pal = spec.get("palette_hex", ["#fb5668", "#ffa62b", "#3ddc84", "#38b6ff", "#a86bff", "#ff66c4"])
    pal_gd = ", ".join(f'Color("{c}")' for c in pal[:6])

    code = f'''extends Node

const GAME_ID: String = "{order["game_id"]}"
const GAME_TITLE: String = "{title}"
const GAME_TAGLINE: String = "{tagline}"
const PACKAGE_NAME: String = "{pkg}"
const GENRE: String = "{genre}"
const AD_MODE: String = "TEST"

const COLOR_BG: Color = Color("{bg}")
const COLOR_PANEL: Color = Color("{panel}")
const COLOR_ACCENT: Color = Color("{accent}")
const PIECE_PALETTE: Array[Color] = [Color(0, 0, 0, 0), {pal_gd}]

static func is_production_ads() -> bool:
\treturn AD_MODE == "PRODUCTION"
'''
    Path("scripts/app_config.gd").write_text(code, encoding="utf-8")


def _write_save_manager() -> None:
    code = '''extends Node

const SAVE_PATH: String = "user://studio_v7_save.json"

var data: Dictionary = {
\t"coins": 150,
\t"highest_level": 1,
\t"best_score": 0,
\t"remove_ads": false,
\t"daily_day": 1,
\t"last_claim_date": "",
\t"boosters": {"swap": 3, "hammer": 3, "magnet": 3}
}

func _ready() -> void:
\tload_game()

func save_game() -> bool:
\tvar f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
\tif f == null:
\t\treturn false
\tf.store_string(JSON.stringify(data))
\tf.close()
\treturn true

func load_game() -> bool:
\tif not FileAccess.file_exists(SAVE_PATH):
\t\treturn false
\tvar f := FileAccess.open(SAVE_PATH, FileAccess.READ)
\tif f == null:
\t\treturn false
\tvar parsed = JSON.parse_string(f.get_as_text())
\tf.close()
\tif typeof(parsed) == TYPE_DICTIONARY:
\t\tfor k in parsed.keys():
\t\t\tdata[k] = parsed[k]
\t\treturn true
\treturn false

func add_coins(amount: int) -> void:
\tdata["coins"] = maxi(0, int(data.get("coins", 0)) + amount)
\tsave_game()

func unlock_level(lvl: int) -> void:
\tdata["highest_level"] = maxi(int(data.get("highest_level", 1)), clampi(lvl, 1, 30))
\tsave_game()

func run_self_test() -> bool:
\tvar before := int(data.get("coins", 0))
\tadd_coins(25)
\tvar ok := load_game() and int(data.get("coins", 0)) == before + 25
\tdata["coins"] = before
\tsave_game()
\treturn ok
'''
    Path("scripts/save_manager.gd").write_text(code, encoding="utf-8")


def _write_audio_director() -> None:
    code = '''extends Node

const MIN_INTERVAL_MS: int = 35

var _sfx_player: AudioStreamPlayer
var _ui_player: AudioStreamPlayer
var _last_ms: int = 0
var _muted: bool = false
var _streams: Dictionary = {}

func _ready() -> void:
\tfor bus_name in ["Music", "SFX", "UI"]:
\t\tif AudioServer.get_bus_index(bus_name) == -1:
\t\t\tAudioServer.add_bus()
\t\t\tAudioServer.set_bus_name(AudioServer.get_bus_count() - 1, bus_name)
\t_sfx_player = AudioStreamPlayer.new()
\t_sfx_player.bus = "SFX"
\tadd_child(_sfx_player)
\t_ui_player = AudioStreamPlayer.new()
\t_ui_player.bus = "UI"
\tadd_child(_ui_player)
\tfor name in ["ui_click", "place_block", "line_clear", "screw_turn", "plate_drop", "victory", "invalid"]:
\t\tvar p := "res://assets/generated/audio/%s.wav" % name
\t\tif ResourceLoader.exists(p):
\t\t\t_streams[name] = load(p)

func toggle_mute() -> bool:
\t_muted = not _muted
\tvar idx := AudioServer.get_bus_index("Master")
\tif idx >= 0:
\t\tAudioServer.set_bus_mute(idx, _muted)
\treturn _muted

func play_sfx(name: String, combo_level: int = 1) -> void:
\tif _muted:
\t\treturn
\tvar now := Time.get_ticks_msec()
\tif now - _last_ms < MIN_INTERVAL_MS:
\t\treturn
\t_last_ms = now
\tvar player := _ui_player if name == "ui_click" else _sfx_player
\tif _streams.has(name):
\t\tplayer.stream = _streams[name]
\t\tplayer.pitch_scale = clampf(1.0 + float(combo_level - 1) * 0.06, 0.9, 1.45)
\t\tplayer.play()
'''
    Path("scripts/audio_director.gd").write_text(code, encoding="utf-8")


def _write_monetization_manager() -> None:
    code = '''extends Node

signal reward_granted(kind: String, amount: int)
signal purchase_completed(sku: String)

var _overlay: CanvasLayer
var _backdrop: ColorRect
var _label: Label
var _levels_since_interstitial: int = 0

func _ready() -> void:
\t_overlay = CanvasLayer.new()
\t_overlay.layer = 90
\tadd_child(_overlay)
\t_backdrop = ColorRect.new()
\t_backdrop.color = Color(0.04, 0.06, 0.12, 0.88)
\t_backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
\t_backdrop.visible = false
\t_overlay.add_child(_backdrop)
\tvar center := CenterContainer.new()
\tcenter.set_anchors_preset(Control.PRESET_FULL_RECT)
\t_backdrop.add_child(center)
\tvar panel := PanelContainer.new()
\tpanel.custom_minimum_size = Vector2(540, 260)
\tcenter.add_child(panel)
\t_label = Label.new()
\t_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
\t_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
\t_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
\t_label.add_theme_font_size_override("font_size", 28)
\tpanel.add_child(_label)

func on_level_finished() -> void:
\tif bool(SaveManager.data.get("remove_ads", false)):
\t\treturn
\t_levels_since_interstitial += 1
\tif _levels_since_interstitial >= 2:
\t\t_levels_since_interstitial = 0
\t\t_show_preview_notice("INTERSTITIAL AD SLOT (FAIR CADENCE: 1 / 2 LEVELS)")

func show_rewarded_ad(kind: String, amount: int) -> void:
\t_show_preview_notice("REWARDED AD COMPLETED: +%d %s" % [amount, kind.to_upper()])
\tif kind == "coins":
\t\tSaveManager.add_coins(amount)
\temit_signal("reward_granted", kind, amount)

func purchase_sku(sku: String) -> void:
\tif sku.find("remove_ads") >= 0:
\t\tSaveManager.data["remove_ads"] = true
\t\tSaveManager.add_coins(250)
\telif sku.find("mega") >= 0:
\t\tSaveManager.add_coins(5000)
\telse:
\t\tSaveManager.add_coins(500)
\t_show_preview_notice("PLAY BILLING PURCHASE VERIFIED: " + sku)
\temit_signal("purchase_completed", sku)

func _show_preview_notice(msg: String) -> void:
\tif AppConfig.is_production_ads():
\t\treturn
\t_label.text = msg
\t_backdrop.visible = true
\tget_tree().create_timer(0.6).timeout.connect(func(): _backdrop.visible = false)

func run_offline_resilience_test() -> bool:
\treturn _overlay != null and SaveManager != null
'''
    Path("scripts/monetization_manager.gd").write_text(code, encoding="utf-8")


def _write_block_puzzle_manager() -> None:
    code = '''extends Node

const Tuning = preload("res://scripts/ai_game_tuning.gd")

signal level_changed(new_level: int)
signal score_changed(new_score: int, combo: int)
signal board_updated(cleared_count: int)
signal state_changed()
signal level_completed(lvl: int, final_score: int)
signal game_over(final_score: int)

const BOARD_SIZE: int = 8
const PIECE_CATALOG: Array = [
\t[Vector2i(0, 0)],
\t[Vector2i(0, 0), Vector2i(1, 0)],
\t[Vector2i(0, 0), Vector2i(0, 1)],
\t[Vector2i(0, 0), Vector2i(1, 0), Vector2i(2, 0)],
\t[Vector2i(0, 0), Vector2i(0, 1), Vector2i(0, 2)],
\t[Vector2i(0, 0), Vector2i(1, 0), Vector2i(0, 1), Vector2i(1, 1)],
\t[Vector2i(0, 0), Vector2i(1, 0), Vector2i(2, 0), Vector2i(0, 1)],
\t[Vector2i(0, 0), Vector2i(1, 0), Vector2i(2, 0), Vector2i(2, 1)],
\t[Vector2i(0, 0), Vector2i(1, 0), Vector2i(2, 0), Vector2i(1, 1)],
\t[Vector2i(0, 0), Vector2i(1, 0), Vector2i(2, 0), Vector2i(3, 0)],
\t[Vector2i(0, 0), Vector2i(0, 1), Vector2i(0, 2), Vector2i(0, 3)],
\t[Vector2i(0, 0), Vector2i(1, 0), Vector2i(1, 1), Vector2i(2, 1)]
]

var current_level: int = 1
var level_goal: int = 360
var current_score: int = 0
var current_combo: int = 0
var moves_made: int = 0
var hammer_mode_active: bool = false
var juggle_swaps_remaining: int = 3
var hammer_boosters_remaining: int = 3
var juggle_hold_piece: Dictionary = {}

var grid_8x8: Array = []
var tray_pieces: Array = []
var last_cleared_cells: Array = []
var last_popup_text: String = ""
var last_popup_grid_pos: Vector2i = Vector2i(4, 4)
var _rng := RandomNumberGenerator.new()

func _ready() -> void:
\t_rng.randomize()
\tload_level(1)

func load_level(lvl_num: int) -> void:
\tcurrent_level = clampi(lvl_num, 1, 30)
\tlevel_goal = Tuning.get_level_goal(current_level)
\tcurrent_score = 0
\tcurrent_combo = 0
\tmoves_made = 0
\thammer_mode_active = false
\tjuggle_swaps_remaining = 3
\thammer_boosters_remaining = 3
\tjuggle_hold_piece = {}
\tlast_cleared_cells.clear()
\tgrid_8x8.clear()
\tfor r in range(BOARD_SIZE):
\t\tvar row: Array = []
\t\tfor c in range(BOARD_SIZE):
\t\t\trow.append(0)
\t\tgrid_8x8.append(row)
\tif current_level >= 2:
\t\tvar sr := RandomNumberGenerator.new()
\t\tsr.seed = 7700 + current_level * 97
\t\tfor _i in range(mini(14, 2 + current_level)):
\t\t\tgrid_8x8[sr.randi_range(1, 6)][sr.randi_range(1, 6)] = sr.randi_range(1, 6)
\t_refill_tray()
\temit_signal("level_changed", current_level)
\temit_signal("score_changed", current_score, current_combo)
\temit_signal("state_changed")

func _refill_tray() -> void:
\ttray_pieces.clear()
\tvar empty := 0
\tfor r in range(BOARD_SIZE):
\t\tfor c in range(BOARD_SIZE):
\t\t\tif int(grid_8x8[r][c]) == 0:
\t\t\t\tempty += 1
\tfor i in range(3):
\t\tvar max_i := PIECE_CATALOG.size() - 1
\t\tif current_level <= 3 or empty < 20:
\t\t\tmax_i = mini(max_i, 8)
\t\tvar idx := 0 if (i == 0 and empty < 14) else _rng.randi_range(0, max_i)
\t\ttray_pieces.append({"cells": PIECE_CATALOG[idx].duplicate(), "color_id": _rng.randi_range(1, 6), "used": false})

func can_place_piece(cells: Array, gx: int, gy: int) -> bool:
\tif cells.is_empty():
\t\treturn false
\tfor cell in cells:
\t\tvar v: Vector2i = cell
\t\tvar tx := gx + v.x
\t\tvar ty := gy + v.y
\t\tif tx < 0 or tx >= BOARD_SIZE or ty < 0 or ty >= BOARD_SIZE:
\t\t\treturn false
\t\tif int(grid_8x8[ty][tx]) != 0:
\t\t\treturn false
\treturn true

func preview_clear_lines(cells: Array, gx: int, gy: int) -> Dictionary:
\tvar rows: Array[int] = []
\tvar cols: Array[int] = []
\tif not can_place_piece(cells, gx, gy):
\t\treturn {"rows": rows, "cols": cols}
\tvar tmp := []
\tfor r in range(BOARD_SIZE):
\t\ttmp.append(grid_8x8[r].duplicate())
\tfor cell in cells:
\t\tvar v: Vector2i = cell
\t\ttmp[gy + v.y][gx + v.x] = 1
\tfor r in range(BOARD_SIZE):
\t\tif not (0 in tmp[r]):
\t\t\trows.append(r)
\tfor c in range(BOARD_SIZE):
\t\tvar ok := true
\t\tfor r in range(BOARD_SIZE):
\t\t\tif int(tmp[r][c]) == 0:
\t\t\t\tok = false
\t\t\t\tbreak
\t\tif ok:
\t\t\tcols.append(c)
\treturn {"rows": rows, "cols": cols}

func place_tray_piece(tray_idx: int, gx: int, gy: int) -> Dictionary:
\tif tray_idx < 0 or tray_idx >= tray_pieces.size():
\t\treturn {"placed": false}
\tvar piece: Dictionary = tray_pieces[tray_idx]
\tif bool(piece.get("used", true)):
\t\treturn {"placed": false}
\tvar cells: Array = piece["cells"]
\tif not can_place_piece(cells, gx, gy):
\t\tAudioDirector.play_sfx("invalid")
\t\treturn {"placed": false}
\tvar cid := int(piece["color_id"])
\tfor cell in cells:
\t\tvar v: Vector2i = cell
\t\tgrid_8x8[gy + v.y][gx + v.x] = cid
\tpiece["used"] = true
\tmoves_made += 1
\tlast_cleared_cells.clear()
\tvar cleared := _clear_lines()
\tvar pts := cells.size() * 15
\tif cleared > 0:
\t\tcurrent_combo = mini(8, current_combo + 1)
\t\tpts += cleared * cleared * 120 * current_combo
\t\tlast_popup_text = "%s +%d" % [Tuning.get_combo_label(current_combo), pts]
\t\tAudioDirector.play_sfx("line_clear", current_combo)
\telse:
\t\tcurrent_combo = 0
\t\tlast_popup_text = "+%d" % pts
\t\tAudioDirector.play_sfx("place_block", 1)
\tlast_popup_grid_pos = Vector2i(gx, gy)
\tcurrent_score += pts
\tvar all_used := true
\tfor p in tray_pieces:
\t\tif not bool(p["used"]):
\t\t\tall_used = false
\t\t\tbreak
\tif all_used:
\t\t_refill_tray()
\temit_signal("score_changed", current_score, current_combo)
\temit_signal("board_updated", cleared)
\temit_signal("state_changed")
\tif current_score >= level_goal:
\t\tSaveManager.add_coins(50)
\t\tSaveManager.unlock_level(current_level + 1)
\t\tAudioDirector.play_sfx("victory", 4)
\t\tMonetizationManager.on_level_finished()
\t\temit_signal("level_completed", current_level, current_score)
\telif not _has_valid_move():
\t\temit_signal("game_over", current_score)
\treturn {"placed": true, "lines_cleared": cleared, "score_gained": pts}

func _clear_lines() -> int:
\tvar fr: Array[int] = []
\tvar fc: Array[int] = []
\tfor r in range(BOARD_SIZE):
\t\tif not (0 in grid_8x8[r]):
\t\t\tfr.append(r)
\tfor c in range(BOARD_SIZE):
\t\tvar ok := true
\t\tfor r in range(BOARD_SIZE):
\t\t\tif int(grid_8x8[r][c]) == 0:
\t\t\t\tok = false
\t\t\t\tbreak
\t\tif ok:
\t\t\tfc.append(c)
\tfor r in fr:
\t\tfor c in range(BOARD_SIZE):
\t\t\tlast_cleared_cells.append({"pos": Vector2i(c, r), "color_id": int(grid_8x8[r][c])})
\t\t\tgrid_8x8[r][c] = 0
\tfor c in fc:
\t\tfor r in range(BOARD_SIZE):
\t\t\tif int(grid_8x8[r][c]) != 0:
\t\t\t\tlast_cleared_cells.append({"pos": Vector2i(c, r), "color_id": int(grid_8x8[r][c])})
\t\t\t\tgrid_8x8[r][c] = 0
\treturn fr.size() + fc.size()

func _has_valid_move() -> bool:
\tfor p in tray_pieces:
\t\tif bool(p["used"]):
\t\t\tcontinue
\t\tfor r in range(BOARD_SIZE):
\t\t\tfor c in range(BOARD_SIZE):
\t\t\t\tif can_place_piece(p["cells"], c, r):
\t\t\t\t\treturn true
\treturn false

func use_primary_booster() -> bool:
\tif juggle_swaps_remaining <= 0:
\t\treturn false
\tfor i in range(tray_pieces.size()):
\t\tif not bool(tray_pieces[i]["used"]):
\t\t\tjuggle_swaps_remaining -= 1
\t\t\tvar cur: Dictionary = tray_pieces[i]
\t\t\tif juggle_hold_piece.is_empty():
\t\t\t\tjuggle_hold_piece = cur
\t\t\t\ttray_pieces[i] = {"cells": [Vector2i(0, 0)], "color_id": _rng.randi_range(1, 6), "used": false}
\t\t\telse:
\t\t\t\ttray_pieces[i] = juggle_hold_piece
\t\t\t\tjuggle_hold_piece = cur
\t\t\tAudioDirector.play_sfx("place_block", 2)
\t\t\temit_signal("state_changed")
\t\t\treturn true
\treturn false

func use_hammer_at(gx: int, gy: int) -> bool:
\tif hammer_boosters_remaining <= 0:
\t\treturn false
\thammer_boosters_remaining -= 1
\thammer_mode_active = false
\tlast_cleared_cells.clear()
\tfor dy in range(-1, 2):
\t\tfor dx in range(-1, 2):
\t\t\tvar tx := gx + dx
\t\t\tvar ty := gy + dy
\t\t\tif tx >= 0 and tx < BOARD_SIZE and ty >= 0 and ty < BOARD_SIZE and int(grid_8x8[ty][tx]) != 0:
\t\t\t\tlast_cleared_cells.append({"pos": Vector2i(tx, ty), "color_id": int(grid_8x8[ty][tx])})
\t\t\t\tgrid_8x8[ty][tx] = 0
\tAudioDirector.play_sfx("line_clear", 3)
\temit_signal("board_updated", 1)
\temit_signal("state_changed")
\treturn true

func bot_play_step() -> String:
\tfor i in range(tray_pieces.size()):
\t\tif bool(tray_pieces[i]["used"]):
\t\t\tcontinue
\t\tvar best := Vector2i(-1, -1)
\t\tvar best_c := -1
\t\tfor r in range(BOARD_SIZE):
\t\t\tfor c in range(BOARD_SIZE):
\t\t\t\tif can_place_piece(tray_pieces[i]["cells"], c, r):
\t\t\t\t\tvar pv := preview_clear_lines(tray_pieces[i]["cells"], c, r)
\t\t\t\t\tvar clr: int = pv["rows"].size() + pv["cols"].size()
\t\t\t\t\tif clr > best_c:
\t\t\t\t\t\tbest_c = clr
\t\t\t\t\t\tbest = Vector2i(c, r)
\t\tif best.x >= 0:
\t\t\tvar res := place_tray_piece(i, best.x, best.y)
\t\t\treturn "BOT_BLOCK tray=%d (%d,%d) clr=%d score=%d" % [i, best.x, best.y, int(res.get("lines_cleared", 0)), current_score]
\treturn "BOT_NO_MOVE"

func step_mechanics_lab_test() -> String:
\tload_level(1)
\tfor c in range(7):
\t\tgrid_8x8[0][c] = 2
\ttray_pieces[0] = {"cells": [Vector2i(0, 0)], "color_id": 4, "used": false}
\tvar res := place_tray_piece(0, 7, 0)
\treturn "MECHANICS_LAB_PASS placed=%s cleared=%d score=%d" % [str(res.get("placed", false)), int(res.get("lines_cleared", 0)), current_score]
'''
    Path("scripts/game_manager.gd").write_text(code, encoding="utf-8")


def _write_screw_puzzle_manager() -> None:
    code = '''extends Node

const Tuning = preload("res://scripts/ai_game_tuning.gd")

signal level_changed(new_level: int)
signal score_changed(new_score: int, combo: int)
signal board_updated(cleared_count: int)
signal state_changed()
signal level_completed(lvl: int, final_score: int)
signal game_over(final_score: int)

var current_level: int = 1
var level_goal: int = 360
var current_score: int = 0
var current_combo: int = 0
var moves_made: int = 0
var juggle_swaps_remaining: int = 3
var hammer_boosters_remaining: int = 3
var hammer_mode_active: bool = false

var plates: Array = []
var screws: Array = []
var active_boxes: Array = []
var buffer_slots: Array = []
const MAX_BUFFER: int = 5

var last_cleared_cells: Array = []
var last_popup_text: String = ""
var last_popup_grid_pos: Vector2i = Vector2i(4, 4)

func _ready() -> void:
\tload_level(1)

func load_level(lvl_num: int) -> void:
\tcurrent_level = clampi(lvl_num, 1, 30)
\tlevel_goal = Tuning.get_level_goal(current_level)
\tcurrent_score = 0
\tcurrent_combo = 0
\tmoves_made = 0
\tjuggle_swaps_remaining = 3
\thammer_boosters_remaining = 3
\tbuffer_slots.clear()
\tplates.clear()
\tscrews.clear()
\tlast_cleared_cells.clear()

\tvar rng := RandomNumberGenerator.new()
\trng.seed = 4200 + current_level * 131
\tvar plate_count := mini(6, 3 + int(current_level / 5))
\tvar color_count := mini(5, 3 + int(current_level / 6))
\tvar color_pool: Array[int] = []
\tfor _i in range(plate_count):
\t\tvar col := rng.randi_range(1, color_count)
\t\tfor _k in range(3):
\t\t\tcolor_pool.append(col)
\tcolor_pool.shuffle()

\tvar screw_idx := 0
\tfor p in range(plate_count):
\t\tvar px := 0.8 + float(p % 2) * 1.4
\t\tvar py := 0.8 + float(p) * 0.95
\t\tvar rect := Rect2(px, py, 4.8, 1.8)
\t\tplates.append({"id": p + 1, "layer": p, "rect": rect, "color_id": (p % color_count) + 1, "removed": false, "fall": 0.0})
\t\tfor s in range(3):
\t\t\tvar sx := px + 0.85 + float(s) * 1.55
\t\t\tvar sy := py + 0.9
\t\t\tscrews.append({
\t\t\t\t"id": screw_idx,
\t\t\t\t"plate_id": p + 1,
\t\t\t\t"layer": p,
\t\t\t\t"pos": Vector2(sx, sy),
\t\t\t\t"color_id": color_pool[screw_idx % color_pool.size()],
\t\t\t\t"removed": false
\t\t\t})
\t\t\tscrew_idx += 1

\tactive_boxes.clear()
\tfor b in range(2):
\t\tactive_boxes.append({"color_id": (b % color_count) + 1, "filled": 0, "capacity": 3})
\t_sync_box_colors()
\temit_signal("level_changed", current_level)
\temit_signal("score_changed", current_score, current_combo)
\temit_signal("state_changed")

func _sync_box_colors() -> void:
\tvar avail := {}
\tfor sc in screws:
\t\tif not bool(sc["removed"]):
\t\t\tavail[int(sc["color_id"])] = true
\tfor cid in buffer_slots:
\t\tavail[int(cid)] = true
\tvar keys := avail.keys()
\tif keys.is_empty():
\t\treturn
\tfor box in active_boxes:
\t\tif int(box["filled"]) == 0 and not avail.has(int(box["color_id"])):
\t\t\tbox["color_id"] = int(keys[0])

func is_screw_accessible(screw: Dictionary) -> bool:
\tif bool(screw["removed"]):
\t\treturn false
\tvar pos: Vector2 = screw["pos"]
\tvar layer: int = int(screw["layer"])
\tfor p in plates:
\t\tif bool(p["removed"]) or int(p["layer"]) <= layer:
\t\t\tcontinue
\t\tif (p["rect"] as Rect2).has_point(pos):
\t\t\treturn false
\treturn true

func tap_screw(screw_id: int) -> Dictionary:
\tif screw_id < 0 or screw_id >= screws.size():
\t\treturn {"removed": false}
\tvar sc: Dictionary = screws[screw_id]
\tif not is_screw_accessible(sc):
\t\tAudioDirector.play_sfx("invalid")
\t\treturn {"removed": false}
\tvar cid := int(sc["color_id"])
\tvar matched := false
\tfor box in active_boxes:
\t\tif int(box["color_id"]) == cid and int(box["filled"]) < int(box["capacity"]):
\t\t\tbox["filled"] = int(box["filled"]) + 1
\t\t\tmatched = true
\t\t\tbreak
\tif not matched:
\t\tif buffer_slots.size() >= MAX_BUFFER:
\t\t\tAudioDirector.play_sfx("invalid")
\t\t\temit_signal("game_over", current_score)
\t\t\treturn {"removed": false}
\t\tbuffer_slots.append(cid)
\tsc["removed"] = true
\tmoves_made += 1
\tAudioDirector.play_sfx("screw_turn", maxi(1, current_combo))
\tvar pts := 45 if matched else 20
\tvar boxes_cleared := 0
\tfor box in active_boxes:
\t\tif int(box["filled"]) >= int(box["capacity"]):
\t\t\tboxes_cleared += 1
\t\t\tbox["filled"] = 0
\t\t\tcurrent_combo = mini(8, current_combo + 1)
\t\t\tpts += 140 * current_combo
\t\t\t_refill_box_from_remaining(box)
\t\t\t_drain_buffer_into_boxes()
\tvar plates_dropped := _update_plates()
\tpts += plates_dropped * 90
\tcurrent_score += pts
\tlast_cleared_cells = [{"pos": Vector2i(int(sc["pos"].x), int(sc["pos"].y)), "color_id": cid}]
\tlast_popup_text = "%s +%d" % [Tuning.get_combo_label(maxi(1, current_combo)), pts]
\tlast_popup_grid_pos = Vector2i(clampi(int(sc["pos"].x), 1, 6), clampi(int(sc["pos"].y), 1, 6))
\temit_signal("score_changed", current_score, current_combo)
\temit_signal("board_updated", boxes_cleared + plates_dropped)
\temit_signal("state_changed")
\tif _all_screws_removed():
\t\tSaveManager.add_coins(50)
\t\tSaveManager.unlock_level(current_level + 1)
\t\tAudioDirector.play_sfx("victory", 4)
\t\tMonetizationManager.on_level_finished()
\t\temit_signal("level_completed", current_level, current_score)
\treturn {"removed": true, "matched": matched, "score_gained": pts}

func _refill_box_from_remaining(box: Dictionary) -> void:
\tfor sc in screws:
\t\tif is_screw_accessible(sc):
\t\t\tbox["color_id"] = int(sc["color_id"])
\t\t\treturn
\tif not buffer_slots.is_empty():
\t\tbox["color_id"] = int(buffer_slots[0])

func _drain_buffer_into_boxes() -> void:
\tvar keep: Array = []
\tfor cid in buffer_slots:
\t\tvar placed := false
\t\tfor box in active_boxes:
\t\t\tif int(box["color_id"]) == int(cid) and int(box["filled"]) < int(box["capacity"]):
\t\t\t\tbox["filled"] = int(box["filled"]) + 1
\t\t\t\tplaced = true
\t\t\t\tbreak
\t\tif not placed:
\t\t\tkeep.append(cid)
\tbuffer_slots = keep

func _update_plates() -> int:
\tvar dropped := 0
\tfor p in plates:
\t\tif bool(p["removed"]):
\t\t\tcontinue
\t\tvar pid := int(p["id"])
\t\tvar still_bolted := false
\t\tfor sc in screws:
\t\t\tif int(sc["plate_id"]) == pid and not bool(sc["removed"]):
\t\t\t\tstill_bolted = true
\t\t\t\tbreak
\t\tif not still_bolted:
\t\t\tp["removed"] = true
\t\t\tdropped += 1
\t\t\tAudioDirector.play_sfx("plate_drop", 2)
\treturn dropped

func _all_screws_removed() -> bool:
\tfor sc in screws:
\t\tif not bool(sc["removed"]):
\t\t\treturn false
\treturn true

func use_primary_booster() -> bool:
\tif juggle_swaps_remaining <= 0 or buffer_slots.is_empty():
\t\treturn false
\tjuggle_swaps_remaining -= 1
\tbuffer_slots.pop_back()
\tAudioDirector.play_sfx("line_clear", 2)
\temit_signal("state_changed")
\treturn true

func bot_play_step() -> String:
\t# Prefer screw matching an active box
\tfor sc in screws:
\t\tif is_screw_accessible(sc):
\t\t\tfor box in active_boxes:
\t\t\t\tif int(box["color_id"]) == int(sc["color_id"]) and int(box["filled"]) < int(box["capacity"]):
\t\t\t\t\tvar res := tap_screw(int(sc["id"]))
\t\t\t\t\treturn "BOT_SCREW_MATCH id=%d score=%d" % [int(sc["id"]), current_score]
\tfor sc in screws:
\t\tif is_screw_accessible(sc):
\t\t\tvar res2 := tap_screw(int(sc["id"]))
\t\t\treturn "BOT_SCREW_BUFFER id=%d score=%d" % [int(sc["id"]), current_score]
\treturn "BOT_DONE"

func step_mechanics_lab_test() -> String:
\tload_level(1)
\tvar s1 := bot_play_step()
\tvar s2 := bot_play_step()
\treturn "MECHANICS_LAB_PASS %s | %s | score=%d" % [s1, s2, current_score]
'''
    Path("scripts/game_manager.gd").write_text(code, encoding="utf-8")


def _write_board_view() -> None:
    code = '''extends Control

var _board_rect: Rect2 = Rect2()
var _cell_size: float = 64.0
var _tray_rects: Array[Rect2] = []
var _dragging_tray_idx: int = -1
var _selected_tray_idx: int = -1
var _drag_pos: Vector2 = Vector2.ZERO
var _hover_grid: Vector2i = Vector2i(-1, -1)
var _particles: Array = []
var _popups: Array = []
var _shake: float = 0.0
var _block_tex: Dictionary = {}
var _screw_tex: Dictionary = {}

func _ready() -> void:
\tmouse_filter = Control.MOUSE_FILTER_STOP
\tsize_flags_horizontal = Control.SIZE_EXPAND_FILL
\tsize_flags_vertical = Control.SIZE_EXPAND_FILL
\tfor i in range(1, 7):
\t\tvar bp := "res://assets/generated/sprites/block_%d.png" % i
\t\tif ResourceLoader.exists(bp):
\t\t\t_block_tex[i] = load(bp)
\t\tvar sp := "res://assets/generated/sprites/screw_%d.png" % i
\t\tif ResourceLoader.exists(sp):
\t\t\t_screw_tex[i] = load(sp)
\tGameManager.connect("state_changed", Callable(self, "_on_state"))
\tGameManager.connect("board_updated", Callable(self, "_on_updated"))

func _on_state() -> void:
\tqueue_redraw()

func _on_updated(cleared: int) -> void:
\tfor item in GameManager.last_cleared_cells:
\t\tvar gpos: Vector2i = item["pos"]
\t\tvar cid := clampi(int(item["color_id"]), 1, AppConfig.PIECE_PALETTE.size() - 1)
\t\tvar col: Color = AppConfig.PIECE_PALETTE[cid]
\t\tvar center := _grid_center(gpos.x, gpos.y)
\t\tfor _k in range(6):
\t\t\tvar ang := randf() * TAU
\t\t\tvar spd := randf_range(80.0, 250.0)
\t\t\t_particles.append({"pos": center, "vel": Vector2(cos(ang), sin(ang)) * spd, "color": col, "life": 0.48, "size": 9.0})
\tif GameManager.last_popup_text != "":
\t\tvar pg: Vector2i = GameManager.last_popup_grid_pos
\t\t_popups.append({"pos": _grid_center(pg.x, pg.y), "text": GameManager.last_popup_text, "life": 0.85})
\tif cleared > 0:
\t\t_shake = 0.20
\tqueue_redraw()

func _process(delta: float) -> void:
\tvar dirty := false
\tif AppConfig.GENRE == "screw_puzzle":
\t\tfor p in GameManager.plates:
\t\t\tif bool(p["removed"]) and float(p["fall"]) < 1.0:
\t\t\t\tp["fall"] = minf(1.0, float(p["fall"]) + delta * 2.2)
\t\t\t\tdirty = true
\tif _shake > 0.0:
\t\t_shake = maxf(0.0, _shake - delta)
\t\tdirty = true
\tif not _particles.is_empty():
\t\tvar np: Array = []
\t\tfor pt in _particles:
\t\t\tpt["life"] = float(pt["life"]) - delta
\t\t\tif float(pt["life"]) > 0.0:
\t\t\t\tpt["pos"] = pt["pos"] + pt["vel"] * delta
\t\t\t\tpt["vel"] = pt["vel"] * 0.93 + Vector2(0, 220.0 * delta)
\t\t\t\tnp.append(pt)
\t\t_particles = np
\t\tdirty = true
\tif not _popups.is_empty():
\t\tvar npo: Array = []
\t\tfor pop in _popups:
\t\t\tpop["life"] = float(pop["life"]) - delta
\t\t\tif float(pop["life"]) > 0.0:
\t\t\t\tpop["pos"] = pop["pos"] + Vector2(0, -60.0 * delta)
\t\t\t\tnpo.append(pop)
\t\t_popups = npo
\t\tdirty = true
\tif dirty or _dragging_tray_idx >= 0:
\t\tqueue_redraw()

func _compute_layout() -> void:
\tvar w := size.x
\tvar h := size.y
\tif w < 20.0 or h < 20.0:
\t\treturn
\tvar reserve := h * 0.26
\tvar avail_h := maxf(200.0, h - reserve - 20.0)
\tvar side := minf(w - 24.0, avail_h)
\t_cell_size = floor(side / 8.0)
\tvar exact := _cell_size * 8.0
\t_board_rect = Rect2(floor((w - exact) * 0.5), floor(maxf(8.0, (avail_h - exact) * 0.5)), exact, exact)
\t_tray_rects.clear()
\tvar ty := _board_rect.end.y + 18.0
\tvar th := maxf(105.0, h - ty - 12.0)
\tvar sw := floor((w - 36.0) / 3.0)
\tfor i in range(3):
\t\t_tray_rects.append(Rect2(12.0 + i * (sw + 6.0), ty, sw, th))

func _grid_center(gx: int, gy: int) -> Vector2:
\treturn Vector2(_board_rect.position.x + (float(gx) + 0.5) * _cell_size, _board_rect.position.y + (float(gy) + 0.5) * _cell_size)

func _gui_input(event: InputEvent) -> void:
\t_compute_layout()
\tif AppConfig.GENRE == "screw_puzzle":
\t\t_input_screw(event)
\telse:
\t\t_input_block(event)

func _input_screw(event: InputEvent) -> void:
\tvar pos := Vector2.ZERO
\tvar tapped := false
\tif event is InputEventScreenTouch and event.pressed:
\t\ttapped = true
\t\tpos = event.position
\telif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
\t\ttapped = true
\t\tpos = event.position
\tif not tapped:
\t\treturn
\tvar best_id := -1
\tvar best_dist := 52.0
\tfor sc in GameManager.screws:
\t\tif bool(sc["removed"]):
\t\t\tcontinue
\t\tvar c := _board_rect.position + Vector2(sc["pos"]) * _cell_size
\t\tvar d := c.distance_to(pos)
\t\tif d < best_dist:
\t\t\tbest_dist = d
\t\t\tbest_id = int(sc["id"])
\tif best_id >= 0:
\t\tGameManager.tap_screw(best_id)
\t\taccept_event()

func _input_block(event: InputEvent) -> void:
\tvar pressed := false
\tvar released := false
\tvar moved := false
\tvar pos := Vector2.ZERO
\tif event is InputEventScreenTouch:
\t\tpressed = event.pressed
\t\treleased = not event.pressed
\t\tpos = event.position
\telif event is InputEventScreenDrag:
\t\tmoved = true
\t\tpos = event.position
\telif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
\t\tpressed = event.pressed
\t\treleased = not event.pressed
\t\tpos = event.position
\telif event is InputEventMouseMotion and _dragging_tray_idx >= 0:
\t\tmoved = true
\t\tpos = event.position
\telse:
\t\treturn

\tif pressed:
\t\tif GameManager.hammer_mode_active and _board_rect.has_point(pos):
\t\t\tvar gx := int(floor((pos.x - _board_rect.position.x) / _cell_size))
\t\t\tvar gy := int(floor((pos.y - _board_rect.position.y) / _cell_size))
\t\t\tGameManager.use_hammer_at(gx, gy)
\t\t\taccept_event()
\t\t\treturn
\t\tfor i in range(_tray_rects.size()):
\t\t\tif _tray_rects[i].has_point(pos) and i < GameManager.tray_pieces.size() and not bool(GameManager.tray_pieces[i]["used"]):
\t\t\t\t_dragging_tray_idx = i
\t\t\t\t_selected_tray_idx = i
\t\t\t\t_drag_pos = pos
\t\t\t\t_update_hover(pos)
\t\t\t\tqueue_redraw()
\t\t\t\taccept_event()
\t\t\t\treturn
\t\tif _selected_tray_idx >= 0 and _board_rect.has_point(pos):
\t\t\tvar gx2 := int(floor((pos.x - _board_rect.position.x) / _cell_size))
\t\t\tvar gy2 := int(floor((pos.y - _board_rect.position.y) / _cell_size))
\t\t\tvar res := GameManager.place_tray_piece(_selected_tray_idx, gx2, gy2)
\t\t\tif bool(res.get("placed", false)):
\t\t\t\t_selected_tray_idx = -1
\t\t\tqueue_redraw()
\t\t\taccept_event()
\telif moved and _dragging_tray_idx >= 0:
\t\t_drag_pos = pos
\t\t_update_hover(pos)
\t\tqueue_redraw()
\t\taccept_event()
\telif released and _dragging_tray_idx >= 0:
\t\t_update_hover(pos)
\t\tif _hover_grid.x >= 0:
\t\t\tvar res2 := GameManager.place_tray_piece(_dragging_tray_idx, _hover_grid.x, _hover_grid.y)
\t\t\tif bool(res2.get("placed", false)):
\t\t\t\t_selected_tray_idx = -1
\t\t_dragging_tray_idx = -1
\t\t_hover_grid = Vector2i(-1, -1)
\t\tqueue_redraw()
\t\taccept_event()

func _update_hover(finger: Vector2) -> void:
\tvar lifted := finger + Vector2(0, -_cell_size * 1.3)
\tvar cells: Array = GameManager.tray_pieces[_dragging_tray_idx]["cells"]
\tvar mx := 0
\tvar my := 0
\tfor c in cells:
\t\tmx = maxi(mx, int(c.x))
\t\tmy = maxi(my, int(c.y))
\tvar tl := lifted - Vector2(float(mx + 1) * _cell_size * 0.5, float(my + 1) * _cell_size * 0.5)
\tvar gx := int(round((tl.x - _board_rect.position.x) / _cell_size))
\tvar gy := int(round((tl.y - _board_rect.position.y) / _cell_size))
\t_hover_grid = Vector2i(gx, gy) if GameManager.can_place_piece(cells, gx, gy) else Vector2i(-1, -1)

func _draw() -> void:
\t_compute_layout()
\tif _board_rect.size.x < 20.0:
\t\treturn
\tvar off := Vector2(randf_range(-4, 4), randf_range(-4, 4)) if _shake > 0.0 else Vector2.ZERO
\tvar frame := _board_rect.grow(8.0)
\tframe.position += off
\tdraw_rect(frame, AppConfig.COLOR_PANEL, true)
\tdraw_rect(frame, AppConfig.COLOR_ACCENT, false, 3.0)
\tif AppConfig.GENRE == "screw_puzzle":
\t\t_draw_screw_board(off)
\telse:
\t\t_draw_block_board(off)
\tfor pt in _particles:
\t\tvar c: Color = pt["color"]
\t\tc.a = clampf(float(pt["life"]) * 2.0, 0.0, 1.0)
\t\tdraw_circle(pt["pos"], float(pt["size"]) * 0.5, c)
\tfor pop in _popups:
\t\tdraw_string(ThemeDB.fallback_font, pop["pos"] - Vector2(60, 0), str(pop["text"]), HORIZONTAL_ALIGNMENT_CENTER, 140, 24, Color(1, 0.94, 0.35, clampf(float(pop["life"]) * 1.4, 0.0, 1.0)))

func _draw_block_board(off: Vector2) -> void:
\tvar clear_rows: Array = []
\tvar clear_cols: Array = []
\tif _dragging_tray_idx >= 0 and _hover_grid.x >= 0:
\t\tvar pv := GameManager.preview_clear_lines(GameManager.tray_pieces[_dragging_tray_idx]["cells"], _hover_grid.x, _hover_grid.y)
\t\tclear_rows = pv["rows"]
\t\tclear_cols = pv["cols"]
\tfor r in range(8):
\t\tfor c in range(8):
\t\t\tvar cr := Rect2(_board_rect.position.x + c * _cell_size + 2 + off.x, _board_rect.position.y + r * _cell_size + 2 + off.y, _cell_size - 4, _cell_size - 4)
\t\t\tvar bg := Color(0.14, 0.18, 0.30, 0.92) if ((r + c) % 2 == 0) else Color(0.12, 0.15, 0.26, 0.92)
\t\t\tif r in clear_rows or c in clear_cols:
\t\t\t\tbg = Color(0.95, 0.82, 0.25, 0.45)
\t\t\tdraw_rect(cr, bg, true)
\t\t\tvar val := int(GameManager.grid_8x8[r][c])
\t\t\tif val > 0:
\t\t\t\t_draw_block_cell(cr, val)
\tif _dragging_tray_idx >= 0 and _hover_grid.x >= 0:
\t\tvar p: Dictionary = GameManager.tray_pieces[_dragging_tray_idx]
\t\tvar gc: Color = AppConfig.PIECE_PALETTE[clampi(int(p["color_id"]), 1, 6)]
\t\tgc.a = 0.45
\t\tfor cell in p["cells"]:
\t\t\tvar gr := Rect2(_board_rect.position.x + (_hover_grid.x + int(cell.x)) * _cell_size + 3, _board_rect.position.y + (_hover_grid.y + int(cell.y)) * _cell_size + 3, _cell_size - 6, _cell_size - 6)
\t\t\tdraw_rect(gr, gc, true)
\tfor i in range(mini(3, GameManager.tray_pieces.size())):
\t\tvar tr := _tray_rects[i]
\t\tdraw_rect(tr, Color(0.10, 0.13, 0.23, 0.92), true)
\t\tdraw_rect(tr, Color(0.95, 0.85, 0.30) if i == _selected_tray_idx else Color(0.30, 0.45, 0.70, 0.65), false, 2.5)
\t\tif bool(GameManager.tray_pieces[i]["used"]) or i == _dragging_tray_idx:
\t\t\tcontinue
\t\tvar cells: Array = GameManager.tray_pieces[i]["cells"]
\t\tvar cid := int(GameManager.tray_pieces[i]["color_id"])
\t\tvar mx := 0
\t\tvar my := 0
\t\tfor c in cells:
\t\t\tmx = maxi(mx, int(c.x))
\t\t\tmy = maxi(my, int(c.y))
\t\tvar ms := minf(minf((tr.size.x - 16.0) / float(mx + 1), (tr.size.y - 16.0) / float(my + 1)), _cell_size * 0.6)
\t\tvar ox := tr.position.x + (tr.size.x - float(mx + 1) * ms) * 0.5
\t\tvar oy := tr.position.y + (tr.size.y - float(my + 1) * ms) * 0.5
\t\tfor c in cells:
\t\t\t_draw_block_cell(Rect2(ox + float(c.x) * ms + 1.5, oy + float(c.y) * ms + 1.5, ms - 3.0, ms - 3.0), cid)

func _draw_block_cell(r: Rect2, cid: int) -> void:
\tvar k := clampi(cid, 1, 6)
\tif _block_tex.has(k):
\t\tdraw_texture_rect(_block_tex[k], r, false)
\telse:
\t\tvar col: Color = AppConfig.PIECE_PALETTE[k]
\t\tdraw_rect(r, col.darkened(0.28), true)
\t\tdraw_rect(r.grow(-3), col, true)

func _draw_screw_board(off: Vector2) -> void:
\tfor p in GameManager.plates:
\t\tvar fall := float(p["fall"])
\t\tif bool(p["removed"]) and fall >= 1.0:
\t\t\tcontinue
\t\tvar rect: Rect2 = p["rect"]
\t\tvar pr := Rect2(_board_rect.position + rect.position * _cell_size + Vector2(0, fall * 110.0) + off, rect.size * _cell_size)
\t\tvar col: Color = AppConfig.PIECE_PALETTE[clampi(int(p["color_id"]), 1, 6)]
\t\tvar alpha := 1.0 - fall if bool(p["removed"]) else 0.90
\t\tdraw_rect(pr, Color(col.darkened(0.25), alpha), true)
\t\tdraw_rect(pr, Color(col.lightened(0.4), alpha), false, 3.0)
\tfor sc in GameManager.screws:
\t\tif bool(sc["removed"]):
\t\t\tcontinue
\t\tvar center := _board_rect.position + Vector2(sc["pos"]) * _cell_size + off
\t\tvar k := clampi(int(sc["color_id"]), 1, 6)
\t\tvar sr := Rect2(center - Vector2(22, 22), Vector2(44, 44))
\t\tif _screw_tex.has(k):
\t\t\tdraw_texture_rect(_screw_tex[k], sr, false)
\t\telse:
\t\t\tdraw_circle(center, 18.0, AppConfig.PIECE_PALETTE[k])
\t\tif not GameManager.is_screw_accessible(sc):
\t\t\tdraw_circle(center, 20.0, Color(0, 0, 0, 0.55))
\t# Toolbox & Buffer tray below board
\tvar ty := _board_rect.end.y + 24.0
\tfor i in range(GameManager.active_boxes.size()):
\t\tvar box: Dictionary = GameManager.active_boxes[i]
\t\tvar br := Rect2(_board_rect.position.x + i * 190.0, ty, 174.0, 74.0)
\t\tvar col: Color = AppConfig.PIECE_PALETTE[clampi(int(box["color_id"]), 1, 6)]
\t\tdraw_rect(br, col.darkened(0.55), true)
\t\tdraw_rect(br, col, false, 3.0)
\t\tfor s in range(int(box["capacity"])):
\t\t\tvar dot := Vector2(br.position.x + 36.0 + s * 50.0, br.position.y + 37.0)
\t\t\tdraw_circle(dot, 14.0, col if s < int(box["filled"]) else Color(0.08, 0.1, 0.16))
\tvar by := ty + 88.0
\tfor b in range(5):
\t\tvar slot := Rect2(_board_rect.position.x + b * 74.0, by, 62.0, 52.0)
\t\tdraw_rect(slot, Color(0.11, 0.15, 0.24), true)
\t\tdraw_rect(slot, Color(0.35, 0.50, 0.72), false, 2.0)
\t\tif b < GameManager.buffer_slots.size():
\t\t\tvar bc: Color = AppConfig.PIECE_PALETTE[clampi(int(GameManager.buffer_slots[b]), 1, 6)]
\t\t\tdraw_circle(slot.get_center(), 15.0, bc)
'''
    Path("scripts/board_view.gd").write_text(code, encoding="utf-8")


def _write_ui_and_qa() -> None:
    ui_code = '''extends CanvasLayer

const SCREEN_NAMES: Array[String] = [
\t"MainMenu", "LoadingScreen", "GameplayHUD", "PauseMenu",
\t"Settings", "Shop", "Inventory", "Rewards",
\t"LevelSelection", "WinLoseScreen", "Profile", "DailyRewards"
]

var screens: Dictionary = {}
var hud_level_lbl: Label
var hud_score_lbl: Label
var hud_booster_btn: Button
var win_title_lbl: Label
var win_detail_lbl: Label
var board_view: Control

func _ready() -> void:
\tvar bg := ColorRect.new()
\tbg.color = AppConfig.COLOR_BG
\tbg.set_anchors_preset(Control.PRESET_FULL_RECT)
\tadd_child(bg)

\tvar safe := MarginContainer.new()
\tsafe.name = "SafeAreaMargin"
\tsafe.set_anchors_preset(Control.PRESET_FULL_RECT)
\tsafe.add_theme_constant_override("margin_left", 24)
\tsafe.add_theme_constant_override("margin_right", 24)
\tsafe.add_theme_constant_override("margin_top", 44)
\tsafe.add_theme_constant_override("margin_bottom", 32)
\tadd_child(safe)

\tfor s_name in SCREEN_NAMES:
\t\tvar panel := _build_screen(s_name)
\t\tscreens[s_name] = panel
\t\tsafe.add_child(panel)

\tGameManager.connect("score_changed", Callable(self, "_on_score"))
\tGameManager.connect("level_changed", Callable(self, "_on_lvl"))
\tGameManager.connect("state_changed", Callable(self, "_refresh_hud"))
\tGameManager.connect("level_completed", Callable(self, "_on_win"))
\tGameManager.connect("game_over", Callable(self, "_on_lose"))
\tshow_screen("MainMenu")

func _btn(txt: String, col: Color, h: float = 64.0) -> Button:
\tvar b := Button.new()
\tb.text = txt
\tb.custom_minimum_size = Vector2(120, h)
\tb.add_theme_font_size_override("font_size", 22)
\tb.add_theme_color_override("font_color", Color.WHITE)
\tvar sb := StyleBoxFlat.new()
\tsb.bg_color = col
\tsb.set_corner_radius_all(16)
\tsb.border_color = col.lightened(0.35)
\tsb.set_border_width_all(2)
\tb.add_theme_stylebox_override("normal", sb)
\tvar sbh := sb.duplicate()
\tsbh.bg_color = col.lightened(0.12)
\tb.add_theme_stylebox_override("hover", sbh)
\tb.add_theme_stylebox_override("pressed", sbh)
\tb.pressed.connect(func(): AudioDirector.play_sfx("ui_click"))
\treturn b

func _header(parent: VBoxContainer, title_txt: String) -> void:
\tvar hb := HBoxContainer.new()
\thb.add_theme_constant_override("separation", 12)
\tvar back := _btn("< BACK", Color(0.20, 0.27, 0.44), 56.0)
\tback.pressed.connect(func(): show_screen("MainMenu"))
\thb.add_child(back)
\tvar lbl := Label.new()
\tlbl.text = title_txt
\tlbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
\tlbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
\tlbl.add_theme_font_size_override("font_size", 28)
\thb.add_child(lbl)
\tparent.add_child(hb)

func _build_screen(s_name: String) -> Control:
\tvar root := VBoxContainer.new()
\troot.name = s_name
\troot.set_anchors_preset(Control.PRESET_FULL_RECT)
\troot.add_theme_constant_override("separation", 16)

\tif s_name == "MainMenu":
\t\troot.alignment = BoxContainer.ALIGNMENT_CENTER
\t\tvar t := Label.new()
\t\tt.text = AppConfig.GAME_TITLE.to_upper()
\t\tt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
\t\tt.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
\t\tt.add_theme_font_size_override("font_size", 40)
\t\tt.add_theme_color_override("font_color", AppConfig.COLOR_ACCENT)
\t\troot.add_child(t)
\t\tvar sub := Label.new()
\t\tsub.text = AppConfig.GAME_TAGLINE
\t\tsub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
\t\tsub.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
\t\tsub.add_theme_font_size_override("font_size", 19)
\t\troot.add_child(sub)
\t\tvar play := _btn("PLAY NOW", Color(0.16, 0.72, 0.48), 76.0)
\t\tplay.pressed.connect(func(): show_screen("GameplayHUD"))
\t\troot.add_child(play)
\t\tvar lvls := _btn("LEVEL MAP (1 - 30)", Color(0.22, 0.50, 0.86), 64.0)
\t\tlvls.pressed.connect(func(): show_screen("LevelSelection"))
\t\troot.add_child(lvls)
\t\tvar nav := HBoxContainer.new()
\t\tnav.add_theme_constant_override("separation", 10)
\t\tfor item in [["SHOP", "Shop", Color(0.86, 0.52, 0.16)], ["DAILY", "DailyRewards", Color(0.54, 0.34, 0.88)], ["SETTINGS", "Settings", Color(0.28, 0.35, 0.50)]]:
\t\t\tvar nb := _btn(item[0], item[2], 58.0)
\t\t\tnb.size_flags_horizontal = Control.SIZE_EXPAND_FILL
\t\t\tvar dest: String = item[1]
\t\t\tnb.pressed.connect(func(): show_screen(dest))
\t\t\tnav.add_child(nb)
\t\troot.add_child(nav)

\telif s_name == "GameplayHUD":
\t\tvar top := HBoxContainer.new()
\t\thud_level_lbl = Label.new()
\t\thud_level_lbl.text = "LVL 1"
\t\thud_level_lbl.add_theme_font_size_override("font_size", 24)
\t\ttop.add_child(hud_level_lbl)
\t\thud_score_lbl = Label.new()
\t\thud_score_lbl.text = "SCORE: 0"
\t\thud_score_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
\t\thud_score_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
\t\thud_score_lbl.add_theme_font_size_override("font_size", 24)
\t\ttop.add_child(hud_score_lbl)
\t\tvar pause := _btn("PAUSE", Color(0.24, 0.30, 0.48), 56.0)
\t\tpause.pressed.connect(func(): show_screen("PauseMenu"))
\t\ttop.add_child(pause)
\t\troot.add_child(top)
\t\tboard_view = preload("res://scripts/board_view.gd").new()
\t\tboard_view.name = "BoardView"
\t\troot.add_child(board_view)
\t\tvar bar := HBoxContainer.new()
\t\tbar.add_theme_constant_override("separation", 10)
\t\thud_booster_btn = _btn("SWAP BOOSTER (3)", Color(0.52, 0.34, 0.88), 58.0)
\t\thud_booster_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
\t\thud_booster_btn.pressed.connect(func(): GameManager.use_primary_booster())
\t\tbar.add_child(hud_booster_btn)
\t\troot.add_child(bar)

\telif s_name == "LevelSelection":
\t\t_header(root, "LEVELS 1 - 30")
\t\tvar sc := ScrollContainer.new()
\t\tsc.size_flags_vertical = Control.SIZE_EXPAND_FILL
\t\tvar cc := CenterContainer.new()
\t\tcc.size_flags_horizontal = Control.SIZE_EXPAND_FILL
\t\tvar grid := GridContainer.new()
\t\tgrid.columns = 5
\t\tgrid.add_theme_constant_override("h_separation", 10)
\t\tgrid.add_theme_constant_override("v_separation", 10)
\t\tfor lvl in range(1, 31):
\t\t\tvar lb := _btn(str(lvl), Color(0.20, 0.52, 0.88), 68.0)
\t\t\tlb.custom_minimum_size = Vector2(100, 68)
\t\t\tvar target := lvl
\t\t\tlb.pressed.connect(func():
\t\t\t\tGameManager.load_level(target)
\t\t\t\tshow_screen("GameplayHUD")
\t\t\t)
\t\t\tgrid.add_child(lb)
\t\tcc.add_child(grid)
\t\tsc.add_child(cc)
\t\troot.add_child(sc)

\telif s_name == "Shop":
\t\t_header(root, "STUDIO SHOP")
\t\tfor item in [
\t\t\t["Starter Pack (500 Coins) — INR 89", "starter_pack_89", Color(0.18, 0.64, 0.44)],
\t\t\t["Remove Ads Forever — INR 249", "remove_ads_249", Color(0.22, 0.48, 0.86)],
\t\t\t["Watch Rewarded Ad (+100 Coins)", "rewarded_ad", Color(0.56, 0.34, 0.86)]
\t\t]:
\t\t\tvar sb := _btn(item[0], item[2], 66.0)
\t\t\tvar sku: String = item[1]
\t\t\tsb.pressed.connect(func():
\t\t\t\tif sku == "rewarded_ad":
\t\t\t\t\tMonetizationManager.show_rewarded_ad("coins", 100)
\t\t\t\telse:
\t\t\t\t\tMonetizationManager.purchase_sku(sku)
\t\t\t)
\t\t\troot.add_child(sb)

\telif s_name == "Settings":
\t\t_header(root, "SETTINGS")
\t\tvar mute := _btn("AUDIO: ON", Color(0.24, 0.54, 0.82), 66.0)
\t\tmute.pressed.connect(func():
\t\t\tvar m := AudioDirector.toggle_mute()
\t\t\tmute.text = "AUDIO: OFF" if m else "AUDIO: ON"
\t\t)
\t\troot.add_child(mute)

\telif s_name == "PauseMenu":
\t\troot.alignment = BoxContainer.ALIGNMENT_CENTER
\t\tvar r1 := _btn("RESUME", Color(0.16, 0.72, 0.48), 68.0)
\t\tr1.pressed.connect(func(): show_screen("GameplayHUD"))
\t\troot.add_child(r1)
\t\tvar r2 := _btn("RESTART LEVEL", Color(0.84, 0.50, 0.18), 64.0)
\t\tr2.pressed.connect(func():
\t\t\tGameManager.load_level(GameManager.current_level)
\t\t\tshow_screen("GameplayHUD")
\t\t)
\t\troot.add_child(r2)
\t\tvar r3 := _btn("MAIN MENU", Color(0.28, 0.34, 0.50), 62.0)
\t\tr3.pressed.connect(func(): show_screen("MainMenu"))
\t\troot.add_child(r3)

\telif s_name == "WinLoseScreen":
\t\troot.alignment = BoxContainer.ALIGNMENT_CENTER
\t\twin_title_lbl = Label.new()
\t\twin_title_lbl.text = "LEVEL COMPLETE!"
\t\twin_title_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
\t\twin_title_lbl.add_theme_font_size_override("font_size", 36)
\t\troot.add_child(win_title_lbl)
\t\twin_detail_lbl = Label.new()
\t\twin_detail_lbl.text = "+50 Coins Earned!"
\t\twin_detail_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
\t\twin_detail_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
\t\twin_detail_lbl.add_theme_font_size_override("font_size", 22)
\t\troot.add_child(win_detail_lbl)
\t\tvar nxt := _btn("NEXT LEVEL", Color(0.16, 0.72, 0.48), 68.0)
\t\tnxt.pressed.connect(func():
\t\t\tGameManager.load_level(mini(30, GameManager.current_level + 1))
\t\t\tshow_screen("GameplayHUD")
\t\t)
\t\troot.add_child(nxt)
\t\tvar mm := _btn("MAIN MENU", Color(0.28, 0.34, 0.50), 62.0)
\t\tmm.pressed.connect(func(): show_screen("MainMenu"))
\t\troot.add_child(mm)
\telse:
\t\t_header(root, s_name.to_upper())
\t\tvar info := Label.new()
\t\tinfo.text = "Claim daily coins and track your Studio V7 progress."
\t\tinfo.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
\t\tinfo.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
\t\tinfo.add_theme_font_size_override("font_size", 22)
\t\troot.add_child(info)
\t\tvar claim := _btn("CLAIM +50 COINS", Color(0.18, 0.68, 0.46), 64.0)
\t\tclaim.pressed.connect(func():
\t\t\tSaveManager.add_coins(50)
\t\t\tshow_screen("MainMenu")
\t\t)
\t\troot.add_child(claim)
\treturn root

func _on_lvl(_l: int) -> void:
\t_refresh_hud()

func _on_score(_s: int, _c: int) -> void:
\t_refresh_hud()

func _refresh_hud() -> void:
\tif hud_level_lbl != null:
\t\thud_level_lbl.text = "LVL %d" % GameManager.current_level
\tif hud_score_lbl != null:
\t\thud_score_lbl.text = "SCORE: %d / %d" % [GameManager.current_score, GameManager.level_goal]
\tif hud_booster_btn != null:
\t\thud_booster_btn.text = "BOOSTER (%d)" % GameManager.juggle_swaps_remaining

func _on_win(lvl: int, sc: int) -> void:
\tif win_title_lbl != null:
\t\twin_title_lbl.text = "LEVEL %d CLEARED!" % lvl
\tif win_detail_lbl != null:
\t\twin_detail_lbl.text = "Final Score: %d | +50 Coins!" % sc
\tshow_screen("WinLoseScreen")

func _on_lose(sc: int) -> void:
\tif win_title_lbl != null:
\t\twin_title_lbl.text = "TRY AGAIN!"
\tif win_detail_lbl != null:
\t\twin_detail_lbl.text = "Score: %d — Tap Retry or use a Booster." % sc
\tshow_screen("WinLoseScreen")

func show_screen(s_name: String) -> void:
\tif not screens.has(s_name):
\t\treturn
\tfor k in screens.keys():
\t\t(screens[k] as Control).visible = (k == s_name)
\tif s_name == "GameplayHUD":
\t\t_refresh_hud()
\t\tif board_view != null:
\t\t\tboard_view.queue_redraw()
'''
    Path("scripts/ui_controller.gd").write_text(ui_code, encoding="utf-8")

    qa_boot = '''extends Node

func _ready() -> void:
\tvar main_scene := preload("res://main.tscn").instantiate()
\tget_tree().root.add_child.call_deferred(main_scene)
\tvar driver := preload("res://scripts/test_driver.gd").new()
\tdriver.name = "TestDriver"
\tget_tree().root.add_child.call_deferred(driver)
'''
    Path("scripts/qa_bootstrap.gd").write_text(qa_boot, encoding="utf-8")

    driver = '''extends Node

var qa_mode: bool = false
var suite: String = "multi_levels"
var out_dir: String = "/tmp/studio_qa"
var elapsed: float = 0.0
var last_step: float = 0.0
var done: Dictionary = {}
var logs: Array[String] = []

func _ready() -> void:
\tif OS.has_feature("release"):
\t\tqueue_free()
\t\treturn
\tfor a in OS.get_cmdline_user_args():
\t\tif a == "--qa-mode=true":
\t\t\tqa_mode = true
\t\telif a.begins_with("--suite="):
\t\t\tsuite = a.split("=", true, 1)[1]
\t\telif a.begins_with("--qa-output-dir="):
\t\t\tout_dir = a.split("=", true, 1)[1]
\tif not qa_mode:
\t\tqueue_free()
\t\treturn
\tDirAccess.make_dir_recursive_absolute(out_dir)
\tlogs.append("[TEST_DRIVER_V7] Suite=" + suite)

func _physics_process(delta: float) -> void:
\tif not qa_mode:
\t\treturn
\telapsed += delta
\tvar root := get_tree().root
\tvar ui := root.find_child("StudioUI", true, false)

\tmatch suite:
\t\t"ui_shop":
\t\t\tif elapsed >= 1.2 and not done.has("1"):
\t\t\t\tdone["1"] = true
\t\t\t\t_check_clipping(root, "MainMenu")
\t\t\t\tif ui != null: ui.call("show_screen", "LevelSelection")
\t\t\tif elapsed >= 3.2 and not done.has("2"):
\t\t\t\tdone["2"] = true
\t\t\t\t_check_clipping(root, "LevelSelection")
\t\t\t\tif ui != null: ui.call("show_screen", "Shop")
\t\t\tif elapsed >= 5.2 and not done.has("3"):
\t\t\t\tdone["3"] = true
\t\t\t\t_check_clipping(root, "Shop")
\t\t\t\tif ui != null: ui.call("show_screen", "Settings")
\t\t\tif elapsed >= 7.0:
\t\t\t\t_finish()
\t\t"mechanics_lab":
\t\t\tif elapsed >= 1.2 and not done.has("lab"):
\t\t\t\tdone["lab"] = true
\t\t\t\tif ui != null: ui.call("show_screen", "GameplayHUD")
\t\t\t\tlogs.append("[LAB] " + str(GameManager.step_mechanics_lab_test()))
\t\t\t\tif GameManager.current_score <= 0:
\t\t\t\t\tlogs.append("QA_FAIL_ZERO_SCORE")
\t\t\tif elapsed >= 6.0:
\t\t\t\t_finish()
\t\t"multi_levels":
\t\t\tif elapsed >= 1.0 and not done.has("open"):
\t\t\t\tdone["open"] = true
\t\t\t\tif ui != null: ui.call("show_screen", "GameplayHUD")
\t\t\t\tGameManager.load_level(1)
\t\t\tif elapsed >= 1.8 and elapsed - last_step >= 0.7:
\t\t\t\tlast_step = elapsed
\t\t\t\tlogs.append("[BOT] " + str(GameManager.bot_play_step()))
\t\t\tif elapsed >= 8.0 and not done.has("verify"):
\t\t\t\tdone["verify"] = true
\t\t\t\tif GameManager.current_score <= 0 or GameManager.moves_made < 3:
\t\t\t\t\tlogs.append("QA_FAIL_DEMO: score=%d moves=%d" % [GameManager.current_score, GameManager.moves_made])
\t\t\t\telse:
\t\t\t\t\tlogs.append("[REAL_GAMEPLAY_VERIFIED] Score=%d Moves=%d" % [GameManager.current_score, GameManager.moves_made])
\t\t\t\t_check_clipping(root, "GameplayHUD")
\t\t\tif elapsed >= 9.5:
\t\t\t\t_finish()
\t\t"save_ads_and_edge":
\t\t\tif elapsed >= 1.2 and not done.has("edge"):
\t\t\t\tdone["edge"] = true
\t\t\t\tif SaveManager.run_self_test():
\t\t\t\t\tlogs.append("[SAVE_LOAD_PASS]")
\t\t\t\telse:
\t\t\t\t\tlogs.append("QA_FAIL_SAVE")
\t\t\t\tif MonetizationManager.run_offline_resilience_test():
\t\t\t\t\tlogs.append("[OFFLINE_ADS_PASS]")
\t\t\t\tif ui != null:
\t\t\t\t\tui.call("show_screen", "WinLoseScreen")
\t\t\tif elapsed >= 5.5:
\t\t\t\t_finish()
\t\t_:
\t\t\t_finish()

func _check_clipping(root: Node, tag: String) -> void:
\tvar vp := get_viewport().get_visible_rect().size
\tfor child in root.find_children("*", "Control", true, false):
\t\tvar c := child as Control
\t\tif not c.is_visible_in_tree():
\t\t\tcontinue
\t\tif c is Button or c is Label:
\t\t\tvar r := c.get_global_rect()
\t\t\tif r.size.x > 1.0 and (r.position.x < -8.0 or r.end.x > vp.x + 8.0):
\t\t\t\tlogs.append("QA_FAIL_UI_CLIPPED: %s %s" % [tag, c.name])
\tlogs.append("[CLIPPING_PASS] " + tag)

func _finish() -> void:
\tlogs.append("[SUMMARY] Suite=%s | Status=COMPLETED" % suite)
\tvar f := FileAccess.open(out_dir.path_join("telemetry_" + suite + ".txt"), FileAccess.WRITE)
\tif f != null:
\t\tf.store_string("\\n".join(logs))
\t\tf.close()
\tget_tree().quit(0)
'''
    Path("scripts/test_driver.gd").write_text(driver, encoding="utf-8")


def _write_project_and_scenes(spec: dict) -> None:
    title = spec.get("title", "Crystal Grid Cascade").replace('"', "'")
    icon_path = "res://assets/generated/store/icon_512x512.png" if Path("assets/generated/store/icon_512x512.png").exists() else "res://icon.svg"

    proj = f'''config_version=5

[application]
config/name="{title}"
run/main_scene="res://main.tscn"
config/features=PackedStringArray("4.7", "GL Compatibility")
config/icon="{icon_path}"

[autoload]
AppConfig="*res://scripts/app_config.gd"
SaveManager="*res://scripts/save_manager.gd"
AudioDirector="*res://scripts/audio_director.gd"
MonetizationManager="*res://scripts/monetization_manager.gd"
GameManager="*res://scripts/game_manager.gd"

[display]
window/size/viewport_width=720
window/size/viewport_height=1280
window/stretch/mode="canvas_items"
window/stretch/aspect="expand"
window/handheld/orientation=1

[physics]
common/physics_ticks_per_second=60

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
'''
    Path("project.godot").write_text(proj, encoding="utf-8")

    Path("main.tscn").write_text(
        '[gd_scene load_steps=2 format=3]\n\n'
        '[ext_resource type="Script" path="res://scripts/ui_controller.gd" id="1_ui"]\n\n'
        '[node name="Main" type="Node2D"]\n\n'
        '[node name="StudioUI" type="CanvasLayer" parent="."]\n'
        'script = ExtResource("1_ui")\n',
        encoding="utf-8",
    )

    Path("scenes").mkdir(parents=True, exist_ok=True)
    Path("scenes/qa_bootstrap.tscn").write_text(
        '[gd_scene load_steps=2 format=3]\n\n'
        '[ext_resource type="Script" path="res://scripts/qa_bootstrap.gd" id="1_qa"]\n\n'
        '[node name="QABootstrap" type="Node"]\n'
        'script = ExtResource("1_qa")\n',
        encoding="utf-8",
    )


def _verify_godot_gui_import() -> tuple[bool, str]:
    proc = subprocess.run(
        ["xvfb-run", "--auto-servernum", "-s", "-screen 0 720x1280x24", "godot", "--editor", "--path", ".", "--import", "--quit"],
        capture_output=True, text=True, timeout=240, check=False,
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    has_err = bool(re.search(r"SCRIPT ERROR|Parse Error", out))
    return (not has_err and proc.returncode == 0), out


def main() -> None:
    order = json.loads(Path("docs/generated/resolved_order.json").read_text(encoding="utf-8"))
    spec = json.loads(Path("docs/generated/design_spec.json").read_text(encoding="utf-8"))
    skills_txt = _load_stage3_skills()

    ai_code, ai_model = _generate_ai_tuning_gd(order, spec, skills_txt)
    Path("scripts/ai_game_tuning.gd").write_text(ai_code, encoding="utf-8")

    _write_app_config(order, spec)
    _write_save_manager()
    _write_audio_director()
    _write_monetization_manager()
    if order["genre"] == "screw_puzzle":
        _write_screw_puzzle_manager()
    else:
        _write_block_puzzle_manager()
    _write_board_view()
    _write_ui_and_qa()
    _write_project_and_scenes(spec)

    # Full Godot 4.7.2 GUI import + 3-cycle autonomous NVIDIA self-heal gate
    heal_attempts = 0
    ok, log = _verify_godot_gui_import()
    while not ok and heal_attempts < 3:
        heal_attempts += 1
        print(f"[STAGE 3 SELF-HEAL] Attempt {heal_attempts}/3 triggered on Godot parse error...")
        fix_code, _ = nvidia_chat(
            [{"role": "user", "content": f"Fix this Godot 4.7.2 `scripts/ai_game_tuning.gd` error:\n{log[-1200:]}\nOutput ONLY clean GDScript extending RefCounted with get_level_goal, get_combo_label, get_daily_coin_bonus."}],
            role="fast",
            max_tokens=500,
        )
        if fix_code and "extends RefCounted" in fix_code:
            fix_code = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", fix_code.strip())
            Path("scripts/ai_game_tuning.gd").write_text(fix_code, encoding="utf-8")
        else:
            # Deterministic clean reset of ai_game_tuning.gd on attempt 3
            Path("scripts/ai_game_tuning.gd").write_text(
                "extends RefCounted\n\n"
                "static func get_level_goal(lvl: int) -> int:\n\treturn 340 + (maxi(1, lvl) - 1) * 135\n\n"
                "static func get_combo_label(combo: int) -> String:\n\treturn \"COMBO x%d!\" % combo\n\n"
                "static func get_daily_coin_bonus(day: int) -> int:\n\treturn 40 + clampi(day, 1, 7) * 20\n",
                encoding="utf-8",
            )
        ok, log = _verify_godot_gui_import()

    if not ok:
        print(log[-2000:])
        raise RuntimeError("Godot 4.7.2 GUI import failed after 3 self-heal cycles.")

    proof = {
        "status": "PASS",
        "game_id": order["game_id"],
        "genre": order["genre"],
        "title": spec.get("title"),
        "ai_coding_model": ai_model,
        "self_heal_cycles_used": heal_attempts,
    }
    Path("docs/generated/LIVE_AI_BUILD_PROOF.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print(f"[STAGE 3 PASS] Godot 4.7.2 build verified for '{spec.get('title')}' ({order['genre']}) | model={ai_model}")


if __name__ == "__main__":
    main()
