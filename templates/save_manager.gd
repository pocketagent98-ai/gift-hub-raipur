extends Node

const SAVE_PATH := "user://savegame.json"
const SAVE_SCHEMA_VERSION := 2

var data: Dictionary = {
        "schema_version": SAVE_SCHEMA_VERSION,
        "coins": 500,
        "current_level": 1,
        "highest_level": 1,
        "best_score": 0,
        "boosters": {"hammer": 2, "shuffle": 2, "swap": 2},
        "level_stars": {},
        "ads_removed": false,
        "daily_reward_claimed": false,
        "daily_reward_day": 1,
        "last_claim_date": "",
        "vibration": true,
        "equipped_booster": "",
}

func _ready() -> void:
	load_game()

func save_game() -> bool:
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f == null:
		return false
	f.store_string(JSON.stringify(data))
	f.close()
	return true

func load_game() -> bool:
	if not FileAccess.file_exists(SAVE_PATH):
		return false
	var f := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if f == null:
		return false
	var parsed = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY:
		return false
	var migrated := migrate_save_schema(parsed)
	for key in migrated.keys():
		data[key] = migrated[key]
	return true

func migrate_save_schema(parsed: Dictionary) -> Dictionary:
	var migrated := parsed.duplicate(true)
	if not migrated.has("schema_version"):
		migrated["schema_version"] = 1
	if int(migrated["schema_version"]) < SAVE_SCHEMA_VERSION:
		if migrated.has("unlocked_level") and not migrated.has("current_level"):
			migrated["current_level"] = int(migrated["unlocked_level"])
		if migrated.has("high_score") and not migrated.has("best_score"):
			migrated["best_score"] = int(migrated["high_score"])
		migrated["schema_version"] = SAVE_SCHEMA_VERSION
	return migrated

func add_coins(amount: int) -> void:
	data["coins"] = int(data.get("coins", 0)) + amount
	save_game()

func spend_coins(amount: int) -> bool:
	if int(data.get("coins", 0)) < amount:
		return false
	data["coins"] = int(data.get("coins", 0)) - amount
	save_game()
	return true

func set_level(level_num: int) -> void:
	data["current_level"] = level_num
	data["highest_level"] = maxi(int(data.get("highest_level", 1)), level_num)
	save_game()

func add_booster(kind: String, amount: int = 1) -> void:
	var boosters: Dictionary = data.get("boosters", {})
	boosters[kind] = maxi(0, int(boosters.get(kind, 0)) + amount)
	data["boosters"] = boosters
	save_game()

func run_self_test() -> bool:
	var before: Dictionary = data.duplicate(true)
	data["self_test_marker"] = "roundtrip"
	var saved := save_game()
	var loaded := load_game()
	var ok := saved and loaded and str(data.get("self_test_marker", "")) == "roundtrip"
	data.erase("self_test_marker")
	data = before
	save_game()
	return ok
