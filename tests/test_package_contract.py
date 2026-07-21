import json
import plistlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackageContractTests(unittest.TestCase):
    def test_package_does_not_expose_dead_settings(self):
        for name in (
            "Sema.sublime-settings",
            "Default.sublime-commands",
            "Main.sublime-menu",
        ):
            self.assertFalse((ROOT / name).exists(), name)

    def test_build_system_uses_argument_arrays(self):
        with (ROOT / "Sema.sublime-build").open() as file:
            build = json.load(file)

        self.assertEqual(build["cmd"], ["sema", "$file"])
        self.assertEqual(build["working_dir"], "$file_path")
        self.assertNotIn("shell_cmd", build)
        self.assertEqual(
            [variant["cmd"] for variant in build["variants"]],
            [
                ["sema", "fmt", "$file"],
                ["sema", "compile", "$file"],
            ],
        )
        self.assertTrue(
            all("shell_cmd" not in variant for variant in build["variants"])
        )

    def test_only_supported_comment_syntax_is_advertised(self):
        syntax = (ROOT / "Sema.sublime-syntax").read_text()
        self.assertNotIn("block-comment", syntax)
        self.assertNotIn("#\\|", syntax)

        with (ROOT / "Comments.tmPreferences").open("rb") as file:
            preferences = plistlib.load(file)
        variables = {
            item["name"]: item["value"]
            for item in preferences["settings"]["shellVariables"]
        }
        self.assertEqual(variables, {"TM_COMMENT_START": "; "})

    def test_documentation_uses_installable_package_paths_and_current_lsp_shape(self):
        readme = (ROOT / "README.md").read_text()
        self.assertNotIn("Packages/sublime-sema", readme)
        self.assertNotIn("block `#| |#`", readme)
        self.assertNotIn('"clients"', readme)
        self.assertIn("Packages/Sema", readme)
        self.assertIn("LanguageServers.sublime-settings", readme)
        self.assertIn('"codeLensProvider": true', readme)

    def test_syntax_fixtures_use_the_installed_package_name(self):
        expected_header = '; SYNTAX TEST "Packages/Sema/Sema.sublime-syntax"'
        fixtures = sorted((ROOT / "tests").glob("syntax_test_*.sema"))
        self.assertGreaterEqual(len(fixtures), 2)
        for fixture in fixtures:
            self.assertEqual(fixture.read_text().splitlines()[0], expected_header)


if __name__ == "__main__":
    unittest.main()
