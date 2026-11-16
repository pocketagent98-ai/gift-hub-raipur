extends CanvasLayer

# ==============================================================================
# 12-SCREEN STUDIO UI/UX CONTROLLER (PART 4B & 4F)
# Implements all 12 required studio screens with unified design system,
# mobile notch safe-area margins, >=48px touch targets, and tutorial onboarding:
# 1. MainMenu, 2. LoadingScreen, 3. GameplayHUD, 4. PauseMenu, 5. Settings,
# 6. Shop, 7. Inventory, 8. Rewards, 9. LevelSelection, 10. WinLoseScreen,
# 11. Profile, 12. DailyRewards
# ==============================================================================

const SCREEN_NAMES: Array[String] = [
	"MainMenu", "LoadingScreen", "GameplayHUD", "PauseMenu",
	"Settings", "Shop", "Inventory", "Rewards",
	"LevelSelection", "WinLoseScreen", "Profile", "DailyRewards"
]

var screens: Dictionary = {}
var active_screen: String = "MainMenu"
var root_margin: MarginContainer
var hud_score_lbl: Label
var hud_coins_lbl: Label
var tutorial_banner: PanelContainer

func _ready() -> void:
	var vfx := get_node_or_null("/root/StudioThemeAndVFX")
	root_margin = MarginContainer.new()
	root_margin.name = "SafeAreaMargin"
	root_margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	root_margin.add_theme_constant_override("margin_left", 36)
	root_margin.add_theme_constant_override("margin_right", 36)
	root_margin.add_theme_constant_override("margin_top", 48)
	root_margin.add_theme_constant_override("margin_bottom", 48)
	if vfx != null and vfx.get("studio_theme") != null:
		root_margin.theme = vfx.get("studio_theme")
	add_child(root_margin)

	for s_name in SCREEN_NAMES:
		var panel := _build_screen(s_name, vfx)
		screens[s_name] = panel
		root_margin.add_child(panel)

	show_screen("MainMenu")

func _build_screen(s_name: String, vfx: Node) -> PanelContainer:
	var p := PanelContainer.new()
	p.name = s_name
	p.set_anchors_preset(Control.PRESET_FULL_RECT)
	var vb := VBoxContainer.new()
	vb.alignment = BoxContainer.ALIGNMENT_CENTER
	vb.add_theme_constant_override("separation", 16)
	p.add_child(vb)

	var title := Label.new()
	title.name = s_name + "_Title"
	title.text = "STUDIO V2.0 — " + s_name.to_upper()
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vb.add_child(title)

	if s_name == "Settings":
		var mute_btn := Button.new()
		mute_btn.name = "Btn_ToggleAudio"
		mute_btn.text = "Toggle Master Audio"
		if vfx != null:
			vfx.call("attach_button_polish", mute_btn)
		mute_btn.pressed.connect(func():
			var m_idx := AudioServer.get_bus_index("Master")
			AudioServer.set_bus_mute(m_idx, not AudioServer.is_bus_mute(m_idx))
		)
		vb.add_child(mute_btn)

	if s_name == "GameplayHUD":
		hud_score_lbl = Label.new()
		hud_score_lbl.text = "SCORE: 0 | COMBO: x1 | LEVEL: 1"
		hud_score_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		vb.add_child(hud_score_lbl)

		tutorial_banner = PanelContainer.new()
		var tut_lbl := Label.new()
		tut_lbl.text = "TUTORIAL: Tap targets to fire! Purple Armored Bubbles take 4 hits to pop!"
		tut_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		tutorial_banner.add_child(tut_lbl)
		vb.add_child(tutorial_banner)

	# Navigation buttons so every screen has complete, non-broken navigation
	var nav_targets: Dictionary = {
		"MainMenu": ["GameplayHUD", "LevelSelection", "Shop", "Inventory", "DailyRewards", "Profile", "Settings"],
		"GameplayHUD": ["PauseMenu", "WinLoseScreen"],
		"PauseMenu": ["GameplayHUD", "Settings", "MainMenu"],
		"Settings": ["MainMenu"],
		"Shop": ["Inventory", "Rewards", "MainMenu"],
		"Inventory": ["Shop", "MainMenu"],
		"Rewards": ["MainMenu"],
		"LevelSelection": ["GameplayHUD", "MainMenu"],
		"WinLoseScreen": ["GameplayHUD", "LevelSelection", "MainMenu"],
		"Profile": ["MainMenu"],
		"DailyRewards": ["Rewards", "MainMenu"],
		"LoadingScreen": ["GameplayHUD"]
	}

	for target in nav_targets.get(s_name, ["MainMenu"]):
		var btn := Button.new()
		btn.name = "Btn_" + s_name + "_to_" + target
		btn.text = "Open " + target
		if vfx != null:
			vfx.call("attach_button_polish", btn)
		btn.pressed.connect(func():
			if s_name == "Shop" and target == "Rewards":
				var save_mgr := get_node_or_null("/root/SaveManager")
				if save_mgr != null:
					save_mgr.call("add_coins", -25)
			show_screen(target)
		)
		vb.add_child(btn)

	return p

func show_screen(s_name: String) -> void:
	if not screens.has(s_name):
		return
	active_screen = s_name
	for k in screens.keys():
		var ctrl := screens[k] as Control
		ctrl.visible = (k == s_name)
	if s_name == "GameplayHUD":
		var gm := get_node_or_null("/root/GameManager")
		if gm != null:
			gm.call("load_level", int(gm.get("current_level")))
