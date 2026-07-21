import json
import plistlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackageContractTests(unittest.TestCase):
    def test_package_does_not_expose_dead_syntax_settings(self):
        # The syntax-settings file (and its bogus comment_token) is gone.
        self.assertFalse((ROOT / "Sema.sublime-settings").exists())

    def test_python_38_host_opt_in(self):
        self.assertEqual((ROOT / ".python-version").read_text().strip(), "3.8")

    def test_eval_command_is_wired(self):
        commands = json.loads((ROOT / "Default.sublime-commands").read_text())
        self.assertTrue(any(c.get("command") == "sema_eval" for c in commands))
        menu = json.loads((ROOT / "Main.sublime-menu").read_text())
        self.assertIn("sema_eval", json.dumps(menu))
        for keymap in (
            "Default (OSX).sublime-keymap",
            "Default (Linux).sublime-keymap",
            "Default (Windows).sublime-keymap",
        ):
            binding = json.loads((ROOT / keymap).read_text())
            eval_bindings = [b for b in binding if b.get("command") == "sema_eval"]
            self.assertTrue(eval_bindings, keymap)
            self.assertTrue(
                all(
                    any(ctx.get("operand") == "source.sema" for ctx in b.get("context", []))
                    for b in eval_bindings
                ),
                keymap,
            )

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
                ["sema", "build", "$file"],
            ],
        )
        self.assertEqual(
            [variant["name"] for variant in build["variants"]],
            ["Format", "Compile to bytecode", "Build executable"],
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
