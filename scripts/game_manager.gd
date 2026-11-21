extends Node

# ==============================================================================
# COMPLETE PLAYABLE STUDIO GAME MANAGER (V5.0 — CRYSTAL GRID CASCADE 8x8 + 3D HYBRID)
# - Implements full 8x8 Crystal Grid Cascade Clean-Room board (`grid_8x8`), 3-piece spawn
#   tray (`tray_pieces`), Juggle/Hold swap slot (`juggle_hold_piece`), row & column
#   line-clear engine (`clear_completed_rows_and_cols`), and Hammer smash booster.
# - Supports 30 distinct progressive levels (`load_level(1..30)` including
#   QA milestones 1, 3, 6, 8, 10, 16, 30).
# - Supports 5 modular Endless map chunks + stitched seam verification.
# - Implements multi-hit armored crystal blocks/targets (`hits_required = 4`:
#   intact -> crack_1 -> crack_2 -> crack_3 -> popped on 4th hit!).
# - Never hijacks player controls in production; only responds to user input
#   or explicit CI test hooks (`bot_play_step`, `step_mechanics_lab_test`).
# ==============================================================================

signal level_changed(new_level: int)
signal score_changed(new_score: int, combo: int)
signal board_updated(lines_cleared: int)
signal screen_requested(screen_name: String)

const BOARD_SIZE: int = 8
const PIECE_SHAPES: Array = [
	[Vector2i(0, 0)],
	[Vector2i(0, 0), Vector2i(1, 0)],
	[Vector2i(0, 0), Vector2i(1, 0), Vector2i(2, 0)],
	[Vector2i(0, 0), Vector2i(0, 1), Vector2i(0, 2)],
	[Vector2i(0, 0), Vector2i(1, 0), Vector2i(0, 1), Vector2i(1, 1)],
	[Vector2i(0, 0), Vector2i(1, 0), Vector2i(2, 0), Vector2i(0, 1)],
	[Vector2i(0, 0), Vector2i(1, 0), Vector2i(2, 0), Vector2i(1, 1)],
	[Vector2i(0, 0), Vector2i(1, 0), Vector2i(2, 0), Vector2i(3, 0)]
]

var current_level: int = 1
var current_score: int = 0
var current_combo: int = 1
var grid_8x8: Array = []
var tray_pieces: Array = []
var juggle_hold_piece: Array = []
var juggle_swaps_remaining: int = 3
var hammer_boosters_remaining: int = 3
var active_targets: Array[Node3D] = []
var active_chunks: Array[Node3D] = []
var lab_target: Node3D = null

func _ready() -> void:
	_init_empty_board()
	_refill_tray_pieces()

func _init_empty_board() -> void:
	grid_8x8.clear()
	for r in range(BOARD_SIZE):
		var row: Array = []
		for c in range(BOARD_SIZE):
			row.append(0)
		grid_8x8.append(row)

func _refill_tray_pieces() -> void:
	tray_pieces.clear()
	for i in range(3):
		var shape_idx: int = (current_level + i) % PIECE_SHAPES.size()
		tray_pieces.append(PIECE_SHAPES[shape_idx])

func can_place_piece(shape: Array, gx: int, gy: int) -> bool:
	if grid_8x8.size() != BOARD_SIZE:
		_init_empty_board()
	for cell in shape:
		var v: Vector2i = cell
		var tx: int = gx + v.x
		var ty: int = gy + v.y
		if tx < 0 or tx >= BOARD_SIZE or ty < 0 or ty >= BOARD_SIZE:
			return false
		if int(grid_8x8[ty][tx]) != 0:
			return false
	return true

