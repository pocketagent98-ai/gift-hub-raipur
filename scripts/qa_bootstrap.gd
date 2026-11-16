extends Node

func _ready() -> void:
	if OS.has_feature("release"):
		push_error("[QA_BOOTSTRAP] Refusing to run QA bootstrap in release build.")
		get_tree().quit(1)
		return

	var main_scene := load("res://main.tscn") as PackedScene
	if main_scene == null:
		push_error("[QA_BOOTSTRAP] Failed to load res://main.tscn")
		get_tree().quit(1)
		return
	var main_inst := main_scene.instantiate()
	get_tree().root.add_child.call_deferred(main_inst)

	var bot_script := load("res://scripts/deep_game_verifier_bot.gd") as Script
	if bot_script == null:
		push_error("[QA_BOOTSTRAP] Failed to load res://scripts/deep_game_verifier_bot.gd")
		get_tree().quit(1)
		return
	var bot_node := Node.new()
	bot_node.name = "DeepGameVerifierBot"
	bot_node.set_script(bot_script)
	get_tree().root.add_child.call_deferred(bot_node)
