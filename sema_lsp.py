"""Optional LSP integration for Sema.

Active only when the sublimelsp/LSP package is installed. Its main job is to
register the `sema lsp` server automatically (zero-config) for `source.sema`
files. When LSP is absent this module is an inert no-op, so the rest of the
package works without it.

The server's per-form "Run" code lens is disabled by default (see
`sema-lsp.sublime-settings`): it runs sandboxed without LLM access and
duplicates the Sema: Eval command. The `sema/evalResult` handler below is kept
so that if a user re-enables the code lens, clicking Run still shows a result
(into the shared Sema output panel) instead of being a silent no-op.
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
