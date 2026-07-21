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
