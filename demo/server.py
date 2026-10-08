"""Interactive demo harness for Screen Answer v1.

Serves a live in-browser view of the three v1 surfaces — the Settings GUI,
the tray icon (color states + fade), and the diagnostics console — driven by
the REAL `screenanswer` core (app pipeline, parser, prompts, payload
builder). The gateway is simulated locally so the demo runs anywhere.

Run:  python3 demo/server.py   (default http://0.0.0.0:8765)
"""

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from screenanswer.app import ScreenAnswerApp                      # noqa: E402
from screenanswer.capture import encode_rgb_png                   # noqa: E402
from screenanswer.config import Settings                          # noqa: E402
from screenanswer.diagnostics import Diagnostics                  # noqa: E402
from screenanswer.gateway import GatewayResult, GatewayRateLimited, build_payload  # noqa: E402
from screenanswer.tray import NullShell                           # noqa: E402

PORT = int(os.environ.get("PORT", "8765"))
PNG = encode_rgb_png(4, 4, bytes((i * 17) % 256 for i in range(4 * 4 * 3)), stride=12)

STATE_LOCK = threading.Lock()
STATE = {
    "tray": [128, 128, 128],
    "tooltip": "Screen Answer (ready)",
    "balloon": "",
    "logs": [],
    "captures": 0,
    "busy": False,
}


class DemoShell(NullShell):
    def set_state(self, rgb, tooltip=""):
        with STATE_LOCK:
            STATE["tray"] = list(rgb)
            STATE["tooltip"] = tooltip or STATE["tooltip"]

    def show_balloon(self, title, message):
        with STATE_LOCK:
            STATE["balloon"] = "%s: %s" % (title, message)


SCENARIOS = [
    {
        "label": "grounded success",
        "text": "TRANSCRIPTION: If a train travels 240 km in 3 hours, its speed is?\n"
                "SOLUTION: 240 km / 3 h = 80 km/h.\nANSWER: 2",
        "model": "google/gemini-3.8-flash",
    },
    {
        "label": "grounded search verification",
        "text": "TRANSCRIPTION: Which planet is known as the Red Planet?\n"
                "SOLUTION: Web search confirms Mars is called the Red Planet. 1=Venus 2=Mars 3=Jupiter 4=Mercury.\nANSWER: 2",
        "model": "google/gemini-3.8-flash",
    },
    {
        "label": "ungrounded success",
        "text": "TRANSCRIPTION: Solve x + 5 = 12.\nSOLUTION: x = 7, choice 4.\nANSWER: 4",
        "model": "openrouter/nemotron-nano-12b-vl",
    },
    {
        "label": "ambiguous -> neutral",
        "text": "TRANSCRIPTION: (two questions detected)\nSOLUTION: not single-choice.\nANSWER: 0",
        "model": "google/gemini-3.8-flash",
    },
]
_scenario_index = {"i": 0}


def simulated_gateway(settings, png_bytes, report=None):
    def say(msg):
        if report:
            report(msg)

    payload = build_payload(settings, png_bytes)
    say("Gateway request attempt 1/3 -> %s (model=%s, search=%s)"
        % (settings.chat_completions_url(), payload["model"], settings.web_search))
    scenario = SCENARIOS[_scenario_index["i"] % len(SCENARIOS)]
    _scenario_index["i"] += 1

    if scenario["label"] == "ungrounded success" and settings.web_search:
        say("Simulated rate limit (HTTP 429, Retry-After: 1); waiting 1.0s before retry")
        time.sleep(0.4)
        say("Gateway OK on attempt 2 (served model: %s, grounded: %s)"
            % (scenario["model"], settings.web_search))

    if settings.web_search and scenario["model"].startswith("google/"):
        say("google_search grounding tool attached; gateway translated it to Gemini native grounding")
    say("Gateway OK (served model: %s, usage: {\"prompt_tokens\": 1180, \"completion_tokens\": 96})"
        % scenario["model"])
    return GatewayResult(text=scenario["text"], model=scenario["model"], attempts=1,
                         usage={"prompt_tokens": 1180, "completion_tokens": 96},
                         request_id="demo-req-%d" % STATE["captures"])


settings = Settings(
    endpoint="http://127.0.0.1:3001/v1",
    api_key="freellmapi-demo",
    model="auto:reliable",
    web_search=True,
    allow_uploads=True,
)
diagnostics = Diagnostics(secrets=lambda: [settings.api_key])


def on_log(line):
    with STATE_LOCK:
        STATE["logs"].append(line)
        del STATE["logs"][:-400]


diagnostics.add_listener(on_log)
app = ScreenAnswerApp(
    settings,
    shell=DemoShell(),
    diagnostics=diagnostics,
    capture_fn=lambda: PNG,
    gateway_fn=simulated_gateway,
)
diagnostics.log("Screen Answer v1 demo started — GUI + tray + diagnostics console.")
diagnostics.log("Gateway is simulated in this preview; the pipeline code is the real v1 core.")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
            with open(path, "rb") as fh:
                self._send(200, fh.read(), "text/html; charset=utf-8")
        elif self.path == "/api/state":
            with STATE_LOCK:
                snapshot = dict(STATE)
            snapshot["settings"] = {
                "endpoint": settings.endpoint,
                "model": settings.model,
                "request_model": settings.request_model(),
                "web_search": settings.web_search,
                "allow_uploads": settings.allow_uploads,
            }
            self._send(200, snapshot)
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode() or "{}")
        except ValueError:
            data = {}
        if self.path == "/api/capture":
            with STATE_LOCK:
                STATE["captures"] += 1
                STATE["busy"] = True
                STATE["balloon"] = ""
            threading.Thread(target=self._run_capture, daemon=True).start()
            self._send(202, {"ok": True})
        elif self.path == "/api/settings":
            if "endpoint" in data:
                settings.endpoint = str(data["endpoint"]) or settings.endpoint
            if "model" in data:
                settings.model = str(data["model"]) or settings.model
            if "web_search" in data:
                settings.web_search = bool(data["web_search"])
            if "allow_uploads" in data:
                settings.allow_uploads = bool(data["allow_uploads"])
            app.save()
            diagnostics.log("Settings updated (search=%s, model=%s)."
                            % (settings.web_search, settings.model))
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not found"})

    def _run_capture(self):
        try:
            app.run_capture_sync()
        finally:
            with STATE_LOCK:
                STATE["busy"] = False


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("Screen Answer v1 demo on http://0.0.0.0:%d" % PORT, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
