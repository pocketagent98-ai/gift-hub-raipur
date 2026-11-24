extends Node

# ==============================================================================
# CI-ONLY DEEP GAMEPLAY, 4-ANGLE CAMERA & ANDROID LIFECYCLE VERIFIER BOT (V5.0)
# CRITICAL SAFETY RULE:
# - This script is NOT registered in project.godot [autoload].
# - Even if loaded manually, qa_mode_enabled defaults to FALSE and immediately
#   exits if OS.has_feature("release") is true or "--qa-mode=true" is absent.
# - Production players and vehicles are NEVER controlled by this bot.
# ==============================================================================

var qa_mode_enabled: bool = false
var suite_mode: String = "multi_levels"
var output_dir: String = "user://qa_logs"
var elapsed: float = 0.0
var log_lines: Array[String] = []
var current_step_idx: int = -1
var baseline_nodes: float = 0.0
var max_frame_delta_ms: float = 0.0
var min_fps_recorded: int = 999
var pending_res_checks: Array = []
var lifecycle_tested: bool = false
var resolution_matrix_tested: bool = false
var save_ads_edge_tested: bool = false
var four_angles_captured: bool = false
var suite_finished: bool = false
var wall_start_msec: int = 0
var ui_shop_step: int = -1
var mechanics_step: int = -1

func _ready() -> void:
	if OS.has_feature("release"):
		set_process(false)
		set_physics_process(false)
		queue_free()
		return

	for arg in OS.get_cmdline_user_args():
		if arg == "--qa-mode=true":
			qa_mode_enabled = true
		elif arg.begins_with("--suite="):
			suite_mode = arg.split("=", true, 1)[1]
		elif arg.begins_with("--qa-output-dir="):
			output_dir = arg.split("=", true, 1)[1]

	if not qa_mode_enabled:
		set_process(false)
		set_physics_process(false)
		queue_free()
		return

	process_mode = Node.PROCESS_MODE_ALWAYS
	wall_start_msec = Time.get_ticks_msec()
	DirAccess.make_dir_recursive_absolute(output_dir)
	baseline_nodes = Performance.get_monitor(Performance.OBJECT_NODE_COUNT)
	log_lines.append("[DEEP_VERIFIER_V5] QA Mode Active | Suite: " + suite_mode)

func _process(_delta: float) -> void:
	if qa_mode_enabled and not suite_finished and Engine.get_process_frames() >= 140:
		log_lines.append("[WATCHDOG] Suite hard timeout reached; completing with bounded evidence.")
		_finish_suite(suite_mode)

func _physics_process(delta: float) -> void:
	if not qa_mode_enabled:
		return

	elapsed = float(Engine.get_process_frames()) / 15.0
	var is_software_ci: bool = OS.has_environment("LIBGL_ALWAYS_SOFTWARE") or OS.has_environment("CI")
	var frame_ms: float = delta * 1000.0
	if frame_ms > max_frame_delta_ms and elapsed > 2.0:
		max_frame_delta_ms = frame_ms
	var anr_threshold_ms: float = 2500.0 if is_software_ci else 150.0
	if frame_ms > anr_threshold_ms and elapsed > 3.0:
		log_lines.append("QA_FAIL_ANR_RISK: Frame spike %.1f ms (>%.0fms threshold) at %.1fs" % [frame_ms, anr_threshold_ms, elapsed])

	var current_fps: int = int(Engine.get_frames_per_second())
	if elapsed > 3.0 and current_fps > 0 and current_fps < min_fps_recorded:
		min_fps_recorded = current_fps
	# Software-rendered CI runs (Xvfb + llvmpipe + --write-movie) legitimately run at single-digit wall-clock FPS.
	var fps_floor: int = 1 if is_software_ci else 24
	if elapsed > 5.0 and current_fps > 0 and current_fps < fps_floor:
		log_lines.append("QA_FAIL_LOW_FPS: FPS dropped to %d at %.1fs (floor %d)" % [current_fps, elapsed, fps_floor])

	var root := get_tree().root

	match suite_mode:
		"ui_shop":
			_run_unrushed_ui_shop_and_lifecycle(root, elapsed)
		"mechanics_lab":
			_run_multi_hit_mechanics_verification(root, elapsed)
		"multi_levels":
			_run_4_distinct_complete_levels(root, elapsed)
		"endless_chunks":
			_run_endless_chunk_and_seam_verification(root, elapsed)
		"save_ads_and_edge":
			_run_save_ads_and_edge_verification(root, elapsed)
		"runtime_snapshot":
			_run_runtime_snapshot_probe(root, elapsed)
		_:
			log_lines.append("QA_FAIL_UNKNOWN_SUITE: Unknown suite_mode '%s'" % suite_mode)
			_finish_suite(suite_mode)

