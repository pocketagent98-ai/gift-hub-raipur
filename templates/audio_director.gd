extends Node

# ==============================================================================
# MUSICAL PROCEDURAL AUDIO DIRECTOR (V7.0 — MARIMBA / BELL / CHIME SYNTH)
# ==============================================================================

const SAMPLE_RATE: float = 22050.0
const MIN_SFX_INTERVAL_MS: int = 40

var _last_sfx_ms: int = 0
var _sfx_player: AudioStreamPlayer
var _ui_player: AudioStreamPlayer
var _muted: bool = false

func _ready() -> void:
	_ensure_buses()
	_sfx_player = AudioStreamPlayer.new()
	_sfx_player.bus = "SFX"
	add_child(_sfx_player)

	_ui_player = AudioStreamPlayer.new()
	_ui_player.bus = "UI"
	add_child(_ui_player)

func _ensure_buses() -> void:
	for bus_name in ["Music", "SFX", "UI"]:
		if AudioServer.get_bus_index(bus_name) == -1:
			AudioServer.add_bus()
			AudioServer.set_bus_name(AudioServer.get_bus_count() - 1, bus_name)

func toggle_mute() -> bool:
	_muted = not _muted
	var idx := AudioServer.get_bus_index("Master")
	if idx >= 0:
		AudioServer.set_bus_mute(idx, _muted)
	return _muted

func play_ui(_sound_name: String = "click") -> void:
	play_sfx("ui_click", 1)

func play_sfx(sfx_name: String, combo_level: int = 1) -> void:
	if _muted:
		return
	var now_ms := Time.get_ticks_msec()
	if now_ms - _last_sfx_ms < MIN_SFX_INTERVAL_MS:
		return
	_last_sfx_ms = now_ms

	var pentatonic := [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.66, 1318.51]
	var base_freq: float = pentatonic[clampi(combo_level - 1, 0, pentatonic.size() - 1)]

	match sfx_name:
		"ui_click", "click":
			_play_marimba_tone(_ui_player, 660.0, 0.06, 0.25)
		"place_block", "swap":
			_play_marimba_tone(_sfx_player, 440.0, 0.09, 0.35)
		"line_clear", "bubble_pop", "match", "pop", "coin":
			_play_chord(_sfx_player, [base_freq, base_freq * 1.25, base_freq * 1.5], 0.24, 0.35)
		"bubble_hit_crack", "armor_crack":
			_play_marimba_tone(_sfx_player, 320.0, 0.11, 0.35)
		"victory", "win":
			_play_chord(_sfx_player, [523.25, 659.25, 783.99, 1046.5], 0.38, 0.38)
		"invalid", "lose":
			_play_marimba_tone(_sfx_player, 196.0, 0.10, 0.25)
		_:
			_play_marimba_tone(_sfx_player, base_freq, 0.10, 0.28)

func _play_marimba_tone(player: AudioStreamPlayer, freq: float, duration: float, gain: float) -> void:
	var gen := AudioStreamGenerator.new()
	gen.mix_rate = SAMPLE_RATE
	gen.buffer_length = maxf(0.15, duration + 0.05)
	player.stream = gen
	player.play()
	var pb := player.get_stream_playback() as AudioStreamGeneratorPlayback
	if pb == null:
		return
	var total_frames := mini(pb.get_frames_available(), int(SAMPLE_RATE * duration))
	for i in range(total_frames):
		var t := float(i) / SAMPLE_RATE
		var env := exp(-t * (8.0 / maxf(duration, 0.05)))
		var s := (sin(TAU * freq * t) * 0.75 + sin(TAU * freq * 2.0 * t) * 0.25) * env * gain
		pb.push_frame(Vector2(s, s))

func _play_chord(player: AudioStreamPlayer, freqs: Array, duration: float, gain: float) -> void:
	var gen := AudioStreamGenerator.new()
	gen.mix_rate = SAMPLE_RATE
	gen.buffer_length = maxf(0.25, duration + 0.05)
	player.stream = gen
	player.play()
	var pb := player.get_stream_playback() as AudioStreamGeneratorPlayback
	if pb == null:
		return
	var total_frames := mini(pb.get_frames_available(), int(SAMPLE_RATE * duration))
	var inv_n := 1.0 / float(max(1, freqs.size()))
	for i in range(total_frames):
		var t := float(i) / SAMPLE_RATE
		var env := exp(-t * (5.5 / maxf(duration, 0.08)))
		var mix := 0.0
		for idx in range(freqs.size()):
			var f := float(freqs[idx])
			var delay := float(idx) * 0.03
			if t >= delay:
				mix += sin(TAU * f * (t - delay)) * inv_n
		var s := mix * env * gain
		pb.push_frame(Vector2(s, s))

func cleanup_qa_runtime_objects() -> void:
	pass
