extends CanvasLayer

# ==============================================================================
# COMMERCIAL-GRADE 12-SCREEN MOBILE UI CONTROLLER (V6.0)
# ==============================================================================

const SCREEN_NAMES: Array[String] = [
	"MainMenu", "LoadingScreen", "GameplayHUD", "PauseMenu",
	"Settings", "Shop", "Inventory", "Rewards",
	"LevelSelection", "WinLoseScreen", "Profile", "DailyRewards"
]

var screens: Dictionary = {}
var active_screen: String = "MainMenu"
var hud_score_lbl: Label
var hud_level_lbl: Label
var hud_coins_lbl: Label
var hud_juggle_btn: Button
var hud_hammer_btn: Button
var win_title_lbl: Label
var win_detail_lbl: Label
var board_view: Control

func _ready() -> void:
	var bg := ColorRect.new()
	bg.name = "StudioBackdrop"
	bg.color = Color(0.06, 0.09, 0.18, 1.0)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var safe := MarginContainer.new()
	safe.name = "SafeAreaMargin"
	safe.set_anchors_preset(Control.PRESET_FULL_RECT)
	safe.add_theme_constant_override("margin_left", 24)
	safe.add_theme_constant_override("margin_right", 24)
	safe.add_theme_constant_override("margin_top", 44)
	safe.add_theme_constant_override("margin_bottom", 32)
	add_child(safe)

	for s_name in SCREEN_NAMES:
		var panel := _build_screen(s_name)
		screens[s_name] = panel
		safe.add_child(panel)

	var gm := get_node_or_null("/root/GameManager")
	if gm != null:
		if gm.has_signal("score_changed"):
			gm.connect("score_changed", Callable(self, "_refresh_hud"))
		if gm.has_signal("level_changed"):
			gm.connect("level_changed", Callable(self, "_on_level_changed"))
		if gm.has_signal("state_changed"):
			gm.connect("state_changed", Callable(self, "_refresh_hud_noargs"))
		if gm.has_signal("level_completed"):
			gm.connect("level_completed", Callable(self, "_on_level_completed"))
		if gm.has_signal("game_over"):
			gm.connect("game_over", Callable(self, "_on_game_over"))

	show_screen("MainMenu")

func _styled_btn(label_txt: String, bg_col: Color, min_h: float = 64.0) -> Button:
	var b := Button.new()
	b.text = label_txt
	b.custom_minimum_size = Vector2(180, min_h)
	b.add_theme_font_size_override("font_size", 24)
	b.add_theme_color_override("font_color", Color(1, 1, 1))
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg_col
	sb.corner_radius_top_left = 18
	sb.corner_radius_top_right = 18
	sb.corner_radius_bottom_left = 18
	sb.corner_radius_bottom_right = 18
	sb.border_color = bg_col.lightened(0.35)
	sb.set_border_width_all(2)
	sb.content_margin_left = 16
	sb.content_margin_right = 16
	sb.content_margin_top = 10
	sb.content_margin_bottom = 10
	b.add_theme_stylebox_override("normal", sb)
	var sb_h := sb.duplicate()
	sb_h.bg_color = bg_col.lightened(0.12)
	b.add_theme_stylebox_override("hover", sb_h)
	b.add_theme_stylebox_override("pressed", sb_h)
	b.pressed.connect(func():
		var aud := get_node_or_null("/root/AudioDirector")
		if aud != null:
			aud.call("play_sfx", "ui_click")
	)
	return b

func _make_header(parent: VBoxContainer, title_txt: String, back_target: String) -> void:
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 12)
	var back_b := _styled_btn("< BACK", Color(0.20, 0.27, 0.44), 56.0)
	back_b.custom_minimum_size = Vector2(120, 56)
	back_b.name = "Btn_Back_" + title_txt.replace(" ", "")
	back_b.pressed.connect(func(): show_screen(back_target))
	hb.add_child(back_b)

	var title := Label.new()
	title.text = title_txt
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 30)
	title.add_theme_color_override("font_color", Color(0.95, 0.97, 1.0))
	hb.add_child(title)
	parent.add_child(hb)

