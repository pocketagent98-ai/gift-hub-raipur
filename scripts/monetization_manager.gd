extends Node

# ==============================================================================
# COMMERCIAL MONETIZATION & CONSENT MANAGER (V3.0 — CALLBACK-VERIFIED)
# - Rewards and IAP entitlements are NEVER granted when show_rewarded_ad() or
#   purchase_sku() is called. They are ONLY granted inside verified provider
#   callbacks (`_on_rewarded_ad_earned_reward`, `_on_purchase_acknowledged`).
# - Connects to PoingGodotAdMob / GodotAdMob and GodotGooglePlayBilling signals.
# ==============================================================================

signal rewarded_ad_completed(reward_type: String, amount: int)
signal rewarded_ad_failed(reason: String)
signal interstitial_ad_closed()
signal purchase_completed(sku: String)
signal purchase_failed(sku: String, reason: String)
signal consent_updated(granted: bool)

var offline_mode: bool = false
var ad_loaded_rewarded: bool = false
var ad_loaded_interstitial: bool = false
var admob_singleton: Object = null
var billing_singleton: Object = null

var _pending_reward: Dictionary = {}
var _pending_purchase_sku: String = ""

func _ready() -> void:
	if Engine.has_singleton("PoingGodotAdMob"):
		admob_singleton = Engine.get_singleton("PoingGodotAdMob")
	elif Engine.has_singleton("GodotAdMob"):
		admob_singleton = Engine.get_singleton("GodotAdMob")

	if admob_singleton != null:
		if admob_singleton.has_signal("rewarded_ad_earned_reward"):
			admob_singleton.connect("rewarded_ad_earned_reward", Callable(self, "_on_rewarded_ad_earned_reward"))
		if admob_singleton.has_signal("rewarded_ad_failed_to_show"):
			admob_singleton.connect("rewarded_ad_failed_to_show", Callable(self, "_on_rewarded_ad_failed"))

	if Engine.has_singleton("GodotGooglePlayBilling"):
		billing_singleton = Engine.get_singleton("GodotGooglePlayBilling")
		if billing_singleton.has_signal("purchases_updated"):
			billing_singleton.connect("purchases_updated", Callable(self, "_on_purchases_updated"))
		if billing_singleton.has_signal("purchase_acknowledged"):
			billing_singleton.connect("purchase_acknowledged", Callable(self, "_on_purchase_acknowledged"))
		if billing_singleton.has_signal("purchase_error"):
			billing_singleton.connect("purchase_error", Callable(self, "_on_purchase_error"))

	_initialize_ad_lifecycle()

func set_user_consent(granted: bool) -> void:
	var save_mgr := get_node_or_null("/root/SaveManager")
	if save_mgr != null:
		save_mgr.state["consent_granted"] = granted
		save_mgr.save_game()
	emit_signal("consent_updated", granted)
	_initialize_ad_lifecycle()

func _initialize_ad_lifecycle() -> void:
	if offline_mode or admob_singleton == null:
		ad_loaded_rewarded = false
		ad_loaded_interstitial = false
		return
	var app_cfg := get_node_or_null("/root/AppConfig")
	var rew_id: String = app_cfg.call("get_ad_unit_id", "REWARDED_AD_UNIT_ID") if app_cfg != null else ""
	var int_id: String = app_cfg.call("get_ad_unit_id", "INTERSTITIAL_AD_UNIT_ID") if app_cfg != null else ""
	if admob_singleton.has_method("load_rewarded_ad") and rew_id != "":
		admob_singleton.call("load_rewarded_ad", rew_id)
		ad_loaded_rewarded = true
	if admob_singleton.has_method("load_interstitial_ad") and int_id != "":
		admob_singleton.call("load_interstitial_ad", int_id)
		ad_loaded_interstitial = true

func show_rewarded_ad(reward_type: String = "coins", amount: int = 50) -> bool:
	if offline_mode or not ad_loaded_rewarded or admob_singleton == null:
		emit_signal("rewarded_ad_failed", "ad_unavailable_or_offline")
		return false
	_pending_reward = {"type": reward_type, "amount": amount}
	if admob_singleton.has_method("show_rewarded_ad"):
		admob_singleton.call("show_rewarded_ad")
		return true
	_pending_reward.clear()
	return false

