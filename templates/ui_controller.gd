extends CanvasLayer

const Spec = preload("res://scripts/generated_ui_spec.gd")
const SCREEN_NAMES = [
        "MainMenu", "LoadingScreen", "GameplayHUD", "PauseMenu",
        "Settings", "Shop", "Inventory", "Rewards",
        "LevelSelection", "WinLoseScreen", "Profile", "DailyRewards",
]
const SafeAreaMargin := 32
const TOUCH_MIN := Vector2(96, 56)

var screens: Dictionary = {}
var current_screen := "LoadingScreen"
var hud_level_lbl: Label
var hud_goal_lbl: Label
var hud_moves_lbl: Label
var hud_score_lbl: Label
var hud_coin_lbl: Label
var hud_progress: ProgressBar
var tutorial_banner: Label
var result_lbl: Label
var result_stars: Label
var result_score_lbl: Label
var result_coin_lbl: Label
var coin_labels: Array[Label] = []
var booster_buttons: Dictionary = {}
var daily_grid: GridContainer
var inventory_grid: GridContainer
var level_grid: GridContainer
var loading_bar: ProgressBar
var toast_label: Label
var _toast_tween: Tween

var nav_targets: Dictionary = {
        "MainMenu": ["LevelSelection", "Shop", "DailyRewards", "Settings"],
        "LoadingScreen": ["MainMenu"],
        "GameplayHUD": ["PauseMenu"],
        "PauseMenu": ["GameplayHUD", "Settings", "MainMenu"],
        "Settings": ["MainMenu", "PauseMenu"],
        "Shop": ["MainMenu", "Inventory", "Rewards"],
        "Inventory": ["MainMenu", "Shop"],
        "Rewards": ["MainMenu", "DailyRewards", "Shop"],
        "LevelSelection": ["GameplayHUD", "MainMenu"],
        "WinLoseScreen": ["GameplayHUD", "LevelSelection", "MainMenu"],
        "Profile": ["MainMenu", "DailyRewards"],
        "DailyRewards": ["MainMenu", "Rewards"],
}

func _ready() -> void:
        layer = 10
        process_mode = Node.PROCESS_MODE_ALWAYS
        for screen_name in SCREEN_NAMES:
                var root := Control.new()
                root.name = screen_name
                root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
                root.visible = false
                root.mouse_filter = Control.MOUSE_FILTER_STOP
                add_child(root)
                screens[screen_name] = root
                _build_screen(screen_name, root)
        _build_toast()
        show_screen("LoadingScreen")
        _run_loading_sequence()

func _build_screen(screen_name: String, root: Control) -> void:
        match screen_name:
                "LoadingScreen": _build_loading(root)
                "MainMenu": _build_main_menu(root)
                "GameplayHUD": _build_gameplay_hud(root)
                "PauseMenu": _build_pause_menu(root)
                "Settings": _build_settings(root)
                "Shop": _build_shop(root)
                "Inventory": _build_inventory(root)
                "Rewards": _build_rewards(root)
                "LevelSelection": _build_level_selection(root)
                "WinLoseScreen": _build_win_lose(root)
                "Profile": _build_profile(root)
                "DailyRewards": _build_daily_rewards(root)

func _theme_color(key: String, fallback: String = "#FFFFFF") -> Color:
        return Color(str(Spec.THEME.get(key, fallback)))

func _gradient_bg(root: Control, top: Color, bottom: Color) -> void:
        var grad := Gradient.new()
        grad.colors = PackedColorArray([top, bottom])
        grad.offsets = PackedFloat32Array([0.0, 1.0])
        var tex := GradientTexture2D.new()
        tex.gradient = grad
        tex.width = 8
        tex.height = 256
        tex.fill_from = Vector2(0, 0)
        tex.fill_to = Vector2(0, 1)
        var bg := TextureRect.new()
        bg.name = "GradientBG"
        bg.texture = tex
        bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
        bg.stretch_mode = TextureRect.STRETCH_SCALE
        bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
        bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
        root.add_child(bg)

func _panel_style(color: Color, radius: int = 22, border: Color = Color(1, 1, 1, 0.14)) -> StyleBoxFlat:
        var sb := StyleBoxFlat.new()
        sb.bg_color = color
        sb.set_corner_radius_all(radius)
        sb.border_width_left = 2
        sb.border_width_right = 2
        sb.border_width_top = 2
        sb.border_width_bottom = 2
        sb.border_color = border
        sb.shadow_color = Color(0, 0, 0, 0.35)
        sb.shadow_size = 12
        sb.shadow_offset = Vector2(0, 6)
        sb.content_margin_left = 16
        sb.content_margin_right = 16
        sb.content_margin_top = 12
        sb.content_margin_bottom = 12
        return sb

func _panel(color: Color, radius: int = 22) -> PanelContainer:
        var p := PanelContainer.new()
        p.add_theme_stylebox_override("panel", _panel_style(color, radius))
        return p

