extends CanvasLayer

const SCREEN_NAMES = [
	"MainMenu", "LoadingScreen", "GameplayHUD", "PauseMenu",
	"Settings", "Shop", "Inventory", "Rewards",
	"LevelSelection", "WinLoseScreen", "Profile", "DailyRewards",
]
const SafeAreaMargin := 36
const TUTORIAL_TEXT := "TUTORIAL: Match 3+ crystals. Crack armored crystals 4 times. Reach the target score!"

var screens: Dictionary = {}
var current_screen := "MainMenu"
var hud_score_lbl: Label
var hud_level_lbl: Label
var hud_moves_lbl: Label
var tutorial_banner: Label
var result_lbl: Label

var nav_targets : Dictionary = {
	"MainMenu": ["LevelSelection", "Shop", "Settings", "Profile", "DailyRewards"],
	"LoadingScreen": ["GameplayHUD"],
	"GameplayHUD": ["PauseMenu"],
	"PauseMenu": ["GameplayHUD", "Settings", "MainMenu"],
	"Settings": ["MainMenu", "PauseMenu"],
	"Shop": ["MainMenu", "Rewards"],
	"Inventory": ["MainMenu", "Shop"],
	"Rewards": ["MainMenu", "Shop"],
	"LevelSelection": ["GameplayHUD", "MainMenu"],
	"WinLoseScreen": ["GameplayHUD", "LevelSelection", "MainMenu"],
	"Profile": ["MainMenu", "DailyRewards"],
	"DailyRewards": ["MainMenu", "Rewards"],
}

func _ready() -> void:
	layer = 10
	for screen_name in SCREEN_NAMES:
		screens[screen_name] = _build_screen(screen_name)
	show_screen("MainMenu")

func _build_screen(screen_name: String) -> Control:
	var root := Control.new()
	root.name = screen_name
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.visible = false
	add_child(root)

	if screen_name == "GameplayHUD":
		_build_gameplay_hud(root)
		return root

	var bg := ColorRect.new()
	bg.color = Color(0.04, 0.06, 0.12, 1.0)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(bg)

	var margin := MarginContainer.new()
	margin.name = "SafeAreaMargin"
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 36)
	margin.add_theme_constant_override("margin_right", 36)
	margin.add_theme_constant_override("margin_top", 48)
	margin.add_theme_constant_override("margin_bottom", 48)
	root.add_child(margin)

	var panel := PanelContainer.new()
	panel.name = "Panel"
	panel.add_theme_stylebox_override("panel", StudioThemeAndVFX.make_panel_style(Color(0.07, 0.11, 0.20, 0.96)))
	margin.add_child(panel)

	var vb := VBoxContainer.new()
	vb.name = "ContentVBox"
	vb.add_theme_constant_override("separation", 16)
	panel.add_child(vb)

	var title := Label.new()
	title.name = "Title"
	title.text = "STUDIO V5.0 - " + screen_name.to_upper()
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 40)
	vb.add_child(title)

	if screen_name == "WinLoseScreen":
		result_lbl = Label.new()
		result_lbl.name = "result_lbl"
		result_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		result_lbl.add_theme_font_size_override("font_size", 32)
		result_lbl.text = "RESULT"
		vb.add_child(result_lbl)

	if screen_name == "Settings":
		var mute_btn := Button.new()
		mute_btn.name = "Btn_ToggleAudio"
		mute_btn.text = "Toggle Master Audio"
		mute_btn.pressed.connect(func() -> void:
			var master := AudioServer.get_bus_index("Master")
			AudioServer.set_bus_mute(master, not AudioServer.is_bus_mute(master))
		)
		_style_button(mute_btn)
		vb.add_child(mute_btn)

	if screen_name == "Shop":
		var offers := [
			["Starter Pack - 1200 Coins", "starter_pack"],
			["Remove Ads Forever", "remove_ads"],
			["Coin Pack - 1200", "coins_small"],
		]
		for offer in offers:
			var buy_btn := Button.new()
			buy_btn.name = "Btn_Buy_" + str(offer[1])
			buy_btn.text = str(offer[0])
			var sku := str(offer[1])
			buy_btn.pressed.connect(func() -> void:
				MonetizationManager.purchase(sku)
			)
			_style_button(buy_btn)
			vb.add_child(buy_btn)

	if screen_name == "Rewards":
		var reward_btn := Button.new()
		reward_btn.name = "Btn_ClaimDaily"
		reward_btn.text = "Claim Daily Reward"
		reward_btn.pressed.connect(func() -> void:
			SaveManager.add_coins(100)
			SaveManager.data["daily_reward_claimed"] = true
			SaveManager.save_game()
			AudioDirector.play_sfx("coin")
		)
		_style_button(reward_btn)
		vb.add_child(reward_btn)

	for target in nav_targets.get(screen_name, []):
		var btn := Button.new()
		btn.name = "Btn_" + screen_name + "_to_" + str(target)
		btn.text = "Open " + str(target)
		var target_screen := str(target)
		btn.pressed.connect(func() -> void:
			show_screen(target_screen)
		)
		_style_button(btn)
		vb.add_child(btn)

	return root

