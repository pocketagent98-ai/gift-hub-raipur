class_name Procedural3DFactory
extends Node

# ==============================================================================
# ORIGINAL 3D ASSET FACTORY (GODOT 4.7.2 — PATH 2 & PATH 3 HYBRID PIPELINE)
# Generates 100% original, copyright-free 3D characters, vehicles, multi-hit
# armored bubbles, hazard bombs, and collectible coins with glossy PBR clearcoat.
# ==============================================================================

static func create_humanoid_character(primary_color: Color, accent_color: Color) -> CharacterBody3D:
	var body := CharacterBody3D.new()
	body.name = "PlayerCharacter3D"

	var col := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.35
	cap.height = 1.8
	col.shape = cap
	col.position = Vector3(0, 0.9, 0)
	body.add_child(col)

	var rig := Node3D.new()
	rig.name = "VisualRig"
	body.add_child(rig)

	var mat_main := StandardMaterial3D.new()
	mat_main.albedo_color = primary_color
	mat_main.roughness = 0.35
	mat_main.metallic = 0.2
	mat_main.clearcoat_enabled = true
	mat_main.clearcoat = 0.85

	var mat_accent := StandardMaterial3D.new()
	mat_accent.albedo_color = accent_color
	mat_accent.emission_enabled = true
	mat_accent.emission = accent_color * 0.4

	for side in [-0.16, 0.16]:
		var leg := MeshInstance3D.new()
		var leg_mesh := CapsuleMesh.new()
		leg_mesh.radius = 0.11
		leg_mesh.height = 0.8
		leg.mesh = leg_mesh
		leg.material_override = mat_main
		leg.position = Vector3(side, 0.4, 0)
		rig.add_child(leg)

	var torso := MeshInstance3D.new()
	var torso_mesh := BoxMesh.new()
	torso_mesh.size = Vector3(0.5, 0.65, 0.28)
	torso.mesh = torso_mesh
	torso.material_override = mat_main
	torso.position = Vector3(0, 1.12, 0)
	rig.add_child(torso)

	var head := MeshInstance3D.new()
	var head_mesh := SphereMesh.new()
	head_mesh.radius = 0.2
	head_mesh.height = 0.4
	head.mesh = head_mesh
	head.material_override = mat_main
	head.position = Vector3(0, 1.62, 0)
	rig.add_child(head)

	var visor := MeshInstance3D.new()
	var visor_mesh := BoxMesh.new()
	visor_mesh.size = Vector3(0.28, 0.08, 0.12)
	visor.mesh = visor_mesh
	visor.material_override = mat_accent
	visor.position = Vector3(0, 1.64, -0.16)
	rig.add_child(visor)

	return body

static func create_arcade_vehicle(chassis_color: Color, neon_color: Color) -> CharacterBody3D:
	var car := CharacterBody3D.new()
	car.name = "OriginalArcadeVehicle3D"

	var col := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(1.8, 0.9, 3.6)
	col.shape = box
	col.position = Vector3(0, 0.55, 0)
	car.add_child(col)

	var mat_body := StandardMaterial3D.new()
	mat_body.albedo_color = chassis_color
	mat_body.metallic = 0.65
	mat_body.roughness = 0.22
	mat_body.clearcoat_enabled = true
	mat_body.clearcoat = 0.95

	var mat_neon := StandardMaterial3D.new()
	mat_neon.albedo_color = neon_color
	mat_neon.emission_enabled = true
	mat_neon.emission = neon_color * 0.7

	var chassis := MeshInstance3D.new()
	var c_mesh := BoxMesh.new()
	c_mesh.size = Vector3(1.75, 0.5, 3.5)
	chassis.mesh = c_mesh
	chassis.material_override = mat_body
	chassis.position = Vector3(0, 0.45, 0)
	car.add_child(chassis)

	var cabin := MeshInstance3D.new()
	var cab_mesh := BoxMesh.new()
	cab_mesh.size = Vector3(1.4, 0.42, 1.6)
	cabin.mesh = cab_mesh
	cabin.material_override = mat_neon
	cabin.position = Vector3(0, 0.85, -0.1)
	car.add_child(cabin)

	return car

static func create_hazard_bomb(warning_color: Color) -> StaticBody3D:
	var bomb := StaticBody3D.new()
	bomb.name = "OriginalHazardBomb3D"
	var col := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.5
	col.shape = sph
	bomb.add_child(col)

	var mi := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.5
	sm.height = 1.0
	mi.mesh = sm
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.12, 0.14, 0.18)
	mat.metallic = 0.85
	mat.roughness = 0.28
	mat.emission_enabled = true
	mat.emission = warning_color * 0.35
	mi.material_override = mat
	bomb.add_child(mi)
	return bomb

static func create_collectible_coin(gold_color: Color) -> Area3D:
	var coin := Area3D.new()
	coin.name = "OriginalCollectibleCoin3D"
	var col := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.4
	col.shape = sph
	coin.add_child(col)

	var mi := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.38
	cyl.bottom_radius = 0.38
	cyl.height = 0.12
	mi.mesh = cyl
	var mat := StandardMaterial3D.new()
	mat.albedo_color = gold_color
	mat.metallic = 0.9
	mat.roughness = 0.18
	mat.emission_enabled = true
	mat.emission = gold_color * 0.25
	mi.material_override = mat
	coin.add_child(mi)
	return coin