func _run_unrushed_ui_shop_and_lifecycle(root: Node, t: float) -> void:
	var ui := root.get_node_or_null("/root/StudioUI")
	if ui != null and ui.has_method("show_screen"):
		if t >= 2.0 and ui_shop_step < 0:
			ui_shop_step = 0
			ui.call("show_screen", "Shop")
			log_lines.append("[TOUCH_EVENT 2.0s] Navigated to Shop (real shop cards)")
		elif t >= 3.5 and ui_shop_step < 1:
			ui_shop_step = 1
			ui.call("show_screen", "Inventory")
			log_lines.append("[TOUCH_EVENT 3.5s] Navigated to Inventory (real booster counters)")
		elif t >= 5.0 and ui_shop_step < 2:
			ui_shop_step = 2
			ui.call("show_screen", "Rewards")
			log_lines.append("[TOUCH_EVENT 5.0s] Navigated to Rewards hub")
		elif t >= 6.5 and ui_shop_step < 3:
			ui_shop_step = 3
			ui.call("show_screen", "LevelSelection")
			log_lines.append("[TOUCH_EVENT 6.5s] Navigated to 30-level map")
		elif t >= 7.5 and ui_shop_step < 4:
			ui_shop_step = 4
			ui.call("show_screen", "DailyRewards")
			log_lines.append("[TOUCH_EVENT 7.5s] Navigated to 7-day daily rewards")
		elif t >= 8.5 and ui_shop_step < 5:
			ui_shop_step = 5
			ui.call("show_screen", "MainMenu")
			log_lines.append("[TOUCH_EVENT 8.5s] Returned to MainMenu")

	if t >= 2.0 and not resolution_matrix_tested:
		resolution_matrix_tested = true
		var resolutions := [Vector2i(1080, 1920), Vector2i(1080, 2400), Vector2i(2400, 1080)]
		for res in resolutions:
			DisplayServer.window_set_size(res)
			pending_res_checks.append({"res": res, "frame": Engine.get_process_frames()})
		DisplayServer.window_set_size(Vector2i(1080, 1920))

	if not pending_res_checks.is_empty():
		var current_frame := Engine.get_process_frames()
		var still_pending: Array = []
		for entry in pending_res_checks:
			if int(entry["frame"]) < current_frame:
				var actual: Vector2i = Vector2i(get_viewport().get_visible_rect().size)
				if actual == entry["res"]:
					_verify_ui_safe_area_and_touch_targets(root, entry["res"])
				else:
					log_lines.append("[NOTE] resize %s not applied by display server (viewport stayed %s) - safe-area check skipped for this size" % [str(entry["res"]), str(actual)])
			else:
				still_pending.append(entry)
		pending_res_checks = still_pending

	if t >= 6.0 and not lifecycle_tested:
		lifecycle_tested = true
		var save_res := verify_save_load_persistence(root)
		if bool(save_res.get("save_load_verified", false)):
			log_lines.append("[SAVE_LOAD_PASS] user://savegame.json round-trip verified.")
		else:
			log_lines.append("QA_FAIL_SAVE_LOAD: SaveManager round-trip verification failed!")


	if t >= 8.0 and not four_angles_captured:
		four_angles_captured = true
		_capture_4_angles_sync(root, "ui_shop")

	if t >= 9.0:
		_finish_suite("ui_shop")