func _build_gameplay_hud(root: Control) -> void:
	var bg := ColorRect.new()
	bg.color = Color(0.04, 0.06, 0.12, 0.0)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(bg)

	var top := MarginContainer.new()
	top.name = "SafeAreaMargin"
	top.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	top.add_theme_constant_override("margin_left", 36)
	top.add_theme_constant_override("margin_right", 36)
	top.add_theme_constant_override("margin_top", 28)
	root.add_child(top)

	var vb := VBoxContainer.new()
	vb.name = "ContentVBox"
	vb.add_theme_constant_override("separation", 6)
	top.add_child(vb)

	var title := Label.new()
	title.name = "Title"
	title.text = "STUDIO V5.0 - GAMEPLAY"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 30)
	vb.add_child(title)

	hud_level_lbl = Label.new()
	hud_level_lbl.name = "hud_level_lbl"
	hud_level_lbl.add_theme_font_size_override("font_size", 26)
	hud_level_lbl.text = "LEVEL: 1"
	vb.add_child(hud_level_lbl)

	hud_score_lbl = Label.new()
	hud_score_lbl.name = "hud_score_lbl"
	hud_score_lbl.add_theme_font_size_override("font_size", 26)
	hud_score_lbl.text = "SCORE: 0 | TARGET: 0"
	vb.add_child(hud_score_lbl)

	hud_moves_lbl = Label.new()
	hud_moves_lbl.name = "hud_moves_lbl"
	hud_moves_lbl.add_theme_font_size_override("font_size", 26)
	hud_moves_lbl.text = "MOVES: 0"
	vb.add_child(hud_moves_lbl)

	tutorial_banner = Label.new()
	tutorial_banner.name = "tutorial_banner"
	tutorial_banner.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	tutorial_banner.add_theme_font_size_override("font_size", 20)
	tutorial_banner.text = TUTORIAL_TEXT
	vb.add_child(tutorial_banner)

	var pause_btn := Button.new()
	pause_btn.name = "Btn_GameplayHUD_to_PauseMenu"
	pause_btn.text = "Pause"
	pause_btn.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	pause_btn.offset_left = 36
	pause_btn.offset_right = -36
	pause_btn.offset_top = -150
	pause_btn.offset_bottom = -70
	pause_btn.pressed.connect(func() -> void:
		show_screen("PauseMenu")
	)
	_style_button(pause_btn)
	root.add_child(pause_btn)

func _style_button(btn: Button) -> void:
	StudioThemeAndVFX.attach_button_polish(btn)
	btn.add_theme_color_override("font_color", Color(0.96, 0.98, 1.0))

func show_screen(screen_name: String) -> void:
	if not screens.has(screen_name):
		return
	for key in screens.keys():
		screens[key].visible = false
	screens[screen_name].visible = true
	current_screen = screen_name
	screens[screen_name].modulate = Color(1, 1, 1, 0)
	var tw := create_tween()
	tw.tween_property(screens[screen_name], "modulate", Color(1, 1, 1, 1), 0.18)
	AnalyticsManager.record_event("screen_shown", {"screen": screen_name})

	var board_visible := screen_name in ["GameplayHUD", "PauseMenu", "WinLoseScreen"]
	GameManager.set_board_visible(board_visible)
	if screen_name == "GameplayHUD" and GameManager.state == "idle":
		GameManager.load_level(int(SaveManager.data.get("current_level", 1)))
	if screen_name == "MainMenu":
		AudioDirector.play_ui("click")

func update_hud(level_num: int, score: int, moves: int, target: int) -> void:
	if hud_level_lbl != null:
		hud_level_lbl.text = "LEVEL: %d" % level_num
	if hud_score_lbl != null:
		hud_score_lbl.text = "SCORE: %d | TARGET: %d" % [score, target]
	if hud_moves_lbl != null:
		hud_moves_lbl.text = "MOVES: %d" % moves

func set_result(won: bool, score: int, target: int) -> void:
	if result_lbl != null:
		result_lbl.text = ("VICTORY!\nSCORE %d / %d" % [score, target]) if won else ("TRY AGAIN\nSCORE %d / %d" % [score, target])
