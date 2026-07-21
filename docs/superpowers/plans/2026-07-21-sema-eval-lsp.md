# Sema Sublime — Eval command, build variant, in-package LSP glue — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `sema build` build variant, a standalone "Eval" command that runs the selection/buffer via `sema eval` and shows output in a panel, and in-package LSP glue that renders the `sema/evalResult` code-lens result — then trim the README to current facts.

**Architecture:** Pure, `sublime`-free helpers live in `sema_eval.py` (unit-tested in CI). Thin Sublime `TextCommand` and subprocess plumbing wrap them behind a guarded `import sublime`. LSP integration lives in `sema_lsp.py` behind a guarded `from LSP.plugin import ...`, registering an `AbstractPlugin` that supplies the server config and handles the custom `sema/evalResult` notification. Nothing here requires the LSP package to be installed for the syntax/build/eval features to work.

**Tech Stack:** Sublime Text 4 (Python 3.8 plugin host), Python stdlib (`subprocess`, `threading`, `shutil`, `json`), the sublimelsp/LSP public plugin API, the `sema` CLI.

## Global Constraints

- Target the Sublime Text 4 **Python 3.8** plugin host — requires a `.python-version` file containing `3.8` at the package root.
- Package is installed as **`Packages/Sema`**; cross-module imports use `from Sema.sema_eval import ...`.
- `sema eval --stdin --json` returns `{"ok":bool,"value":str|null,"stdout":str,"stderr":str,"error":obj|str|null,"elapsedMs":int}` and **exits 0 even on eval errors** — treat the envelope as source of truth. The CLI `error` is a structured object (`{message,line,col,hint}`); the LSP `sema/evalResult` `error` is a string. Both must format.
- No narrative prose in `README.md` — current facts and guides only.
- Keep the Package Control archive lean: `export-ignore` dev-only paths in `.gitattributes`.
- All commits happen **inside the `sublime-sema` repo** to its own remote (workspace rule). Never `git add -A` at the workspace root.
- No "Generated with Claude" attribution in commits.

---

### Task 1: Add the `sema build` variant

**Files:**
- Modify: `Sema.sublime-build`
- Modify: `tests/test_package_contract.py` (`test_build_system_uses_argument_arrays`)
- Modify: `.gitattributes` (export-ignore `docs/`)

**Interfaces:**
- Produces: a third build variant `{"name": "Build executable", "cmd": ["sema", "build", "$file"]}`.

- [ ] **Step 1: Update the contract test to expect the build variant (RED)**

In `tests/test_package_contract.py`, replace the variant assertion inside `test_build_system_uses_argument_arrays`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 tests/test_package_contract.py -k test_build_system_uses_argument_arrays`
Expected: FAIL — the current build has only two variants (Format, Compile to bytecode).

- [ ] **Step 3: Add the variant to `Sema.sublime-build`**

The `variants` array becomes:

```json
	"variants": [
		{
			"name": "Format",
			"cmd": ["sema", "fmt", "$file"]
		},
		{
			"name": "Compile to bytecode",
			"cmd": ["sema", "compile", "$file"]
		},
		{
			"name": "Build executable",
			"cmd": ["sema", "build", "$file"]
		}
	]