func _label(text: String, size: int = 24, color: Color = Color.WHITE, align: int = HORIZONTAL_ALIGNMENT_CENTER) -> Label:
        var l := Label.new()
        l.text = text
        l.horizontal_alignment = align
        l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
        l.add_theme_font_size_override("font_size", size)
        l.add_theme_color_override("font_color", color)
        l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.65))
        l.add_theme_constant_override("shadow_offset_x", 2)
        l.add_theme_constant_override("shadow_offset_y", 3)
        l.autowrap_mode = TextServer.AUTOWRAP_OFF
        return l

func _button(text: String, callback: Callable, primary: bool = false, min_size: Vector2 = TOUCH_MIN) -> Button:
        var b := Button.new()
        b.text = text
        b.custom_minimum_size = min_size
        b.add_theme_font_size_override("font_size", 26)
        b.add_theme_color_override("font_color", Color.WHITE)
        b.add_theme_color_override("font_hover_color", Color.WHITE)
        var normal := _panel_style(_theme_color("accent") if primary else _theme_color("panel_alt"), 18)
        var hover := _panel_style((_theme_color("accent") if primary else _theme_color("panel_alt")).lightened(0.12), 18)
        var pressed := _panel_style((_theme_color("accent") if primary else _theme_color("panel_alt")).darkened(0.18), 18)
        b.add_theme_stylebox_override("normal", normal)
        b.add_theme_stylebox_override("hover", hover)
        b.add_theme_stylebox_override("pressed", pressed)
        b.add_theme_stylebox_override("disabled", _panel_style(Color(0.18, 0.2, 0.26, 0.7), 18))
        b.pressed.connect(func() -> void:
                AudioDirector.play_ui("click")
                Input.vibrate_handheld(16)
                callback.call()
        )
        return b

func _icon(name: String, size: Vector2 = Vector2(64, 64)) -> TextureRect:
        var icon := TextureRect.new()
        icon.custom_minimum_size = size
        icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
        icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
        var path := "res://assets/icons/%s.svg" % name
        if ResourceLoader.exists(path):
                icon.texture = load(path)
        icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
        return icon

func _safe_margin(root: Control, top: int = 48, bottom: int = 32) -> MarginContainer:
        var margin := MarginContainer.new()
        margin.name = "SafeAreaMargin"
        margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
        margin.add_theme_constant_override("margin_left", SafeAreaMargin)
        margin.add_theme_constant_override("margin_right", SafeAreaMargin)
        margin.add_theme_constant_override("margin_top", top)
        margin.add_theme_constant_override("margin_bottom", bottom)
        root.add_child(margin)
        return margin

func _top_bar(parent: Control, title: String, back_target: String = "") -> HBoxContainer:
        var bar := HBoxContainer.new()
        bar.custom_minimum_size = Vector2(0, 72)
        bar.add_theme_constant_override("separation", 12)
        if back_target != "":
                var back := _button("‹", func() -> void: show_screen(back_target), false, Vector2(56, 56))
                back.add_theme_font_size_override("font_size", 40)
                bar.add_child(back)
        var title_label := _label(title, 34, _theme_color("text"), HORIZONTAL_ALIGNMENT_LEFT)
        title_label.autowrap_mode = TextServer.AUTOWRAP_OFF
        title_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
        bar.add_child(title_label)
        var spacer := Control.new()
        spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
        bar.add_child(spacer)
        bar.add_child(_icon("coin_badge", Vector2(36, 36)))
        var coin := _label("0", 28, _theme_color("accent_2"), HORIZONTAL_ALIGNMENT_RIGHT)
        coin.custom_minimum_size = Vector2(86, 0)
        coin_labels.append(coin)
        bar.add_child(coin)
        parent.add_child(bar)
        return bar

func _nav_bar(parent: Control) -> void:
        var bar := HBoxContainer.new()
        bar.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
        bar.offset_left = 20
        bar.offset_right = -20
        bar.offset_top = -92
        bar.offset_bottom = -16
        bar.add_theme_constant_override("separation", 10)
        var entries := [
                ["SHOP", "Shop", "coin_badge"],
                ["LEVELS", "LevelSelection", "btn_play"],
                ["DAILY", "DailyRewards", "shield_armor"],
                ["SETTINGS", "Settings", "bomb_hazard"],
        ]
        for entry in entries:
                var btn := _button(str(entry[0]), func(target := str(entry[1])) -> void: show_screen(target), false, Vector2(0, 68))
                btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
                btn.add_theme_font_size_override("font_size", 18)
                btn.icon = _icon(str(entry[2]), Vector2(26, 26)).texture
                btn.expand_icon = true
                bar.add_child(btn)
        parent.add_child(bar)

