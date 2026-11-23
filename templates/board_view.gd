extends Control

var manager
var _redraw_accum := 0.0

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	set_anchors_preset(Control.PRESET_FULL_RECT)

func _process(delta: float) -> void:
	_redraw_accum += delta
	if _redraw_accum >= 0.2:
		_redraw_accum = 0.0
		queue_redraw()

func _board_rect() -> Rect2:
	var view := get_viewport_rect().size
	var side: float = min(view.x - 40.0, view.y * 0.58)
	var top := view.y * 0.22
	return Rect2((view.x - side) * 0.5, top, side, side)

func cell_center(cell_index: int) -> Vector2:
	var r := int(cell_index / 8)
	var c := cell_index % 8
	var br := _board_rect()
	var cell := br.size.x / 8.0
	return br.position + Vector2((c + 0.5) * cell, (r + 0.5) * cell)

func _draw() -> void:
	if manager == null:
		return
	if manager.genre == "match_3":
		_draw_match3()
	else:
		_draw_screw()
	_draw_header()

func _draw_header() -> void:
	var view := get_viewport_rect().size
	var title := "SUGAR CASCADE" if manager.genre == "match_3" else "BOLT MASTER"
	draw_string(ThemeDB.fallback_font, Vector2(36, 70), title, HORIZONTAL_ALIGNMENT_LEFT, -1, 38, Color(0.95, 0.98, 1.0))
	var sub := "LEVEL %d  |  SCORE %d  |  %s %d" % [manager.current_level, manager.score, ("MOVES" if manager.genre == "match_3" else "TOOLS"), manager.moves_left]
	draw_string(ThemeDB.fallback_font, Vector2(36, 110), sub, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, Color(0.65, 0.82, 1.0))
	if manager.state != "playing":
		draw_string(ThemeDB.fallback_font, Vector2(view.x * 0.5 - 90, view.y * 0.15), manager.state.to_upper(), HORIZONTAL_ALIGNMENT_LEFT, -1, 34, Color(1.0, 0.85, 0.25))

func _draw_match3() -> void:
	var br := _board_rect()
	draw_rect(br.grow(12), Color(0.06, 0.09, 0.16, 0.96), true)
	draw_rect(br.grow(12), Color(0.20, 0.36, 0.60, 0.85), false, 3.0)
	var cell := br.size.x / 8.0
	for r in 8:
		for c in 8:
			var idx := r * 8 + c
			var col: int = manager.colors[idx]
			if col < 0:
				continue
			var center := br.position + Vector2((c + 0.5) * cell, (r + 0.5) * cell)
			var radius := cell * 0.36
			var base: Color = manager.palette[col % manager.palette.size()]
			draw_circle(center, radius, base)
			draw_circle(center + Vector2(-radius * 0.28, -radius * 0.28), radius * 0.34, Color(1, 1, 1, 0.55))
			draw_circle(center + Vector2(radius * 0.30, radius * 0.30), radius * 0.18, Color(0, 0, 0, 0.18))
			if manager.armor[idx] > 0:
				draw_arc(center, radius + 4.0, 0.0, TAU, 28, Color(1.0, 0.82, 0.18), 3.0)
				draw_string(ThemeDB.fallback_font, center + Vector2(-7, 9), str(manager.armor[idx]), HORIZONTAL_ALIGNMENT_LEFT, -1, 26, Color(0.08, 0.05, 0.0))
			if manager.selected == idx:
				draw_arc(center, radius + 8.0, 0.0, TAU, 28, Color(1, 1, 1, 0.95), 4.0)