```

- [ ] **Step 4: Export-ignore the docs dir**

Append to `.gitattributes`:

```
docs/           export-ignore
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python3 tests/test_package_contract.py`
Expected: PASS (all tests).

- [ ] **Step 6: Commit**

```bash
cd /Users/helge/code/sema/sublime-sema
git add Sema.sublime-build tests/test_package_contract.py .gitattributes docs/
git commit -m "feat: add 'Build executable' build variant (sema build)"
```

---

### Task 2: Python 3.8 opt-in + pure eval helpers + unit tests

**Files:**
- Create: `.python-version`
- Create: `sema_eval.py`
- Create: `tests/test_eval_command.py`

**Interfaces:**
- Produces (all `sublime`-free, importable in plain Python):
  - `build_eval_argv(sema: str, path: str | None, timeout_ms: int = 10000) -> list[str]`
  - `choose_source(selection_texts: list[str], buffer_text: str) -> str`
  - `augmented_path(current_path: str, home: str) -> str`
  - `format_result(envelope: dict) -> str`
  - `format_process_error(detail: str) -> str`

- [ ] **Step 1: Write the failing tests (RED)**

Create `tests/test_eval_command.py`:

```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 tests/test_eval_command.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'sema_eval'`.

- [ ] **Step 3: Create `.python-version`**

Create `.python-version` with exactly:

```
3.8
```

- [ ] **Step 4: Write the pure helpers**

Create `sema_eval.py` (only the pure top section for now — the Sublime shell is added in Task 3):

```python
"""Sema eval command for Sublime Text.

The pure helpers below never import `sublime`, so they run under plain Python
(and CI). The Sublime-facing command is defined only when the plugin host is
present.
"""

import json
import os
import shutil
import subprocess
import threading

try:
    import sublime
    import sublime_plugin
    _ST = True
except ImportError:  # running under plain Python (tests) — helpers still work
    _ST = False


DEFAULT_TIMEOUT_MS = 10000
PANEL_NAME = "sema"
COMMON_BIN_DIRS = (
    "/usr/local/bin",
    "/opt/homebrew/bin",
    "~/.cargo/bin",
    "~/.local/bin",
    "/usr/bin",
    "/bin",
)


def build_eval_argv(sema, path, timeout_ms=DEFAULT_TIMEOUT_MS):
    argv = [sema, "eval", "--stdin", "--json", "--timeout", str(int(timeout_ms))]
    if path:
        argv.extend(["--path", path])
    return argv


def choose_source(selection_texts, buffer_text):
    chunks = [t for t in selection_texts if t.strip()]
    return "\n".join(chunks) if chunks else buffer_text


def augmented_path(current_path, home):
    parts = [p for p in (current_path or "").split(os.pathsep) if p]
    for raw in COMMON_BIN_DIRS:
        d = home + raw[1:] if raw.startswith("~") else raw
        if d not in parts:
            parts.append(d)
    return os.pathsep.join(parts)


def _format_error(error):
    if isinstance(error, dict):
        msg = error.get("message", "evaluation failed")
        line = error.get("line")
        col = error.get("col")
        where = " at line {}, col {}".format(line, col) if line is not None else ""
        text = "error{}: {}".format(where, msg)
        hint = error.get("hint")
        if hint:
            text += "\nhint: {}".format(hint)
        return text
    if error:
        return "error: {}".format(error)
    return "error: evaluation failed"


def format_result(envelope):
    lines = []
    stdout = (envelope.get("stdout") or "").rstrip("\n")
    if stdout:
        lines.append(stdout)
    if envelope.get("ok"):
        value = envelope.get("value")
        if value is not None:
            lines.append("=> {}".format(value))
        elif not stdout:
            lines.append("=> nil")
    else:
        lines.append(_format_error(envelope.get("error")))
    stderr = (envelope.get("stderr") or "").rstrip("\n")
    if stderr:
        lines.append(stderr)
    elapsed = envelope.get("elapsedMs")
    if elapsed is not None:
        lines.append("({} ms)".format(elapsed))
    return "\n".join(lines) + "\n"


