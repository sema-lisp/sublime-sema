<div align="center">

<img src="https://sema-lang.com/logo.svg" alt="Sema" height="64">

# Sema for Sublime Text

**[Sema](https://sema-lang.com) support for [Sublime Text](https://www.sublimetext.com)** — a Lisp with first-class LLM primitives.

[![CI](https://img.shields.io/github/actions/workflow/status/sema-lisp/sublime-sema/ci.yml?branch=main&label=CI&logo=github)](https://github.com/sema-lisp/sublime-sema/actions)
[![License](https://img.shields.io/github/license/sema-lisp/sublime-sema?color=c8a855)](LICENSE)
[![Website](https://img.shields.io/badge/website-sema--lang.com-c8a855)](https://sema-lang.com)

</div>

Language support for [Sema](https://sema-lang.com), a Lisp dialect with first-class LLM primitives, for [Sublime Text](https://www.sublimetext.com) 4.

## Install

### Package Control (recommended)

1. Install [Package Control](https://packagecontrol.io/installation) if you haven't already.
2. Open the command palette (`Cmd+Shift+P` / `Ctrl+Shift+P`) → **Package Control: Install Package**.
3. Search for **Sema** and install it.

### Manual

Clone into your Sublime Text `Packages` directory:

```bash
# macOS
git clone https://github.com/sema-lisp/sublime-sema \
  "$HOME/Library/Application Support/Sublime Text/Packages/Sema"

# Linux
git clone https://github.com/sema-lisp/sublime-sema \
  "$HOME/.config/sublime-text/Packages/Sema"

# Windows (PowerShell)
git clone https://github.com/sema-lisp/sublime-sema `
  "$env:APPDATA\Sublime Text\Packages\Sema"
```

Find the `Packages` directory quickly via the command palette → **Preferences: Browse Packages**.

## Features

- Syntax highlighting for `.sema` files (special forms, builtins, LLM primitives, keywords, strings, numbers, characters, quote operators, and more) via a native `.sublime-syntax` definition
- Comment toggling with `Cmd+/` / `Ctrl+/` (Sema's `;` line comments)
- Symbol navigation (`Cmd+R` / `Ctrl+R`) for `define`, `defun`, `defmacro`, `defagent`, `deftool`, and friends
- **Eval** the selection (or whole file) via **Sema: Eval Selection or Buffer** — output shows in the Sema panel (optional key binding below)
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

To evaluate code without a full build, select an expression and run **Sema: Eval Selection or Buffer** from the command palette. With nothing selected, the whole file is evaluated. Output appears in the **Sema** panel.

The build systems and the eval command invoke the `sema` binary, so it must be on your `PATH`. Install it from [sema-lang.com](https://sema-lang.com).

## Language server

For IDE features — completions, hover, go-to-definition, references, rename, signature help, and diagnostics — install the [LSP](https://packagecontrol.io/packages/LSP) package via Package Control. Sema registers its `sema lsp` server automatically for `source.sema` files; no manual configuration is needed. Restart Sublime Text (or run **LSP: Restart Servers**) after installing LSP.

To override the server command or options, open **Preferences → Package Settings → Sema → Settings** (or run **Preferences: Sema Settings** from the command palette).

## Key bindings

The package ships no active key bindings, so it never overrides yours or Sublime's defaults. To bind the eval command, open **Preferences → Package Settings → Sema → Key Bindings** — the left pane shows ready-to-copy examples, the right pane is your user keymap. For instance:

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

Use `ctrl+enter` on Linux/Windows. Heads up: this chord shadows Sublime's built-in "insert line after" inside Sema files — pick another if you rely on it.

## Requirements

- [Sublime Text](https://www.sublimetext.com) 4
- The [`sema`](https://sema-lang.com) binary on your `PATH` — used by the build systems (`sema`, `sema fmt`, `sema compile`, `sema build`), the Eval command (`sema eval`), and the language server (`sema lsp`)
- The [LSP](https://packagecontrol.io/packages/LSP) package (optional) for IDE features

## Links

- **Website** — [sema-lang.com](https://sema-lang.com)
- **Playground** — [sema.run](https://sema.run)
- **Documentation** — [sema-lang.com/docs](https://sema-lang.com/docs/)
- **Grammar** — [tree-sitter-sema](https://github.com/sema-lisp/tree-sitter-sema)
- **Repository** — [sema-lisp/sublime-sema](https://github.com/sema-lisp/sublime-sema)

## License

[MIT](LICENSE) © [Helge Sverre](https://github.com/HelgeSverre)