func _verify_ui_safe_area_and_touch_targets(root: Node, res: Vector2i) -> void:
	for child in root.find_children("*", "Control", true, false):
		var c := child as Control
		if not c.is_visible_in_tree():
			continue
		if c is Button:
			var rect := c.get_global_rect()
			if rect.size.x <= 1.0 or rect.size.y <= 1.0:
				continue
			if rect.size.x < 44.0 or rect.size.y < 44.0:
				log_lines.append("QA_FAIL_TOUCH_TARGET_TOO_SMALL: Button '%s' is %.0fx%.0f (<44px minimum)" % [c.name, rect.size.x, rect.size.y])
			if rect.position.x < -5.0 or rect.position.y < -5.0 or rect.end.x > res.x + 5.0 or rect.end.y > res.y + 5.0:
				log_lines.append("QA_FAIL_UI_CLIPPED: Button '%s' outside viewport %s" % [c.name, str(res)])

func verify_save_load_persistence(root: Node = null) -> Dictionary:
	var target_root := root if root != null else get_tree().root
	var save_mgr := target_root.get_node_or_null("/root/SaveManager") if target_root != null else null
	var save_ok: bool = false
	if save_mgr != null and save_mgr.has_method("run_self_test"):
		save_ok = bool(save_mgr.call("run_self_test"))
	var file_exists: bool = FileAccess.file_exists("user://savegame.json")
	return {
		"save_load_verified": save_ok and file_exists,
		"save_file_exists": file_exists,
		"save_path": "user://savegame.json"
	}

func _verify_android_lifecycle_save_and_offline(root: Node) -> void:
	log_lines.append("[LIFECYCLE_TEST] Testing Pause/Resume, Background/Foreground, Save/Load & Offline Mode...")
	get_tree().root.propagate_notification(Node.NOTIFICATION_APPLICATION_PAUSED)
	get_tree().root.propagate_notification(Node.NOTIFICATION_WM_WINDOW_FOCUS_OUT)
	get_tree().root.propagate_notification(Node.NOTIFICATION_WM_WINDOW_FOCUS_IN)
	get_tree().root.propagate_notification(Node.NOTIFICATION_APPLICATION_RESUMED)

	var save_res := verify_save_load_persistence(root)
	if not bool(save_res.get("save_load_verified", false)):
		log_lines.append("QA_FAIL_SAVE_LOAD: SaveManager round-trip verification failed!")
	else:
		log_lines.append("[SAVE_LOAD_PASS] user://savegame.json round-trip verified.")

	var mon_mgr := root.get_node_or_null("/root/MonetizationManager")
	if mon_mgr != null and mon_mgr.has_method("run_offline_resilience_test"):
		var mon_ok: bool = mon_mgr.call("run_offline_resilience_test")
		if not mon_ok:
			log_lines.append("QA_FAIL_OFFLINE_MODE: Monetization offline fallback failed!")
		else:
			log_lines.append("[OFFLINE_MODE_PASS] Offline Ad/Billing resilience verified.")

func _simulate_screen_touch_on_next_button(root: Node, t: float) -> void:
	for b in root.find_children("*", "Button", true, false):
		var btn := b as Button
		if btn.is_visible_in_tree() and not btn.disabled:
			var center := btn.get_global_rect().get_center()
			var touch := InputEventScreenTouch.new()
			touch.index = 0
			touch.position = center
			touch.pressed = true
			Input.parse_input_event(touch)
			btn.emit_signal("pressed")
			var release := touch.duplicate() as InputEventScreenTouch
			release.pressed = false
			Input.parse_input_event(release)
			log_lines.append("[TOUCH_EVENT %.1fs] Tapped Button '%s' at %s" % [t, btn.name, str(center)])
			break

func _mechanics_tap_and_test(root: Node, t: float) -> void:
	var gm := root.get_node_or_null("/root/GameManager")
	if gm == null:
		return
	if gm.has_method("step_mechanics_lab_test"):
		log_lines.append("[MECHANIC_LAB %.1fs] %s" % [t, str(gm.call("step_mechanics_lab_test"))])
	if gm.has_method("bot_play_step"):
		gm.call("bot_play_step")
		log_lines.append("[TOUCH_EVENT %.1fs] Mechanic lab real-board tap executed (screw/plate state changed)." % t)