func _build_loading(root: Control) -> void:
        _gradient_bg(root, _theme_color("bg_top"), _theme_color("bg_bottom"))
        var center := CenterContainer.new()
        center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
        root.add_child(center)
        var vb := VBoxContainer.new()
        vb.add_theme_constant_override("separation", 22)
        vb.custom_minimum_size = Vector2(520, 0)
        center.add_child(vb)
        vb.add_child(_label(Spec.GAME_TITLE, 54, _theme_color("accent")))
        vb.add_child(_label(Spec.TAGLINE, 22, _theme_color("text_dim")))
        var icon := _icon("btn_play", Vector2(120, 120))
        icon.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
        vb.add_child(icon)
        loading_bar = ProgressBar.new()
        loading_bar.name = "LoadingBar"
        loading_bar.custom_minimum_size = Vector2(460, 28)
        loading_bar.max_value = 100.0
        loading_bar.value = 0.0
        loading_bar.show_percentage = false
        var bar_bg := StyleBoxFlat.new()
        bar_bg.bg_color = Color(0.04, 0.06, 0.12, 0.85)
        bar_bg.set_corner_radius_all(14)
        var bar_fill := StyleBoxFlat.new()
        bar_fill.bg_color = _theme_color("accent")
        bar_fill.set_corner_radius_all(14)
        loading_bar.add_theme_stylebox_override("background", bar_bg)
        loading_bar.add_theme_stylebox_override("fill", bar_fill)
        vb.add_child(loading_bar)
        vb.add_child(_label("Loading original assets, levels and audio…", 18, _theme_color("text_dim")))

func _run_loading_sequence() -> void:
        await get_tree().create_timer(0.25).timeout
        if loading_bar != null:
                var tw := create_tween()
                tw.tween_property(loading_bar, "value", 100.0, 1.15)
                await tw.finished
        await get_tree().create_timer(0.2).timeout
        show_screen("MainMenu")

func _build_main_menu(root: Control) -> void:
        _gradient_bg(root, _theme_color("bg_top"), _theme_color("bg_bottom"))
        _add_menu_particles(root)
        var margin := _safe_margin(root, 56, 120)
        var vb := VBoxContainer.new()
        vb.add_theme_constant_override("separation", 14)
        margin.add_child(vb)
        var top := HBoxContainer.new()
        top.add_child(_icon("coin_badge", Vector2(40, 40)))
        var coin := _label("0", 30, _theme_color("accent_2"), HORIZONTAL_ALIGNMENT_LEFT)
        coin_labels.append(coin)
        top.add_child(coin)
        var spacer := Control.new()
        spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
        top.add_child(spacer)
        top.add_child(_label("LEVEL %d / 30" % int(SaveManager.data.get("highest_level", 1)), 22, _theme_color("text_dim")))
        vb.add_child(top)
        var center := VBoxContainer.new()
        center.alignment = BoxContainer.ALIGNMENT_CENTER
        center.size_flags_vertical = Control.SIZE_EXPAND_FILL
        center.add_theme_constant_override("separation", 18)
        vb.add_child(center)
        center.add_child(_label(Spec.GAME_TITLE, 58, _theme_color("accent")))
        center.add_child(_label(Spec.TAGLINE, 24, _theme_color("text_dim")))
        var logo_icon := _icon("btn_play", Vector2(150, 150))
        logo_icon.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
        center.add_child(logo_icon)
        var play := _button("PLAY", _on_play_pressed, true, Vector2(360, 92))
        play.add_theme_font_size_override("font_size", 38)
        play.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
        center.add_child(play)
        var levels := _button("LEVEL MAP", func() -> void: show_screen("LevelSelection"), false, Vector2(300, 64))
        levels.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
        center.add_child(levels)
        _nav_bar(root)

func _add_menu_particles(root: Control) -> void:
        var p := CPUParticles2D.new()
        p.name = "MenuParticles"
        p.amount = 44
        p.lifetime = 4.5
        p.emitting = true
        p.direction = Vector2(0, -1)
        p.spread = 180.0
        p.gravity = Vector2(0, -12)
        p.initial_velocity_min = 12.0
        p.initial_velocity_max = 55.0
        p.scale_amount_min = 0.35
        p.scale_amount_max = 1.2
        p.color = _theme_color("accent_2")
        p.position = Vector2(360, 1280)
        p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
        p.emission_rect_extents = Vector2(360, 20)
        root.add_child(p)

