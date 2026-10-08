"""Screen Answer v1 application core.

Orchestrates: consent gate -> desktop capture -> gateway (with web search)
-> ANSWER parsing -> tray color + fade. UI-free on purpose: the Tk windows
(settings, diagnostics) and the tray shell are injected, so the whole
pipeline is unit-testable headless.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional, Tuple

from .config import Settings, save_settings
from .gateway import (
    GatewayError,
    GatewayResult,
    ask_gateway,
)
from .parser import NEUTRAL_RGB, OPTION_NAMES, parse_option, result_rgb
from .tray import (
    FADE_INTERVAL_MS,
    RESULT_HOLD_MS,
    ShellBase,
    NullShell,
)

MAX_DIAGNOSTIC_TEXT_CHARS = 16_000


def _fade_colors(rgb: Tuple[int, int, int], steps: int = 5) -> list:
    """Interpolation frames from a result color back to neutral grey."""
    frames = []
    for i in range(1, steps + 1):
        t = i / float(steps)
        frames.append(
            tuple(int(round(c + (n - c) * t)) for c, n in zip(rgb, NEUTRAL_RGB))
        )
    return frames


class ScreenAnswerApp:
    """Owns settings/diagnostics/shell and runs the capture pipeline."""

    def __init__(
        self,
        settings: Settings,
        shell: Optional[ShellBase] = None,
        diagnostics: Optional[Any] = None,
        capture_fn: Optional[Callable[[], bytes]] = None,
        gateway_fn: Optional[Callable[[Settings, bytes, Optional[Callable[[str], None]]], GatewayResult]] = None,
        scheduler: Optional[Callable[[int, Callable[[], None]], None]] = None,
        status_fn: Optional[Callable[[str], None]] = None,
    ) -> None:
        from . import capture as capture_module

        self.settings = settings
        self.shell = shell or NullShell()
        self.diagnostics = diagnostics
        self._capture_fn = capture_fn or capture_module.capture_virtual_desktop_png
        self._gateway_fn = gateway_fn or ask_gateway
        self._scheduler = scheduler
        self._status_fn = status_fn or (lambda text: None)
        self._busy = threading.Lock()
        self._closed = False

    # ------------------------------------------------------------------ logging

    def log(self, message: str) -> None:
        if self.diagnostics is not None:
            self.diagnostics.log(message)

    def _status(self, message: str) -> None:
        self.log(message)
        self._status_fn(message)

    # ------------------------------------------------------------------ events

    def handle_event(self, event: Tuple[Any, ...]) -> None:
        kind = event[0] if event else ""
        if kind == "capture":
            self.request_capture()
        elif kind == "open":
            self._status("Settings requested from the tray.")
        elif kind == "diagnostics":
            self._status("Diagnostics requested from the tray.")
        elif kind == "exit":
            self._closed = True
            self.shell.stop()
        elif kind == "fatal":
            self._status(str(event[1]) if len(event) > 1 else "Fatal tray error.")
            self.shell.set_state(NEUTRAL_RGB, "Screen Answer (error)")

    # ---------------------------------------------------------------- pipeline

    def request_capture(self) -> bool:
        """Kick the capture pipeline on a worker thread; False if already busy."""
        if self._closed:
            return False
        if not self._busy.acquire(blocking=False):
            self._status("A capture is already running.")
            return False
        thread = threading.Thread(
            target=self._run_capture_guarded, name="ScreenAnswerCapture", daemon=True
        )
        thread.start()
        return True

    def run_capture_sync(self) -> Optional[int]:
        """Run the pipeline inline (tests, --selftest). Returns the position or None."""
        if not self._busy.acquire(blocking=False):
            self._status("A capture is already running.")
            return None
        # _run_capture_guarded releases the busy lock in its finally clause.
        return self._run_capture_guarded()

    def _run_capture_guarded(self) -> Optional[int]:
        try:
            return self._run_capture()
        except Exception as exc:  # defensive: never take the tray down
            self._status("Capture pipeline failed (%s): %s" % (type(exc).__name__, exc))
            self.shell.set_state(NEUTRAL_RGB, "Screen Answer (error)")
            return None
        finally:
            try:
                self._busy.release()
            except RuntimeError:
                pass

    def _run_capture(self) -> Optional[int]:
        if not self.settings.allow_uploads:
            self._status(
                "Capture blocked: enable screenshot upload consent in Settings first."
            )
            self.shell.set_state(NEUTRAL_RGB, "Screen Answer (consent required)")
            return None

        self.shell.set_state(NEUTRAL_RGB, "Screen Answer (working…)")
        self._status("Capturing the virtual desktop…")
        try:
            png_bytes = self._capture_fn()
        except Exception as exc:
            self._status("Capture failed: %s" % exc)
            self.shell.set_state(NEUTRAL_RGB, "Screen Answer (capture failed)")
            return None
        self._status("Captured %d PNG bytes (held in memory only)." % len(png_bytes))

        web_search = bool(self.settings.web_search)
        self._status(
            "Asking the gateway (search=%s, request model=%s)…"
            % (web_search, self.settings.request_model())
        )
        try:
            result = self._gateway_fn(self.settings, png_bytes, self.log)
        except GatewayError as exc:
            self._status("Gateway: %s" % exc.message)
            self.shell.set_state(NEUTRAL_RGB, "Screen Answer (no answer)")
            self.shell.show_balloon("Screen Answer", "No answer — see Diagnostics.")
            return None

        position = parse_option(result.text)
        if position is None:
            self._status(
                "No reliable ANSWER line (served model: %s). Staying neutral."
                % result.model
            )
            self.shell.set_state(NEUTRAL_RGB, "Screen Answer (no reliable answer)")
            return None

        name = OPTION_NAMES.get(position, "?")
        self._status(
            "ANSWER: %d (%s) — served by %s after %d attempt(s)."
            % (position, name, result.model, result.attempts)
        )
        rgb = result_rgb(position)
        self.shell.set_state(rgb, "Screen Answer: option %d" % position)
        self._schedule_fade(rgb)
        return position

    # -------------------------------------------------------------------- fade

    def _schedule_fade(self, rgb: Tuple[int, int, int]) -> None:
        frames = _fade_colors(rgb)
        hold = RESULT_HOLD_MS
        step = FADE_INTERVAL_MS

        def apply(index: int = 0) -> None:
            if self._closed:
                return
            if index >= len(frames):
                self.shell.set_state(NEUTRAL_RGB, "Screen Answer (ready)")
                return
            self.shell.set_state(frames[index], "Screen Answer (ready)")
            self._later(step, lambda: apply(index + 1))

        self._later(hold, lambda: apply(0))

    def _later(self, delay_ms: int, callback: Callable[[], None]) -> None:
        if self._scheduler is not None:
            self._scheduler(delay_ms, callback)
        else:
            timer = threading.Timer(delay_ms / 1000.0, callback)
            timer.daemon = True
            timer.start()

    # ----------------------------------------------------------------- helpers

    def save(self) -> str:
        """Persist settings (sidecar only when portable saving is enabled)."""
        path = save_settings(self.settings)
        if path:
            self._status("Settings saved to %s" % path)
        else:
            self._status("Settings kept in memory for this run (portable save is off).")
        return path