func place_piece_on_board(shape: Array, gx: int, gy: int) -> Dictionary:
	if not can_place_piece(shape, gx, gy):
		return {"placed": false, "lines_cleared": 0, "score_gained": 0}
	for cell in shape:
		var v: Vector2i = cell
		grid_8x8[gy + v.y][gx + v.x] = 1
	var cleared: int = clear_completed_rows_and_cols()
	var pts: int = shape.size() * 10
	if cleared > 0:
		current_combo = mini(8, current_combo + 1)
		pts += cleared * cleared * 120 * current_combo
	else:
		current_combo = 1
	current_score += pts
	emit_signal("score_changed", current_score, current_combo)
	emit_signal("board_updated", cleared)
	var vfx := get_node_or_null("/root/StudioThemeAndVFX")
	var cam := get_tree().root.get_node_or_null("Main/Camera3D") as Camera3D
	if cleared > 0 and vfx != null and cam != null:
		vfx.call("pulse_camera_feedback", cam, 0.08)
	return {"placed": true, "lines_cleared": cleared, "score_gained": pts}

func clear_completed_rows_and_cols() -> int:
	var full_rows: Array[int] = []
	var full_cols: Array[int] = []
	for r in range(BOARD_SIZE):
		var row_full: bool = true
		for c in range(BOARD_SIZE):
			if int(grid_8x8[r][c]) == 0:
				row_full = false
				break
		if row_full:
			full_rows.append(r)

	for c in range(BOARD_SIZE):
		var col_full: bool = true
		for r in range(BOARD_SIZE):
			if int(grid_8x8[r][c]) == 0:
				col_full = false
				break
		if col_full:
			full_cols.append(c)

	for r in full_rows:
		for c in range(BOARD_SIZE):
			grid_8x8[r][c] = 0
	for c in full_cols:
		for r in range(BOARD_SIZE):
			grid_8x8[r][c] = 0

	return full_rows.size() + full_cols.size()

func use_juggle_swap(tray_idx: int = 0) -> bool:
	if tray_idx < 0 or tray_idx >= tray_pieces.size() or juggle_swaps_remaining <= 0:
		return false
	juggle_swaps_remaining -= 1
	var current_piece: Array = tray_pieces[tray_idx]
	if juggle_hold_piece.is_empty():
		juggle_hold_piece = current_piece
		tray_pieces[tray_idx] = PIECE_SHAPES[0]
	else:
		var tmp: Array = juggle_hold_piece
		juggle_hold_piece = current_piece
		tray_pieces[tray_idx] = tmp
	return true

func use_hammer_booster(gx: int, gy: int) -> bool:
	if hammer_boosters_remaining <= 0:
		return false
	if gx >= 0 and gx < BOARD_SIZE and gy >= 0 and gy < BOARD_SIZE:
		hammer_boosters_remaining -= 1
		grid_8x8[gy][gx] = 0
		return true
	return false

func load_level(lvl_num: int) -> void:
	current_level = clampi(lvl_num, 1, 30)
	_init_empty_board()
	_refill_tray_pieces()

	# Pre-seed progressive pattern on 8x8 board based on level (1..30)
	var prefill_cells: int = mini(20, (current_level - 1) * 2)
	for i in range(prefill_cells):
		var rx: int = (i * 3 + current_level) % BOARD_SIZE
		var ry: int = (i * 5 + current_level) % BOARD_SIZE
		grid_8x8[ry][rx] = 1

	var world := get_tree().root.get_node_or_null("Main/WorldRoot") as Node3D
	if world == null:
		emit_signal("level_changed", current_level)
		return
	_clear_children(world)

	# Build distinct 3D jewel-block & armored crystal layout for levels 1..30
	var target_count: int = 6 + mini(18, current_level)
	var multi_hit_hp: int = 1
	if current_level >= 3:
		multi_hit_hp = 3
	if current_level >= 6:
		multi_hit_hp = 4

	for i in range(target_count):
		var hp: int = multi_hit_hp if (i % 2 == 0 and current_level >= 3) else 1
		var pos := Vector3((i % 4 - 1.5) * 1.6, 1.0 + int(i / 4) * 0.95, -6.0 - float(current_level % 8) * 0.35)
		var t := _spawn_destructible_target(world, pos, hp, i)
		active_targets.append(t)

	emit_signal("level_changed", current_level)

