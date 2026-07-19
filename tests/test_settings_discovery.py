import json
import unittest
from pathlib import Path


SETTINGS_FILE = "${packages}/Sema/Sema.sublime-settings"
SETTINGS_TEMPLATE = "// Sema Settings - User\n{\n\t$0\n}\n"


def settings_command_paths(items, parents=()):
    paths = []
    for item in items:
        caption = item.get("caption")
        path = parents + ((caption,) if caption else ())
        args = item.get("args", {})
        if (
            item.get("command") == "edit_settings"
            and args.get("base_file") == SETTINGS_FILE
            and args.get("default") == SETTINGS_TEMPLATE
        ):
            paths.append(path)
        paths.extend(settings_command_paths(item.get("children", []), path))
    return paths


class SettingsDiscoveryTests(unittest.TestCase):
    def load_json(self, path):
        self.assertTrue(path.is_file(), f"missing {path.name}")
        with path.open() as file:
            return json.load(file)

    def test_settings_are_available_in_command_palette(self):
        commands = self.load_json(Path("Default.sublime-commands"))
        self.assertIn(
            ("Preferences: Sema Settings",),
            settings_command_paths(commands),
        )

    def test_settings_are_available_in_package_settings_menu(self):
        menu = self.load_json(Path("Main.sublime-menu"))
        self.assertIn(
            ("Preferences", "Package Settings", "Sema", "Settings"),
            settings_command_paths(menu),
        )


if __name__ == "__main__":
    unittest.main()
