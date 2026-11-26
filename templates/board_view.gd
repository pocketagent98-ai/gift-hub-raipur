extends Control

# ==============================================================================
# INTERACTIVE COMMERCIAL-POLISH PUZZLE BOARD VIEW (V6.0)
# ==============================================================================

var _board_rect: Rect2 = Rect2()
var _cell_size: float = 64.0
var _tray_rects: Array[Rect2] = []

var _dragging_tray_idx: int = -1
var _selected_tray_idx: int = -1
var _drag_pos: Vector2 = Vector2.ZERO
var _hover_grid: Vector2i = Vector2i(-1, -1)

var _swipe_start_cell: Vector2i = Vector2i(-1, -1)
var _swipe_start_pos: Vector2 = Vector2.ZERO

var _particles: Array = []
var _popups: Array = []
var _shake_timer: float = 0.0
var _pulse_time: float = 0.0

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	size_flags_vertical = Control.SIZE_EXPAND_FILL
	var gm := get_node_or_null("/root/GameManager")
	if gm != null:
		if gm.has_signal("state_changed"):
			gm.connect("state_changed", Callable(self, "_on_game_state_changed"))
		if gm.has_signal("board_updated"):
			gm.connect("board_updated", Callable(self, "_on_board_updated"))

func _on_game_state_changed() -> void:
	queue_redraw()

func _on_board_updated(cleared_count: int) -> void:
	var gm := get_node_or_null("/root/GameManager")
	if gm == null:
		return
	var cleared_cells: Array = gm.get("last_cleared_cells") if gm.get("last_cleared_cells") != null else []
	var pal: Array = gm.get("PALETTE")
	for item in cleared_cells:
		var gpos: Vector2i = item["pos"]
		var cid: int = int(item["color_id"])
		var col: Color = pal[clampi(cid, 1, pal.size() - 1)] if pal.size() > 1 else Color(1, 0.85, 0.3)
		var center := _grid_to_local_center(gpos.x, gpos.y)
		for _k in range(7):
			var ang := randf() * TAU
			var spd := randf_range(90.0, 290.0)
			_particles.append({
				"pos": center,
				"vel": Vector2(cos(ang), sin(ang)) * spd,
				"color": col.lightened(0.2),
				"life": randf_range(0.35, 0.65),
				"size": randf_range(5.0, 12.0)
			})
	var ptxt := str(gm.get("last_popup_text"))
	if ptxt != "":
		var pgrid: Vector2i = gm.get("last_popup_grid_pos")
		_popups.append({
			"pos": _grid_to_local_center(pgrid.x, pgrid.y),
			"text": ptxt,
			"life": 0.95,
			"color": Color(1.0, 0.92, 0.35) if cleared_count > 0 else Color(0.75, 0.95, 1.0)
		})
	if cleared_count > 0:
		_shake_timer = 0.22
	queue_redraw()

func _process(delta: float) -> void:
	_pulse_time += delta
	var dirty := false
	if _shake_timer > 0.0:
		_shake_timer = maxf(0.0, _shake_timer - delta)
		dirty = true
	if not _particles.is_empty():
		var next_p: Array = []
		for p in _particles:
			p["life"] = float(p["life"]) - delta
			if float(p["life"]) > 0.0:
				p["pos"] = p["pos"] + p["vel"] * delta
				p["vel"] = p["vel"] * 0.94 + Vector2(0, 260.0 * delta)
				next_p.append(p)
		_particles = next_p
		dirty = true
	if not _popups.is_empty():
		var next_pop: Array = []
		for pop in _popups:
			pop["life"] = float(pop["life"]) - delta
			if float(pop["life"]) > 0.0:
				pop["pos"] = pop["pos"] + Vector2(0, -65.0 * delta)
				next_pop.append(pop)
		_popups = next_pop
		dirty = true
	if dirty or _dragging_tray_idx >= 0:
		queue_redraw()

func _compute_layout() -> void:
	var w := size.x
	var h := size.y
	if w <= 10.0 or h <= 10.0:
		return
	var gm := get_node_or_null("/root/GameManager")
	var is_bp := (gm != null and str(gm.get("GENRE")) == "block_puzzle")
	var tray_reserve := h * 0.27 if is_bp else 24.0
	var avail_h := maxf(180.0, h - tray_reserve - 24.0)
	var board_side := minf(w - 28.0, avail_h)
	_cell_size = floor(board_side / 8.0)
	var exact_side := _cell_size * 8.0
	var bx := floor((w - exact_side) * 0.5)
	var by := floor(maxf(8.0, (avail_h - exact_side) * 0.5))
	_board_rect = Rect2(bx, by, exact_side, exact_side)

	_tray_rects.clear()
	if is_bp:
		var ty := _board_rect.end.y + 22.0
		var th := maxf(110.0, h - ty - 14.0)
		var slot_w := floor((w - 40.0) / 3.0)
		for i in range(3):
			_tray_rects.append(Rect2(14.0 + i * (slot_w + 6.0), ty, slot_w, th))