func _build_gameplay_hud(root: Control) -> void:
        var top_panel := _panel(_theme_color("panel"))
        top_panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
        top_panel.offset_left = 12
        top_panel.offset_right = -12
        top_panel.offset_top = 18
        top_panel.offset_bottom = 166
        root.add_child(top_panel)
        var top_margin := MarginContainer.new()
        top_margin.add_theme_constant_override("margin_left", 14)
        top_margin.add_theme_constant_override("margin_right", 14)
        top_margin.add_theme_constant_override("margin_top", 8)
        top_margin.add_theme_constant_override("margin_bottom", 8)
        top_panel.add_child(top_margin)
        var top_vb := VBoxContainer.new()
        top_vb.add_theme_constant_override("separation", 4)
        top_margin.add_child(top_vb)
        var row := HBoxContainer.new()
        row.add_theme_constant_override("separation", 12)
        top_vb.add_child(row)
        var left := VBoxContainer.new()
        left.add_theme_constant_override("separation", 2)
        left.custom_minimum_size = Vector2(170, 0)
        left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
        hud_level_lbl = _label("LEVEL 1", 26, _theme_color("text"), HORIZONTAL_ALIGNMENT_LEFT)
        hud_level_lbl.autowrap_mode = TextServer.AUTOWRAP_OFF
        hud_level_lbl.custom_minimum_size = Vector2(160, 0)
        left.add_child(hud_level_lbl)
        hud_goal_lbl = _label("GOAL 0 / 0", 18, _theme_color("text_dim"), HORIZONTAL_ALIGNMENT_LEFT)
        hud_goal_lbl.autowrap_mode = TextServer.AUTOWRAP_OFF
        hud_goal_lbl.custom_minimum_size = Vector2(160, 0)
        left.add_child(hud_goal_lbl)
        row.add_child(left)
        var mid := VBoxContainer.new()
        mid.add_theme_constant_override("separation", 2)
        mid.custom_minimum_size = Vector2(190, 0)
        mid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
        hud_moves_lbl = _label("MOVES 0", 24, _theme_color("accent_2"))
        hud_moves_lbl.autowrap_mode = TextServer.AUTOWRAP_OFF
        hud_moves_lbl.custom_minimum_size = Vector2(180, 0)
        mid.add_child(hud_moves_lbl)
        hud_score_lbl = _label("SCORE 0", 20, _theme_color("text"))
        hud_score_lbl.autowrap_mode = TextServer.AUTOWRAP_OFF
        hud_score_lbl.custom_minimum_size = Vector2(180, 0)
        mid.add_child(hud_score_lbl)
        row.add_child(mid)
        var right := VBoxContainer.new()
        right.add_theme_constant_override("separation", 2)
        right.custom_minimum_size = Vector2(140, 0)
        right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
        hud_coin_lbl = _label("COINS 0", 20, _theme_color("accent_2"))
        hud_coin_lbl.autowrap_mode = TextServer.AUTOWRAP_OFF
        hud_coin_lbl.custom_minimum_size = Vector2(130, 0)
        right.add_child(hud_coin_lbl)
        var pause := _button("II", func() -> void: show_screen("PauseMenu"), false, Vector2(64, 54))
        pause.add_theme_font_size_override("font_size", 24)
        right.add_child(pause)
        row.add_child(right)
        hud_progress = ProgressBar.new()
        hud_progress.custom_minimum_size = Vector2(0, 14)
        hud_progress.max_value = 100.0
        hud_progress.value = 0.0
        hud_progress.show_percentage = false
        var pbg := StyleBoxFlat.new()
        pbg.bg_color = Color(0, 0, 0, 0.35)
        pbg.set_corner_radius_all(7)
        var pfill := StyleBoxFlat.new()
        pfill.bg_color = _theme_color("success")
        pfill.set_corner_radius_all(7)
        hud_progress.add_theme_stylebox_override("background", pbg)
        hud_progress.add_theme_stylebox_override("fill", pfill)
        top_vb.add_child(hud_progress)
        tutorial_banner = _label(Spec.TUTORIAL, 18, _theme_color("text_dim"))
        tutorial_banner.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
        tutorial_banner.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
        tutorial_banner.offset_left = 24
        tutorial_banner.offset_right = -24
        tutorial_banner.offset_top = 176
        tutorial_banner.offset_bottom = 232
        root.add_child(tutorial_banner)
        var tray := _panel(_theme_color("panel"))
        tray.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
        tray.offset_left = 12
        tray.offset_right = -12
        tray.offset_top = -150
        tray.offset_bottom = -12
        root.add_child(tray)
        var tray_margin := MarginContainer.new()
        tray_margin.add_theme_constant_override("margin_left", 14)
        tray_margin.add_theme_constant_override("margin_right", 14)
        tray_margin.add_theme_constant_override("margin_top", 8)
        tray_margin.add_theme_constant_override("margin_bottom", 8)
        tray.add_child(tray_margin)
        var tray_vb := VBoxContainer.new()
        tray_vb.add_theme_constant_override("separation", 4)
        tray_margin.add_child(tray_vb)
        tray_vb.add_child(_label("BOOSTERS", 16, _theme_color("text_dim"), HORIZONTAL_ALIGNMENT_LEFT))
        var tray_row := HBoxContainer.new()
        tray_row.add_theme_constant_override("separation", 10)
        tray_vb.add_child(tray_row)
        for booster in Spec.BOOSTERS:
                var kind := str(booster.get("id", "hammer"))
                var btn := _button(str(booster.get("name", kind)), func(selected_kind := kind) -> void: _on_booster_pressed(selected_kind), false, Vector2(0, 64))
                btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
                btn.add_theme_font_size_override("font_size", 18)
                btn.icon = _icon(str(booster.get("icon", "bomb_hazard")), Vector2(28, 28)).texture
                btn.expand_icon = true
                tray_row.add_child(btn)
                booster_buttons[kind] = btn