func _build_screen(s_name: String) -> Control:
	var root := VBoxContainer.new()
	root.name = s_name
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_theme_constant_override("separation", 18)

	var gm := get_node_or_null("/root/GameManager")
	var gtitle := str(gm.get("GAME_TITLE")) if (gm != null and gm.get("GAME_TITLE") != null) else "Crystal Grid Cascade"
	var genre := str(gm.get("GENRE")) if (gm != null and gm.get("GENRE") != null) else "block_puzzle"

	if s_name == "MainMenu":
		root.alignment = BoxContainer.ALIGNMENT_CENTER
		var title := Label.new()
		title.text = gtitle.to_upper()
		title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		title.add_theme_font_size_override("font_size", 42)
		title.add_theme_color_override("font_color", Color(0.35, 0.85, 1.0))
		root.add_child(title)

		var sub := Label.new()
		sub.text = "Drag blocks onto the 8x8 crystal board, clear rows & columns, and ignite Fever Overdrive!" if genre == "block_puzzle" else "Swipe adjacent crystals to match 3+, unleash cascades, and conquer 30 handcrafted levels!"
		sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		sub.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		sub.add_theme_font_size_override("font_size", 20)
		sub.add_theme_color_override("font_color", Color(0.76, 0.84, 0.96))
		root.add_child(sub)

		var play_b := _styled_btn("PLAY NOW", Color(0.16, 0.72, 0.48), 78.0)
		play_b.name = "Btn_MainMenu_to_GameplayHUD"
		play_b.pressed.connect(func(): show_screen("GameplayHUD"))
		root.add_child(play_b)

		var lvl_b := _styled_btn("LEVEL MAP (1 - 30)", Color(0.22, 0.50, 0.86), 66.0)
		lvl_b.name = "Btn_MainMenu_to_LevelSelection"
		lvl_b.pressed.connect(func(): show_screen("LevelSelection"))
		root.add_child(lvl_b)

		var row_nav := HBoxContainer.new()
		row_nav.alignment = BoxContainer.ALIGNMENT_CENTER
		row_nav.add_theme_constant_override("separation", 12)
		for pair in [["SHOP", "Shop", Color(0.86, 0.52, 0.16)], ["DAILY", "DailyRewards", Color(0.54, 0.34, 0.88)], ["SETTINGS", "Settings", Color(0.28, 0.35, 0.50)]]:
			var nb := _styled_btn(pair[0], pair[2], 60.0)
			nb.name = "Btn_MainMenu_to_" + pair[1]
			nb.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			nb.custom_minimum_size = Vector2(100, 60)
			var dest: String = pair[1]
			nb.pressed.connect(func(): show_screen(dest))
			row_nav.add_child(nb)
		root.add_child(row_nav)

	elif s_name == "GameplayHUD":
		var top := HBoxContainer.new()
		top.add_theme_constant_override("separation", 10)
		hud_level_lbl = Label.new()
		hud_level_lbl.text = "LVL 1"
		hud_level_lbl.add_theme_font_size_override("font_size", 24)
		hud_level_lbl.add_theme_color_override("font_color", Color(0.45, 0.85, 1.0))
		top.add_child(hud_level_lbl)

		hud_score_lbl = Label.new()
		hud_score_lbl.text = "SCORE: 0 / 360"
		hud_score_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		hud_score_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		hud_score_lbl.add_theme_font_size_override("font_size", 24)
		hud_score_lbl.add_theme_color_override("font_color", Color(1.0, 0.92, 0.38))
		top.add_child(hud_score_lbl)

		var pause_b := _styled_btn("PAUSE", Color(0.24, 0.30, 0.48), 56.0)
		pause_b.name = "Btn_GameplayHUD_to_PauseMenu"
		pause_b.custom_minimum_size = Vector2(110, 56)
		pause_b.pressed.connect(func(): show_screen("PauseMenu"))
		top.add_child(pause_b)
		root.add_child(top)

		var hint := Label.new()
		hint.text = "TUTORIAL: Drag a block from the tray onto the 8x8 board (or tap piece then tap board)!" if genre == "block_puzzle" else "TUTORIAL: Swipe any two adjacent gems to match 3+ in a row!"
		hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		hint.add_theme_font_size_override("font_size", 17)
		hint.add_theme_color_override("font_color", Color(0.75, 0.85, 0.98))
		root.add_child(hint)

		var bv_script := load("res://scripts/board_view.gd")
		if bv_script != null:
			board_view = bv_script.new()
			board_view.name = "BoardView"
			root.add_child(board_view)

		if genre == "block_puzzle":
			var boosters := HBoxContainer.new()
			boosters.add_theme_constant_override("separation", 12)
			hud_juggle_btn = _styled_btn("JUGGLE SWAP (3)", Color(0.52, 0.34, 0.88), 58.0)
			hud_juggle_btn.name = "Btn_JuggleSwap"
			hud_juggle_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			hud_juggle_btn.pressed.connect(func():
				var g := get_node_or_null("/root/GameManager")
				if g != null and g.has_method("use_juggle_swap"):
					g.call("use_juggle_swap")
			)
			boosters.add_child(hud_juggle_btn)

			hud_hammer_btn = _styled_btn("HAMMER 3x3 (3)", Color(0.88, 0.34, 0.42), 58.0)
			hud_hammer_btn.name = "Btn_HammerBooster"
			hud_hammer_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			hud_hammer_btn.pressed.connect(func():
				var g := get_node_or_null("/root/GameManager")
				if g != null:
					g.set("hammer_mode_active", not bool(g.get("hammer_mode_active")))
					_refresh_hud_noargs()
			)
			boosters.add_child(hud_hammer_btn)
			root.add_child(boosters)

	elif s_name == "LevelSelection":
		_make_header(root, "LEVEL MAP (1 - 30)", "MainMenu")
		var scroll := ScrollContainer.new()
		scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
		var center := CenterContainer.new()
		center.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var grid := GridContainer.new()
		grid.columns = 5
		grid.add_theme_constant_override("h_separation", 12)
		grid.add_theme_constant_override("v_separation", 12)
		for lvl in range(1, 31):
			var lb := _styled_btn(str(lvl), Color(0.20, 0.52, 0.88) if lvl <= 10 else Color(0.24, 0.28, 0.42), 72.0)
			lb.custom_minimum_size = Vector2(104, 72)
			lb.name = "Btn_Level_%d" % lvl
			var target_lvl := lvl
			lb.pressed.connect(func():
				var g := get_node_or_null("/root/GameManager")
				if g != null:
					g.call("load_level", target_lvl)
				show_screen("GameplayHUD")
			)
			grid.add_child(lb)
		center.add_child(grid)
		scroll.add_child(center)
		root.add_child(scroll)

	elif s_name == "Shop":
		_make_header(root, "STUDIO SHOP", "MainMenu")
		var items := [
			["Starter Pack (500 Coins + Boosters) — INR 89", "starter_pack_099", Color(0.18, 0.64, 0.44)],
			["Remove Ads Forever — INR 249", "remove_ads_forever", Color(0.22, 0.48, 0.86)],
			["Mega Coin Vault (8,000 Coins) — INR 849", "coin_vault_mega_999", Color(0.76, 0.46, 0.16)],
			["Watch Rewarded Ad (+100 Free Coins)", "rewarded_ad", Color(0.56, 0.34, 0.86)]
		]
		for it in items:
			var sb := _styled_btn(it[0], it[2], 68.0)
			sb.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			var sku: String = it[1]
			sb.pressed.connect(func():
				var mon := get_node_or_null("/root/MonetizationManager")
				if mon != null:
					if sku == "rewarded_ad":
						mon.call("show_rewarded_ad", "coins", 100)
					else:
						mon.call("purchase_sku", sku)
			)
			root.add_child(sb)

	elif s_name == "Settings":
		_make_header(root, "SETTINGS", "MainMenu")
		var mute_b := _styled_btn("TOGGLE SOUND EFFECTS", Color(0.24, 0.54, 0.82), 68.0)
		mute_b.name = "Btn_ToggleAudio"
		mute_b.pressed.connect(func():
			var aud := get_node_or_null("/root/AudioDirector")
			if aud != null:
				var is_m: bool = aud.call("toggle_mute")
				mute_b.text = "SOUND: OFF" if is_m else "SOUND: ON"
		)
		root.add_child(mute_b)

	elif s_name == "PauseMenu":
		root.alignment = BoxContainer.ALIGNMENT_CENTER
		var pt := Label.new()
		pt.text = "PAUSED"
		pt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		pt.add_theme_font_size_override("font_size", 38)
		root.add_child(pt)
		var res_b := _styled_btn("RESUME GAME", Color(0.16, 0.72, 0.48), 70.0)
		res_b.pressed.connect(func(): show_screen("GameplayHUD"))
		root.add_child(res_b)
		var rst_b := _styled_btn("RESTART LEVEL", Color(0.84, 0.50, 0.18), 66.0)
		rst_b.pressed.connect(func():
			var g := get_node_or_null("/root/GameManager")
			if g != null:
				g.call("load_level", int(g.get("current_level")))
			show_screen("GameplayHUD")
		)
		root.add_child(rst_b)
		var mm_b := _styled_btn("MAIN MENU", Color(0.28, 0.34, 0.50), 64.0)
		mm_b.pressed.connect(func(): show_screen("MainMenu"))
		root.add_child(mm_b)

	elif s_name == "WinLoseScreen":
		root.alignment = BoxContainer.ALIGNMENT_CENTER
		win_title_lbl = Label.new()
		win_title_lbl.text = "LEVEL COMPLETE!"
		win_title_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		win_title_lbl.add_theme_font_size_override("font_size", 38)
		win_title_lbl.add_theme_color_override("font_color", Color(1.0, 0.88, 0.30))
		root.add_child(win_title_lbl)

		win_detail_lbl = Label.new()
		win_detail_lbl.text = "Great job! +50 Coins Earned"
		win_detail_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		win_detail_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		win_detail_lbl.add_theme_font_size_override("font_size", 22)
		root.add_child(win_detail_lbl)

		var nxt_b := _styled_btn("NEXT LEVEL", Color(0.16, 0.72, 0.48), 72.0)
		nxt_b.pressed.connect(func():
			var g := get_node_or_null("/root/GameManager")
			if g != null:
				g.call("load_level", mini(30, int(g.get("current_level")) + 1))
			show_screen("GameplayHUD")
		)
		root.add_child(nxt_b)

		var home_b := _styled_btn("MAIN MENU", Color(0.26, 0.34, 0.50), 64.0)
		home_b.pressed.connect(func(): show_screen("MainMenu"))
		root.add_child(home_b)

	else:
		_make_header(root, s_name.to_upper(), "MainMenu")
		var info := Label.new()
		info.text = "Welcome to %s — claim daily coins, track your stats, and unlock crystal themes!" % s_name
		info.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		info.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		info.add_theme_font_size_override("font_size", 22)
		root.add_child(info)
		var claim_b := _styled_btn("CLAIM +50 COINS", Color(0.18, 0.68, 0.46), 66.0)
		claim_b.pressed.connect(func():
			var sm := get_node_or_null("/root/SaveManager")
			if sm != null:
				sm.call("add_coins", 50)
			show_screen("MainMenu")
		)
		root.add_child(claim_b)

	return root

