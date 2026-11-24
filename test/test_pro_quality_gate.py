import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import ai_game_designer
import multi_video_inspector
import pro_quality_gate
import release_hardening
import studio_game_factory


class AntiStubGateTests(unittest.TestCase):
    def test_gate_rejects_old_dummy_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "docs").mkdir()
            (root / "scripts/ui_controller.gd").write_text(
                'extends CanvasLayer\nfunc _ready():\n    var title := Label.new()\n    title.text = "STUDIO V2.0 — MAIN MENU"\n    var b := Button.new()\n    b.text = "Open GameplayHUD"\n',
                encoding="utf-8",
            )
            (root / "scripts/game_manager.gd").write_text("extends Node\n", encoding="utf-8")
            (root / "scripts/board_view.gd").write_text("extends Control\n", encoding="utf-8")
            report = pro_quality_gate.run_gate(root, "stage2", "stub_game", "match_3", Path("/tmp/qa"), Path("/tmp/videos"))
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["checks"]["anti_stub_ban"], "FAIL")
            self.assertTrue(any("Anti-stub ban" in e for e in report["errors"]))
            self.assertGreater(len(report["stub_strings_found"]), 0)

    def test_real_generated_match3_passes_stage2(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "templates", root / "templates")
            (root / "scripts").mkdir()
            (root / "docs").mkdir()
            (root / "ORDER.md").write_text(
                "GAME_ID: test_sugar_gate_01\nGENRE: match_3\nGAME_VERSION: v1.0.0\nACTION_MODE: NEW_GAME\n",
                encoding="utf-8",
            )
            defaults = ai_game_designer._defaults("match_3")
            blueprint = ai_game_designer._merge(defaults, {})
            blueprint["genre"] = "match_3"
            blueprint["game_id"] = "test_sugar_gate_01"
            blueprint["status"] = "TEST_FALLBACK"
            (root / "docs/AI_GAME_DESIGN_BLUEPRINT.json").write_text(json.dumps(blueprint), encoding="utf-8")
            studio_game_factory.build_game(root)
            report = pro_quality_gate.run_gate(root, "stage2", "test_sugar_gate_01", "match_3", Path("/tmp/qa"), Path("/tmp/videos"))
            self.assertEqual(report["status"], "PASS", json.dumps(report["errors"], indent=2))
            self.assertEqual(report["checks"]["anti_stub_ban"], "PASS")
            self.assertEqual(report["checks"]["real_ui_contract"], "PASS")
            self.assertEqual(report["checks"]["gameplay_substance"], "PASS")
            self.assertTrue((root / "docs/UI_SPEC.json").exists())
            self.assertIn("func load_level(", (root / "scripts/game_manager.gd").read_text(encoding="utf-8"))
            self.assertIn("Spec.SHOP_ITEMS", (root / "scripts/ui_controller.gd").read_text(encoding="utf-8"))

    def test_real_generated_screw_passes_stage2(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "templates", root / "templates")
            (root / "scripts").mkdir()
            (root / "docs").mkdir()
            (root / "ORDER.md").write_text(
                "GAME_ID: test_bolt_gate_02\nGENRE: screw_puzzle\nGAME_VERSION: v1.0.0\nACTION_MODE: NEW_GAME\n",
                encoding="utf-8",
            )
            defaults = ai_game_designer._defaults("screw_puzzle")
            blueprint = ai_game_designer._merge(defaults, {})
            blueprint["genre"] = "screw_puzzle"
            blueprint["game_id"] = "test_bolt_gate_02"
            blueprint["status"] = "TEST_FALLBACK"
            (root / "docs/AI_GAME_DESIGN_BLUEPRINT.json").write_text(json.dumps(blueprint), encoding="utf-8")
            studio_game_factory.build_game(root)
            report = pro_quality_gate.run_gate(root, "stage2", "test_bolt_gate_02", "screw_puzzle", Path("/tmp/qa"), Path("/tmp/videos"))
            self.assertEqual(report["status"], "PASS", json.dumps(report["errors"], indent=2))
            self.assertIn("handle_screw_tap", (root / "scripts/game_manager.gd").read_text(encoding="utf-8"))


class VisualCriticTests(unittest.TestCase):
    def test_low_visual_score_is_rejected(self):
        passed, errors = multi_video_inspector._enforce({
            "overall_score": 72,
            "ui_layout": 90,
            "shop_level_booster_completeness": 90,
            "gameplay_movement_visible": 90,
            "verdict": "PASS",
        }, "ui_shop")
        self.assertFalse(passed)
        self.assertTrue(any("72" in e for e in errors))

    def test_placeholder_flag_is_rejected(self):
        passed, errors = multi_video_inspector._enforce({
            "overall_score": 95,
            "ui_layout": 90,
            "shop_level_booster_completeness": 90,
            "gameplay_movement_visible": 90,
            "placeholder_art_detected": True,
            "verdict": "PASS",
        }, "mechanics_lab")
        self.assertFalse(passed)
        self.assertTrue(any("placeholder_art_detected" in e for e in errors))


class HardeningTests(unittest.TestCase):
    def test_comment_strip_preserves_string_hashes(self):
        source = 'extends Node\n# remove me\nconst COLOR := "#FF00AA" # trailing\n'
        cleaned = release_hardening.strip_gdscript_comments(source)
        self.assertNotIn("remove me", cleaned)
        self.assertIn('"#FF00AA"', cleaned)

    def test_encrypted_vault_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs/AI_GAME_DESIGN_BLUEPRINT.json").write_text(json.dumps({
                "game_id": "vault_test",
                "level_names": [f"L{i}" for i in range(1, 31)],
                "shop_items": [{"sku": "a"}],
                "theme": {"accent": "#FF0000"},
            }), encoding="utf-8")
            report = release_hardening.build_encrypted_vault(root, "test-secure-key")
            vault = root / report["vault_path"]
            raw = vault.read_bytes()
            self.assertEqual(raw[:8], b"STUDIOV1")
            import hashlib
            from cryptography.hazmat.primitives import padding
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            salt, iv, ciphertext = raw[8:24], raw[24:40], raw[40:]
            key = hashlib.sha256(("test-secure-key" + salt.hex()).encode()).digest()
            decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
            padded = decryptor.update(ciphertext) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            plain = unpadder.update(padded) + unpadder.finalize()
            payload = json.loads(plain.decode("utf-8"))
            self.assertEqual(payload["game_id"], "vault_test")
            self.assertEqual(len(payload["levels"]), 30)


if __name__ == "__main__":
    unittest.main()