func _build_pause_menu(root: Control) -> void:
        _gradient_bg(root, _theme_color("bg_top"), _theme_color("bg_bottom"))
        var center := CenterContainer.new()
        center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
        root.add_child(center)
        var panel := _panel(_theme_color("panel"))
        panel.custom_minimum_size = Vector2(520, 0)
        center.add_child(panel)
        var vb := VBoxContainer.new()
        vb.add_theme_constant_override("separation", 14)
        panel.add_child(vb)
        vb.add_child(_label("PAUSED", 42, _theme_color("accent")))
        vb.add_child(_button("RESUME", func() -> void: show_screen("GameplayHUD"), true, Vector2(0, 64)))
        vb.add_child(_button("RESTART LEVEL", func() -> void: GameManager.load_level(GameManager.current_level), false, Vector2(0, 64)))
        vb.add_child(_button("SETTINGS", func() -> void: show_screen("Settings"), false, Vector2(0, 64)))
        vb.add_child(_button("MAIN MENU", func() -> void: show_screen("MainMenu"), false, Vector2(0, 64)))

func _build_settings(root: Control) -> void:
        _gradient_bg(root, _theme_color("bg_top"), _theme_color("bg_bottom"))
        var margin := _safe_margin(root, 48, 32)
        var vb := VBoxContainer.new()
        vb.add_theme_constant_override("separation", 14)
        margin.add_child(vb)
        _top_bar(vb, "SETTINGS", "MainMenu")
        vb.add_child(_button("TOGGLE MASTER AUDIO", _toggle_audio, false, Vector2(0, 64)))
        vb.add_child(_button("TOGGLE VIBRATION", _toggle_vibration, false, Vector2(0, 64)))
        vb.add_child(_button("PRIVACY POLICY", func() -> void: show_toast("Privacy policy is available in the store listing."), false, Vector2(0, 64)))
        vb.add_child(_button("BACK", func() -> void: show_screen("MainMenu"), false, Vector2(0, 64)))

func _build_shop(root: Control) -> void:
        _gradient_bg(root, _theme_color("bg_top"), _theme_color("bg_bottom"))
        var margin := _safe_margin(root, 40, 32)
        var vb := VBoxContainer.new()
        vb.add_theme_constant_override("separation", 10)
        margin.add_child(vb)
        _top_bar(vb, "SHOP", "MainMenu")
        var scroll := ScrollContainer.new()
        scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
        vb.add_child(scroll)
        var grid := GridContainer.new()
        grid.columns = 2
        grid.add_theme_constant_override("h_separation", 12)
        grid.add_theme_constant_override("v_separation", 12)
        grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
        scroll.add_child(grid)
        for item in Spec.SHOP_ITEMS:
                grid.add_child(_shop_card(item))

func _shop_card(item: Dictionary) -> Control:
        var card := _panel(_theme_color("panel_alt"))
        card.custom_minimum_size = Vector2(0, 250)
        card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
        var vb := VBoxContainer.new()
        vb.add_theme_constant_override("separation", 6)
        card.add_child(vb)
        var icon := _icon(str(item.get("icon", "coin_badge")), Vector2(64, 64))
        icon.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
        vb.add_child(icon)
        vb.add_child(_label(str(item.get("title", "Item")), 22, _theme_color("text")))
        var desc := _label(str(item.get("desc", "")), 16, _theme_color("text_dim"))
        desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
        desc.custom_minimum_size = Vector2(0, 44)
        vb.add_child(desc)
        vb.add_child(_label(str(item.get("price_label", "₹99")), 20, _theme_color("accent_2")))
        vb.add_child(_button("BUY", func(selected_item := item) -> void: _on_shop_buy(selected_item), true, Vector2(0, 52)))
        return card

func _build_level_selection(root: Control) -> void:
        _gradient_bg(root, _theme_color("bg_top"), _theme_color("bg_bottom"))
        var margin := _safe_margin(root, 40, 32)
        var vb := VBoxContainer.new()
        vb.add_theme_constant_override("separation", 10)
        margin.add_child(vb)
        _top_bar(vb, "LEVELS", "MainMenu")
        var scroll := ScrollContainer.new()
        scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
        vb.add_child(scroll)
        level_grid = GridContainer.new()
        level_grid.columns = 5
        level_grid.add_theme_constant_override("h_separation", 10)
        level_grid.add_theme_constant_override("v_separation", 10)
        scroll.add_child(level_grid)
        _refresh_level_grid()