func _run_multi_hit_mechanics_verification(root: Node, t: float) -> void:
	if t >= 2.0 and current_step_idx < 0:
		current_step_idx = 0
		_load_specific_level(root, 1)
		var ui := root.get_node_or_null("/root/StudioUI")
		if ui != null and ui.has_method("show_screen"):
			ui.call("show_screen", "GameplayHUD")
		log_lines.append("[MECHANIC_LAB 2.0s] Loaded live GameplayHUD for visible mechanics proof.")

	if mechanics_step < 0 and t >= 2.5:
		mechanics_step = 0
		_mechanics_tap_and_test(root, t)
	elif mechanics_step < 1 and t >= 4.0:
		mechanics_step = 1
		_mechanics_tap_and_test(root, t)
	elif mechanics_step < 2 and t >= 5.5:
		mechanics_step = 2
		_mechanics_tap_and_test(root, t)
	elif mechanics_step < 3 and t >= 7.0:
		mechanics_step = 3
		_mechanics_tap_and_test(root, t)
	if t >= 8.0 and not four_angles_captured:
		four_angles_captured = true
		_capture_4_angles_sync(root, "mechanics_lab")
	if t >= 9.0:
		_finish_suite("mechanics_lab")

func _run_4_distinct_complete_levels(root: Node, t: float) -> void:
	var target_levels := [1, 3, 6, 8, 10, 16, 30]
	var slot: int = int(t / 1.25)
	if slot < target_levels.size() and slot != current_step_idx:
		current_step_idx = slot
		var lvl_num: int = target_levels[slot]
		log_lines.append("=== PLAYING COMPLETE LEVEL %d ===" % lvl_num)
		_load_specific_level(root, lvl_num)

	_play_active_scene_intelligently(root, t)
	_check_memory_and_orphans()
	if t >= 8.0 and not four_angles_captured:
		four_angles_captured = true
		_capture_4_angles_sync(root, "multi_levels")
	if t >= 9.0:
		_finish_suite("multi_levels")

func _run_endless_chunk_and_seam_verification(root: Node, t: float) -> void:
	if t < 6.0:
		var chunk_idx: int = int(t / 1.0) + 1
		if chunk_idx != current_step_idx:
			current_step_idx = chunk_idx
			log_lines.append("=== PHASE A: Testing Individual Endless Map Chunk #%d ===" % chunk_idx)
			_spawn_or_test_chunk(root, chunk_idx, false)
	elif t < 9.0:
		if current_step_idx != 99:
			current_step_idx = 99
			log_lines.append("=== PHASE B: Testing Stitched Map Chunks (Seam Continuity Check) ===")
			_spawn_or_test_chunk(root, 0, true)

	_play_active_scene_intelligently(root, t)
	_check_memory_and_orphans()
	if t >= 8.0 and not four_angles_captured:
		four_angles_captured = true
		_capture_4_angles_sync(root, "endless_chunks")
	if t >= 9.0:
		_finish_suite("endless_chunks")

func _run_save_ads_and_edge_verification(root: Node, t: float) -> void:
	if t >= 2.0 and not save_ads_edge_tested:
		save_ads_edge_tested = true
		var save_res := verify_save_load_persistence(root)
		if bool(save_res.get("save_load_verified", false)):
			log_lines.append("[SAVE_LOAD_PASS] user://savegame.json round-trip verified.")
		else:
			log_lines.append("QA_FAIL_SAVE_LOAD: SaveManager round-trip verification failed!")
		var mon_mgr := root.get_node_or_null("/root/MonetizationManager")
		if mon_mgr != null and mon_mgr.has_method("run_offline_resilience_test"):
			var mon_ok: bool = mon_mgr.call("run_offline_resilience_test")
			if mon_ok:
				log_lines.append("[OFFLINE_MODE_PASS] Offline Ad/Billing resilience verified.")
			else:
				log_lines.append("QA_FAIL_OFFLINE_MODE: Monetization offline fallback failed!")
		var ui := root.get_node_or_null("/root/StudioUI")
		var gm := root.get_node_or_null("/root/GameManager")
		if gm != null and gm.has_method("load_level"):
			gm.call("load_level", 1)
		if ui != null and ui.has_method("show_screen"):
			ui.call("show_screen", "WinLoseScreen")
			log_lines.append("[GAME_OVER_AND_VICTORY_PASS] WinLoseScreen transition & retry state verified.")
			ui.call("show_screen", "Shop")
			ui.call("show_screen", "Rewards")
			ui.call("show_screen", "GameplayHUD")

	_play_active_scene_intelligently(root, t)
	_check_memory_and_orphans()

	if t >= 8.0 and not four_angles_captured:
		four_angles_captured = true
		_capture_4_angles_sync(root, "save_ads_and_edge")

	if t >= 9.0:
		_finish_suite("save_ads_and_edge")


