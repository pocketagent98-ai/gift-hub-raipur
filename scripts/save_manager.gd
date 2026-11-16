extends Node

const SAVE_PATH: String = "user://savegame.json"
const CURRENT_SCHEMA_VERSION: int = 5

var state: Dictionary = {
	"schema_version": CURRENT_SCHEMA_VERSION,
	"coins": 250,
	"high_score": 0,
	"unlocked_level": 1,
	"equipped_skin": "neon_azure",
	"owned_items": ["neon_azure"],
	"daily_streak": 1,
	"last_claim_day": 0,
	"master_volume": 0.85,
	"music_volume": 0.70,
	"sfx_volume": 0.90,
	"haptics_enabled": true,
	"high_contrast_ui": false,
	"tutorial_completed": false,
	"consent_granted": false,
	"no_ads_purchased": false
}

func _ready() -> void:
	load_game()

func migrate_save_schema(loaded_dict: Dictionary) -> Dictionary:
	# Preserves all player coins, high_score, unlocked_level, owned_items, and no_ads_purchased
	# across future Android Target SDK and game version updates without data loss.
	var migrated := state.duplicate(true)
	for k in loaded_dict.keys():
		migrated[k] = loaded_dict[k]
	migrated["schema_version"] = CURRENT_SCHEMA_VERSION
	migrated["coins"] = max(0, int(migrated.get("coins", 250)))
	migrated["unlocked_level"] = max(1, int(migrated.get("unlocked_level", 1)))
	return migrated

func save_game() -> bool:
	state["schema_version"] = CURRENT_SCHEMA_VERSION
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f == null:
		push_error("[SaveManager] Failed to open " + SAVE_PATH + " for writing.")
		return false
	f.store_string(JSON.stringify(state, "\t"))
	f.close()
	return true

func load_game() -> bool:
	if not FileAccess.file_exists(SAVE_PATH):
		return save_game()
	var f := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if f == null:
		return false
	var raw := f.get_as_text()
	f.close()
	var parsed = JSON.parse_string(raw)
	if typeof(parsed) == TYPE_DICTIONARY:
		state = migrate_save_schema(parsed)
		return true
	return false

func add_coins(amount: int) -> void:
	state["coins"] = max(0, int(state.get("coins", 0)) + amount)
	save_game()

func unlock_level(lvl: int) -> void:
	if lvl > int(state.get("unlocked_level", 1)):
		state["unlocked_level"] = lvl
		save_game()

func run_self_test() -> bool:
	var orig_coins: int = int(state.get("coins", 0))
	state["coins"] = orig_coins + 77
	if not save_game():
		return false
	state["coins"] = 0
	if not load_game():
		return false
	var verified: bool = (int(state.get("coins", 0)) == orig_coins + 77) and (int(state.get("schema_version", 0)) == CURRENT_SCHEMA_VERSION)
	state["coins"] = orig_coins
	save_game()
	return verified
