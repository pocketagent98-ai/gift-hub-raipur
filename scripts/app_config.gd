extends Node

# ==============================================================================
# HONEST CLIENT CONFIGURATION (V2.0)
# 1. Private API keys, backend tokens, and signing passwords are NEVER stored in
#    client APK/AAB builds (any client binary can be decompiled).
# 2. Only public client identifiers (e.g. AdMob App ID, Ad Unit IDs, Test Mode flag)
#    are stored here.
# ==============================================================================

const PUBLIC_CLIENT_CONFIG: Dictionary = {}

# Official Google AdMob Test IDs used safely whenever production IDs are not configured
const TEST_ADMOB_IDS: Dictionary = {
	"ADMOB_APP_ID": "ca-app-pub-3940256099942544~3347511713",
	"REWARDED_AD_UNIT_ID": "ca-app-pub-3940256099942544/5224354917",
	"INTERSTITIAL_AD_UNIT_ID": "ca-app-pub-3940256099942544/1033173712",
	"BANNER_AD_UNIT_ID": "ca-app-pub-3940256099942544/6300978111"
}

func is_test_ads_enabled() -> bool:
	if OS.is_debug_build():
		return true
	var flag: String = str(PUBLIC_CLIENT_CONFIG.get("USE_TEST_ADS", "true")).to_lower()
	return flag == "true" or flag == "1"

func get_ad_unit_id(unit_key: String) -> String:
	if not is_test_ads_enabled() and PUBLIC_CLIENT_CONFIG.has(unit_key):
		var prod_id: String = str(PUBLIC_CLIENT_CONFIG[unit_key]).strip_edges()
		if prod_id != "" and not prod_id.ends_with("0000000000"):
			return prod_id
	return str(TEST_ADMOB_IDS.get(unit_key, ""))