func _grid_to_local_center(gx: int, gy: int) -> Vector2:
	return Vector2(
		_board_rect.position.x + (float(gx) + 0.5) * _cell_size,
		_board_rect.position.y + (float(gy) + 0.5) * _cell_size
	)

func _local_to_grid(pos: Vector2) -> Vector2i:
	if not _board_rect.has_point(pos):
		return Vector2i(-1, -1)
	var gx := int(floor((pos.x - _board_rect.position.x) / _cell_size))
	var gy := int(floor((pos.y - _board_rect.position.y) / _cell_size))
	if gx >= 0 and gx < 8 and gy >= 0 and gy < 8:
		return Vector2i(gx, gy)
	return Vector2i(-1, -1)

func _gui_input(event: InputEvent) -> void:
	var gm := get_node_or_null("/root/GameManager")
	if gm == null:
		return
	var genre := str(gm.get("GENRE"))
	if genre == "block_puzzle":
		_handle_block_puzzle_input(event, gm)
	else:
		_handle_match3_input(event, gm)

func _handle_block_puzzle_input(event: InputEvent, gm: Node) -> void:
	var pressed := false
	var released := false
	var moved := false
	var pos := Vector2.ZERO

	if event is InputEventScreenTouch:
		pressed = event.pressed
		released = not event.pressed
		pos = event.position
	elif event is InputEventScreenDrag:
		moved = true
		pos = event.position
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		pressed = event.pressed
		released = not event.pressed
		pos = event.position
	elif event is InputEventMouseMotion and _dragging_tray_idx >= 0:
		moved = true
		pos = event.position
	else:
		return

	_compute_layout()

	if pressed:
		if bool(gm.get("hammer_mode_active")):
			var g := _local_to_grid(pos)
			if g.x >= 0:
				gm.call("use_hammer_at", g.x, g.y)
				accept_event()
				return

		for i in range(_tray_rects.size()):
			if _tray_rects[i].has_point(pos):
				var tray: Array = gm.get("tray_pieces")
				if i < tray.size() and not bool(tray[i]["used"]):
					_dragging_tray_idx = i
					_selected_tray_idx = i
					_drag_pos = pos
					_update_hover_grid(gm, pos)
					queue_redraw()
					accept_event()
					return

		if _selected_tray_idx >= 0:
			var g2 := _local_to_grid(pos)
			if g2.x >= 0:
				var res: Dictionary = gm.call("place_tray_piece", _selected_tray_idx, g2.x, g2.y)
				if bool(res.get("placed", false)):
					_selected_tray_idx = -1
				queue_redraw()
				accept_event()
				return

	elif moved and _dragging_tray_idx >= 0:
		_drag_pos = pos
		_update_hover_grid(gm, pos)
		queue_redraw()
		accept_event()

	elif released and _dragging_tray_idx >= 0:
		_update_hover_grid(gm, pos)
		if _hover_grid.x >= 0:
			var res: Dictionary = gm.call("place_tray_piece", _dragging_tray_idx, _hover_grid.x, _hover_grid.y)
			if bool(res.get("placed", false)):
				_selected_tray_idx = -1
		_dragging_tray_idx = -1
		_hover_grid = Vector2i(-1, -1)
		queue_redraw()
		accept_event()

func _update_hover_grid(gm: Node, finger_pos: Vector2) -> void:
	var lifted := finger_pos + Vector2(0, -_cell_size * 1.35)
	var tray: Array = gm.get("tray_pieces")
	if _dragging_tray_idx < 0 or _dragging_tray_idx >= tray.size():
		_hover_grid = Vector2i(-1, -1)
		return
	var cells: Array = tray[_dragging_tray_idx]["cells"]
	var max_x := 0
	var max_y := 0
	for c in cells:
		max_x = maxi(max_x, int(c.x))
		max_y = maxi(max_y, int(c.y))
	var top_left := lifted - Vector2(float(max_x + 1) * _cell_size * 0.5, float(max_y + 1) * _cell_size * 0.5)
	var gx := int(round((top_left.x - _board_rect.position.x) / _cell_size))
	var gy := int(round((top_left.y - _board_rect.position.y) / _cell_size))
	if gm.call("can_place_piece", cells, gx, gy):
		_hover_grid = Vector2i(gx, gy)
	else:
		_hover_grid = Vector2i(-1, -1)