def format_process_error(detail):
    return (
        "Could not run `sema eval`: {}\n"
        "Install sema from https://sema-lang.com and make sure it is on your PATH.\n"
    ).format(detail)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 tests/test_eval_command.py`
Expected: PASS (all 12 tests).

- [ ] **Step 6: Commit**

```bash
cd /Users/helge/code/sema/sublime-sema
git add .python-version sema_eval.py tests/test_eval_command.py
git commit -m "feat: add pure sema-eval helpers + Python 3.8 host opt-in"
```

---

### Task 3: Eval command Sublime shell + palette/menu/keymap wiring

**Files:**
- Modify: `sema_eval.py` (append the `_ST` section)
- Create: `Default.sublime-commands`
- Create: `Main.sublime-menu`
- Create: `Default (OSX).sublime-keymap`
- Create: `Default (Linux).sublime-keymap`
- Create: `Default (Windows).sublime-keymap`
- Modify: `tests/test_package_contract.py`

**Interfaces:**
- Consumes: `build_eval_argv`, `choose_source`, `augmented_path`, `format_result`, `format_process_error` from Task 2.
- Produces: the `sema_eval` TextCommand.

- [ ] **Step 1: Update the contract test (RED)**

In `tests/test_package_contract.py`, replace `test_package_does_not_expose_dead_settings` and add wiring assertions:

```python
    def test_package_does_not_expose_dead_syntax_settings(self):
        # The syntax-settings file (and its bogus comment_token) is gone.
        self.assertFalse((ROOT / "Sema.sublime-settings").exists())

    def test_python_38_host_opt_in(self):
        self.assertEqual((ROOT / ".python-version").read_text().strip(), "3.8")

    def test_eval_command_is_wired(self):
        commands = json.loads((ROOT / "Default.sublime-commands").read_text())
        self.assertTrue(any(c.get("command") == "sema_eval" for c in commands))
        menu = json.loads((ROOT / "Main.sublime-menu").read_text())
        blob = json.dumps(menu)
        self.assertIn("sema_eval", blob)
        for keymap in ("Default (OSX).sublime-keymap", "Default (Linux).sublime-keymap", "Default (Windows).sublime-keymap"):
            binding = json.loads((ROOT / keymap).read_text())
            self.assertTrue(any(b.get("command") == "sema_eval" for b in binding))
            self.assertTrue(
                all(
                    any(ctx.get("operand") == "source.sema" for ctx in b.get("context", []))
                    for b in binding if b.get("command") == "sema_eval"
                )
            )
```

Also delete the now-obsolete `test_package_does_not_expose_dead_settings` body's references to `Default.sublime-commands` / `Main.sublime-menu` (they are re-added here for eval, not settings).

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 tests/test_package_contract.py`
Expected: FAIL — `.python-version` check passes but `Default.sublime-commands`/keymaps don't exist yet.

- [ ] **Step 3: Append the Sublime shell to `sema_eval.py`**

```python
def _startupinfo_kwargs():
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return {"startupinfo": si}
    return {}


def _resolve_sema():
    path = augmented_path(os.environ.get("PATH", ""), os.path.expanduser("~"))
    return shutil.which("sema", path=path) or "sema"


def _evaluate(source, path):
    argv = build_eval_argv(_resolve_sema(), path)
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **_startupinfo_kwargs()
        )
        out, err = proc.communicate(input=source.encode("utf-8"), timeout=30)
    except FileNotFoundError as exc:
        return format_process_error(str(exc))
    except subprocess.TimeoutExpired:
        proc.kill()
        return format_process_error("timed out after 30s")
    raw = out.decode("utf-8", "replace").strip()
    try:
        return format_result(json.loads(raw))
    except ValueError:
        detail = raw or err.decode("utf-8", "replace").strip() or "no output"
        return format_process_error(detail)


if _ST:

    def _show_panel(window, text):
        if window is None:
            return
        panel = window.create_output_panel(PANEL_NAME)
        panel.set_read_only(False)
        panel.run_command("append", {"characters": text})
        panel.set_read_only(True)
        window.run_command("show_panel", {"panel": "output.{}".format(PANEL_NAME)})

    class SemaEvalCommand(sublime_plugin.TextCommand):
        def run(self, edit):
            view = self.view
            selection_texts = [view.substr(r) for r in view.sel()]
            buffer_text = view.substr(sublime.Region(0, view.size()))
            source = choose_source(selection_texts, buffer_text)
            if not source.strip():
                sublime.status_message("Sema: nothing to evaluate")
                return
            path = view.file_name()
            window = view.window()

            def worker():
                text = _evaluate(source, path)
                sublime.set_timeout(lambda: _show_panel(window, text), 0)

            threading.Thread(target=worker, daemon=True).start()

        def is_enabled(self):
            syntax = self.view.syntax()
            return bool(syntax and "source.sema" in (syntax.scope or ""))
```

