"""Settings window (Tkinter): gateway endpoint, key, model, web search, consent.

Consent rules preserved from the v1.7 line: upload consent is session-only
and resets whenever the route (endpoint/model) or search setting changes;
nothing is written to disk unless portable saving is explicitly enabled.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from .config import Settings, valid_endpoint, valid_model_name

CONSENT_NOTICE = (
    "Data path: the full desktop screenshot is captured in memory and sent to "
    "the configured gateway endpoint, which routes it to a vision model "
    "provider. Nothing is written to disk. Keys stay with the gateway."
)

SEARCH_NOTICE = (
    "Web search: when enabled, question-derived query text may also be sent "
    "to the search upstream through the gateway's grounding tool. The "
    "screenshot still goes only to the vision solver."
)


class SettingsWindow:
    """The v1 Settings GUI. Build with `build(root)`; requires Tkinter."""

    def __init__(
        self,
        settings: Settings,
        on_save: Callable[[], None],
        on_capture: Callable[[], None],
        on_diagnostics: Callable[[], None],
        on_exit: Callable[[], None],
        on_providers: Optional[Callable[[], None]] = None,
        status_fn: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.settings = settings
        self._on_save = on_save
        self._on_capture = on_capture
        self._on_diagnostics = on_diagnostics
        self._on_exit = on_exit
        self._on_providers = on_providers
        self._status_fn = status_fn or (lambda text: None)
        self.root = None
        self._suspend_traces = False

    # ------------------------------------------------------------------- build

    def build(self, root: Any) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        root.title("Screen Answer — Settings")
        root.geometry("520x470")
        root.resizable(False, False)

        frame = ttk.Frame(root, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Gateway endpoint (FreeLLMAPI / OpenAI-compatible):").grid(
            row=0, column=0, sticky="w"
        )
        self.endpoint_var = tk.StringVar(value=self.settings.endpoint)
        ttk.Entry(frame, textvariable=self.endpoint_var, width=52).grid(
            row=1, column=0, columnspan=2, sticky="we", pady=(0, 8)
        )

        ttk.Label(frame, text="Gateway API key (stored only with portable saving):").grid(
            row=2, column=0, sticky="w"
        )
        self.key_var = tk.StringVar(value=self.settings.api_key)
        ttk.Entry(frame, textvariable=self.key_var, show="*", width=52).grid(
            row=3, column=0, columnspan=2, sticky="we", pady=(0, 8)
        )

        ttk.Label(
            frame,
            text="Model (auto, auto:reliable, auto:fast, auto:search, or a pinned ID):",
        ).grid(row=4, column=0, sticky="w")
        self.model_var = tk.StringVar(value=self.settings.model)
        ttk.Entry(frame, textvariable=self.model_var, width=52).grid(
            row=5, column=0, columnspan=2, sticky="we", pady=(0, 8)
        )

        self.search_var = tk.BooleanVar(value=self.settings.web_search)
        self.search_check = ttk.Checkbutton(
            frame,
            text="Enable live web search (google_search grounding via the gateway)",
            variable=self.search_var,
            command=self._route_changed,
        )
        self.search_check.grid(row=6, column=0, columnspan=2, sticky="w")
        ttk.Label(frame, text=SEARCH_NOTICE, wraplength=480, foreground="#444").grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(2, 8)
        )

        self.consent_var = tk.BooleanVar(value=self.settings.allow_uploads)
        ttk.Checkbutton(
            frame,
            text="I allow sending screenshots of my desktop to the configured endpoint",
            variable=self.consent_var,
            command=self._consent_toggled,
        ).grid(row=8, column=0, columnspan=2, sticky="w")
        ttk.Label(frame, text=CONSENT_NOTICE, wraplength=480, foreground="#444").grid(
            row=9, column=0, columnspan=2, sticky="w", pady=(2, 8)
        )

        self.save_var = tk.BooleanVar(value=self.settings.save_to_file)
        ttk.Checkbutton(
            frame,
            text="Portable: save settings to screen_answer_config.json (plaintext)",
            variable=self.save_var,
        ).grid(row=10, column=0, columnspan=2, sticky="w")

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(frame, textvariable=self.status_var, foreground="#222").grid(
            row=11, column=0, columnspan=2, sticky="w", pady=(8, 4)
        )

        buttons = ttk.Frame(frame)
        buttons.grid(row=12, column=0, columnspan=2, sticky="we")
        ttk.Button(buttons, text="Save", command=self._save).pack(side="left")
        ttk.Button(buttons, text="Capture & ask now", command=self._on_capture).pack(
            side="left", padx=6
        )
        ttk.Button(buttons, text="Diagnostics", command=self._on_diagnostics).pack(
            side="left"
        )
        if self._on_providers is not None:
            ttk.Button(buttons, text="Providers & status", command=self._on_providers).pack(
                side="left", padx=6
            )
        ttk.Button(buttons, text="Exit", command=self._on_exit).pack(side="right")

        # Changing the route or search mode resets consent (project rule).
        for var in (self.endpoint_var, self.model_var):
            var.trace_add("write", lambda *_: self._route_changed())

        self._status = self.status_var.set

    # ------------------------------------------------------------------ events

    def _consent_toggled(self) -> None:
        self.settings.allow_uploads = bool(self.consent_var.get())

    def _route_changed(self) -> None:
        if self._suspend_traces:
            return
        if self.consent_var.get():
            self.consent_var.set(False)
            self.settings.allow_uploads = False
            self.set_status("Consent reset — the route or search setting changed. Re-check to continue.")

    def set_status(self, text: str) -> None:
        if self.root is not None:
            try:
                self.status_var.set(text)
            except Exception:
                pass
        self._status_fn(text)

    # -------------------------------------------------------------------- save

    def _save(self) -> None:
        endpoint = self.endpoint_var.get().strip()
        model = self.model_var.get().strip()
        if not valid_endpoint(endpoint):
            self.set_status("Endpoint must start with http:// or https://")
            return
        if not valid_model_name(model):
            self.set_status(
                "Model must be a routing profile (auto:…) or a model id like "
                "google/gemini-3.8-flash"
            )
            return
        self._suspend_traces = True
        try:
            self.settings.endpoint = endpoint
            self.settings.model = model
            self.settings.api_key = self.key_var.get().strip()
            self.settings.web_search = bool(self.search_var.get())
            self.settings.save_to_file = bool(self.save_var.get())
            self.settings.allow_uploads = bool(self.consent_var.get())
            self._on_save()
        finally:
            self._suspend_traces = False
        if self.root is not None:
            self.root.withdraw()