func _handle_match3_input(event: InputEvent, gm: Node) -> void:
	_compute_layout()
	if event is InputEventScreenTouch or (event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT):
		if event.pressed:
			var g := _local_to_grid(event.position)
			if g.x >= 0:
				_swipe_start_cell = g
				_swipe_start_pos = event.position
				var prev: Vector2i = gm.get("selected_cell")
				if prev.x >= 0 and abs(prev.x - g.x) + abs(prev.y - g.y) == 1:
					gm.call("try_swap", prev, g)
					_swipe_start_cell = Vector2i(-1, -1)
				else:
					gm.set("selected_cell", g)
				queue_redraw()
				accept_event()
		else:
			_swipe_start_cell = Vector2i(-1, -1)
	elif (event is InputEventScreenDrag or event is InputEventMouseMotion) and _swipe_start_cell.x >= 0:
		var delta_v: Vector2 = event.position - _swipe_start_pos
		if delta_v.length() >= _cell_size * 0.35:
			var dir := Vector2i.ZERO
			if abs(delta_v.x) > abs(delta_v.y):
				dir = Vector2i(1 if delta_v.x > 0 else -1, 0)
			else:
				dir = Vector2i(0, 1 if delta_v.y > 0 else -1)
			gm.call("try_swap", _swipe_start_cell, _swipe_start_cell + dir)
			_swipe_start_cell = Vector2i(-1, -1)
			queue_redraw()
			accept_event()

func _draw() -> void:
	_compute_layout()
	var gm := get_node_or_null("/root/GameManager")
	if gm == null or _board_rect.size.x <= 10.0:
		return

	var shake_off := Vector2.ZERO
	if _shake_timer > 0.0:
		shake_off = Vector2(randf_range(-5.0, 5.0), randf_range(-5.0, 5.0)) * (_shake_timer / 0.22)

	var frame := _board_rect.grow(10.0)
	frame.position += shake_off
	draw_rect(frame, Color(0.11, 0.14, 0.26, 0.96), true)
	draw_rect(frame, Color(0.36, 0.68, 1.0, 0.85), false, 3.0)

	var grid: Array = gm.get("grid_8x8")
	var pal: Array = gm.get("PALETTE")
	var is_bp := (str(gm.get("GENRE")) == "block_puzzle")

	var clear_rows: Array = []
	var clear_cols: Array = []
	if is_bp and _dragging_tray_idx >= 0 and _hover_grid.x >= 0:
		var tray: Array = gm.get("tray_pieces")
		var pv: Dictionary = gm.call("preview_clear_lines", tray[_dragging_tray_idx]["cells"], _hover_grid.x, _hover_grid.y)
		clear_rows = pv.get("rows", [])
		clear_cols = pv.get("cols", [])

	for r in range(8):
		for c in range(8):
			var cell_r := Rect2(
				_board_rect.position.x + c * _cell_size + 2.0 + shake_off.x,
				_board_rect.position.y + r * _cell_size + 2.0 + shake_off.y,
				_cell_size - 4.0,
				_cell_size - 4.0
			)
			var bg_col := Color(0.16, 0.20, 0.34, 0.92) if ((r + c) % 2 == 0) else Color(0.14, 0.17, 0.30, 0.92)
			if r in clear_rows or c in clear_cols:
				bg_col = Color(0.95, 0.82, 0.25, 0.45)
			draw_rect(cell_r, bg_col, true)

			var val := int(grid[r][c]) if (r < grid.size() and c < grid[r].size()) else 0
			if val > 0:
				var col: Color = pal[clampi(val, 1, pal.size() - 1)]
				_draw_glossy_block(cell_r, col, not is_bp)

	if not is_bp:
		var sel: Vector2i = gm.get("selected_cell")
		if sel.x >= 0:
			var sr := Rect2(
				_board_rect.position.x + sel.x * _cell_size + 2.0 + shake_off.x,
				_board_rect.position.y + sel.y * _cell_size + 2.0 + shake_off.y,
				_cell_size - 4.0,
				_cell_size - 4.0
			)
			draw_rect(sr, Color(1.0, 0.95, 0.4, 0.95), false, 4.0)

	if is_bp:
		var tray: Array = gm.get("tray_pieces")
		if _dragging_tray_idx >= 0 and _hover_grid.x >= 0 and _dragging_tray_idx < tray.size():
			var piece: Dictionary = tray[_dragging_tray_idx]
			var gcol: Color = pal[clampi(int(piece["color_id"]), 1, pal.size() - 1)]
			gcol.a = 0.45
			for cell in piece["cells"]:
				var gx := _hover_grid.x + int(cell.x)
				var gy := _hover_grid.y + int(cell.y)
				var gr := Rect2(_board_rect.position.x + gx * _cell_size + 3.0, _board_rect.position.y + gy * _cell_size + 3.0, _cell_size - 6.0, _cell_size - 6.0)
				draw_rect(gr, gcol, true)
				draw_rect(gr, Color(1, 1, 1, 0.75), false, 2.0)

		for i in range(mini(3, tray.size())):
			if i >= _tray_rects.size():
				break
			var tr := _tray_rects[i]
			var border_c := Color(0.95, 0.85, 0.30, 0.95) if (i == _selected_tray_idx) else Color(0.28, 0.42, 0.68, 0.65)
			draw_rect(tr, Color(0.10, 0.13, 0.24, 0.90), true)
			draw_rect(tr, border_c, false, 2.5)
			if bool(tray[i]["used"]) or i == _dragging_tray_idx:
				continue
			_draw_tray_piece(tr, tray[i]["cells"], pal[clampi(int(tray[i]["color_id"]), 1, pal.size() - 1)])

		if _dragging_tray_idx >= 0 and _dragging_tray_idx < tray.size():
			var piece: Dictionary = tray[_dragging_tray_idx]
			var col: Color = pal[clampi(int(piece["color_id"]), 1, pal.size() - 1)]
			var lifted := _drag_pos + Vector2(0, -_cell_size * 1.35)
			var cells: Array = piece["cells"]
			var max_x := 0
			var max_y := 0
			for c in cells:
				max_x = maxi(max_x, int(c.x))
				max_y = maxi(max_y, int(c.y))
			var origin := lifted - Vector2(float(max_x + 1) * _cell_size * 0.5, float(max_y + 1) * _cell_size * 0.5)
			for c in cells:
				var dr := Rect2(origin.x + float(c.x) * _cell_size + 2.0, origin.y + float(c.y) * _cell_size + 2.0, _cell_size - 4.0, _cell_size - 4.0)
				_draw_glossy_block(dr, col, false)

	for p in _particles:
		var c: Color = p["color"]
		c.a = clampf(float(p["life"]) * 1.8, 0.0, 1.0)
		draw_circle(p["pos"], float(p["size"]) * 0.5, c)

	var font := ThemeDB.fallback_font
	for pop in _popups:
		var pc: Color = pop["color"]
		pc.a = clampf(float(pop["life"]) * 1.4, 0.0, 1.0)
		draw_string(font, pop["pos"] - Vector2(50, 0), str(pop["text"]), HORIZONTAL_ALIGNMENT_CENTER, 120, 28, pc)

