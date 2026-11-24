extends Node

const VAULT_DIR := "res://assets/secure/"
const VAULT_FILE := "config_vault.enc"
const MAGIC := "STUDIOV1"

var _config: Dictionary = {}
var _loaded := false

func _ready() -> void:
        load_secure_vault()

func load_secure_vault() -> bool:
        var vault_path := VAULT_DIR + VAULT_FILE
        if not FileAccess.file_exists(vault_path):
                _loaded = true
                return false
        var f := FileAccess.open(vault_path, FileAccess.READ)
        if f == null:
                push_warning("[SECURE_LOADER] Unable to open encrypted config vault.")
                _loaded = true
                return false
        var raw := f.get_buffer(f.get_length())
        f.close()
        if raw.size() < 40:
                _loaded = true
                return false
        var magic := raw.slice(0, 8).get_string_from_ascii()
        if magic != MAGIC:
                push_warning("[SECURE_LOADER] Encrypted vault magic mismatch.")
                _loaded = true
                return false
        var salt := raw.slice(8, 24)
        var iv := raw.slice(24, 40)
        var ciphertext := raw.slice(40)
        var key := _derive_key(AppConfig.SECURE_CONFIG_KEY, salt)
        var aes := AESContext.new()
        var err := aes.start(AESContext.MODE_CBC_DECRYPT, key, iv)
        if err != OK:
                push_warning("[SECURE_LOADER] AES start failed: %s" % str(err))
                _loaded = true
                return false
        var plain: PackedByteArray = aes.update(ciphertext)
        aes.finish()
        aes = null
        if plain.is_empty():
                _loaded = true
                return false
        var pad := int(plain[plain.size() - 1])
        if pad > 0 and pad <= 16 and pad <= plain.size():
                plain = plain.slice(0, plain.size() - pad)
        var parsed = JSON.parse_string(plain.get_string_from_utf8())
        if typeof(parsed) == TYPE_DICTIONARY:
                _config = parsed
                _loaded = true
                return true
        _loaded = true
        return false

func _derive_key(secret: String, salt: PackedByteArray) -> PackedByteArray:
        var h := HashingContext.new()
        h.start(HashingContext.HASH_SHA256)
        h.update(secret.to_utf8_buffer())
        h.update(salt)
        return h.finish()

func get_config(key: String, fallback: Variant = null) -> Variant:
        if not _loaded:
                load_secure_vault()
        return _config.get(key, fallback)

func get_level_tuning(level_num: int) -> Dictionary:
        var levels: Array = get_config("levels", [])
        if levels.is_empty():
                return {}
        var idx := clampi(level_num - 1, 0, levels.size() - 1)
        return levels[idx] if typeof(levels[idx]) == TYPE_DICTIONARY else {}

func is_loaded() -> bool:
        return _loaded
