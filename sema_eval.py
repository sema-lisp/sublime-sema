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
