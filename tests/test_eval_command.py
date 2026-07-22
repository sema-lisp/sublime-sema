import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sema_eval as se


class EvalHelperTests(unittest.TestCase):
    def test_build_eval_argv_with_path(self):
        self.assertEqual(
            se.build_eval_argv("sema", "/tmp/x.sema", 5000),
            ["sema", "eval", "--stdin", "--json", "--timeout", "5000", "--path", "/tmp/x.sema"],
        )

    def test_build_eval_argv_without_path(self):
        self.assertEqual(
            se.build_eval_argv("/usr/bin/sema", None),
            ["/usr/bin/sema", "eval", "--stdin", "--json", "--timeout", "10000"],
        )

    def test_choose_source_prefers_nonempty_selection(self):
        self.assertEqual(se.choose_source(["(+ 1 2)", "   "], "WHOLE"), "(+ 1 2)")

    def test_choose_source_joins_multiple_selections(self):
        self.assertEqual(se.choose_source(["(a)", "(b)"], "WHOLE"), "(a)\n(b)")

    def test_choose_source_falls_back_to_buffer(self):
        self.assertEqual(se.choose_source(["", "  "], "WHOLE"), "WHOLE")

    def test_augmented_path_appends_common_dirs(self):
        result = se.augmented_path("/existing", "/home/u").split(":")
        self.assertEqual(result[0], "/existing")
        self.assertIn("/home/u/.cargo/bin", result)
        self.assertIn("/opt/homebrew/bin", result)

    def test_augmented_path_no_duplicates(self):
        result = se.augmented_path("/usr/bin", "/home/u").split(":")
        self.assertEqual(result.count("/usr/bin"), 1)

    def test_format_result_ok_with_value(self):
        text = se.format_result({"ok": True, "value": "42", "stdout": "hi\n", "stderr": "", "elapsedMs": 3})
        self.assertIn("hi", text)
        self.assertIn("=> 42", text)
        self.assertIn("(3 ms)", text)

    def test_format_result_ok_nil(self):
        text = se.format_result({"ok": True, "value": None, "stdout": "", "stderr": "", "elapsedMs": 0})
        self.assertIn("=> nil", text)

    def test_format_result_structured_error_with_hint(self):
        text = se.format_result({
            "ok": False, "value": None, "stdout": "", "stderr": "",
            "error": {"message": "Unbound variable: eprintln", "line": 1, "col": 1, "hint": "Did you mean 'println'?"},
            "elapsedMs": 0,
        })
        self.assertIn("error at line 1, col 1: Unbound variable: eprintln", text)
        self.assertIn("hint: Did you mean 'println'?", text)

    def test_format_result_string_error(self):
        text = se.format_result({"ok": False, "error": "boom", "stdout": "", "stderr": "", "elapsedMs": 0})
        self.assertIn("error: boom", text)

    def test_format_process_error_mentions_path(self):
        self.assertIn("PATH", se.format_process_error("No such file"))

    def test_resolve_sema_missing_binary_returns_none(self):
        self.assertIsNone(se.resolve_sema("definitely-not-a-real-binary-xyz"))

    def test_process_timeout_exceeds_cli_timeout(self):
        self.assertGreater(se.PROCESS_TIMEOUT_S, se.DEFAULT_TIMEOUT_MS / 1000)


if __name__ == "__main__":
    unittest.main()
