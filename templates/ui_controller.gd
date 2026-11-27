extends CanvasLayer

# ==============================================================================
# COMMERCIAL-GRADE 12-SCREEN MOBILE UI CONTROLLER (V7.0 — MULTI-GENRE POLISHED)
# ==============================================================================

const Spec = preload("res://scripts/generated_ui_spec.gd")
const TOUCH_MIN := Vector2(96, 56)

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

func _theme_color(key: String, fallback: String = "#FFFFFF") -> Color:
	return Color(str(Spec.THEME.get(key, fallback)))

func _ready() -> void:
	var bg := ColorRect.new()
	bg.name = "StudioBackdrop"
	bg.color = _theme_color("bg_top", "#0F172E")
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	_add_menu_particles(self)

	var safe := MarginContainer.new()
	safe.name = "SafeAreaMargin"
	safe.set_anchors_preset(Control.PRESET_FULL_RECT)
	safe.add_theme_constant_override("margin_left", 24)
	safe.add_theme_constant_override("margin_right", 24)
	safe.add_theme_constant_override("margin_top", 44)
	safe.add_theme_constant_override("margin_bottom", 32)
	add_child(safe)

	for s_name in SCREEN_NAMES:
		var panel: Control = _build_screen(s_name)
		screens[s_name] = panel
		safe.add_child(panel)

	var gm: Node = get_node_or_null("/root/GameManager")
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

func _add_menu_particles(parent: Node) -> void:
	var p := CPUParticles2D.new()
	p.name = "MenuParticles"
	p.amount = 32
	p.lifetime = 4.0
	p.emitting = true
	p.direction = Vector2(0, -1)
	p.spread = 180.0
	p.gravity = Vector2(0, -10)
	p.initial_velocity_min = 12.0
	p.initial_velocity_max = 45.0
	p.scale_amount_min = 0.4
	p.scale_amount_max = 1.1
	p.color = _theme_color("accent_2", "#FFD166")
	p.position = Vector2(360, 1240)
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = Vector2(340, 20)
	parent.add_child(p)

func _styled_btn(label_txt: String, bg_col: Color, min_h: float = 64.0) -> Button:
	var b := Button.new()
	b.text = label_txt
	b.custom_minimum_size = Vector2(maxf(TOUCH_MIN.x, 180.0), maxf(TOUCH_MIN.y, min_h))
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
	var sb_h: StyleBoxFlat = sb.duplicate() as StyleBoxFlat
	sb_h.bg_color = bg_col.lightened(0.12)
	b.add_theme_stylebox_override("hover", sb_h)
	b.add_theme_stylebox_override("pressed", sb_h)
	b.pressed.connect(func():
		Input.vibrate_handheld(16)
		var aud: Node = get_node_or_null("/root/AudioDirector")
		if aud != null:
			aud.call("play_sfx", "ui_click")
	)
	return b