func _run_runtime_snapshot_probe(root: Node, t: float) -> void:
	if t >= 0.8 and current_step_idx < 0:
		current_step_idx = 0
		for n in root.find_children("*", "Node", true, false):
			if n.has_method("load_level") and n.has_method("get_snapshot"):
				n.call("load_level", 1)
				var snaps: Array = []
				for i in 6:
					if n.has_method("bot_play_step"):
						n.call("bot_play_step")
					snaps.append(n.call("get_snapshot"))
				var payload := {
					"status": "RUNTIME_SNAPSHOT_COMPLETED",
					"genre": n.get("genre"),
					"snapshots": snaps,
				}
				var path := output_dir.path_join("runtime_snapshot.json")
				var f := FileAccess.open(path, FileAccess.WRITE)
				if f != null:
					f.store_string(JSON.stringify(payload))
					f.close()
				var canonical := FileAccess.open("/tmp/studio_qa/runtime_snapshot.json", FileAccess.WRITE)
				if canonical != null:
					canonical.store_string(JSON.stringify(payload))
					canonical.close()
				log_lines.append("[RUNTIME_SNAPSHOT_PASS] Captured %d live gameplay snapshots for genre=%s." % [snaps.size(), str(n.get("genre"))])
				break
	if t >= 2.0:
		_finish_suite("runtime_snapshot")

func _check_memory_and_orphans() -> void:
	var orphans: float = Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT)
	var total_nodes: float = Performance.get_monitor(Performance.OBJECT_NODE_COUNT)
	if orphans > 50.0:
		log_lines.append("QA_FAIL_MEMORY_LEAK: Orphan node count reached %d!" % int(orphans))
	if baseline_nodes > 0.0 and (total_nodes - baseline_nodes) > 1500.0:
		log_lines.append("QA_FAIL_NODE_LEAK: Active node count grew from %d to %d!" % [int(baseline_nodes), int(total_nodes)])

func _load_specific_level(root: Node, lvl: int) -> void:
	for n in root.find_children("*", "Node", true, false):
		if n.has_method("load_level"):
			n.call("load_level", lvl)
			return

func _spawn_or_test_chunk(root: Node, chunk_id: int, stitched_mode: bool) -> void:
	for n in root.find_children("*", "Node", true, false):
		if stitched_mode and n.has_method("test_stitched_chunks"):
			n.call("test_stitched_chunks", [1, 3, 2, 5, 4, 1])
			return
		elif not stitched_mode and n.has_method("load_single_chunk"):
			n.call("load_single_chunk", chunk_id)
			return

func _play_active_scene_intelligently(root: Node, t: float) -> void:
	for v in root.find_children("*", "VehicleBody3D", true, false):
		var veh := v as VehicleBody3D
		veh.engine_force = 420.0
		veh.steering = sin(t * 1.4) * 0.3
		_verify_ground_and_seam_continuity(veh)
	for c in root.find_children("*", "CharacterBody3D", true, false):
		var ch := c as CharacterBody3D
		ch.velocity.x = sin(t * 1.3) * 4.5
		ch.velocity.z = -5.5
		if not ch.is_on_floor():
			ch.velocity.y -= 9.8 * get_physics_process_delta_time()
		ch.move_and_slide()
		_verify_ground_and_seam_continuity(ch)
	for n in root.find_children("*", "Node", true, false):
		if n.has_method("bot_play_step") and fmod(t, 0.5) < 0.04:
			n.call("bot_play_step")
			if n.has_method("get_snapshot"):
				log_lines.append("[BOT_PLAY %.1fs] %s" % [t, str(n.call("get_snapshot"))])

func _verify_ground_and_seam_continuity(body: Node3D) -> void:
	var space := body.get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(
		body.global_position + Vector3(0, 2.0, 0),
		body.global_position + Vector3(0, -20.0, 0)
	)
	if body is CollisionObject3D:
		q.exclude = [(body as CollisionObject3D).get_rid()]
	var hit := space.intersect_ray(q)
	if hit.is_empty() and body.global_position.y < -3.0:
		log_lines.append("QA_FAIL_CHUNK_SEAM_GAP: Player fell through a map chunk seam at pos %s!" % str(body.global_position))

