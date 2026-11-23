extends Node

const MIN_SFX_INTERVAL_MS := 60
const SAMPLE_RATE := 44100

var _last_sfx_ms := 0
var _music_player: AudioStreamPlayer
var _sfx_player: AudioStreamPlayer
var _ui_player: AudioStreamPlayer
var _tones: Dictionary = {}

func _ready() -> void:
	_ensure_buses()
	_music_player = _make_player("Music")
	_sfx_player = _make_player("SFX")
	_ui_player = _make_player("UI")
	_tones["click"] = _tone(880.0, 0.06, 0.25)
	_tones["pop"] = _tone(660.0, 0.10, 0.35)
	_tones["win"] = _tone(1046.5, 0.22, 0.40)
	_tones["lose"] = _tone(196.0, 0.25, 0.40)
	_tones["coin"] = _tone(1318.5, 0.08, 0.30)
	_start_music_loop()

func _ensure_buses() -> void:
	for bus_name in ["Music", "SFX", "UI"]:
		if AudioServer.get_bus_index(bus_name) == -1:
			var idx := AudioServer.bus_count
			AudioServer.add_bus(idx)
			AudioServer.set_bus_name(idx, bus_name)
			AudioServer.set_bus_send(idx, "Master")

func _make_player(bus: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.bus = bus
	add_child(p)
	return p

func _tone(freq: float, duration: float, volume: float) -> AudioStreamWAV:
	var n := int(SAMPLE_RATE * duration)
	var bytes := PackedByteArray()
	bytes.resize(n * 2)
	for i in n:
		var t := float(i) / float(SAMPLE_RATE)
		var env := 1.0 - (float(i) / float(n))
		var sample := sin(TAU * freq * t) * volume * env
		bytes.encode_s16(i * 2, int(clamp(sample, -1.0, 1.0) * 32767.0))
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = SAMPLE_RATE
	wav.stereo = false
	wav.data = bytes
	return wav

func _start_music_loop() -> void:
	var wav := _tone(220.0, 2.0, 0.07)
	wav.loop_mode = AudioStreamWAV.LOOP_FORWARD
	wav.loop_begin = 0
	wav.loop_end = SAMPLE_RATE * 2
	_music_player.stream = wav
	_music_player.volume_db = -14.0
	_music_player.play()

func _start_procedural_generator() -> void:
	var generator := AudioStreamGenerator.new()
	generator.mix_rate = SAMPLE_RATE
	generator.buffer_length = 0.25
	var player := _make_player("Music")
	player.stream = generator
	player.volume_db = -30.0
	player.play()
	var playback := player.get_stream_playback() as AudioStreamGeneratorPlayback
	if playback != null:
		for i in 256:
			playback.push_frame(Vector2(0.0, 0.0))

func play_sfx(sound_name: String) -> void:
	var now := Time.get_ticks_msec()
	if now - _last_sfx_ms < MIN_SFX_INTERVAL_MS:
		return
	_last_sfx_ms = now
	if _tones.has(sound_name):
		_sfx_player.stream = _tones[sound_name]
		_sfx_player.play()

func play_ui(sound_name: String) -> void:
	if _tones.has(sound_name):
		_ui_player.stream = _tones[sound_name]
		_ui_player.play()

func set_master_muted(muted: bool) -> void:
	var master := AudioServer.get_bus_index("Master")
	AudioServer.set_bus_mute(master, muted)

func cleanup_qa_runtime_objects() -> void:
	pass
