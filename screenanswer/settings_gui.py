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
        root.geometry("560x580")
        root.resizable(False, False)

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=6, pady=6)

        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text="General")
        self._build_keys_tab(notebook)

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

        buttons = ttk.Frame(root)
        buttons.pack(fill="x", padx=12, pady=(0, 10))
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

    # ------------------------------------------------------- bulk keys tab

    def _build_keys_tab(self, notebook: Any) -> None:
        import tkinter as tk
        from tkinter import ttk

        from .admin_api import KNOWN_PLATFORMS

        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text="API keys (bulk)")

        ttk.Label(
            tab,
            text=(
                "Gateway dashboard login — the email/password of your FreeLLMAPI "
                "dashboard (localhost:3001). Used once to register the keys below; "
                "never saved by Screen Answer."
            ),
            wraplength=500,
            foreground="#444",
        ).pack(anchor="w")
        login_row = ttk.Frame(tab)
        login_row.pack(fill="x", pady=(4, 8))
        self._dash_email = tk.StringVar()
        self._dash_password = tk.StringVar()
        ttk.Label(login_row, text="Email:").pack(side="left")
        ttk.Entry(login_row, textvariable=self._dash_email, width=24).pack(
            side="left", padx=(2, 10)
        )
        ttk.Label(login_row, text="Password:").pack(side="left")
        ttk.Entry(login_row, textvariable=self._dash_password, width=24, show="•").pack(
            side="left", padx=2
        )

        assume_row = ttk.Frame(tab)
        assume_row.pack(fill="x", pady=(0, 6))
        ttk.Label(assume_row, text="Provider for unmarked keys:").pack(side="left")
        self._assume_platform = tk.StringVar(value="auto-detect")
        ttk.Combobox(
            assume_row,
            textvariable=self._assume_platform,
            values=("auto-detect",) + KNOWN_PLATFORMS,
            state="readonly",
            width=14,
        ).pack(side="left", padx=6)

        ttk.Label(
            tab,
            text="One key per line. Auto-detected: AIza…=google, gsk_…=groq, "
            "sk-or-…=openrouter, ghp_/github_pat_…=github. Or mark it: zhipu:abc123.",
            wraplength=500,
            foreground="#444",
        ).pack(anchor="w")
        self._keys_text = tk.Text(tab, height=8, width=62, wrap="none")
        self._keys_text.pack(fill="both", expand=True, pady=(2, 6))

        push_row = ttk.Frame(tab)
        push_row.pack(fill="x")
        self._add_keys_btn = ttk.Button(
            push_row, text="Add keys to gateway", command=self._push_keys
        )
        self._add_keys_btn.pack(side="left")
        ttk.Label(
            push_row,
            text="Sent to your gateway only — Screen Answer keeps none of them.",
            foreground="#444",
        ).pack(side="left", padx=10)

        self._keys_log = tk.Text(tab, height=7, width=62, state="disabled", wrap="word")
        self._keys_log.pack(fill="both", expand=True, pady=(6, 0))

    def _push_keys(self) -> None:
        import threading

        from .admin_api import AdminApiError, AdminClient, parse_keys_text

        def append(line: str) -> None:
            log = self._keys_log
            log.configure(state="normal")
            log.insert("end", line + "\n")
            log.see("end")
            log.configure(state="disabled")

        assume = self._assume_platform.get()
        pairs, errors = parse_keys_text(
            self._keys_text.get("1.0", "end"), None if assume == "auto-detect" else assume
        )
        for lineno, message in errors[:20]:
            append("line %d: %s" % (lineno, message))
        if not pairs:
            if not errors:
                append("Nothing to add — paste one key per line first.")
            return

        email = self._dash_email.get().strip()
        password = self._dash_password.get()
        if not email or not password:
            append("Dashboard email and password are required to register keys.")
            return

        self._add_keys_btn.configure(state="disabled")
        append("Logging in to the gateway dashboard…")

        def mask(value: str) -> str:
            if len(value) <= 10:
                return value[:2] + "…"
            return value[:6] + "…" + value[-2:]

        def worker() -> None:
            ok = 0
            try:
                client = AdminClient(self.settings.endpoint)
                client.login(email, password)
                append("Logged in — adding %d keys…" % len(pairs))
                for platform, key in pairs:
                    try:
                        result = client.add_key(platform, key)
                        ok += 1
                        append(
                            "added %-12s %s  (key id %s)"
                            % (platform, mask(key), result.get("id", "?"))
                        )
                    except AdminApiError as exc:
                        append("FAILED %-12s %s — %s" % (platform, mask(key), exc.message))
                append(
                    "Done: %d of %d keys added. Open Providers & status to see them go green."
                    % (ok, len(pairs))
                )
            except AdminApiError as exc:
                append("Login failed: %s" % exc.message)
            except Exception as exc:
                append("Unexpected error: %s: %s" % (type(exc).__name__, exc))
            finally:
                def done() -> None:
                    self._add_keys_btn.configure(state="normal")

                try:
                    if self.root is not None:
                        self.root.after(0, done)
                    else:
                        done()
                except Exception:
                    pass

        threading.Thread(target=worker, name="KeysPush", daemon=True).start()

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
