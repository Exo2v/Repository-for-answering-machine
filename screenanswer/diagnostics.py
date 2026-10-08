"""Diagnostics event bus and console window.

Events are kept in memory only (never written without an explicit save),
API keys and key-like tokens are redacted before display, and the console
is a live scrolling log with Clear / Save buttons (the v1.7 diagnostic
window behaviour, minus OCR/lasso-specific events).
"""

from __future__ import annotations

import queue
import re
import threading
import time
from typing import Callable, List, Optional

MAX_DIAGNOSTIC_TEXT_CHARS = 16_000
MAX_RETAINED_EVENTS = 2_000

_SECRET_RE = re.compile(r"\b(?:sk|freellmapi)-[A-Za-z0-9_\-]{8,}\b")
_BEARER_RE = re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE)


def redact(text: str, extra_secrets: Optional[List[str]] = None) -> str:
    """Strip key-like tokens and any explicitly known secret values."""
    if not text:
        return text
    out = _SECRET_RE.sub("[redacted]", text)
    out = _BEARER_RE.sub(r"\1[redacted]", out)
    for secret in extra_secrets or []:
        if secret and len(secret) >= 6:
            out = out.replace(secret, "[redacted]")
    return out


class Diagnostics:
    """Thread-safe event log feeding the console UI and any listeners."""

    def __init__(self, secrets: Optional[Callable[[], List[str]]] = None) -> None:
        self._lock = threading.RLock()
        self._events: "queue.Queue[str]" = queue.Queue()
        self._retained: List[str] = []
        self._listeners: List[Callable[[str], None]] = []
        self._secrets = secrets or (lambda: [])

    def add_listener(self, listener: Callable[[str], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def log(self, message: str) -> None:
        stamped = "%s  %s" % (time.strftime("%H:%M:%S"), redact(message, self._secrets()))
        with self._lock:
            self._retained.append(stamped)
            if len(self._retained) > MAX_RETAINED_EVENTS:
                del self._retained[: len(self._retained) - MAX_RETAINED_EVENTS]
            listeners = list(self._listeners)
        self._events.put(stamped)
        for listener in listeners:
            try:
                listener(stamped)
            except Exception:
                pass

    def drain(self) -> List[str]:
        """Return queued lines for a UI poll loop (non-blocking)."""
        lines = []
        while True:
            try:
                lines.append(self._events.get_nowait())
            except queue.Empty:
                return lines

    def snapshot(self) -> str:
        with self._lock:
            return "\n".join(self._retained)


class DiagnosticConsole:
    """Tk window with a live scrolling log. Import Tk lazily (headless-safe)."""

    POLL_MS = 250

    def __init__(self, diagnostics: Diagnostics, title: str = "Screen Answer — Diagnostics") -> None:
        import tkinter as tk

        self._diagnostics = diagnostics
        self.root = tk.Toplevel()
        self.root.title(title)
        self.root.geometry("760x460")
        frame = tk.Frame(self.root)
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        self._text = tk.Text(frame, wrap="word", state="disabled", font=("Consolas", 9))
        self._text.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(frame, command=self._text.yview)
        scrollbar.pack(side="right", fill="y")
        self._text.configure(yscrollcommand=scrollbar.set)
        buttons = tk.Frame(self.root)
        buttons.pack(fill="x", padx=6, pady=(0, 6))
        tk.Button(buttons, text="Clear", command=self._clear).pack(side="left")
        tk.Button(buttons, text="Save log…", command=self._save).pack(side="left", padx=6)
        tk.Button(buttons, text="Close", command=self.root.withdraw).pack(side="right")
        self.root.protocol("WM_DELETE_WINDOW", self.root.withdraw)
        self._poll()

    def _poll(self) -> None:
        try:
            lines = self._diagnostics.drain()
            if lines:
                self._text.configure(state="normal")
                for line in lines:
                    self._text.insert("end", line + "\n")
                self._text.see("end")
                self._text.configure(state="disabled")
        except Exception:
            pass
        try:
            self.root.after(self.POLL_MS, self._poll)
        except Exception:
            pass

    def _clear(self) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")

    def _save(self) -> None:
        from tkinter import filedialog

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All files", "*.*")],
            title="Save diagnostic log",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self._diagnostics.snapshot())
        except OSError:
            pass

    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()
