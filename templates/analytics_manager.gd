extends Node

const ANALYTICS_PATH := "user://analytics.json"
const MAX_EVENTS := 300

var events: Array = []

func record_event(event_name: String, data: Dictionary = {}) -> void:
	events.append({
		"event": event_name,
		"data": data,
		"ts": Time.get_unix_time_from_system(),
	})
	if events.size() > MAX_EVENTS:
		events.pop_front()
	_save()

func _save() -> void:
	var f := FileAccess.open(ANALYTICS_PATH, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify({"events": events}))
	f.close()

func run_self_test() -> bool:
	record_event("self_test", {"ok": true})
	return FileAccess.file_exists(ANALYTICS_PATH)
