extends Node

# ==============================================================================
# STUDIO AUDIO DIRECTOR (PART 4E)
# Manages Master, Music, SFX, and UI audio buses with polyphony limiters so
# sounds never clip or overlap harshly, and synthesizes clean procedural waveforms.
# ==============================================================================

var sfx_players: Array[AudioStreamPlayer] = []
var music_player: AudioStreamPlayer
var last_sfx_time_ms: Dictionary = {}
const MIN_SFX_INTERVAL_MS: int = 45

func _ready() -> void:
	_setup_audio_buses()
	music_player = AudioStreamPlayer.new()
	music_player.bus = "Music"
	add_child(music_player)

	for i in range(6):
		var p := AudioStreamPlayer.new()
		p.bus = "SFX"
		add_child(p)
		sfx_players.append(p)

func _setup_audio_buses() -> void:
	for bus_name in ["Music", "SFX", "UI"]:
		if AudioServer.get_bus_index(bus_name) == -1:
			var idx := AudioServer.bus_count
			AudioServer.add_bus(idx)
			AudioServer.set_bus_name(idx, bus_name)
			AudioServer.set_bus_send(idx, "Master")

func set_bus_volume_linear(bus_name: String, linear_val: float) -> void:
	var idx := AudioServer.get_bus_index(bus_name)
	if idx != -1:
		AudioServer.set_bus_volume_db(idx, linear_to_db(clampf(linear_val, 0.0001, 1.0)))

func play_sfx(event_name: String) -> void:
	var now_ms: int = Time.get_ticks_msec()
	var prev_ms: int = int(last_sfx_time_ms.get(event_name, 0))
	if now_ms - prev_ms < MIN_SFX_INTERVAL_MS:
		return
	last_sfx_time_ms[event_name] = now_ms

	var freqs: Dictionary = {
		"ui_click": 660.0,
		"bubble_hit_crack": 392.0,
		"bubble_pop": 880.0,
		"combo_chime": 1046.5,
		"reward_fanfare": 784.0,
		"level_win": 987.7,
		"level_lose": 220.0
	}
	var base_freq: float = float(freqs.get(event_name, 523.25))
	_trigger_tone(base_freq, 0.14)

func _trigger_tone(freq: float, duration: float) -> void:
	for p in sfx_players:
		if not p.playing:
			var gen := AudioStreamGenerator.new()
			gen.mix_rate = 22050.0
			gen.buffer_length = duration
			p.stream = gen
			p.play()
			var playback := p.get_stream_playback() as AudioStreamGeneratorPlayback
			if playback != null:
				var total_frames := int(gen.mix_rate * duration)
				for i in range(min(total_frames, playback.get_frames_available())):
					var t := float(i) / gen.mix_rate
					var env := 1.0 - (t / duration)
					var sample := sin(TAU * freq * t) * 0.25 * env
					playback.push_frame(Vector2(sample, sample))
			break