func _on_level_changed(_lvl: int) -> void:
	_refresh_hud_noargs()

func _refresh_hud(_s: int, _c: int) -> void:
	_refresh_hud_noargs()

func _refresh_hud_noargs() -> void:
	var gm := get_node_or_null("/root/GameManager")
	if gm == null:
		return
	if hud_level_lbl != null:
		hud_level_lbl.text = "LVL %d" % int(gm.get("current_level"))
	if hud_score_lbl != null:
		var goal := int(gm.get("level_goal"))
		var sc := int(gm.get("current_score"))
		var combo := int(gm.get("current_combo"))
		var ctxt := ("  x%d!" % combo) if combo > 1 else ""
		hud_score_lbl.text = "SCORE: %d / %d%s" % [sc, goal, ctxt]
	if hud_juggle_btn != null:
		hud_juggle_btn.text = "JUGGLE SWAP (%d)" % int(gm.get("juggle_swaps_remaining"))
	if hud_hammer_btn != null:
		var act := bool(gm.get("hammer_mode_active"))
		hud_hammer_btn.text = ("TAP BOARD TO SMASH!" if act else "HAMMER 3x3 (%d)" % int(gm.get("hammer_boosters_remaining")))

func _on_level_completed(lvl: int, final_score: int) -> void:
	if win_title_lbl != null:
		win_title_lbl.text = "LEVEL %d CLEARED!" % lvl
	if win_detail_lbl != null:
		win_detail_lbl.text = "Final Score: %d | +50 Coins Added!" % final_score
	show_screen("WinLoseScreen")

func _on_game_over(final_score: int) -> void:
	if win_title_lbl != null:
		win_title_lbl.text = "OUT OF MOVES!"
	if win_detail_lbl != null:
		win_detail_lbl.text = "Score: %d — Tap Retry or use Juggle Swap!" % final_score
	show_screen("WinLoseScreen")

func show_screen(s_name: String) -> void:
	if not screens.has(s_name):
		return
	active_screen = s_name
	for k in screens.keys():
		(screens[k] as Control).visible = (k == s_name)
	if s_name == "GameplayHUD":
		_refresh_hud_noargs()
		if board_view != null:
			board_view.queue_redraw()
