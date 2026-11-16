extends Node

# ==============================================================================
# PRIVACY-RESPECTING LOCAL ANALYTICS MANAGER (V4.0)
# Tracks aggregate progression counters (session_start, level_complete,
# rewarded_ad_earned) locally in memory/user:// without collecting any PII.
# ==============================================================================

var counters: Dictionary = {
	"session_start": 0,
	"level_complete": 0,
	"level_fail": 0,
	"rewarded_ad_earned": 0,
	"iap_purchase_verified": 0
}

func _ready() -> void:
	record_event("session_start")

func record_event(event_name: String) -> void:
	counters[event_name] = int(counters.get(event_name, 0)) + 1

func get_summary() -> Dictionary:
	return counters.duplicate()