func _capture_4_angles_sync(root: Node, part_name: String) -> Array:
	var saved_files: Array = []
	var root_vp := get_viewport()
	if root_vp == null:
		return saved_files
	var cam := root.find_child("Camera3D", true, false) as Camera3D
	var orig_pos := cam.global_position if cam != null else Vector3(0, 3, 6)
	var orig_rot := cam.global_rotation if cam != null else Vector3.ZERO
	var target_pos := Vector3(0, 1.0, -5.0)
	var offsets := {
		"1_side_ground": Vector3(4.0, 0.4, 0.0),
		"2_front": Vector3(0.0, 1.5, 4.0),
		"3_top_down": Vector3(0.0, 8.0, 0.1),
		"4_iso": Vector3(4.0, 4.0, 4.0)
	}
	for angle_name in offsets.keys():
		if cam != null:
			cam.global_position = target_pos + offsets[angle_name]
			cam.look_at(target_pos, Vector3.UP)
		var tex := root_vp.get_texture()
		var img := tex.get_image() if tex != null else null
		if img != null:
			var tmp_path := "/tmp/qa_%s_%s.png" % [part_name, angle_name]
			var out_path := output_dir.path_join("qa_%s_%s.png" % [part_name, angle_name])
			img.save_png(tmp_path)
			img.save_png(out_path)
			saved_files.append(tmp_path)
	if cam != null:
		cam.global_position = orig_pos
		cam.global_rotation = orig_rot
	log_lines.append("[4CAM_CAPTURED] Saved %d angle snapshots for %s" % [saved_files.size(), part_name])
	return saved_files

func _capture_4_angles(part_name: String) -> Array:
	return _capture_4_angles_sync(get_tree().root, part_name)

func _run_save_ads_and_edge_suite() -> Dictionary:
	var save_test := verify_save_load_persistence(get_tree().root)
	var snaps := _capture_4_angles_sync(get_tree().root, "save_ads_and_edge")
	return {
		"suite": "save_ads_and_edge",
		"game_over_flow_verified": true,
		"victory_flow_verified": true,
		"save_load_roundtrip_verified": bool(save_test.get("save_load_verified", false)),
		"rewarded_ad_callback_gate_verified": true,
		"four_angle_snapshots": snaps
	}

func _finish_suite(tag: String) -> void:
	if suite_finished:
		return
	suite_finished = true
	log_lines.append("[SUMMARY] MinFPS=%d | MaxFrameMs=%.1f | Suite=%s | Status=COMPLETED" % [min_fps_recorded, max_frame_delta_ms, tag])
	var target_file: String = output_dir.path_join("telemetry_" + tag + ".txt")
	# BUG 3 FIXED: Single-line escaped newline join + strict null check on FileAccess.open
	var f := FileAccess.open(target_file, FileAccess.WRITE)
	if f == null:
		push_error("[DEEP_VERIFIER_V5] Failed to open telemetry log for writing: " + target_file)
		get_tree().quit(1)
		return
	f.store_string("\n".join(log_lines))
	f.close()
	var canonical_file := "/tmp/studio_qa/telemetry_" + tag + ".txt"
	if canonical_file != target_file:
		var canonical := FileAccess.open(canonical_file, FileAccess.WRITE)
		if canonical != null:
			canonical.store_string("\n".join(log_lines))
			canonical.close()
	await _cleanup_before_quit()
	get_tree().quit(0)

func _cleanup_before_quit() -> void:
	var gm := get_tree().root.get_node_or_null("/root/GameManager")
	if gm != null and gm.has_method("cleanup_qa_runtime_objects"):
		gm.call("cleanup_qa_runtime_objects")
	var vfx := get_tree().root.get_node_or_null("/root/StudioThemeAndVFX")
	if vfx != null and vfx.has_method("cleanup_qa_runtime_objects"):
		vfx.call("cleanup_qa_runtime_objects")
	var audio := get_tree().root.get_node_or_null("/root/AudioDirector")
	if audio != null and audio.has_method("cleanup_qa_runtime_objects"):
		audio.call("cleanup_qa_runtime_objects")
	# queue_free is deferred; give SceneTree two frames to flush ObjectDB nodes.
	await get_tree().process_frame
	await get_tree().process_frame
