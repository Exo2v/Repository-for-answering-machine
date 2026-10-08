"""Screen Answer v1 — tray app on the FreeLLMAPI gateway architecture.

Version 1 scope (owner decision, 8 October 2026):
- GUI (Settings), notification-area tray, and a diagnostics console.
- Backend: one OpenAI-compatible gateway (FreeLLMAPI by default) with a
  working live web-search function (Gemini grounding pseudo-tool).
- No WebPull scripts, no OCR backends, no Lasso variants in this line.

Stdlib-only runtime (Tkinter + ctypes on Windows).
"""

__version__ = "1.0.0"

APP_NAME = "ScreenAnswer"
