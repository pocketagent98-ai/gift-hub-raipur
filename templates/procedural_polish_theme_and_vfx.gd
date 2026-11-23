extends Node

const TOUCH_MIN := Vector2(220, 56)
const TOUCH_MIN_HEIGHT := 56.0

func make_panel_style(color: Color, radius: int = 18) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = color
	sb.set_corner_radius_all(radius)
	sb.border_width_left = 2
	sb.border_width_right = 2
	sb.border_width_top = 2
	sb.border_width_bottom = 2
	sb.border_color = color.lightened(0.35)
	return sb

func attach_button_polish(btn: Button) -> void:
	btn.custom_minimum_size = Vector2(220, 56)
	btn.add_theme_font_size_override("font_size", 30)
	btn.add_theme_stylebox_override("normal", make_panel_style(Color(0.10, 0.24, 0.42)))
	btn.add_theme_stylebox_override("hover", make_panel_style(Color(0.14, 0.34, 0.58)))
	btn.add_theme_stylebox_override("pressed", make_panel_style(Color(0.06, 0.16, 0.30)))
	btn.pressed.connect(func() -> void:
		Input.vibrate_handheld(18)
		var tw := create_tween()
		tw.tween_property(btn, "scale", Vector2(0.95, 0.95), 0.06)
		tw.tween_property(btn, "scale", Vector2.ONE, 0.08)
	)

func pulse_camera_feedback(cam: Camera3D, amount: float) -> void:
	if cam == null:
		return
	var base := cam.position
	var tw := create_tween()
	tw.tween_property(cam, "position", base + Vector3(amount, amount, 0.0), 0.05)
	tw.tween_property(cam, "position", base, 0.08)

func burst_at_screen(parent: Control, cell_index: int, color: Color) -> void:
	var p := CPUParticles2D.new()
	p.position = parent.cell_center(cell_index) if parent.has_method("cell_center") else Vector2(360, 640)
	p.one_shot = true
	p.emitting = true
	p.amount = 12
	p.lifetime = 0.5
	p.color = color
	p.spread = 180.0
	p.initial_velocity_min = 40.0
	p.initial_velocity_max = 140.0
	parent.add_child(p)
	await get_tree().create_timer(0.8).timeout
	if is_instance_valid(p):
		p.queue_free()

func burst_particles(parent: Node3D, world_position: Vector3, color: Color) -> void:
	var p := CPUParticles3D.new()
	p.position = world_position
	p.one_shot = true
	p.emitting = true
	p.amount = 18
	p.lifetime = 0.6
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	p.emission_sphere_radius = 0.3
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.emission_enabled = true
	mat.emission = color.lerp(Color.WHITE, 0.35)
	mat.clearcoat_enabled = true
	mat.clearcoat = 0.9
	var mesh := SphereMesh.new()
	mesh.radius = 0.05
	mesh.height = 0.1
	mesh.material = mat
	p.mesh = mesh
	parent.add_child(p)
	await get_tree().create_timer(1.0).timeout
	if is_instance_valid(p):
		p.queue_free()

func cleanup_qa_runtime_objects() -> void:
	for child in get_children():
		if str(child.name).begins_with("QATemp"):
			child.queue_free()