func bot_play_step() -> String:
	if tray_pieces.is_empty():
		_refill_tray_pieces()
	var shape: Array = tray_pieces[0]
	for r in range(BOARD_SIZE):
		for c in range(BOARD_SIZE):
			if can_place_piece(shape, c, r):
				var res := place_piece_on_board(shape, c, r)
				tray_pieces.remove_at(0)
				if tray_pieces.is_empty():
					_refill_tray_pieces()
				return "BOT_PLACED_PIECE at (%d,%d) | Cleared=%d" % [c, r, int(res.get("lines_cleared", 0))]
	# If board is full, trigger clean row clear recovery
	_init_empty_board()
	return "BOT_RESET_FULL_BOARD"

func step_block_juggle_self_test() -> String:
	_init_empty_board()
	for c in range(7):
		grid_8x8[0][c] = 1
	var res := place_piece_on_board([Vector2i(0, 0)], 7, 0)
	return "CRYSTAL_GRID_8X8_SELF_TEST: Placed=%s | LinesCleared=%d | Score=%d" % [
		str(res.get("placed", false)),
		int(res.get("lines_cleared", 0)),
		current_score
	]

func load_single_chunk(chunk_id: int) -> void:
	var world := get_tree().root.get_node_or_null("Main/WorldRoot") as Node3D
	if world == null:
		return
	_clear_children(world)
	var chunk := _create_map_chunk(chunk_id, 0.0)
	world.add_child(chunk)
	active_chunks.append(chunk)

func test_stitched_chunks(chunk_order: Array) -> void:
	var world := get_tree().root.get_node_or_null("Main/WorldRoot") as Node3D
	if world == null:
		return
	_clear_children(world)
	var offset_z: float = 0.0
	for cid in chunk_order:
		var chunk := _create_map_chunk(int(cid), offset_z)
		world.add_child(chunk)
		active_chunks.append(chunk)
		offset_z -= 30.0 # Exact 30.0m length per chunk -> 0.000m seam gap!

func _create_map_chunk(chunk_id: int, start_z: float) -> Node3D:
	var root := Node3D.new()
	root.name = "MapChunk_%d" % chunk_id
	root.position = Vector3(0, 0, start_z)

	var floor_body := StaticBody3D.new()
	var col := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(16.0, 1.0, 30.0)
	col.shape = box
	col.position = Vector3(0, -0.5, -15.0)
	floor_body.add_child(col)

	var mesh_inst := MeshInstance3D.new()
	var bmesh := BoxMesh.new()
	bmesh.size = Vector3(16.0, 1.0, 30.0)
	mesh_inst.mesh = bmesh
	mesh_inst.position = Vector3(0, -0.5, -15.0)
	floor_body.add_child(mesh_inst)
	root.add_child(floor_body)

	# Distinct obstacle pattern per chunk_id (1..5)
	for i in range(chunk_id + 1):
		var hp: int = 4 if (i == 0 and chunk_id >= 3) else 2
		_spawn_destructible_target(root, Vector3((i - 1) * 2.2, 1.0, -6.0 - i * 5.0), hp, i)

	return root

func _spawn_destructible_target(parent: Node3D, pos: Vector3, hits_req: int, idx: int) -> Node3D:
	var node := StaticBody3D.new()
	node.name = "TargetBubble_%d_HP%d" % [idx, hits_req]
	node.position = pos
	node.set_meta("hits_required", hits_req)
	node.set_meta("hit_points", hits_req)

	var col := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.55
	col.shape = sph
	node.add_child(col)

	var mi := MeshInstance3D.new()
	mi.name = "Mesh"
	var smesh := SphereMesh.new()
	smesh.radius = 0.55
	smesh.height = 1.1
	mi.mesh = smesh

	var vfx := get_node_or_null("/root/StudioThemeAndVFX")
	var base_col := Color(0.2, 0.75, 1.0) if hits_req == 1 else Color(0.95, 0.35, 0.75)
	if vfx != null:
		mi.material_override = vfx.call("create_glossy_bubble_or_car_material", base_col, 0.0)
	node.add_child(mi)
	parent.add_child(node)
	return node

