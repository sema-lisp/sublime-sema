import json
import plistlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _without_comments(raw):
    # Sublime's JSON dialect allows // line comments; strip them before parsing.
    return "".join(
        line for line in raw.splitlines(keepends=True)
        if not line.lstrip().startswith("//")
    )


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

    def test_keymaps_ship_no_active_bindings(self):
        # Package Control policy: no live key bindings (they'd shadow core or
        # other packages' chords) — only commented-out suggestions.
        for keymap in (
            "Default (OSX).sublime-keymap",
            "Default (Linux).sublime-keymap",
            "Default (Windows).sublime-keymap",
        ):
            raw = (ROOT / keymap).read_text()
            self.assertEqual(json.loads(_without_comments(raw)), [], keymap)
            self.assertIn("sema_eval", raw, keymap)  # suggestion is present
            self.assertIn("source.sema", raw, keymap)  # ... and scoped

    def test_settings_and_keymap_are_editable_from_ui(self):
        # The st_package_reviewer bot warns when a .sublime-settings file has
        # no command-palette / menu entry to edit it (split view, edit_settings).
        commands = json.loads((ROOT / "Default.sublime-commands").read_text())
        base_files = {
            c["args"]["base_file"]
            for c in commands
            if c.get("command") == "edit_settings"
        }
        self.assertIn("${packages}/Sema/sema-lsp.sublime-settings", base_files)
        self.assertIn("${packages}/Sema/Default ($platform).sublime-keymap", base_files)

        menu_raw = (ROOT / "Main.sublime-menu").read_text()
        menu = json.loads(menu_raw)
        self.assertTrue(any(entry.get("id") == "preferences" for entry in menu))
        self.assertIn('"edit_settings"', menu_raw)
        self.assertIn("${packages}/Sema/sema-lsp.sublime-settings", menu_raw)

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

    def test_documentation_is_current_and_narrative_free(self):
        readme = (ROOT / "README.md").read_text()
        # installable paths / no stale references
        self.assertIn("Packages/Sema", readme)
        self.assertNotIn("Packages/sublime-sema", readme)
        self.assertNotIn("block `#| |#`", readme)
        self.assertNotIn('"clients"', readme)
        # the code-lens workaround is an implementation detail — no narrative
        self.assertNotIn("disabled_capabilities", readme)
        self.assertNotIn("sema/evalResult", readme)
        self.assertNotIn("incomplete feature", readme)
        # new features documented
        self.assertIn("Build executable", readme)
        self.assertIn("Eval", readme)
        self.assertIn("registers", readme)  # "registers its language server automatically"

    def test_syntax_fixtures_use_the_installed_package_name(self):
        expected_header = '; SYNTAX TEST "Packages/Sema/Sema.sublime-syntax"'
        fixtures = sorted((ROOT / "tests").glob("syntax_test_*.sema"))
        self.assertGreaterEqual(len(fixtures), 2)
        for fixture in fixtures:
            self.assertEqual(fixture.read_text().splitlines()[0], expected_header)

    def test_lsp_session_settings_disable_code_lens(self):
        raw = (ROOT / "sema-lsp.sublime-settings").read_text()
        settings = json.loads(_without_comments(raw))
        self.assertEqual(settings["command"], ["sema", "lsp"])
        self.assertEqual(settings["selector"], "source.sema")
        self.assertTrue(settings.get("enabled", False))
        # The per-form Run code lens runs sandboxed/no-LLM and duplicates the
        # Eval command; it is disabled in Sublime.
        self.assertTrue(
            settings.get("disabled_capabilities", {}).get("codeLensProvider", False)
        )

    def test_lsp_plugin_module_is_guarded(self):
        source = (ROOT / "sema_lsp.py").read_text()
        self.assertIn("except ImportError", source)
        self.assertIn("sema/evalResult", source)
        # Missing-binary and bare-GUI-PATH handling, so LSP users without the
        # sema CLI get a hint instead of spawn errors.
        self.assertIn("def can_start", source)
        self.assertIn("def on_pre_start", source)


if __name__ == "__main__":
    unittest.main()
