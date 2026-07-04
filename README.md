<div align="center">

<img src="https://sema-lang.com/logo.svg" alt="Sema" height="64">

# Sema for Sublime Text

**[Sema](https://sema-lang.com) support for [Sublime Text](https://www.sublimetext.com)** — a Lisp with first-class LLM primitives.

[![CI](https://img.shields.io/github/actions/workflow/status/sema-lisp/sublime-sema/ci.yml?branch=main&label=CI&logo=github)](https://github.com/sema-lisp/sublime-sema/actions)
[![License](https://img.shields.io/github/license/sema-lisp/sublime-sema?color=c8a855)](LICENSE)
[![Website](https://img.shields.io/badge/website-sema--lang.com-c8a855)](https://sema-lang.com)

</div>

Language support for [Sema](https://sema-lang.com), a Lisp dialect with first-class LLM primitives, for [Sublime Text](https://www.sublimetext.com) 4.

## Features

- Syntax highlighting for `.sema` files (special forms, builtins, LLM primitives, keywords, strings, numbers, characters, quote operators, and more) via a native `.sublime-syntax` definition
- Comment toggling with `Cmd+/` / `Ctrl+/` (line `;` and block `#| |#`)
- Symbol navigation (`Cmd+R` / `Ctrl+R`) for `define`, `defun`, `defmacro`, `defagent`, `deftool`, and friends
- Build systems for **running** (`sema`), **formatting** (`sema fmt`), and **compiling** (`sema compile`)
- Optional **language server** (`sema lsp`) via the [LSP](https://packagecontrol.io/packages/LSP) package: completions, hover docs, go-to-definition, references, rename, signature help, and diagnostics

The scope names match [vscode-sema](https://github.com/sema-lisp/vscode-sema)'s TextMate grammar, so color schemes theme both editors identically.

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
  "$HOME/Library/Application Support/Sublime Text/Packages/sublime-sema"

# Linux
git clone https://github.com/sema-lisp/sublime-sema \
  "$HOME/.config/sublime-text/Packages/sublime-sema"

# Windows (PowerShell)
git clone https://github.com/sema-lisp/sublime-sema `
  "$env:APPDATA\Sublime Text\Packages\sublime-sema"
```

Find the `Packages` directory quickly via the command palette → **Preferences: Browse Packages**.

## Building & running

Open a `.sema` file and use **Tools → Build System → Sema** (or `Cmd+B` / `Ctrl+B`). Variants (`Cmd+Shift+B` / `Ctrl+Shift+B`):

| Variant | Command |
| --- | --- |
| Sema | `sema <file>` — run the program |
| Sema — Format | `sema fmt <file>` |
| Sema — Compile to bytecode | `sema compile <file>` |

The build systems shell out to the `sema` binary, so it must be on your `PATH`. Install it from [sema-lang.com](https://sema-lang.com).

## Language server

Syntax highlighting, comments, symbols, and build systems work without any extra setup. For IDE features (completions, hover, go-to-definition, diagnostics), Sema ships a language server behind `sema lsp`. Wire it up through the [LSP](https://packagecontrol.io/packages/LSP) package:

1. Install **LSP** via Package Control.
2. Open the command palette → **Preferences: LSP Settings** and add a client:

```jsonc
{
  "clients": {
    "sema": {
      "enabled": true,
      "command": ["sema", "lsp"],
      "selector": "source.sema"
    }
  }
}
```

Restart Sublime Text (or run **LSP: Restart Servers**). The `selector` matches this package's `source.sema` scope, so the server attaches to any `.sema` file.

## Links

- **Website** — [sema-lang.com](https://sema-lang.com)
- **Playground** — [sema.run](https://sema.run)
- **Documentation** — [sema-lang.com/docs](https://sema-lang.com/docs/)
- **Grammar** — [tree-sitter-sema](https://github.com/sema-lisp/tree-sitter-sema)
- **Repository** — [sema-lisp/sublime-sema](https://github.com/sema-lisp/sublime-sema)

## License

[MIT](LICENSE) © [Helge Sverre](https://github.com/HelgeSverre)
