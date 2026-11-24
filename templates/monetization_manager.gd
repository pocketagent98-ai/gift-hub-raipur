extends Node

const MOCK_DURATION_SEC := 2.0

var consent_granted := false
var _overlay: CanvasLayer
var _backdrop: ColorRect
var _panel: PanelContainer
var _label: Label
var _timer: Timer
var _reward_cb: Callable = Callable()

func _ready() -> void:
	_build_overlay()

func set_user_consent(value: bool) -> void:
	consent_granted = value
	AnalyticsManager.record_event("consent_updated", {"granted": value})

func _build_overlay() -> void:
	_overlay = CanvasLayer.new()
	_overlay.layer = 100
	add_child(_overlay)

	_backdrop = ColorRect.new()
	_backdrop.color = Color(0.0, 0.0, 0.0, 0.72)
	_backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
	_backdrop.visible = false
	_overlay.add_child(_backdrop)

	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_backdrop.add_child(center)

	_panel = PanelContainer.new()
	_panel.custom_minimum_size = Vector2(560, 360)
	var ad_style := StyleBoxFlat.new()
	ad_style.bg_color = Color(0.06, 0.05, 0.12, 0.97)
	ad_style.border_color = Color(0.45, 0.85, 1.0, 0.95)
	ad_style.set_border_width_all(4)
	ad_style.set_corner_radius_all(22)
	_panel.add_theme_stylebox_override("panel", ad_style)
	center.add_child(_panel)

	_label = Label.new()
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_label.custom_minimum_size = Vector2(520, 0)
	_label.add_theme_font_size_override("font_size", 32)
	_label.text = "SIMULATED AD"
	_panel.add_child(_label)

	_timer = Timer.new()
	_timer.one_shot = true
	add_child(_timer)
	_timer.timeout.connect(_on_mock_ad_finished)

func _show_mock(kind: String, reward_cb: Callable = Callable()) -> void:
	_reward_cb = reward_cb
	_label.text = "SIMULATED %s\n2s QA TEMPLATE\nZERO REAL IMPRESSIONS" % kind.to_upper()
	_backdrop.visible = true
	_timer.start(MOCK_DURATION_SEC)
	AnalyticsManager.record_event("mock_ad_shown", {"kind": kind, "mode": AppConfig.AD_MODE})

func show_banner() -> void:
	_show_mock("banner")

func show_interstitial() -> void:
	_show_mock("interstitial")

func show_rewarded(reward_cb: Callable) -> void:
	_show_mock("rewarded", reward_cb)

func _on_mock_ad_finished() -> void:
	_backdrop.visible = false
	if _reward_cb.is_valid():
		_on_rewarded_ad_earned_reward(_reward_cb)
	_reward_cb = Callable()

func _on_rewarded_ad_earned_reward(callback: Callable) -> void:
	callback.call()

func _on_purchase_acknowledged(sku: String) -> void:
	AnalyticsManager.record_event("purchase_acknowledged", {"sku": sku})
	if sku == "remove_ads":
		SaveManager.data["ads_removed"] = true
		SaveManager.save_game()
	elif sku == "starter_pack":
		SaveManager.add_coins(1200)
		SaveManager.add_booster("hammer", 3)
	elif sku == "coins_small":
		SaveManager.add_coins(1200)

func purchase(sku: String) -> bool:
	_on_purchase_acknowledged(sku)
	return true

func run_offline_resilience_test() -> bool:
	show_interstitial()
	return true
