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

        @classmethod
        def _server_exe(cls, configuration):
            from Sema.sema_eval import resolve_sema
            command = configuration.command or ["sema"]
            return resolve_sema(command[0])

        @classmethod
        def can_start(cls, window, initiating_view, workspace_folders, configuration):
            # GUI-launched Sublime gets a bare PATH (no cargo/homebrew dirs),
            # so check an augmented one — and fail with a hint, not a spawn error.
            if cls._server_exe(configuration) is None:
                return (
                    "The `sema` binary was not found on your PATH. "
                    "Install it from https://sema-lang.com to enable the language server."
                )
            return None

        @classmethod
        def on_pre_start(cls, window, initiating_view, workspace_folders, configuration):
            exe = cls._server_exe(configuration)
            if exe:
                configuration.command[0] = exe
            return None

        @notification_handler("sema/evalResult")
        def on_eval_result(self, params):
            from Sema.sema_eval import format_result, show_panel
            session = self.weaksession()
            window = session.window if session else sublime.active_window()
            show_panel(window, format_result(params))

    def plugin_loaded():
        register_plugin(SemaLanguageServer)

    def plugin_unloaded():
        unregister_plugin(SemaLanguageServer)

else:

    def plugin_loaded():
        pass

    def plugin_unloaded():
        pass