func _refresh_level_grid() -> void:
        if level_grid == null:
                return
        for child in level_grid.get_children():
                child.free()
        var highest := int(SaveManager.data.get("highest_level", 1))
        var stars: Dictionary = SaveManager.data.get("level_stars", {})
        for level in range(1, 31):
                var unlocked := level <= highest
                var star_count := int(stars.get(str(level), 0))
                var text := "%d\n%s" % [level, "★".repeat(star_count) + "☆".repeat(3 - star_count)]
                var btn := _button(text, func(selected_level := level) -> void: _on_level_pressed(selected_level), false, Vector2(0, 96))
                btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
                btn.add_theme_font_size_override("font_size", 18)
                btn.disabled = not unlocked
                if not unlocked:
                        btn.text = "%d\nLOCK" % level
                level_grid.add_child(btn)

func _build_daily_rewards(root: Control) -> void:
        _gradient_bg(root, _theme_color("bg_top"), _theme_color("bg_bottom"))
        var margin := _safe_margin(root, 40, 32)
        var vb := VBoxContainer.new()
        vb.add_theme_constant_override("separation", 12)
        margin.add_child(vb)
        _top_bar(vb, "DAILY REWARDS", "MainMenu")
        var scroll := ScrollContainer.new()
        scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
        vb.add_child(scroll)
        daily_grid = GridContainer.new()
        daily_grid.columns = 2
        daily_grid.add_theme_constant_override("h_separation", 12)
        daily_grid.add_theme_constant_override("v_separation", 12)
        scroll.add_child(daily_grid)
        _refresh_daily_grid()

func _refresh_daily_grid() -> void:
        if daily_grid == null:
                return
        for child in daily_grid.get_children():
                child.free()
        var claimed_day := int(SaveManager.data.get("daily_reward_day", 1))
        var today := Time.get_date_string_from_system()
        var claimed_today := str(SaveManager.data.get("last_claim_date", "")) == today
        for reward in Spec.DAILY_REWARDS:
                var day := int(reward.get("day", 1))
                var card := _panel(_theme_color("panel_alt"))
                card.custom_minimum_size = Vector2(0, 180)
                card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
                var cvb := VBoxContainer.new()
                cvb.add_theme_constant_override("separation", 4)
                card.add_child(cvb)
                cvb.add_child(_label("DAY %d" % day, 22, _theme_color("accent")))
                cvb.add_child(_label("%d coins" % int(reward.get("coins", 0)), 18, _theme_color("text")))
                var booster := str(reward.get("booster", ""))
                if booster != "":
                        cvb.add_child(_label("+ %s" % booster.capitalize(), 16, _theme_color("text_dim")))
                var state := "CLAIMED" if (claimed_today or day < claimed_day) else ("CLAIM" if day == claimed_day else "LOCKED")
                var btn := _button(state, func(selected_day: int = day, selected_reward: Dictionary = reward) -> void: _claim_daily(selected_day, selected_reward), day == claimed_day and not claimed_today, Vector2(0, 52))
                btn.disabled = state != "CLAIM"
                cvb.add_child(btn)
                daily_grid.add_child(card)

func _build_inventory(root: Control) -> void:
        _gradient_bg(root, _theme_color("bg_top"), _theme_color("bg_bottom"))
        var margin := _safe_margin(root, 40, 32)
        var vb := VBoxContainer.new()
        vb.add_theme_constant_override("separation", 12)
        margin.add_child(vb)
        _top_bar(vb, "INVENTORY", "MainMenu")
        inventory_grid = GridContainer.new()
        inventory_grid.columns = 1
        inventory_grid.add_theme_constant_override("v_separation", 12)
        vb.add_child(inventory_grid)
        _refresh_inventory_grid()

func _refresh_inventory_grid() -> void:
        if inventory_grid == null:
                return
        for child in inventory_grid.get_children():
                child.free()
        var boosters: Dictionary = SaveManager.data.get("boosters", {})
        for booster in Spec.BOOSTERS:
                var kind := str(booster.get("id", "hammer"))
                var card := _panel(_theme_color("panel_alt"))
                card.custom_minimum_size = Vector2(0, 100)
                var row := HBoxContainer.new()
                row.add_theme_constant_override("separation", 12)
                card.add_child(row)
                row.add_child(_icon(str(booster.get("icon", "bomb_hazard")), Vector2(56, 56)))
                var info := VBoxContainer.new()
                info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
                info.add_child(_label(str(booster.get("name", kind)), 22, _theme_color("text"), HORIZONTAL_ALIGNMENT_LEFT))
                var bdesc := _label(str(booster.get("desc", "")), 16, _theme_color("text_dim"), HORIZONTAL_ALIGNMENT_LEFT)
                bdesc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
                info.add_child(bdesc)
                row.add_child(info)
                row.add_child(_label("x%d" % int(boosters.get(kind, 0)), 24, _theme_color("accent_2")))
                inventory_grid.add_child(card)

