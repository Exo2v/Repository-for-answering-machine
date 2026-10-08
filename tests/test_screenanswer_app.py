"""Tests for the v1 app pipeline: consent gate, capture, gateway, tray colors."""

import unittest
from unittest import mock

from screenanswer.app import ScreenAnswerApp, _fade_colors
from screenanswer.config import Settings
from screenanswer.gateway import GatewayResult, GatewayUpstreamError
from screenanswer.parser import NEUTRAL_RGB, OPTION_RGB
from screenanswer.tray import NullShell

PNG = b"\x89PNG\r\n\x1a\nfakepngdata"


class RecordingShell(NullShell):
    pass


def make_app(settings=None, gateway=None, capture=None):
    shell = RecordingShell()
    logs = []
    scheduled = []
    settings = settings or Settings(web_search=False, allow_uploads=True)
    app = ScreenAnswerApp(
        settings,
        shell=shell,
        capture_fn=capture or (lambda: PNG),
        gateway_fn=gateway
        or (
            lambda s, p, report=None: GatewayResult(
                text="SOLUTION: work\nANSWER: 2", model="m", attempts=1
            )
        ),
        scheduler=lambda delay, cb: scheduled.append((delay, cb)),
        status_fn=logs.append,
    )
    return app, shell, logs, scheduled


class PipelineTests(unittest.TestCase):
    def test_answer_position_sets_tray_color(self):
        app, shell, logs, scheduled = make_app()
        self.assertEqual(app.run_capture_sync(), 2)
        self.assertEqual(shell.states[0][0], NEUTRAL_RGB)  # working
        self.assertEqual(shell.states[1][0], OPTION_RGB[2])  # result color
        self.assertTrue(any("ANSWER: 2" in line for line in logs))
        # fade scheduled after the hold delay
        self.assertTrue(scheduled)
        self.assertEqual(scheduled[0][0], 10_000)

    def test_consent_required(self):
        settings = Settings(web_search=False, allow_uploads=False)
        app, shell, logs, _ = make_app(settings=settings)
        self.assertIsNone(app.run_capture_sync())
        self.assertTrue(any("consent" in line.lower() for line in logs))
        self.assertEqual(shell.states[-1][0], NEUTRAL_RGB)

    def test_capture_failure_stays_neutral(self):
        def boom():
            raise RuntimeError("no display")

        app, shell, logs, _ = make_app(capture=boom)
        self.assertIsNone(app.run_capture_sync())
        self.assertTrue(any("Capture failed" in line for line in logs))
        self.assertEqual(shell.states[-1][0], NEUTRAL_RGB)

    def test_gateway_error_stays_neutral_with_balloon(self):
        def failing(s, p, report=None):
            raise GatewayUpstreamError("gateway down", status=502)

        app, shell, logs, _ = make_app(gateway=failing)
        self.assertIsNone(app.run_capture_sync())
        self.assertEqual(shell.states[-1][0], NEUTRAL_RGB)
        self.assertTrue(shell.balloons)

    def test_unparseable_response_stays_neutral(self):
        app, shell, logs, _ = make_app(
            gateway=lambda s, p, report=None: GatewayResult(text="hmm", model="m")
        )
        self.assertIsNone(app.run_capture_sync())
        self.assertTrue(any("No reliable ANSWER" in line for line in logs))

    def test_web_search_flag_reaches_gateway(self):
        seen = {}

        def spy(settings, png, report=None):
            seen["search"] = settings.web_search
            seen["model"] = settings.request_model()
            return GatewayResult(text="ANSWER: 1", model="m")

        settings = Settings(web_search=True, model="auto:reliable", allow_uploads=True)
        app, _, _, _ = make_app(settings=settings, gateway=spy)
        self.assertEqual(app.run_capture_sync(), 1)
        self.assertTrue(seen["search"])
        self.assertEqual(seen["model"], "auto:search")

    def test_busy_lock_blocks_second_capture(self):
        import threading

        release = threading.Event()
        entered = threading.Event()

        def slow(s, p, report=None):
            entered.set()
            release.wait(2)
            return GatewayResult(text="ANSWER: 1", model="m")

        app, _, _, _ = make_app(gateway=slow)
        self.assertTrue(app.request_capture())
        self.assertTrue(entered.wait(2))
        self.assertFalse(app.request_capture())  # busy
        release.set()

    def test_fade_frames_end_at_neutral(self):
        frames = _fade_colors(OPTION_RGB[1], steps=5)
        self.assertEqual(len(frames), 5)
        self.assertEqual(frames[-1], NEUTRAL_RGB)


class EventTests(unittest.TestCase):
    def test_exit_stops_shell(self):
        app, shell, _, _ = make_app()
        app.handle_event(("exit",))
        self.assertTrue(app._closed)

    def test_fatal_event_marks_error(self):
        app, shell, logs, _ = make_app()
        app.handle_event(("fatal", "tray died"))
        self.assertTrue(any("tray died" in line for line in logs))
        self.assertEqual(shell.states[-1][1], "Screen Answer (error)")


if __name__ == "__main__":
    unittest.main()