- [ ] **Step 4: Create `Default.sublime-commands`**

```json
[
	{
		"caption": "Sema: Eval Selection or Buffer",
		"command": "sema_eval"
	}
]
```

- [ ] **Step 5: Create `Main.sublime-menu`**

```json
[
	{
		"caption": "Tools",
		"id": "tools",
		"children": [
			{
				"caption": "Sema",
				"children": [
					{
						"caption": "Eval Selection or Buffer",
						"command": "sema_eval"
					}
				]
			}
		]
	}
]
```

- [ ] **Step 6: Create the three keymaps**

`Default (OSX).sublime-keymap`:

```json
[
	{
		"keys": ["super+enter"],
		"command": "sema_eval",
		"context": [
			{ "key": "selector", "operator": "equal", "operand": "source.sema" }
		]
	}
]
```

`Default (Linux).sublime-keymap` and `Default (Windows).sublime-keymap` (identical, `ctrl+enter`):

```json
[
	{
		"keys": ["ctrl+enter"],
		"command": "sema_eval",
		"context": [
			{ "key": "selector", "operator": "equal", "operand": "source.sema" }
		]
	}
]
```

- [ ] **Step 7: Run the automated tests**

Run: `python3 tests/test_eval_command.py && python3 tests/test_package_contract.py`
Expected: PASS. (The `_ST` shell isn't exercised here — see manual step.)

- [ ] **Step 8: Manual runtime verification (record results in the commit/PR)**

In Sublime Text 4 with the package installed as `Packages/Sema`:
1. Open a `.sema` file; select `(+ 20 22)`; press `super+enter`/`ctrl+enter` → the **Sema** panel shows `=> 42`.
2. Clear the selection; run **Sema: Eval Selection or Buffer** from the palette → the whole buffer runs; `println` output appears.
3. Select `(+ 1 undefined-symbol)` → panel shows `error at line 1, col 1: Unbound variable: undefined-symbol`.
4. Temporarily rename `sema` off PATH → panel shows the install/PATH message.

- [ ] **Step 9: Commit**

```bash
cd /Users/helge/code/sema/sublime-sema
git add sema_eval.py Default.sublime-commands Main.sublime-menu "Default (OSX).sublime-keymap" "Default (Linux).sublime-keymap" "Default (Windows).sublime-keymap" tests/test_package_contract.py
git commit -m "feat: add 'Sema: Eval' command with output panel + keybindings"
```

---

### Task 4: In-package LSP glue (`sema/evalResult` + auto-register)

**Files:**
- Create: `sema_lsp.py`
- Create: `sema-lsp.sublime-settings`
- Modify: `tests/test_package_contract.py`

**Interfaces:**
- Consumes: `format_result` from `sema_eval` (via `from Sema.sema_eval import format_result`, imported lazily inside the handler).
- Produces: an `AbstractPlugin` bound to session name `sema`, config from `sema-lsp.sublime-settings`, handling `sema/evalResult`.

- [ ] **Step 1: Add the contract test for the LSP session config (RED)**

Append to `tests/test_package_contract.py`:

```python
    def test_lsp_session_settings_present(self):
        settings = json.loads((ROOT / "sema-lsp.sublime-settings").read_text())
        self.assertEqual(settings["command"], ["sema", "lsp"])
        self.assertEqual(settings["selector"], "source.sema")
        self.assertTrue(settings.get("enabled", False))

    def test_lsp_plugin_module_is_guarded(self):
        source = (ROOT / "sema_lsp.py").read_text()
        self.assertIn("except ImportError", source)
        self.assertIn("sema/evalResult", source)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 tests/test_package_contract.py`
Expected: FAIL — `sema-lsp.sublime-settings` and `sema_lsp.py` don't exist.

- [ ] **Step 3: Create `sema-lsp.sublime-settings`**

```json
{
	"enabled": true,
	"command": ["sema", "lsp"],
	"selector": "source.sema"
}
```

- [ ] **Step 4: Create `sema_lsp.py`**

```python
"""Optional LSP integration for Sema.

Active only when the sublimelsp/LSP package is installed. When present it
registers the `sema lsp` server automatically and renders the custom
`sema/evalResult` notification (the result of the "Run" code lens) into the
shared Sema output panel. When LSP is absent this module is an inert no-op, so
the rest of the package works without it.
"""

try:
    import sublime
    from LSP.plugin import AbstractPlugin, register_plugin, unregister_plugin
    from LSP.plugin import notification_handler
    _LSP = True
except ImportError:
    _LSP = False


if _LSP:

    SETTINGS_BASENAME = "sema-lsp.sublime-settings"

    class SemaLanguageServer(AbstractPlugin):
        @classmethod
        def name(cls):
            return "sema"

        @classmethod
        def configuration(cls):
            settings = sublime.load_settings(SETTINGS_BASENAME)
            filepath = "Packages/Sema/{}".format(SETTINGS_BASENAME)
            return settings, filepath

        @notification_handler("sema/evalResult")
        def on_eval_result(self, params):
            from Sema.sema_eval import format_result, PANEL_NAME
            text = format_result(params)
            window = sublime.active_window()
            if window is None:
                return
            panel = window.create_output_panel(PANEL_NAME)
            panel.set_read_only(False)
            panel.run_command("append", {"characters": text})
            panel.set_read_only(True)
            window.run_command("show_panel", {"panel": "output.{}".format(PANEL_NAME)})

    def plugin_loaded():
        register_plugin(SemaLanguageServer)

    def plugin_unloaded():
        unregister_plugin(SemaLanguageServer)

else:

    def plugin_loaded():
        pass

    def plugin_unloaded():
        pass
```

- [ ] **Step 5: Run the automated tests**

Run: `python3 tests/test_package_contract.py`
Expected: PASS.

- [ ] **Step 6: Manual runtime verification (record results)**

In Sublime Text 4 with **both** the Sema package and the LSP package installed:
1. Open a `.sema` file → LSP status bar shows the `sema` server attached; completions/hover work.
2. A `▶ Run` code lens appears above each top-level form.
3. Click it → the Sema panel shows the form's stdout / `=> value` / error.
4. If the `@notification_handler`/`configuration()` API differs in the installed LSP version, fall back to the documented `LanguageServers.sublime-settings` config for registration (Task 5 notes this) and keep the notification handler; re-verify.

- [ ] **Step 7: Commit**

```bash
cd /Users/helge/code/sema/sublime-sema
git add sema_lsp.py sema-lsp.sublime-settings tests/test_package_contract.py
git commit -m "feat: in-package LSP glue — auto-register server + render sema/evalResult"
```

---

### Task 5: README cleanup + docs contract

**Files:**
- Modify: `README.md`
- Modify: `tests/test_package_contract.py` (`test_documentation_*`)

**Interfaces:**
- Consumes: nothing. Produces: the final user-facing docs.

- [ ] **Step 1: Update the docs contract test (RED)**

Replace `test_documentation_uses_installable_package_paths_and_current_lsp_shape` with:

```python
    def test_documentation_is_current_and_narrative_free(self):
        readme = (ROOT / "README.md").read_text()
        # installable paths / no stale references
        self.assertIn("Packages/Sema", readme)
        self.assertNotIn("Packages/sublime-sema", readme)
        self.assertNotIn("block `#| |#`", readme)
        self.assertNotIn('"clients"', readme)
        # lens is enabled now — no capability workaround, no narrative
        self.assertNotIn("disabled_capabilities", readme)
        self.assertNotIn("sema/evalResult", readme)
        self.assertNotIn("incomplete feature", readme)
        # new features documented
        self.assertIn("Build executable", readme)
        self.assertIn("Eval", readme)
        self.assertIn("registers", readme)  # "registers its language server automatically"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 tests/test_package_contract.py`
Expected: FAIL — the current README still contains `disabled_capabilities`, `sema/evalResult`, and lacks "Build executable"/"Eval".

- [ ] **Step 3: Rewrite the README `Features`, `Building & running`, and `Language server` sections**

Replace the `## Features` list item for comments and add eval/build; replace the `## Building & running` table and the `## Language server` section with:

```markdown
## Features

- Syntax highlighting for `.sema` files via a native `.sublime-syntax` definition
- Comment toggling with `Cmd+/` / `Ctrl+/` (Sema's `;` line comments)
- Symbol navigation (`Cmd+R` / `Ctrl+R`) for `define`, `defun`, `defmacro`, `defagent`, `deftool`, and friends
- **Eval** the selection (or whole file) with `Cmd+Enter` / `Ctrl+Enter` — output shows in the Sema panel
- Build systems for **running**, **formatting**, **compiling**, and **building a standalone executable**
- Optional **language server** (`sema lsp`) via the [LSP](https://packagecontrol.io/packages/LSP) package

## Building & running

Open a `.sema` file and use **Tools → Build System → Sema** (or `Cmd+B` / `Ctrl+B`). Variants (`Cmd+Shift+B` / `Ctrl+Shift+B`):

| Variant | Command |
| --- | --- |
| Sema | `sema <file>` — run the program |
| Sema — Format | `sema fmt <file>` |
| Sema — Compile to bytecode | `sema compile <file>` |
| Sema — Build executable | `sema build <file>` |

To evaluate code without a full build, select an expression and press `Cmd+Enter` / `Ctrl+Enter` (or run **Sema: Eval Selection or Buffer** from the command palette). With nothing selected, the whole file is evaluated. Output appears in the **Sema** panel.

The build systems and the eval command invoke the `sema` binary, so it must be on your `PATH`. Install it from [sema-lang.com](https://sema-lang.com).

## Language server

For IDE features — completions, hover, go-to-definition, references, rename, signature help, diagnostics, and ▶ Run code lenses — install the [LSP](https://packagecontrol.io/packages/LSP) package via Package Control. Sema registers its `sema lsp` server automatically for `source.sema` files; no manual configuration is needed. Restart Sublime Text (or run **LSP: Restart Servers**) after installing LSP.

To override the server command or options, edit `Packages/User/sema-lsp.sublime-settings`.
```

- [ ] **Step 4: Run the full automated suite**

Run: `python3 tests/test_eval_command.py && python3 tests/test_package_contract.py`
Expected: PASS (both suites).

- [ ] **Step 5: Commit**

```bash
cd /Users/helge/code/sema/sublime-sema
git add README.md tests/test_package_contract.py
git commit -m "docs: current-facts README — eval, build variant, auto LSP; drop narrative"
```

---

## Final verification (before considering the plan done)

- [ ] `python3 tests/test_eval_command.py` → OK
- [ ] `python3 tests/test_package_contract.py` → OK
- [ ] YAML/JSON/plist CI validations still pass (`ci.yml` steps run locally)
- [ ] Manual Sublime checks from Task 3 Step 8 recorded
- [ ] Manual LSP checks from Task 4 Step 6 recorded (or fallback documented)
- [ ] `git status` inside `sublime-sema` clean; nothing staged at the workspace root

## Notes for the implementer

- The two hard-to-verify pieces are the Sublime `TextCommand` shell (Task 3) and the LSP glue (Task 4) — neither runs headlessly. The pure helpers they wrap are unit-tested; verify the shells manually in Sublime and record what you saw.
- If `from LSP.plugin import notification_handler` is unavailable in the installed LSP version, the older dispatch is a method named `m_sema_evalResult(self, params)` on the `AbstractPlugin` subclass — swap the decorator for that method and re-verify.
- Do not re-add `Sema.sublime-settings` (the dead syntax-settings file); the eval panel and LSP make it unnecessary, and the contract test forbids it.