func _build_rewards(root: Control) -> void:
        _gradient_bg(root, _theme_color("bg_top"), _theme_color("bg_bottom"))
        var margin := _safe_margin(root, 48, 32)
        var vb := VBoxContainer.new()
        vb.add_theme_constant_override("separation", 14)
        margin.add_child(vb)
        _top_bar(vb, "REWARDS", "MainMenu")
        vb.add_child(_button("DAILY REWARDS", func() -> void: show_screen("DailyRewards"), true, Vector2(0, 68)))
        vb.add_child(_button("WATCH AD: +50 COINS", func() -> void: _watch_ad_coins(), false, Vector2(0, 68)))
        vb.add_child(_button("FREE BOOSTER", func() -> void: _free_booster(), false, Vector2(0, 68)))
        vb.add_child(_button("BACK", func() -> void: show_screen("MainMenu"), false, Vector2(0, 68)))

func _build_win_lose(root: Control) -> void:
        var dim := ColorRect.new()
        dim.color = Color(0, 0, 0, 0.72)
        dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
        root.add_child(dim)
        var center := CenterContainer.new()
        center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
        root.add_child(center)
        var panel := _panel(_theme_color("panel"))
        panel.custom_minimum_size = Vector2(560, 0)
        center.add_child(panel)
        var vb := VBoxContainer.new()
        vb.add_theme_constant_override("separation", 10)
        panel.add_child(vb)
        result_lbl = _label("LEVEL COMPLETE", 40, _theme_color("accent"))
        vb.add_child(result_lbl)
        result_stars = _label("★★★", 42, _theme_color("accent_2"))
        vb.add_child(result_stars)
        result_score_lbl = _label("SCORE 0 / 0", 24, _theme_color("text"))
        vb.add_child(result_score_lbl)
        result_coin_lbl = _label("+0 COINS", 24, _theme_color("accent_2"))
        vb.add_child(result_coin_lbl)
        vb.add_child(_button("NEXT LEVEL", func() -> void: GameManager.load_level(mini(GameManager.current_level + 1, 30)), true, Vector2(0, 64)))
        vb.add_child(_button("RETRY", func() -> void: GameManager.load_level(GameManager.current_level), false, Vector2(0, 64)))
        vb.add_child(_button("WATCH AD: +5 MOVES", func() -> void: _watch_ad_moves(), false, Vector2(0, 64)))
        vb.add_child(_button("MAIN MENU", func() -> void: show_screen("MainMenu"), false, Vector2(0, 64)))

func _build_profile(root: Control) -> void:
        _gradient_bg(root, _theme_color("bg_top"), _theme_color("bg_bottom"))
        var margin := _safe_margin(root, 48, 32)
        var vb := VBoxContainer.new()
        vb.add_theme_constant_override("separation", 12)
        margin.add_child(vb)
        _top_bar(vb, "PROFILE", "MainMenu")
        var stats := _panel(_theme_color("panel_alt"))
        var svb := VBoxContainer.new()
        stats.add_child(svb)
        svb.add_child(_label("Highest level: %d" % int(SaveManager.data.get("highest_level", 1)), 24, _theme_color("text")))
        svb.add_child(_label("Best score: %d" % int(SaveManager.data.get("best_score", 0)), 24, _theme_color("text")))
        svb.add_child(_label("Coins: %d" % int(SaveManager.data.get("coins", 0)), 24, _theme_color("text")))
        svb.add_child(_label("Genre: %s" % Spec.GENRE.capitalize(), 22, _theme_color("text_dim")))
        vb.add_child(stats)
        vb.add_child(_button("BACK", func() -> void: show_screen("MainMenu"), false, Vector2(0, 64)))

func _build_toast() -> void:
        toast_label = _label("", 22, Color.WHITE)
        toast_label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
        toast_label.offset_left = 40
        toast_label.offset_right = -40
        toast_label.offset_top = -210
        toast_label.offset_bottom = -160
        toast_label.modulate = Color(1, 1, 1, 0)
        add_child(toast_label)

func show_toast(message: String) -> void:
        if toast_label == null:
                return
        toast_label.text = message
        toast_label.modulate = Color(1, 1, 1, 1)
        if _toast_tween != null and _toast_tween.is_valid():
                _toast_tween.kill()
        _toast_tween = create_tween()
        _toast_tween.tween_interval(1.2)
        _toast_tween.tween_property(toast_label, "modulate", Color(1, 1, 1, 0), 0.35)

func _on_play_pressed() -> void:
        var level := maxi(1, int(SaveManager.data.get("current_level", 1)))
        GameManager.load_level(level)

func _on_level_pressed(level: int) -> void:
        GameManager.load_level(level)

func _on_booster_pressed(kind: String) -> void:
        var ok: bool = GameManager.use_booster(kind)
        show_toast("%s used" % kind.capitalize() if ok else "No %s left" % kind.capitalize())

func _on_shop_buy(item: Dictionary) -> void:
        var kind := str(item.get("kind", "iap"))
        if kind == "coins":
                var price := int(item.get("price_coins", 0))
                if SaveManager.spend_coins(price):
                        SaveManager.add_coins(int(item.get("reward_coins", 0)))
                        show_toast("Purchase complete")
                else:
                        show_toast("Not enough coins")
        else:
                MonetizationManager.purchase(str(item.get("sku", "starter_pack")))
                show_toast("Purchase simulated" if not AppConfig.is_production_ads() else "Purchase complete")
        refresh_coins()