func _on_rewarded_ad_earned_reward(_currency: String, _provider_amount: int) -> void:
	if _pending_reward.is_empty():
		return
	var r_type: String = str(_pending_reward.get("type", "coins"))
	var r_amt: int = int(_pending_reward.get("amount", 0))
	_pending_reward.clear()
	if r_amt > 0 and r_type == "coins":
		var save_mgr := get_node_or_null("/root/SaveManager")
		if save_mgr != null:
			save_mgr.call("add_coins", r_amt)
	emit_signal("rewarded_ad_completed", r_type, r_amt)

func _on_rewarded_ad_failed(reason: String = "provider_error") -> void:
	_pending_reward.clear()
	emit_signal("rewarded_ad_failed", reason)

func show_interstitial_ad() -> bool:
	var save_mgr := get_node_or_null("/root/SaveManager")
	if save_mgr != null and bool(save_mgr.state.get("no_ads_purchased", false)):
		return false
	if offline_mode or not ad_loaded_interstitial or admob_singleton == null:
		return false
	if admob_singleton.has_method("show_interstitial_ad"):
		admob_singleton.call("show_interstitial_ad")
		emit_signal("interstitial_ad_closed")
		return true
	return false

func purchase_sku(sku: String) -> bool:
	var clean_sku := sku.strip_edges()
	if offline_mode or clean_sku == "" or billing_singleton == null:
		emit_signal("purchase_failed", clean_sku, "billing_unavailable_or_offline")
		return false
	_pending_purchase_sku = clean_sku
	if billing_singleton.has_method("purchase"):
		billing_singleton.call("purchase", clean_sku)
		return true
	_pending_purchase_sku = ""
	return false

func _on_purchases_updated(purchases: Array) -> void:
	for p in purchases:
		if typeof(p) == TYPE_DICTIONARY and int(p.get("purchase_state", 0)) == 1:
			var token: String = str(p.get("purchase_token", ""))
			var sku: String = str(p.get("sku", _pending_purchase_sku))
			if token != "" and billing_singleton != null and billing_singleton.has_method("acknowledgePurchase"):
				billing_singleton.call("acknowledgePurchase", token)
			else:
				_grant_verified_purchase(sku)

func _on_purchase_acknowledged(_purchase_token: String) -> void:
	if _pending_purchase_sku != "":
		var sku := _pending_purchase_sku
		_pending_purchase_sku = ""
		_grant_verified_purchase(sku)

func _on_purchase_error(_code: int, message: String) -> void:
	var failed_sku := _pending_purchase_sku
	_pending_purchase_sku = ""
	emit_signal("purchase_failed", failed_sku, message)

func _grant_verified_purchase(sku: String) -> void:
	if sku == "":
		return
	var save_mgr := get_node_or_null("/root/SaveManager")
	if save_mgr != null:
		if sku == "remove_ads_forever":
			save_mgr.state["no_ads_purchased"] = true
		var owned: Array = save_mgr.state.get("owned_items", [])
		if not owned.has(sku):
			owned.append(sku)
			save_mgr.state["owned_items"] = owned
		save_mgr.save_game()
	emit_signal("purchase_completed", sku)

func restore_purchases() -> Array:
	if billing_singleton != null and billing_singleton.has_method("queryPurchases"):
		billing_singleton.call("queryPurchases", "inapp")
	var save_mgr := get_node_or_null("/root/SaveManager")
	if save_mgr != null:
		return save_mgr.state.get("owned_items", [])
	return []

func run_offline_resilience_test() -> bool:
	var save_mgr := get_node_or_null("/root/SaveManager")
	var coins_before: int = int(save_mgr.state.get("coins", 0)) if save_mgr != null else 0
	offline_mode = true
	_initialize_ad_lifecycle()
	var ad_blocked: bool = not show_rewarded_ad("coins", 50)
	var iap_blocked: bool = not purchase_sku("remove_ads_forever")
	offline_mode = false
	var coins_after: int = int(save_mgr.state.get("coins", 0)) if save_mgr != null else 0
	return ad_blocked and iap_blocked and (coins_before == coins_after)