func _make_header(parent: VBoxContainer, title_txt: String, back_target: String) -> void:
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 12)
	var back_b: Button = _styled_btn("< BACK", Color(0.20, 0.27, 0.44), 56.0)
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

	var gm: Node = get_node_or_null("/root/GameManager")
	var gtitle: String = str(Spec.GAME_TITLE)
	if gm != null and gm.get("GAME_TITLE") != null and str(gm.get("GAME_TITLE")) != "":
		gtitle = str(gm.get("GAME_TITLE"))
	var genre: String = str(Spec.GENRE)
	if gm != null and gm.get("GENRE") != null and str(gm.get("GENRE")) != "":
		genre = str(gm.get("GENRE"))
	elif gm != null and gm.get("genre") != null and str(gm.get("genre")) != "":
		genre = str(gm.get("genre"))

	if s_name == "MainMenu":
		root.alignment = BoxContainer.ALIGNMENT_CENTER
		var title := Label.new()
		title.text = gtitle.to_upper()
		title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		title.add_theme_font_size_override("font_size", 42)
		title.add_theme_color_override("font_color", _theme_color("accent", "#59D9FF"))
		root.add_child(title)

		var sub := Label.new()
		if genre == "block_puzzle":
			sub.text = "Drag blocks onto the 8x8 crystal board, clear rows & columns, and ignite Fever Overdrive!"
		elif genre == "screw_puzzle":
			sub.text = "Unscrew color-matched bolts, drop layered plates, and master 30 handcrafted mechanical puzzles!"
		else:
			sub.text = "Swipe adjacent crystals to match 3+, unleash cascades, and conquer 30 handcrafted levels!"
		sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		sub.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		sub.add_theme_font_size_override("font_size", 20)
		sub.add_theme_color_override("font_color", Color(0.76, 0.84, 0.96))
		root.add_child(sub)

		var play_b: Button = _styled_btn("PLAY NOW", Color(0.16, 0.72, 0.48), 78.0)
		play_b.name = "Btn_MainMenu_to_GameplayHUD"
		play_b.pressed.connect(func():
			var g: Node = get_node_or_null("/root/GameManager")
			if g != null and g.has_method("load_level"):
				g.call("load_level", maxi(1, int(g.get("current_level"))))
			show_screen("GameplayHUD")
		)
		root.add_child(play_b)

		var lvl_b: Button = _styled_btn("LEVEL MAP (1 - 30)", Color(0.22, 0.50, 0.86), 66.0)
		lvl_b.name = "Btn_MainMenu_to_LevelSelection"
		lvl_b.pressed.connect(func(): show_screen("LevelSelection"))
		root.add_child(lvl_b)

		var row_nav := HBoxContainer.new()
		row_nav.alignment = BoxContainer.ALIGNMENT_CENTER
		row_nav.add_theme_constant_override("separation", 12)
		for pair in [["SHOP", "Shop", Color(0.86, 0.52, 0.16)], ["DAILY", "DailyRewards", Color(0.54, 0.34, 0.88)], ["SETTINGS", "Settings", Color(0.28, 0.35, 0.50)]]:
			var nb: Button = _styled_btn(str(pair[0]), pair[2], 60.0)
			nb.name = "Btn_MainMenu_to_" + str(pair[1])
			nb.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			nb.custom_minimum_size = Vector2(100, 60)
			var dest: String = str(pair[1])
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

		var pause_b: Button = _styled_btn("PAUSE", Color(0.24, 0.30, 0.48), 56.0)
		pause_b.name = "Btn_GameplayHUD_to_PauseMenu"
		pause_b.custom_minimum_size = Vector2(110, 56)
		pause_b.pressed.connect(func(): show_screen("PauseMenu"))
		top.add_child(pause_b)
		root.add_child(top)

		var hint := Label.new()
		if genre == "block_puzzle":
			hint.text = "TUTORIAL: Drag a block from the tray onto the 8x8 board (or tap piece then tap board)!"
		elif genre == "screw_puzzle":
			hint.text = "TUTORIAL: Tap color-matched screws to clear each layered plate!"
		else:
			hint.text = "TUTORIAL: Swipe any two adjacent gems to match 3+ in a row!"
		hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		hint.add_theme_font_size_override("font_size", 17)
		hint.add_theme_color_override("font_color", Color(0.75, 0.85, 0.98))
		root.add_child(hint)

		if genre != "screw_puzzle":
			var bv_script: GDScript = load("res://scripts/board_view.gd") as GDScript
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
				var g: Node = get_node_or_null("/root/GameManager")
				if g != null and g.has_method("use_juggle_swap"):
					g.call("use_juggle_swap")
			)
			boosters.add_child(hud_juggle_btn)

			hud_hammer_btn = _styled_btn("HAMMER 3x3 (3)", Color(0.88, 0.34, 0.42), 58.0)
			hud_hammer_btn.name = "Btn_HammerBooster"
			hud_hammer_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			hud_hammer_btn.pressed.connect(func():
				var g: Node = get_node_or_null("/root/GameManager")
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
			var lb: Button = _styled_btn(str(lvl), Color(0.20, 0.52, 0.88) if lvl <= 10 else Color(0.24, 0.28, 0.42), 72.0)
			lb.custom_minimum_size = Vector2(104, 72)
			lb.name = "Btn_Level_%d" % lvl
			var target_lvl: int = lvl
			lb.pressed.connect(func():
				var g: Node = get_node_or_null("/root/GameManager")
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
		var items: Array = [
			["Starter Pack (500 Coins + Boosters) — INR 89", "starter_pack_099", Color(0.18, 0.64, 0.44)],
			["Remove Ads Forever — INR 249", "remove_ads_forever", Color(0.22, 0.48, 0.86)],
			["Mega Coin Vault (8,000 Coins) — INR 849", "coin_vault_mega_999", Color(0.76, 0.46, 0.16)],
			["Watch Rewarded Ad (+100 Free Coins)", "rewarded_ad", Color(0.56, 0.34, 0.86)]
		]
		for it in items:
			var sb: Button = _styled_btn(str(it[0]), it[2], 68.0)
			sb.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			var sku: String = str(it[1])
			sb.pressed.connect(func():
				var mon: Node = get_node_or_null("/root/MonetizationManager")
				if mon != null:
					if sku == "rewarded_ad":
						mon.call("show_rewarded_ad", "coins", 100)
					else:
						mon.call("purchase_sku", sku)
			)
			root.add_child(sb)

	elif s_name == "Settings":
		_make_header(root, "SETTINGS", "MainMenu")
		var mute_b: Button = _styled_btn("TOGGLE SOUND EFFECTS", Color(0.24, 0.54, 0.82), 68.0)
		mute_b.name = "Btn_ToggleAudio"
		mute_b.pressed.connect(func():
			var m_idx: int = AudioServer.get_bus_index("Master")
			if m_idx >= 0:
				var next_muted: bool = not AudioServer.is_bus_mute(m_idx)
				AudioServer.set_bus_mute(m_idx, next_muted)
				mute_b.text = "SOUND: OFF" if next_muted else "SOUND: ON"
		)
		root.add_child(mute_b)

	elif s_name == "PauseMenu":
		root.alignment = BoxContainer.ALIGNMENT_CENTER
		var pt := Label.new()
		pt.text = "PAUSED"
		pt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		pt.add_theme_font_size_override("font_size", 38)
		root.add_child(pt)
		var res_b: Button = _styled_btn("RESUME GAME", Color(0.16, 0.72, 0.48), 70.0)
		res_b.pressed.connect(func(): show_screen("GameplayHUD"))
		root.add_child(res_b)
		var rst_b: Button = _styled_btn("RESTART LEVEL", Color(0.84, 0.50, 0.18), 66.0)
		rst_b.pressed.connect(func():
			var g: Node = get_node_or_null("/root/GameManager")
			if g != null:
				g.call("load_level", int(g.get("current_level")))
			show_screen("GameplayHUD")
		)
		root.add_child(rst_b)
		var mm_b: Button = _styled_btn("MAIN MENU", Color(0.28, 0.34, 0.50), 64.0)
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

		var nxt_b: Button = _styled_btn("NEXT LEVEL", Color(0.16, 0.72, 0.48), 72.0)
		nxt_b.pressed.connect(func():
			var g: Node = get_node_or_null("/root/GameManager")
			if g != null:
				g.call("load_level", mini(30, int(g.get("current_level")) + 1))
			show_screen("GameplayHUD")
		)
		root.add_child(nxt_b)

		var home_b: Button = _styled_btn("MAIN MENU", Color(0.26, 0.34, 0.50), 64.0)
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
		var claim_b: Button = _styled_btn("CLAIM +50 COINS", Color(0.18, 0.68, 0.46), 66.0)
		claim_b.pressed.connect(func():
			var sm: Node = get_node_or_null("/root/SaveManager")
			if sm != null:
				sm.call("add_coins", 50)
			show_screen("MainMenu")
		)
		root.add_child(claim_b)

	return root

func update_hud(level: int, score: int, _moves: int, target: int) -> void:
	if hud_level_lbl != null:
		hud_level_lbl.text = "LVL %d" % level
	if hud_score_lbl != null:
		hud_score_lbl.text = "SCORE: %d / %d" % [score, target]

func set_result(win: bool, score: int, target: int) -> void:
	if win_title_lbl != null:
		win_title_lbl.text = "LEVEL COMPLETE!" if win else "OUT OF MOVES!"
	if win_detail_lbl != null:
		win_detail_lbl.text = "Score: %d / %d" % [score, target]

func _on_level_changed(_lvl: int) -> void:
	_refresh_hud_noargs()

func _refresh_hud(_s: int, _c: int) -> void:
	_refresh_hud_noargs()

func _refresh_hud_noargs() -> void:
	var gm: Node = get_node_or_null("/root/GameManager")
	if gm == null:
		return
	if hud_level_lbl != null:
		hud_level_lbl.text = "LVL %d" % int(gm.get("current_level"))
	if hud_score_lbl != null:
		var goal: int = int(gm.get("level_goal")) if gm.get("level_goal") != null else int(gm.get("target_score"))
		var sc: int = int(gm.get("current_score")) if gm.get("current_score") != null else int(gm.get("score"))
		var combo: int = int(gm.get("current_combo")) if gm.get("current_combo") != null else int(gm.get("combo"))
		var ctxt: String = ("  x%d!" % combo) if combo > 1 else ""
		hud_score_lbl.text = "SCORE: %d / %d%s" % [sc, goal, ctxt]
	if hud_juggle_btn != null and gm.get("juggle_swaps_remaining") != null:
		hud_juggle_btn.text = "JUGGLE SWAP (%d)" % int(gm.get("juggle_swaps_remaining"))
	if hud_hammer_btn != null and gm.get("hammer_boosters_remaining") != null:
		var act: bool = bool(gm.get("hammer_mode_active"))
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

func show_screen(screen_name: String) -> void:
	if not screens.has(screen_name):
		return
	active_screen = screen_name
	for k in screens.keys():
		(screens[k] as Control).visible = (k == screen_name)
	var board_layer: CanvasLayer = get_tree().root.find_child("BoardLayer", true, false) as CanvasLayer
	if board_layer != null:
		board_layer.visible = (screen_name == "GameplayHUD")
	if screen_name == "GameplayHUD":
		_refresh_hud_noargs()
		if board_view != null:
			board_view.queue_redraw()
	var tw: Tween = create_tween()
	screens[screen_name].modulate = Color(1, 1, 1, 0)
	tw.tween_property(screens[screen_name], "modulate", Color(1, 1, 1, 1), 0.18)