func _claim_daily(day: int, reward: Dictionary) -> void:
        var today := Time.get_date_string_from_system()
        if str(SaveManager.data.get("last_claim_date", "")) == today:
                show_toast("Already claimed today")
                return
        SaveManager.add_coins(int(reward.get("coins", 0)))
        var booster := str(reward.get("booster", ""))
        if booster != "":
                SaveManager.add_booster(booster, 1)
        SaveManager.data["last_claim_date"] = today
        SaveManager.data["daily_reward_day"] = mini(day + 1, 7)
        SaveManager.save_game()
        AudioDirector.play_sfx("coin")
        show_toast("Daily reward claimed")
        refresh_coins()
        _refresh_daily_grid()

func _watch_ad_moves() -> void:
        MonetizationManager.show_rewarded(func() -> void:
                GameManager.add_moves(5)
                show_screen("GameplayHUD")
        )

func _watch_ad_coins() -> void:
        MonetizationManager.show_rewarded(func() -> void:
                SaveManager.add_coins(50)
                refresh_coins()
                show_toast("+50 coins")
        )

func _free_booster() -> void:
        SaveManager.add_booster("hammer", 1)
        show_toast("+1 Hammer")
        _refresh_inventory_grid()

func _toggle_audio() -> void:
        var master := AudioServer.get_bus_index("Master")
        AudioServer.set_bus_mute(master, not AudioServer.is_bus_mute(master))
        show_toast("Audio toggled")

func _toggle_vibration() -> void:
        var enabled := not bool(SaveManager.data.get("vibration", true))
        SaveManager.data["vibration"] = enabled
        SaveManager.save_game()
        show_toast("Vibration %s" % ("on" if enabled else "off"))

func refresh_coins() -> void:
        var coins := int(SaveManager.data.get("coins", 0))
        for label in coin_labels:
                if is_instance_valid(label):
                        label.text = str(coins)
        if hud_coin_lbl != null:
                hud_coin_lbl.text = "COINS %d" % coins

func update_hud(level: int, score: int, moves: int, target: int) -> void:
        if hud_level_lbl != null:
                hud_level_lbl.text = "LEVEL %d" % level
        if hud_goal_lbl != null:
                hud_goal_lbl.text = "GOAL %d / %d" % [score, target]
        if hud_moves_lbl != null:
                hud_moves_lbl.text = ("MOVES %d" if Spec.GENRE == "match_3" else "SCREWS %d") % moves
        if hud_score_lbl != null:
                hud_score_lbl.text = "SCORE %d" % score
        if hud_progress != null:
                hud_progress.value = clampf((float(score) / max(float(target), 1.0)) * 100.0, 0.0, 100.0)
        refresh_coins()
        var boosters: Dictionary = SaveManager.data.get("boosters", {})
        for kind in booster_buttons.keys():
                var btn := booster_buttons[kind] as Button
                if btn != null:
                        var base: String = kind
                        for booster in Spec.BOOSTERS:
                                if str(booster.get("id", "")) == kind:
                                        base = str(booster.get("name", kind))
                        btn.text = "%s x%d" % [base, int(boosters.get(kind, 0))]

func set_result(win: bool, score: int, target: int) -> void:
        if result_lbl != null:
                result_lbl.text = "LEVEL COMPLETE!" if win else "OUT OF MOVES"
                result_lbl.add_theme_color_override("font_color", _theme_color("success") if win else _theme_color("danger"))
        if result_stars != null:
                result_stars.text = "★★★" if score >= target else ("★★☆" if score >= target * 0.65 else "★☆☆")
        if result_score_lbl != null:
                result_score_lbl.text = "SCORE %d / %d" % [score, target]
        if result_coin_lbl != null:
                result_coin_lbl.text = "+%d COINS" % (50 if win else 10)
        if win:
                SaveManager.add_coins(50)
        else:
                SaveManager.add_coins(10)
        refresh_coins()

func show_screen(screen_name: String) -> void:
        if not screens.has(screen_name):
                return
        for key in screens.keys():
                screens[key].visible = false
        screens[screen_name].visible = true
        current_screen = screen_name
        var board_layer := get_tree().root.find_child("BoardLayer", true, false) as CanvasLayer
        if board_layer != null:
                board_layer.visible = screen_name == "GameplayHUD"
        if screen_name == "LevelSelection":
                _refresh_level_grid()
        if screen_name == "DailyRewards":
                _refresh_daily_grid()
        if screen_name == "Inventory":
                _refresh_inventory_grid()
        if screen_name == "GameplayHUD":
                refresh_coins()
        var tw := create_tween()
        screens[screen_name].modulate = Color(1, 1, 1, 0)
        tw.tween_property(screens[screen_name], "modulate", Color(1, 1, 1, 1), 0.18)