func _draw_tray_piece(slot: Rect2, cells: Array, col: Color) -> void:
	var max_x := 0
	var max_y := 0
	for c in cells:
		max_x = maxi(max_x, int(c.x))
		max_y = maxi(max_y, int(c.y))
	var mini_sz := minf((slot.size.x - 20.0) / float(max_x + 1), (slot.size.y - 20.0) / float(max_y + 1))
	mini_sz = minf(mini_sz, _cell_size * 0.62)
	var total_w := float(max_x + 1) * mini_sz
	var total_h := float(max_y + 1) * mini_sz
	var ox := slot.position.x + (slot.size.x - total_w) * 0.5
	var oy := slot.position.y + (slot.size.y - total_h) * 0.5
	for c in cells:
		var r := Rect2(ox + float(c.x) * mini_sz + 1.5, oy + float(c.y) * mini_sz + 1.5, mini_sz - 3.0, mini_sz - 3.0)
		_draw_glossy_block(r, col, false)

func _draw_glossy_block(r: Rect2, col: Color, as_gem_circle: bool) -> void:
	if as_gem_circle:
		var center := r.get_center()
		var rad := minf(r.size.x, r.size.y) * 0.44
		draw_circle(center + Vector2(0, 3), rad, col.darkened(0.45))
		draw_circle(center, rad, col)
		draw_circle(center - Vector2(rad * 0.25, rad * 0.28), rad * 0.34, col.lightened(0.55))
	else:
		draw_rect(r, col.darkened(0.32), true)
		var inner := r.grow(-3.0)
		draw_rect(inner, col, true)
		var shine := Rect2(inner.position.x + 2.0, inner.position.y + 2.0, inner.size.x - 4.0, maxf(4.0, inner.size.y * 0.30))
		draw_rect(shine, col.lightened(0.42), true)
		draw_rect(r, col.lightened(0.25), false, 1.5)
