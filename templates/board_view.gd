extends Control

const Spec = preload("res://scripts/generated_ui_spec.gd")

var manager
var _redraw_accum := 0.0

func _ready() -> void:
        mouse_filter = Control.MOUSE_FILTER_STOP
        set_anchors_preset(Control.PRESET_FULL_RECT)

func _process(delta: float) -> void:
        if manager != null:
                if manager.genre == "screw_puzzle":
                        for plate in manager.plates:
                                if bool(plate.get("removed", false)) and float(plate.get("fall", 0.0)) < 1.0:
                                        plate["fall"] = minf(float(plate.get("fall", 0.0)) + delta * 1.8, 1.0)
                        for screw in manager.screws:
                                if float(screw.get("anim", 0.0)) > 0.0:
                                        screw["anim"] = maxf(float(screw.get("anim", 0.0)) - delta * 2.6, 0.0)
        _redraw_accum += delta
        if _redraw_accum >= 0.08:
                _redraw_accum = 0.0
                queue_redraw()

func _board_rect() -> Rect2:
        var view := get_viewport_rect().size
        var side: float = minf(view.x - 36.0, view.y * 0.58)
        var top := view.y * 0.225
        return Rect2((view.x - side) * 0.5, top, side, side)

func cell_center(cell_index: int) -> Vector2:
        var r := int(cell_index / 8)
        var c := cell_index % 8
        var br := _board_rect()
        var cell := br.size.x / 8.0
        return br.position + Vector2((c + 0.5) * cell, (r + 0.5) * cell)

func _theme_color(key: String, fallback: String = "#FFFFFF") -> Color:
        return Color(str(Spec.THEME.get(key, fallback)))

func _panel_style(color: Color, radius: int = 22, border: Color = Color(1, 1, 1, 0.16)) -> StyleBoxFlat:
        var sb := StyleBoxFlat.new()
        sb.bg_color = color
        sb.set_corner_radius_all(radius)
        sb.border_width_left = 3
        sb.border_width_right = 3
        sb.border_width_top = 3
        sb.border_width_bottom = 3
        sb.border_color = border
        sb.shadow_color = Color(0, 0, 0, 0.45)
        sb.shadow_size = 16
        sb.shadow_offset = Vector2(0, 8)
        return sb

func _draw() -> void:
        if manager == null:
                return
        var br := _board_rect()
        draw_style_box(_panel_style(_theme_color("board"), 26), br.grow(10))
        if manager.genre == "match_3":
                _draw_match3(br)
        else:
                _draw_screw(br)

func _draw_match3(br: Rect2) -> void:
        var cell := br.size.x / 8.0
        for r in 8:
                for c in 8:
                        var idx := r * 8 + c
                        var center := br.position + Vector2((c + 0.5) * cell, (r + 0.5) * cell)
                        var tile := Rect2(center - Vector2(cell * 0.46, cell * 0.46), Vector2(cell * 0.92, cell * 0.92))
                        draw_rect(tile, Color(1, 1, 1, 0.035), true)
                        draw_rect(tile, Color(1, 1, 1, 0.07), false, 1.0)
                        var col: int = manager.colors[idx]
                        if col < 0:
                                continue
                        var base: Color = manager.palette[col % manager.palette.size()]
                        var radius := cell * 0.36
                        draw_circle(center, radius * 1.12, Color(0, 0, 0, 0.25))
                        draw_circle(center, radius, base.darkened(0.12))
                        draw_circle(center + Vector2(-radius * 0.18, -radius * 0.18), radius * 0.86, base)
                        draw_circle(center + Vector2(-radius * 0.30, -radius * 0.32), radius * 0.32, Color(1, 1, 1, 0.72))
                        draw_circle(center + Vector2(radius * 0.30, radius * 0.32), radius * 0.16, Color(0, 0, 0, 0.18))
                        if int(manager.specials[idx]) > 0:
                                var sp := int(manager.specials[idx])
                                var special_color := Color(1.0, 0.92, 0.35)
                                draw_arc(center, radius + 6.0, 0.0, TAU, 28, special_color, 3.0)
                                if sp == 1:
                                        draw_line(center + Vector2(-radius, 0), center + Vector2(radius, 0), special_color, 4.0)
                                elif sp == 2:
                                        draw_line(center + Vector2(0, -radius), center + Vector2(0, radius), special_color, 4.0)
                                else:
                                        draw_circle(center, radius * 0.34, Color(1, 1, 1, 0.85))
                        if manager.armor[idx] > 0:
                                draw_arc(center, radius + 4.0, 0.0, TAU, 28, Color(1.0, 0.82, 0.18), 4.0)
                                draw_circle(center, radius * 0.28, Color(0.05, 0.03, 0.0, 0.75))
                                draw_string(ThemeDB.fallback_font, center + Vector2(-7, 9), str(manager.armor[idx]), HORIZONTAL_ALIGNMENT_LEFT, -1, 24, Color(1.0, 0.9, 0.35))
                        if manager.selected == idx:
                                draw_arc(center, radius + 10.0, 0.0, TAU, 32, Color(1, 1, 1, 0.95), 4.0)

