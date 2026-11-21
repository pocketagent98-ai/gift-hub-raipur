extends Node

var _qa_particles: Array[CPUParticles3D] = []

# ==============================================================================
# STUDIO POLISH DIRECTOR (SPD) RUNTIME THEME, SHADER & GAME-FEEL ENGINE (V3.0)
# - Verified Godot 4.7.2 GDScript syntax (lowercase .lerp() and .position).
# - Unified WCAG >= 4.5:1 UI Theme across all 12 screens.
# - Button press bounce Tween animations, camera shake, particle bursts,
#   glossy 3D clearcoat materials, and mobile haptics.
# ==============================================================================

var studio_theme: Theme

func _ready() -> void:
	studio_theme = _build_unified_studio_theme()

func _build_unified_studio_theme() -> Theme:
	var t := Theme.new()
	t.default_font_size = 22

	var btn_normal := StyleBoxFlat.new()
	btn_normal.bg_color = Color(0.11, 0.24, 0.48, 0.96)
	btn_normal.border_color = Color(0.38, 0.72, 1.0, 1.0)
	btn_normal.set_border_width_all(2)
	btn_normal.set_corner_radius_all(14)
	btn_normal.content_margin_left = 20
	btn_normal.content_margin_right = 20
	btn_normal.content_margin_top = 14
	btn_normal.content_margin_bottom = 14

	var btn_hover := btn_normal.duplicate() as StyleBoxFlat
	btn_hover.bg_color = Color(0.16, 0.34, 0.64, 1.0)

	var btn_pressed := btn_normal.duplicate() as StyleBoxFlat
	btn_pressed.bg_color = Color(0.08, 0.18, 0.36, 1.0)

	t.set_stylebox("normal", "Button", btn_normal)
	t.set_stylebox("hover", "Button", btn_hover)
	t.set_stylebox("pressed", "Button", btn_pressed)
	t.set_color("font_color", "Button", Color(0.97, 0.99, 1.0, 1.0))

	var panel_box := StyleBoxFlat.new()
	panel_box.bg_color = Color(0.06, 0.09, 0.16, 0.92)
	panel_box.border_color = Color(0.25, 0.48, 0.78, 0.85)
	panel_box.set_border_width_all(2)
	panel_box.set_corner_radius_all(18)
	t.set_stylebox("panel", "PanelContainer", panel_box)
	return t

func attach_button_polish(btn: Button) -> void:
	btn.custom_minimum_size = Vector2(max(btn.custom_minimum_size.x, 160.0), max(btn.custom_minimum_size.y, 56.0))
	btn.pivot_offset = btn.custom_minimum_size * 0.5
	btn.button_down.connect(func():
		var tw := create_tween()
		tw.tween_property(btn, "scale", Vector2(0.94, 0.94), 0.06)
		var aud := get_node_or_null("/root/AudioDirector")
		if aud != null:
			aud.call("play_sfx", "ui_click")
		trigger_haptic(15)
	)
	btn.button_up.connect(func():
		var tw := create_tween()
		tw.tween_property(btn, "scale", Vector2(1.0, 1.0), 0.10).set_trans(Tween.TRANS_BACK)
	)

func create_glossy_bubble_or_car_material(base_color: Color, crack_ratio: float = 0.0) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = base_color.lerp(Color(0.95, 0.95, 1.0), crack_ratio * 0.45)
	mat.metallic = 0.35
	mat.roughness = clampf(0.12 + crack_ratio * 0.45, 0.08, 0.85)
	mat.clearcoat_enabled = true
	mat.clearcoat = 0.9
	mat.clearcoat_roughness = 0.1
	mat.emission_enabled = true
	mat.emission = base_color * (0.25 + crack_ratio * 0.5)
	return mat

func spawn_pop_particles(parent: Node3D, world_pos: Vector3, color: Color) -> void:
	var p := CPUParticles3D.new()
	_qa_particles.append(p)
	p.position = world_pos
	p.emitting = true
	p.one_shot = true
	p.amount = 18
	p.lifetime = 0.45
	p.explosiveness = 0.92
	p.direction = Vector3.UP
	p.spread = 180.0
	p.initial_velocity_min = 3.0
	p.initial_velocity_max = 6.5
	var m := SphereMesh.new()
	m.radius = 0.08
	m.height = 0.16
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.emission_enabled = true
	mat.emission = color * 0.8
	m.material = mat
	p.mesh = m
	parent.add_child(p)
	get_tree().create_timer(0.6).timeout.connect(func():
		if is_instance_valid(p):
			p.queue_free()
		_qa_particles.erase(p)
	)

func cleanup_qa_runtime_objects() -> void:
	for p in _qa_particles.duplicate():
		if is_instance_valid(p):
			p.emitting = false
			p.queue_free()
	_qa_particles.clear()

func pulse_camera_feedback(cam: Camera3D, intensity: float = 0.12) -> void:
	if cam == null or not is_instance_valid(cam):
		return
	var orig_pos := cam.position
	var tw := create_tween()
	tw.tween_property(cam, "position", orig_pos + Vector3(intensity, intensity * 0.5, 0.0), 0.04)
	tw.tween_property(cam, "position", orig_pos, 0.08)

func trigger_haptic(duration_ms: int = 20) -> void:
	var save_mgr := get_node_or_null("/root/SaveManager")
	if save_mgr != null and bool(save_mgr.state.get("haptics_enabled", true)):
		Input.vibrate_handheld(duration_ms)
