#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import zlib
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


patch_all_js = load_module("patch_all_js", REPOSITORY / "scripts/patch_all_js.py")
configure_steam = load_module(
    "configure_steam", REPOSITORY / "scripts/configure_steam.py"
)
reset_profile = load_module("reset_profile", REPOSITORY / "scripts/reset_profile.py")


class GamePatchTests(unittest.TestCase):
    def test_patch_is_complete_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "all.js"
            source = 'define("nebula/input/gamepad"' + "|".join(
                patch.old[0] for patch in patch_all_js.PATCHES
            )
            path.write_text(source, encoding="utf-8")

            self.assertTrue(patch_all_js.apply_patches(path))
            self.assertEqual(patch_all_js.check_text(path.read_text()), [])
            self.assertFalse(patch_all_js.apply_patches(path))


class SteamConfigTests(unittest.TestCase):
    def test_controller_config_and_localconfig(self):
        configset = '"controller_config"\n{\n\t"285900"\n\t{\n\t\t"autosave" "1"\n\t}\n}\n'
        updated = configure_steam.set_app_template(configset)
        self.assertIn('"399820"', updated)
        self.assertIn('"controller_generic_gamepad_joystick.vdf"', updated)

        preference = (
            '"ControllerPersonalization"\n{\n'
            '\t"reverse_button_diamond_layout_v2" "1"\n'
            '\t"use_universal_face_button_glyphs" "1"\n}\n'
        )
        updated = configure_steam.set_controller_preference(preference)
        self.assertIn('"reverse_button_diamond_layout_v2" "-1"', updated)
        self.assertIn('"use_universal_face_button_glyphs" "0"', updated)

        localconfig = (
            '"UserLocalConfigStore"\n{\n\t"apps"\n\t{\n'
            '\t\t"399820"\n\t\t{\n'
            '\t\t\t"UseSteamControllerConfig" "0"\n'
            '\t\t}\n\t}\n}\n'
        )
        updated = configure_steam.set_steam_input_in_localconfig(localconfig)
        self.assertIn('"UseSteamControllerConfig" "2"', updated)

    def test_full_configuration_and_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "Steam"
            config = root / "steamapps/common/Steam Controller Configs/123/config"
            userdata = root / "userdata/123/config"
            config.mkdir(parents=True)
            userdata.mkdir(parents=True)

            preference = config / "preferences_3537-1041-189266d5.vdf"
            preference.write_text(
                '"ControllerPersonalization"\n{\n'
                '\t"reverse_button_diamond_layout_v2" "1"\n'
                '\t"use_universal_face_button_glyphs" "1"\n}\n'
            )
            configset = config / "configset_3537-1041-189266d5.vdf"
            configset.write_text('"controller_config"\n{\n}\n')
            generic = config / "configset_controller_generic.vdf"
            generic.write_text('"controller_config"\n{\n}\n')
            localconfig = userdata / "localconfig.vdf"
            localconfig.write_text(
                '"UserLocalConfigStore"\n{\n\t"apps"\n\t{\n'
                '\t\t"399820"\n\t\t{\n'
                '\t\t\t"UseSteamControllerConfig" "0"\n'
                '\t\t}\n\t}\n}\n'
            )

            backup = Path(directory) / "backup"
            self.assertEqual(configure_steam.configure(root, backup, False), 0)
            self.assertEqual(configure_steam.configure(root, backup, True), 0)
            self.assertTrue((backup / "steam").is_dir())


class ProfileTests(unittest.TestCase):
    def test_profile_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / "player1.gz"
            data = {
                "controls": {
                    f"gamepadLayout{index}Enabled": False for index in range(1, 5)
                },
                "gamepadLayout1": {"powerup": "axisButton5"},
                "gamepadLayout2": {"powerup": "axisButton5"},
            }
            profile.write_bytes(zlib.compress(json.dumps(data).encode()))
            reset_profile.reset_profile(profile, root / "backup")
            restored = json.loads(zlib.decompress(profile.read_bytes()))
            self.assertEqual(restored["gamepadLayout1"]["powerup"], "button6")
            self.assertEqual(restored["gamepadLayout2"]["powerup"], "button6")
            self.assertTrue(restored["controls"]["gamepadLayout1Enabled"])
            self.assertTrue(restored["controls"]["gamepadLayout2Enabled"])
            self.assertFalse(restored["controls"]["gamepadLayout3Enabled"])


if __name__ == "__main__":
    unittest.main()
