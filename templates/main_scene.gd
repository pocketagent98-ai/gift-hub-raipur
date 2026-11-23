extends Node3D

var _decor: Array = []

func _ready() -> void:
	_build_decor()
	StudioUI.show_screen("MainMenu")
	AnalyticsManager.record_event("app_started", {"game": AppConfig.GAME_ID, "genre": AppConfig.GAME_GENRE})

func _process(delta: float) -> void:
	for i in _decor.size():
		var node = _decor[i]
		if is_instance_valid(node):
			node.rotate_y(delta * (0.18 + float(i) * 0.04))
			node.rotate_x(delta * 0.07)

func _build_decor() -> void:
	var colors := [
		Color(0.96, 0.34, 0.40),
		Color(0.32, 0.64, 0.98),
		Color(0.36, 0.86, 0.54),
		Color(0.98, 0.78, 0.24),
		Color(0.74, 0.44, 0.96),
		Color(0.24, 0.86, 0.88),
	]
	for i in 10:
		var mi := MeshInstance3D.new()
		mi.name = "DecorCrystal%d" % i
		var mesh := BoxMesh.new()
		mesh.size = Vector3(0.35, 0.35, 0.35)
		var mat := StandardMaterial3D.new()
		mat.albedo_color = colors[i % colors.size()]
		mat.emission_enabled = true
		mat.emission = colors[i % colors.size()].lerp(Color.WHITE, 0.35)
		mat.emission_energy_multiplier = 0.8
		mat.clearcoat_enabled = true
		mat.clearcoat = 0.9
		mesh.material = mat
		mi.mesh = mesh
		mi.position = Vector3(-4.0 + float(i) * 0.9, 1.2 + sin(float(i) * 0.9) * 1.1, -3.0 - float(i % 3))
		add_child(mi)
		_decor.append(mi)
	StudioThemeAndVFX.burst_particles(self, Vector3(0.0, 1.0, -2.0), Color(0.4, 0.8, 1.0))