func _draw_screw(br: Rect2) -> void:
        var scale := br.size.x / 8.0
        for plate in manager.plates:
                var removed := bool(plate.get("removed", false))
                var fall := float(plate.get("fall", 0.0))
                if removed and fall >= 1.0:
                        continue
                var rect: Rect2 = plate["rect"]
                var offset := Vector2(0, fall * 110.0)
                var pr := Rect2(br.position + rect.position * scale + offset, rect.size * scale)
                var plate_color: Color = manager.palette[int(plate["color"]) % manager.palette.size()]
                var alpha := 1.0 - fall if removed else 1.0
                var style := _panel_style(Color(plate_color.darkened(0.24), alpha), 16, Color(plate_color.lightened(0.45), alpha))
                draw_style_box(style, pr)
                draw_line(pr.position + Vector2(12, 8), pr.position + Vector2(pr.size.x - 12, 8), Color(1, 1, 1, 0.28 * alpha), 2.0)
                draw_string(ThemeDB.fallback_font, pr.position + Vector2(12, 28), "PLATE %d" % int(plate["id"]), HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color(1, 1, 1, 0.85 * alpha))
        for screw in manager.screws:
                if bool(screw.get("removed", false)):
                        continue
                var center := br.position + Vector2(screw["pos"]) * scale
                var screw_color: Color = manager.palette[int(screw["color"]) % manager.palette.size()]
                var anim := float(screw.get("anim", 0.0))
                var spin := anim * TAU
                draw_circle(center, 22.0, Color(0.04, 0.06, 0.08, 0.85))
                draw_circle(center, 17.0, Color(0.22, 0.26, 0.32))
                draw_circle(center, 14.0, screw_color)
                draw_circle(center + Vector2(-4, -5), 4.5, Color(1, 1, 1, 0.7))
                var dir := Vector2(cos(spin), sin(spin)) * 10.0
                draw_line(center - dir, center + dir, Color(0.04, 0.04, 0.05), 3.0)
                if int(screw.get("hp", 0)) > 0:
                        draw_arc(center, 21.0, 0.0, TAU, 24, Color(1.0, 0.78, 0.16), 3.0)
                        draw_string(ThemeDB.fallback_font, center + Vector2(-6, 7), str(int(screw["hp"])), HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color(0.05, 0.03, 0.0))
                if not manager.is_screw_tappable(screw):
                        draw_circle(center, 17.0, Color(0, 0, 0, 0.55))
        var bar_y := br.end.y + 42.0
        draw_string(ThemeDB.fallback_font, Vector2(40, bar_y - 12), "TOOLBOX", HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color(0.85, 0.92, 1.0))
        for i in manager.tools.size():
                var tool_color: Color = manager.palette[int(manager.tools[i]) % manager.palette.size()]
                var tool_pos := Vector2(92.0 + i * 100.0, bar_y + 22.0)
                draw_circle(tool_pos, 30.0, Color(0.08, 0.12, 0.18))
                draw_circle(tool_pos, 23.0, tool_color)
                draw_circle(tool_pos + Vector2(-6, -7), 6.0, Color(1, 1, 1, 0.6))
                draw_arc(tool_pos, 30.0, 0.0, TAU, 24, Color(0.8, 0.9, 1.0), 2.0)
        draw_string(ThemeDB.fallback_font, Vector2(430, bar_y + 30), "TEMP", HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color(0.85, 0.92, 1.0))
        for j in 3:
                var slot := Vector2(520.0 + j * 62.0, bar_y + 22.0)
                draw_rect(Rect2(slot - Vector2(25, 25), Vector2(50, 50)), Color(0.10, 0.14, 0.22), true)
                draw_rect(Rect2(slot - Vector2(25, 25), Vector2(50, 50)), Color(0.4, 0.55, 0.7), false, 2.0)
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
                var best := 52.0
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
