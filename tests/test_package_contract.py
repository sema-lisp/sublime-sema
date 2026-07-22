import json
import plistlib
import re
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
    def test_settings_file_carries_no_editor_preferences(self):
        # Sema.sublime-settings is the LSP client config only. Editor
        # preferences (like the once-shipped bogus comment_token) belong to
        # the user, not the package — reviewer feedback on PR #9468.
        raw = (ROOT / "Sema.sublime-settings").read_text()
        settings = json.loads(_without_comments(raw))
        self.assertNotIn("comment_token", settings)
        self.assertNotIn("tab_size", settings)
        self.assertNotIn("translate_tabs_to_spaces", settings)

    def test_python_38_host_opt_in(self):
        self.assertEqual((ROOT / ".python-version").read_text().strip(), "3.8")

    def test_eval_command_is_wired(self):
        commands = json.loads((ROOT / "Default.sublime-commands").read_text())
        self.assertTrue(any(c.get("command") == "sema_eval" for c in commands))
        menu = json.loads((ROOT / "Main.sublime-menu").read_text())
        self.assertIn("sema_eval", json.dumps(menu))

    def test_keymaps_ship_no_active_bindings(self):
        # Package Control policy: no live key bindings (they'd shadow core or
        # other packages' chords). Sublime only loads "Default (*).sublime-keymap"
        # files, so those must not exist; Example.sublime-keymap is never loaded
        # and holds ready-to-copy (uncommented) examples — the pattern the
        # st_package_reviewer bot recommends.
        for keymap in (
            "Default (OSX).sublime-keymap",
            "Default (Linux).sublime-keymap",
            "Default (Windows).sublime-keymap",
        ):
            self.assertFalse((ROOT / keymap).exists(), keymap)

        raw = (ROOT / "Example.sublime-keymap").read_text()
        examples = json.loads(_without_comments(raw))
        eval_bindings = [b for b in examples if b.get("command") == "sema_eval"]
        self.assertTrue(eval_bindings)
        for binding in eval_bindings:
            self.assertTrue(
                any(
                    ctx.get("operand") == "source.sema"
                    for ctx in binding.get("context", [])
                ),
                binding,
            )

    def test_settings_and_keymap_are_editable_from_ui(self):
        # The st_package_reviewer bot warns when a .sublime-settings file has
        # no command-palette / menu entry to edit it (split view, edit_settings),
        # and FAILS entries whose base_file doesn't literally exist (it doesn't
        # expand $platform) — hence the Example.sublime-keymap base + explicit
        # user_file.
        keymap_user_file = "${packages}/User/Default ($platform).sublime-keymap"
        for source in ("Default.sublime-commands", "Main.sublime-menu"):
            raw = (ROOT / source).read_text()
            args = re.findall(r'"base_file":\s*"([^"]+)"', raw)
            self.assertIn("${packages}/Sema/Sema.sublime-settings", args, source)
            self.assertIn("${packages}/Sema/Example.sublime-keymap", args, source)
            self.assertIn(keymap_user_file, raw, source)
            # every base_file the entries point at must exist in the package
            for base in args:
                rel = base.replace("${packages}/Sema/", "")
                self.assertTrue((ROOT / rel).exists(), base)

        menu = json.loads((ROOT / "Main.sublime-menu").read_text())
        self.assertTrue(any(entry.get("id") == "preferences" for entry in menu))

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
        raw = (ROOT / "Sema.sublime-settings").read_text()
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
