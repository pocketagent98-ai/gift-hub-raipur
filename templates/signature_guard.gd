extends Node

# Best-effort runtime APK signer fingerprint check. The Java API is only
# available on Android; on desktop/QA it returns true so the game still boots.
static func get_apk_signing_cert_sha256() -> String:
        if not OS.has_feature("android"):
                return ""
        if not Engine.has_singleton("JavaClassWrapper"):
                return ""
        var activity_thread = JavaClassWrapper.wrap("android.app.ActivityThread")
        if activity_thread == null:
                return ""
        var app = activity_thread.currentApplication()
        if app == null:
                return ""
        var pm = app.getPackageManager()
        if pm == null:
                return ""
        var package_name = app.getPackageName()
        var info = pm.getPackageInfo(package_name, 64)
        if info == null:
                return ""
        var signatures = info.signatures
        if signatures == null or signatures.size() <= 0:
                return ""
        var signature = signatures[0]
        var bytes = signature.toByteArray()
        if bytes == null:
                return ""
        var h := HashingContext.new()
        h.start(HashingContext.HASH_SHA256)
        h.update(bytes)
        var digest: PackedByteArray = h.finish()
        return digest.hex_encode()

static func verify_expected(expected_sha256: String, strict: bool = false) -> bool:
        var expected := expected_sha256.strip_edges().replace(":", "").to_lower()
        if expected.is_empty():
                return true
        var actual := get_apk_signing_cert_sha256().to_lower()
        if actual.is_empty():
                push_warning("[SIGNATURE_GUARD] Could not read APK signer on this runtime; allowing boot.")
                return true
        if actual == expected:
                return true
        push_error("[SIGNATURE_GUARD] APK signer mismatch: expected %s got %s" % [expected, actual])
        if strict:
                return false
        return true
