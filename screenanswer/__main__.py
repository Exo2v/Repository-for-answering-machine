"""Command-line entry point: `python -m screenanswer`."""

from __future__ import annotations

import argparse
import queue
import sys
from typing import Any, Tuple

from . import __version__
from .config import load_settings, portable_config_path


def _run_selftest() -> int:
    """Headless smoke checks: parser, prompts, payload shape, PNG encoder."""
    import base64

    from .capture import encode_rgb_png
    from .config import Settings
    from .gateway import build_payload, resolve_model
    from .parser import parse_option
    from .prompt import system_instruction, user_prompt

    checks = []

    def check(name: str, condition: bool) -> None:
        checks.append((name, bool(condition)))

    check("parser: ANSWER: 3", parse_option("SOLUTION: work\nANSWER: 3") == 3)
    check("parser: letter D", parse_option("ANSWER: D") == 4)
    check("parser: final wins", parse_option("ANSWER: 1\nFinal ANSWER: 2") == 2)
    check("parser: ambiguous neutral", parse_option("ANSWER: 1\nANSWER: 2") is None)
    check("parser: digits ignored", parse_option("value 42 then\nANSWER: 1") == 1)
    check("parser: ANSWER: 0 neutral", parse_option("ANSWER: 0") is None)

    png = encode_rgb_png(2, 2, bytes(range(2 * 2 * 3)), stride=2 * 3)
    check("capture: PNG magic", png.startswith(b"\x89PNG\r\n\x1a\n"))

    settings = Settings(web_search=True, model="auto:reliable")
    payload = build_payload(settings, png)
    check("gateway: search steering", payload["model"] == "auto:search")
    check("gateway: tool present", payload["tools"][0]["function"]["name"] == "google_search")
    image_url = payload["messages"][1]["content"][1]["image_url"]["url"]
    check("gateway: data URL", image_url.startswith("data:image/png;base64,"))
    check("gateway: base64 round-trip", base64.b64decode(image_url.split(",", 1)[1]) == png)

    settings.web_search = False
    payload = build_payload(settings, png)
    check("gateway: no tools when search off", "tools" not in payload)
    check("gateway: model kept", payload["model"] == "auto:reliable")
    check("gateway: pinned kept", resolve_model("google/gemini-3.8-flash", True) == "google/gemini-3.8-flash")

    check("prompt: search clause", "Live web search is available" in system_instruction(True))
    check("prompt: no-search rule", "Do not use or claim live web search" in system_instruction(False))
    check("prompt: user search clause", "may use live web search" in user_prompt(True))

    failed = 0
    for name, ok in checks:
        print("%s  %s" % ("PASS" if ok else "FAIL", name))
        if not ok:
            failed += 1
    print("%d/%d checks passed." % (len(checks) - failed, len(checks)))
    return 1 if failed else 0


def _run_app(show_diagnostics: bool) -> int:
    try:
        import tkinter as tk
    except ImportError:
        print("Tkinter is required for the GUI. Run --selftest for headless checks.")
        return 1

    from .app import ScreenAnswerApp
    from .diagnostics import DiagnosticConsole, Diagnostics
    from .settings_gui import SettingsWindow
    from .tray import create_shell

    settings = load_settings()
    diagnostics = Diagnostics(secrets=lambda: [settings.api_key] if settings.api_key else [])
    events: "queue.Queue[Tuple[Any, ...]]" = queue.Queue()

    root = tk.Tk()
    root.withdraw()  # settings open on demand; no window at startup

    console_holder: dict = {}
    settings_holder: dict = {}

    def scheduler(delay_ms: int, callback: Any) -> None:
        root.after(delay_ms, callback)

    app = ScreenAnswerApp(
        settings,
        diagnostics=diagnostics,
        scheduler=scheduler,
        status_fn=lambda text: (
            settings_holder.get("window") and settings_holder["window"].set_status(text)
        ),
    )

    def open_settings() -> None:
        window = settings_holder.get("window")
        if window is not None:
            window.root.deiconify()
            window.root.lift()

    def open_diagnostics() -> None:
        if "console" not in console_holder:
            console_holder["console"] = DiagnosticConsole(diagnostics)
        console_holder["console"].show()

    def exit_app() -> None:
        app.handle_event(("exit",))
        root.after(200, root.destroy)

    shell = create_shell(events)

    window = SettingsWindow(
        settings,
        on_save=app.save,
        on_capture=app.request_capture,
        on_diagnostics=open_diagnostics,
        on_exit=exit_app,
    )
    window.build(root)
    settings_holder["window"] = window
    open_settings()
    if show_diagnostics:
        open_diagnostics()

    diagnostics.log(
        "Screen Answer v%s started (endpoint=%s, model=%s, search=%s)."
        % (__version__, settings.endpoint, settings.model, settings.web_search)
    )

    def poll_events() -> None:
        while True:
            try:
                event = events.get_nowait()
            except queue.Empty:
                break
            if event and event[0] == "open":
                open_settings()
            elif event and event[0] == "diagnostics":
                open_diagnostics()
            else:
                # capture / delete (silent self-deletion) / exit / fatal
                app.handle_event(event)
            if app._closed:
                root.after(150, root.destroy)
                return
        root.after(200, poll_events)

    root.after(200, poll_events)
    root.protocol("WM_DELETE_WINDOW", exit_app)
    root.mainloop()
    return 0


def main(argv=None) -> int:
    # Frozen `--windowed` builds have no console: sys.stdout/sys.stderr can be
    # None. Never crash on output (print/argparse) in that mode.
    import io
    if sys.stdout is None:
        sys.stdout = io.StringIO()
    if sys.stderr is None:
        sys.stderr = io.StringIO()

    parser = argparse.ArgumentParser(
        prog="screenanswer",
        description="Screen Answer v1 — tray + GUI + diagnostics on the FreeLLMAPI gateway.",
    )
    parser.add_argument("--version", action="version", version="ScreenAnswer " + __version__)
    parser.add_argument(
        "--diagnostics", action="store_true", help="open the diagnostics console at startup"
    )
    parser.add_argument(
        "--selftest", action="store_true", help="run headless smoke checks and exit"
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="portable config path (default: ./screen_answer_config.json)",
    )
    args = parser.parse_args(argv)

    if args.selftest:
        return _run_selftest()
    if args.config:
        import os

        os.environ["SCREENANSWER_CONFIG"] = args.config  # informational
        from . import config as config_module

        settings = config_module.load_settings(args.config)
        # Temporarily point the default loader at the given path for this run.
        config_module.portable_config_path = lambda: args.config  # type: ignore
        del settings
    return _run_app(show_diagnostics=args.diagnostics)


if __name__ == "__main__":
    sys.exit(main())
