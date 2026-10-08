"""Providers & status window — the FreeLLMAPI-dashboard-style view.

Shows every model behind the gateway with a live status badge
(ready / exhausted / needsKey / router) — the same data the FreeLLMAPI
dashboard highlights — so you can see at a glance which provider is up.
Failover itself is automatic: requests sent as `auto` walk the fallback
chain, so when one model dies the next one answers.
"""

from __future__ import annotations

import threading
from typing import Any, Optional

from .config import Settings
from .gateway import GatewayError, list_models

STATUS_COLORS = {
    "ready": "#3fb950",      # green — will serve now
    "exhausted": "#f85149",  # red — rate-limited / cooldown right now
    "needsKey": "#d29922",   # orange — no usable key configured
    "router": "#58a6ff",     # blue — auto/profile routing entry
    "unknown": "#8b949e",    # grey
}
STATUS_LABELS = {
    "ready": "● ready",
    "exhausted": "● exhausted",
    "needsKey": "● needs key",
    "router": "◆ router",
    "unknown": "● unknown",
}
FILTERS = ("all", "ready", "available", "exhausted", "needsKey", "router")


class ProvidersWindow:
    """Live model/provider table with status badges and auto-refresh."""

    POLL_MS = 5_000

    def __init__(
        self,
        settings: Settings,
        diagnostics: Optional[Any] = None,
        title: str = "Screen Answer — Providers & status",
    ) -> None:
        self.settings = settings
        self.diagnostics = diagnostics
        self._title = title
        self.root = None
        self._rows = []
        self._filter = "all"
        self._busy = False

    # ------------------------------------------------------------------- build

    def build(self) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.root = tk.Toplevel()
        self.root.title(self._title)
        self.root.geometry("820x480")

        top = ttk.Frame(self.root, padding=(10, 8))
        top.pack(fill="x")
        self._header = tk.StringVar(value="Gateway: %s" % self.settings.endpoint)
        ttk.Label(top, textvariable=self._header).pack(side="left")
        ttk.Button(top, text="Open gateway dashboard", command=self._open_dashboard).pack(
            side="right", padx=4
        )
        ttk.Button(top, text="Refresh now", command=self.refresh).pack(side="right")

        filter_bar = ttk.Frame(self.root, padding=(10, 0))
        filter_bar.pack(fill="x")
        ttk.Label(filter_bar, text="Show:").pack(side="left")
        self._filter_var = tk.StringVar(value="all")
        combo = ttk.Combobox(
            filter_bar,
            textvariable=self._filter_var,
            values=FILTERS,
            state="readonly",
            width=12,
        )
        combo.pack(side="left", padx=6)
        combo.bind("<<ComboboxSelected>>", lambda _e: self._apply_rows())
        self._counts = tk.StringVar(value="")
        ttk.Label(filter_bar, textvariable=self._counts).pack(side="left", padx=12)

        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)
        columns = ("status", "name", "id", "owner", "ctx", "note")
        self._tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "status": ("Status", 110),
            "name": ("Model", 240),
            "id": ("ID", 210),
            "owner": ("Provider", 110),
            "ctx": ("Context", 70),
            "note": ("Note", 120),
        }
        for key, (label, width) in headings.items():
            self._tree.heading(key, text=label)
            self._tree.column(key, width=width, anchor="w")
        scrollbar = ttk.Scrollbar(frame, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        for status, color in STATUS_COLORS.items():
            self._tree.tag_configure(status, foreground=color)

        note = ttk.Label(
            self.root,
            text=(
                "Failover is automatic: requests use auto/auto:reliable and walk the "
                "fallback chain — when a model shows ‘exhausted’ or dies, the next "
                "ready model answers. Manage keys & chain order on the gateway dashboard."
            ),
            wraplength=780,
            foreground="#555",
            padding=(10, 4, 10, 10),
        )
        note.pack(fill="x")

        self.refresh()
        self._schedule_poll()

    # ----------------------------------------------------------------- refresh

    def _schedule_poll(self) -> None:
        if self.root is None:
            return
        try:
            self.root.after(self.POLL_MS, self._poll)
        except Exception:
            pass

    def _poll(self) -> None:
        self.refresh()
        self._schedule_poll()

    def refresh(self) -> None:
        if self.root is None or self._busy:
            return
        self._busy = True

        def worker() -> None:
            try:
                rows = list_models(self.settings)
            except GatewayError as exc:
                rows = None
                message = exc.message
            except Exception as exc:
                rows = None
                message = "%s: %s" % (type(exc).__name__, exc)
            def apply() -> None:
                self._busy = False
                if self.root is None:
                    return
                if rows is None:
                    self._header.set("Gateway: %s — %s" % (self.settings.endpoint, message))
                    return
                self._rows = rows
                self._header.set("Gateway: %s" % self.settings.endpoint)
                self._apply_rows()
            try:
                if self.root is not None:
                    self.root.after(0, apply)
                else:
                    self._busy = False
            except Exception:
                self._busy = False

        threading.Thread(target=worker, name="ProvidersRefresh", daemon=True).start()

    def _apply_rows(self) -> None:
        if self.root is None:
            return
        want = self._filter_var.get()
        rows = []
        for row in self._rows:
            if want == "ready" and row["status"] != "ready":
                continue
            if want == "available" and not row["available"]:
                continue
            if want == "exhausted" and row["status"] != "exhausted":
                continue
            if want == "needsKey" and row["status"] != "needsKey":
                continue
            if want == "router" and row["status"] != "router":
                continue
            rows.append(row)

        self._tree.delete(*self._tree.get_children())
        ready = sum(1 for r in self._rows if r["status"] == "ready")
        dead = sum(1 for r in self._rows if r["status"] == "exhausted")
        self._counts.set(
            "%d shown · %d ready · %d exhausted · %d total"
            % (len(rows), ready, dead, len(self._rows))
        )
        for row in rows:
            status = row["status"]
            note = row["reason"] if row["reason"] else ("ok" if row["available"] else "")
            if status == "ready":
                note = "serves now"
            elif status == "router":
                note = "failover chain"
            ctx = row["context_window"]
            self._tree.insert(
                "",
                "end",
                tags=(status,),
                values=(
                    STATUS_LABELS.get(status, status),
                    row["name"][:60],
                    row["id"],
                    row["owner"],
                    ctx if ctx else "—",
                    note,
                ),
            )

    # ----------------------------------------------------------------- actions

    def _open_dashboard(self) -> None:
        import webbrowser

        base = self.settings.endpoint.rstrip("/")
        if base.endswith("/v1"):
            base = base[: -len("/v1")]
        try:
            webbrowser.open(base)
        except Exception:
            pass

    def show(self) -> None:
        if self.root is not None:
            self.root.deiconify()
            self.root.lift()
            self.refresh()
