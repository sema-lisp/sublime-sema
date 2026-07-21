# Sema for Sublime Text — Eval command, in-package LSP glue, build variant

- **Date:** 2026-07-21
- **Status:** Approved (design); implementation pending
- **Repo:** `sublime-sema` (the `Sema` package)

## Goal

Make "run / evaluate Sema code from the editor" work well, entirely inside this
one package, without requiring users to hand-write LSP config. Add the missing
`sema build` build variant. Trim the README to current facts only.

## Non-goals (this iteration)

- No separate `LSP-sema` helper package. All LSP glue lives in this package,
  behind a guarded import so the package still works with zero LSP installed.
- Notebook-in-a-tab is **future work** (see below), not part of this cut.

## Background facts (verified 2026-07-21)

- `sema build [FILE]` builds a standalone bundled executable — distinct from
  `sema compile` (bytecode `.semac`).
- `sema eval --stdin --json --path <file> --timeout <ms>` reads a program from
  stdin and returns a JSON envelope:
  `{"ok":bool,"value":str|null,"stdout":str,"stderr":str,"error":str|null,"elapsedMs":int}`.
  Exit code is non-zero on error; the envelope carries the detail.
- `sema lsp` advertises `code_lens_provider` and emits a `▶ Run` /
  `sema.runTopLevel` code lens. The result is pushed back as a **custom**
  `sema/evalResult` notification (params: uri, range, kind, value, stdout,
  stderr, ok, error, elapsedMs) that a generic LSP client ignores.
- The Sublime **LSP** package exposes a public plugin API any package may call:
  `register_plugin(cls)` in `plugin_loaded()`, an `LspPlugin`/`AbstractPlugin`
  base class that can supply the server config, and a
  `@notification_handler("sema/evalResult")` decorator for custom
  server→client notifications. Separate `LSP-*` repos are a Package Control
  discoverability convention, not a technical requirement.
- Sublime Text 4 runs package Python under 3.3 by default; opting into the 3.8
  plugin host (required to import `LSP.plugin`) needs a `.python-version` file
  containing `3.8` at the package root.

## Scope

### A. Build variant

Add a **Build executable** variant to `Sema.sublime-build`:
`{"name": "Build executable", "cmd": ["sema", "build", "$file"]}`, alongside the
existing run / Format / Compile variants. Update `test_package_contract.py` to
assert the new variant.

### B. Eval command (standalone, no LSP)

New `sema_eval.py`:

- `SemaEvalCommand(sublime_plugin.TextCommand)`, command `sema_eval`.
- Target text: if any selection region is non-empty, concatenate the selected
  regions; otherwise the **whole buffer**.
- Runs `sema eval --stdin --json --path <file> --timeout <ms>` in a background
  thread (never blocks the UI). `--path` uses the view's file name (or a
  placeholder for unsaved buffers) so error spans resolve.
- Parses the JSON envelope and writes a formatted report to a dedicated output
  panel named `Sema` (`window.create_output_panel("exec")`-style, but our own
  panel), showing: stdout, `=> value`, `stderr`, error text, and elapsed ms.
- Non-zero exit / `ok:false` still renders the `error` field; malformed JSON or
  a missing `sema` binary renders a clear diagnostic (how to install / PATH).
- Wiring: palette entry (`Default.sublime-commands`), Tools menu entry
  (`Main.sublime-menu`), and a `source.sema`-scoped key binding
  (`Default (OSX/Linux/Windows).sublime-keymap`), e.g. `ctrl+enter` / `cmd+enter`.

**Testability:** the impure Sublime shell is thin. Pure helpers —
`build_eval_argv(path, timeout)`, `select_source(regions_text, buffer_text)`,
`format_envelope(dict) -> str` — live in a module importable without the
`sublime` module and are covered by `tests/test_eval_command.py`
(plain `unittest`, runnable in CI).

### C. In-package LSP glue (optional, guarded)

New `sema_lsp.py`:

- `try: from LSP.plugin import register_plugin, unregister_plugin, LspPlugin,
  notification_handler` — on `ImportError`, define no-op `plugin_loaded`/
  `plugin_unloaded` and stop (package still fully works without LSP).
- When available: a plugin class registers the `sema` server automatically
  (command `["sema", "lsp"]`, selector `source.sema`) so users need not write
  `LanguageServers.sublime-settings` by hand.
- `@notification_handler("sema/evalResult")` renders the code-lens result into
  the same `Sema` output panel, and adds an inline annotation/phantom at the
  form's `range` (value or error).
- The code lens is **re-enabled** (no more `disabled_capabilities`), since the
  package now renders `sema/evalResult`.
- Exact base class (`LspPlugin` vs `AbstractPlugin`) and config-provision
  mechanism are resolved during implementation against the installed LSP API;
  fallback if auto-registration is finicky at runtime is a documented one-block
  `LanguageServers.sublime-settings` config (same feature, less magic).

### D. README cleanup

- Remove explanatory/narrative paragraphs (the `sema/evalResult` rationale, the
  `sema.toml` formatter aside).
- Keep a single commands/variants table incl. build + eval + the eval keybinding.
- LSP section reduced to current facts: "Install the LSP package via Package
  Control; Sema registers its language server automatically. Features:
  completions, hover, go-to-definition, references, rename, signature help,
  diagnostics, and ▶ Run code lenses." Manual config kept only as a short
  fallback note if needed.

## Error handling

- Missing `sema` on PATH → panel shows an actionable message with the install
  link; no traceback.
- Eval timeout / non-zero exit → render `error`/`stderr` from the envelope.
- LSP import missing → silent no-op (expected when LSP isn't installed).

## Testing strategy

- **Automated (CI):** `tests/test_eval_command.py` unit-tests the pure helpers;
  `test_package_contract.py` extended for the build variant, the presence of the
  eval command wiring, `.python-version == 3.8`, and README shape (no narrative,
  keybinding documented). Existing YAML/JSON/plist validation unchanged.
- **Manual (runtime, documented in the PR):** in Sublime 4 with the package
  installed — eval a selection and the whole buffer; error case; with the LSP
  package installed, confirm the server attaches, the ▶ Run lens appears, and
  clicking it renders output. These can't run headlessly here.

## Conventions to honor

- `.python-version` = `3.8` at package root.
- Export-ignore new dev-only paths (`docs/`, this spec) in `.gitattributes` so
  the Package Control archive stays lean.
- Keep member commits inside `sublime-sema` to its own remote (workspace rule).

## Future work — notebook in an editor tab (deferred, tentative)

IntelliJ (and possibly VSCode) start `sema notebook` in the background and show
its web UI embedded in an editor tab. **Preliminary assessment:** Sublime Text
has no in-editor webview/embedded browser API (unlike VSCode's Webview or
IntelliJ's JCEF), so embedding the notebook UI inside a Sublime tab is very
likely infeasible. The realistic fallback is a `Sema: Open Notebook` command
that launches `sema notebook` in the background and opens its URL in the system
browser. To be confirmed after A–D ship reliably; skip if it adds no real value
over just running `sema notebook` in a terminal.

## Open questions

- Default eval keybinding: `ctrl+enter`/`cmd+enter` vs a chord — pick during
  implementation to avoid clobbering common bindings; scope to `source.sema`.
- Whether to also surface eval output inline (phantom) for the standalone
  command, or keep the panel only (panel-only for the first cut).