func apply_hit_to_target(target: Node3D, damage: int = 1) -> Dictionary:
	if target == null or not is_instance_valid(target):
		return {"alive": false, "hp": 0, "state": "invalid"}
	var total_req: int = int(target.get_meta("hits_required", 4))
	var hp: int = int(target.get_meta("hit_points", total_req))
	var before_hp: int = hp
	hp = max(0, hp - damage)
	target.set_meta("hit_points", hp)

	var aud := get_node_or_null("/root/AudioDirector")
	var vfx := get_node_or_null("/root/StudioThemeAndVFX")

	if hp > 0:
		var crack_ratio: float = float(total_req - hp) / float(max(total_req, 1))
		var mi := target.get_node_or_null("Mesh") as MeshInstance3D
		if mi != null and vfx != null:
			mi.material_override = vfx.call("create_glossy_bubble_or_car_material", Color(0.95, 0.35, 0.75), crack_ratio)
		if aud != null:
			aud.call("play_sfx", "bubble_hit_crack")
		return {"alive": true, "before_hp": before_hp, "after_hp": hp, "state": "cracked_%d" % (total_req - hp)}
	else:
		current_combo += 1
		current_score += 100 * current_combo
		emit_signal("score_changed", current_score, current_combo)
		if aud != null:
			aud.call("play_sfx", "bubble_pop")
		if vfx != null and target.get_parent() is Node3D:
			vfx.call("spawn_pop_particles", target.get_parent(), target.global_position, Color(0.3, 0.9, 1.0))
		var cam := get_tree().root.get_node_or_null("Main/Camera3D") as Camera3D
		if vfx != null and cam != null:
			vfx.call("pulse_camera_feedback", cam, 0.10)
		target.queue_free()
		return {"alive": false, "before_hp": before_hp, "after_hp": 0, "state": "popped"}

func step_mechanics_lab_test() -> String:
	var world := get_tree().root.get_node_or_null("Main/WorldRoot") as Node3D
	if world == null:
		return "NO_WORLD"
	var board_check: String = step_block_juggle_self_test()
	if lab_target == null or not is_instance_valid(lab_target):
		lab_target = _spawn_destructible_target(world, Vector3(0, 1.5, -5.0), 4, 99)
		return "SPAWNED_4_HIT_TARGET: Initial HP=4 (intact) | " + board_check
	var res: Dictionary = apply_hit_to_target(lab_target, 1)
	return "4_HIT_TEST: HP %d -> %d | Alive=%s | State=%s | %s" % [
		int(res.get("before_hp", -1)),
		int(res.get("after_hp", -1)),
		str(res.get("alive", false)),
		str(res.get("state", "")),
		board_check
	]

func _clear_children(n: Node) -> void:
	active_targets.clear()
	active_chunks.clear()
	for c in n.get_children():
		c.queue_free()

func cleanup_qa_runtime_objects() -> void:
	# QA uses deferred queue_free; release mechanics-lab and world nodes before exit.
	if is_instance_valid(lab_target):
		lab_target.queue_free()
	lab_target = null
	var world := get_tree().root.get_node_or_null("Main/WorldRoot") as Node3D
	if world != null:
		_clear_children(world)
	active_targets.clear()
	active_chunks.clear()

var fever_overdrive_active: bool = false

func activate_mercy_rescue_and_juggle_vault() -> String:
	# Unique Upgrade #1 from Negative Reviews: Guarantees a 1x1 rescue piece & +1 Juggle Swap when board is tight
	if tray_pieces.is_empty():
		_refill_tray_pieces()
	tray_pieces[0] = PIECE_SHAPES[0]
	juggle_swaps_remaining = maxi(1, juggle_swaps_remaining)
	return "MERCY_RESCUE_ACTIVE"

func trigger_crystal_fever_overdrive() -> int:
	# Unique Upgrade #2 from Positive Reviews: 3x+ Combo triggers Fever Overdrive & cracks all armored blocks by 1 HP
	fever_overdrive_active = (current_combo >= 3)
	var cracked_count: int = 0
	if fever_overdrive_active:
		for t in active_targets:
			if t != null and is_instance_valid(t):
				apply_hit_to_target(t, 1)
				cracked_count += 1
	return cracked_count
