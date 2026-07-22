"""Extended tests for sema_eval pure helpers.

These test functions that don't require the Sublime plugin host or LSP package.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sema_eval as se


class FormatResultExtendedTests(unittest.TestCase):
    """Test format_result edge cases not covered in test_eval_command.py."""

    def test_format_result_with_stderr_only(self):
        text = se.format_result({
            "ok": True, "value": None, "stdout": "",
            "stderr": "warning: deprecated function", "elapsedMs": 15,
        })
        self.assertIn("warning: deprecated function", text)
        self.assertIn("=> nil", text)

    def test_format_result_no_elapsed_ms(self):
        text = se.format_result({
            "ok": True, "value": "done", "stdout": "", "stderr": "",
        })
        self.assertIn("=> done", text)
        self.assertNotIn("ms", text)

    def test_format_result_empty_output_nil(self):
        text = se.format_result({
            "ok": True, "value": None, "stdout": "", "stderr": "", "elapsedMs": 0,
        })
        self.assertIn("=> nil", text)

    def test_format_result_structured_error_no_hint(self):
        text = se.format_result({
            "ok": False, "value": None, "stdout": "", "stderr": "",
            "error": {"message": "syntax error"},
            "elapsedMs": 0,
        })
        self.assertIn("error: syntax error", text)
        self.assertNotIn("hint", text)

    def test_format_result_with_line_col_no_hint(self):
        text = se.format_result({
            "ok": False, "value": None, "stdout": "", "stderr": "",
            "error": {"message": "type mismatch", "line": 10, "col": 5},
            "elapsedMs": 0,
        })
        self.assertIn("error at line 10, col 5: type mismatch", text)

    def test_format_result_raw_json_decode_failure(self):
        result = se._format_error("some raw error string")
        self.assertEqual(result, "error: some raw error string")


class FormatProcessErrorTests(unittest.TestCase):
    """Test format_process_error edge cases."""

    def test_format_process_error_with_timeout(self):
        result = se.format_process_error("timed out after 15s")
        self.assertIn("timed out", result)
        self.assertIn("PATH", result)

    def test_format_process_error_with_generic(self):
        result = se.format_process_error("permission denied")
        self.assertIn("permission denied", result)
        self.assertIn("sema eval", result)


class AugmentedPathTests(unittest.TestCase):
    """Test augmented_path edge cases."""

    def test_augmented_path_empty_current(self):
        result = se.augmented_path("", "/home/u").split(":")
        self.assertNotIn("", result)
        self.assertIn("/home/u/.cargo/bin", result)

    def test_augmented_path_preserves_order(self):
        result = se.augmented_path("/usr/local/bin:/usr/bin", "/home/u").split(":")
        self.assertEqual(result[0], "/usr/local/bin")
        self.assertEqual(result[1], "/usr/bin")
        common_dirs = ["/home/u/.cargo/bin", "/home/u/.local/bin"]
        first_common_idx = min(result.index(d) for d in common_dirs)
        self.assertGreater(first_common_idx, 1)

    def test_augmented_path_tilde_expansion(self):
        result = se.augmented_path("", "/home/myuser").split(":")
        self.assertIn("/home/myuser/.cargo/bin", result)
        self.assertIn("/home/myuser/.local/bin", result)


class BuildEvalArgvTests(unittest.TestCase):
    """Test build_eval_argv edge cases."""

    def test_build_eval_argv_custom_timeout(self):
        result = se.build_eval_argv("sema", None, 30000)
        self.assertEqual(result, ["sema", "eval", "--stdin", "--json", "--timeout", "30000"])

    def test_build_eval_argv_zero_timeout(self):
        result = se.build_eval_argv("sema", "/test.sema", 0)
        self.assertEqual(
            result,
            ["sema", "eval", "--stdin", "--json", "--timeout", "0", "--path", "/test.sema"],
        )

    def test_build_eval_argv_path_with_spaces(self):
        result = se.build_eval_argv("sema", "/path with spaces/file.sema")
        self.assertIn("/path with spaces/file.sema", result)


class ChooseSourceTests(unittest.TestCase):
    """Test choose_source edge cases."""

    def test_choose_source_empty_buffer_empty_selection(self):
        self.assertEqual(se.choose_source(["", ""], ""), "")

    def test_choose_source_single_empty_selection(self):
        self.assertEqual(se.choose_source([""], "buffer"), "buffer")

    def test_choose_source_multiple_with_empty(self):
        self.assertEqual(se.choose_source(["", "(a)", "", "(b)"], "buffer"), "(a)\n(b)")

    def test_choose_source_whitespace_only_selection(self):
        self.assertEqual(se.choose_source(["   ", "\t"], "buffer"), "buffer")


class ResolveSemaTests(unittest.TestCase):
    """Test resolve_sema behavior."""

    def test_resolve_sema_real_binary_returns_path(self):
        result = se.resolve_sema("python3")
        self.assertIsNotNone(result)

    def test_resolve_sema_nonexistent(self):
        self.assertIsNone(se.resolve_sema("this-binary-definitely-does-not-exist-xyz123"))


class ProcessTimeoutTests(unittest.TestCase):
    """Verify timeout relationship."""

    def test_process_timeout_is_grace_period(self):
        expected = se.DEFAULT_TIMEOUT_MS / 1000 + 5
        self.assertEqual(se.PROCESS_TIMEOUT_S, expected)

    def test_process_timeout_positive(self):
        self.assertGreater(se.PROCESS_TIMEOUT_S, 0)

    def test_default_timeout_positive(self):
        self.assertGreater(se.DEFAULT_TIMEOUT_MS, 0)


class StartupInfoTests(unittest.TestCase):
    """Test _startupinfo_kwargs."""

    def test_startupinfo_returns_empty_on_unix(self):
        import os
        if os.name != "nt":
            result = se._startupinfo_kwargs()
            self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
