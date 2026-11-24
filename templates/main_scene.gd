extends Node3D

const Spec = preload("res://scripts/generated_ui_spec.gd")

var _decor: Array = []
var _elapsed := 0.0
var _camera: Camera3D

func _ready() -> void:
        _camera = get_node_or_null("Camera3D") as Camera3D
        _build_decor()
        AnalyticsManager.record_event("app_started", {"game": AppConfig.GAME_ID, "genre": AppConfig.GAME_GENRE})

func _process(delta: float) -> void:
        _elapsed += delta
        for i in _decor.size():
                var node = _decor[i]
                if is_instance_valid(node):
                        node.rotate_y(delta * (0.20 + float(i) * 0.035))
                        node.rotate_x(delta * 0.08)
                        node.position.y += sin(_elapsed * 1.2 + float(i)) * delta * 0.05
        if _camera != null:
                _camera.position.x = sin(_elapsed * 0.24) * 0.35
                _camera.position.y = 4.0 + sin(_elapsed * 0.18) * 0.15
                _camera.look_at(Vector3(0, 1.2, 0), Vector3.UP)

func _build_decor() -> void:
        var gem_colors: Array = Spec.THEME.get("gem_colors", ["#FF4D6D", "#4DA3FF", "#54E39A", "#FFD447", "#B36BFF", "#33E0E8"])
        var palette: Array[Color] = []
        for hex in gem_colors:
                palette.append(Color(str(hex)))
        if palette.is_empty():
                palette.append(Color(1, 0.3, 0.42))
                palette.append(Color(0.3, 0.64, 1.0))
                palette.append(Color(0.33, 0.89, 0.6))
        if Spec.GENRE == "match_3":
                _build_candy_decor(palette)
        else:
                _build_screw_decor(palette)
        StudioThemeAndVFX.burst_particles(self, Vector3(0.0, 1.0, -2.0), palette[0])

func _glossy_material(color: Color, metallic: float = 0.15) -> StandardMaterial3D:
        var mat := StandardMaterial3D.new()
        mat.albedo_color = color
        mat.roughness = 0.18
        mat.metallic = metallic
        mat.clearcoat_enabled = true
        mat.clearcoat = 1.0
        mat.clearcoat_roughness = 0.08
        mat.emission_enabled = true
        mat.emission = color.lerp(Color.WHITE, 0.25)
        mat.emission_energy_multiplier = 0.35
        return mat

func _add_mesh(mesh: Mesh, position: Vector3, color: Color, scale_value: float = 1.0, metallic: float = 0.15) -> MeshInstance3D:
        var mi := MeshInstance3D.new()
        mi.mesh = mesh
        mi.material_override = _glossy_material(color, metallic)
        mi.position = position
        mi.scale = Vector3.ONE * scale_value
        add_child(mi)
        _decor.append(mi)
        return mi

func _build_candy_decor(palette: Array[Color]) -> void:
        for i in 16:
                var color: Color = palette[i % palette.size()]
                var pos := Vector3(-4.4 + float(i % 8) * 1.25, 1.0 + float(i / 8) * 1.5, -3.2 - float(i % 3) * 0.7)
                if i % 3 == 0:
                        var gem := SphereMesh.new()
                        gem.radius = 0.34
                        gem.height = 0.68
                        gem.radial_segments = 24
                        gem.rings = 12
                        _add_mesh(gem, pos, color, 1.0, 0.25)
                elif i % 3 == 1:
                        var candy := TorusMesh.new()
                        candy.inner_radius = 0.20
                        candy.outer_radius = 0.42
                        candy.rings = 24
                        candy.ring_segments = 12
                        _add_mesh(candy, pos, color, 1.0, 0.35)
                else:
                        var cube := BoxMesh.new()
                        cube.size = Vector3(0.55, 0.55, 0.55)
                        _add_mesh(cube, pos, color, 1.0, 0.1)
        var board := BoxMesh.new()
        board.size = Vector3(7.6, 0.18, 7.6)
        _add_mesh(board, Vector3(0, -0.4, -2.2), Color(0.10, 0.05, 0.16), 1.0, 0.05)

func _build_screw_decor(palette: Array[Color]) -> void:
        for i in 10:
                var color: Color = palette[i % palette.size()]
                var pos := Vector3(-3.8 + float(i % 5) * 1.9, 0.8 + float(i / 5) * 1.8, -3.0 - float(i % 2) * 0.9)
                var plate := BoxMesh.new()
                plate.size = Vector3(1.4, 0.16, 1.4)
                var mi := _add_mesh(plate, pos, color.darkened(0.15), 1.0, 0.75)
                mi.rotation = Vector3(0.15 * float(i), 0.3 * float(i), 0.1 * float(i))
                var screw := CylinderMesh.new()
                screw.top_radius = 0.18
                screw.bottom_radius = 0.18
                screw.height = 0.22
                screw.radial_segments = 20
                _add_mesh(screw, pos + Vector3(0, 0.18, 0), Color(0.85, 0.88, 0.95), 1.0, 0.9)
        var bench := BoxMesh.new()
        bench.size = Vector3(8.0, 0.22, 6.0)
        _add_mesh(bench, Vector3(0, -0.4, -2.0), Color(0.08, 0.14, 0.2), 1.0, 0.6)