func _draw_screw() -> void:
	var br := _board_rect()
	draw_rect(br.grow(12), Color(0.06, 0.09, 0.16, 0.96), true)
	draw_rect(br.grow(12), Color(0.20, 0.36, 0.60, 0.85), false, 3.0)
	var scale := br.size.x / 8.0
	for plate in manager.plates:
		if bool(plate.get("removed", false)):
			continue
		var rect: Rect2 = plate["rect"]
		var pr := Rect2(br.position + rect.position * scale, rect.size * scale)
		var plate_color: Color = manager.palette[int(plate["color"]) % manager.palette.size()]
		draw_rect(pr, plate_color.darkened(0.20), true)
		draw_rect(pr, plate_color.lightened(0.40), false, 3.0)
		draw_string(ThemeDB.fallback_font, pr.position + Vector2(10, 26), "PLATE %d" % int(plate["id"]), HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color(1, 1, 1, 0.85))
	for screw in manager.screws:
		if bool(screw.get("removed", false)):
			continue
		var center := br.position + Vector2(screw["pos"]) * scale
		var screw_color: Color = manager.palette[int(screw["color"]) % manager.palette.size()]
		draw_circle(center, 18.0, Color(0.08, 0.09, 0.12))
		draw_circle(center, 13.0, screw_color)
		draw_line(center + Vector2(-9, 0), center + Vector2(9, 0), Color(0.04, 0.04, 0.05), 3.0)
		draw_line(center + Vector2(0, -9), center + Vector2(0, 9), Color(0.04, 0.04, 0.05), 3.0)
		if int(screw.get("hp", 0)) > 0:
			draw_arc(center, 20.0, 0.0, TAU, 22, Color(1.0, 0.78, 0.16), 3.0)
			draw_string(ThemeDB.fallback_font, center + Vector2(-6, 7), str(int(screw["hp"])), HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color(0.05, 0.03, 0.0))
		if not manager.is_screw_tappable(screw):
			draw_circle(center, 15.0, Color(0, 0, 0, 0.55))

	var bar_y := br.end.y + 46.0
	draw_string(ThemeDB.fallback_font, Vector2(40, bar_y - 12), "TOOLBOX", HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color(0.85, 0.92, 1.0))
	for i in manager.tools.size():
		var tool_color: Color = manager.palette[int(manager.tools[i]) % manager.palette.size()]
		var tool_pos := Vector2(90.0 + i * 96.0, bar_y + 22.0)
		draw_circle(tool_pos, 28.0, Color(0.10, 0.14, 0.22))
		draw_circle(tool_pos, 22.0, tool_color)
		draw_arc(tool_pos, 28.0, 0.0, TAU, 24, Color(0.8, 0.9, 1.0), 2.0)
	draw_string(ThemeDB.fallback_font, Vector2(410, bar_y + 30), "TEMP", HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color(0.85, 0.92, 1.0))
	for j in 3:
		var slot := Vector2(500.0 + j * 62.0, bar_y + 22.0)
		draw_rect(Rect2(slot - Vector2(24, 24), Vector2(48, 48)), Color(0.12, 0.16, 0.24), true)
		if j < manager.temp.size():
			var temp_color: Color = manager.palette[int(manager.temp[j]) % manager.palette.size()]
			draw_circle(slot, 18.0, temp_color)

func _gui_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch and event.pressed:
		_handle_tap(event.position)
		accept_event()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		_handle_tap(event.position)
		accept_event()

func _handle_tap(pos: Vector2) -> void:
	if manager == null:
		return
	if manager.genre == "match_3":
		var br := _board_rect()
		if not br.has_point(pos):
			return
		var cell := br.size.x / 8.0
		var c := int((pos.x - br.position.x) / cell)
		var r := int((pos.y - br.position.y) / cell)
		if c >= 0 and c < 8 and r >= 0 and r < 8:
			manager.handle_tap(r * 8 + c)
	else:
		var nearest := -1
		var best := 46.0
		var br2 := _board_rect()
		var scale := br2.size.x / 8.0
		for i in manager.screws.size():
			var screw = manager.screws[i]
			if bool(screw.get("removed", false)):
				continue
			var center := br2.position + Vector2(screw["pos"]) * scale
			var dist := center.distance_to(pos)
			if dist < best:
				best = dist
				nearest = i
		if nearest >= 0:
			manager.handle_screw_tap(nearest)
