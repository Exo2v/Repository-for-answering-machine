"""Tests for the v1 gateway client: payload shape, search contract, retries."""

import base64
import io
import json
import unittest
import urllib.error
from unittest import mock

from screenanswer.config import Settings
from screenanswer.gateway import (
    GatewayAuthError,
    GatewayRateLimited,
    GatewaySearchUnavailable,
    GatewayUpstreamError,
    ask_gateway,
    build_payload,
    resolve_model,
)

PNG = b"\x89PNG\r\n\x1a\nfakepngdata"
URL = "http://127.0.0.1:3001/v1/chat/completions"


class FakeResponse:
    def __init__(self, payload: dict, headers=None):
        self._body = json.dumps(payload).encode("utf-8")
        self.headers = headers or {}

    def read(self, limit=-1):
        if limit is None or limit < 0:
            return self._body
        return self._body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(code: int, body: bytes, headers=None) -> urllib.error.HTTPError:
    """A real HTTPError so the client's except-clauses match it."""
    return urllib.error.HTTPError(URL, code, "error", headers or {}, io.BytesIO(body))


def ok_response(text="SOLUTION: work\nANSWER: 2", model="google/gemini-3.8-flash"):
    return FakeResponse(
        {
            "id": "chatcmpl-1",
            "model": model,
            "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
        },
        headers={"x-request-id": "req-1"},
    )


class ResolveModelTests(unittest.TestCase):
    def test_search_steers_auto(self):
        self.assertEqual(resolve_model("auto", True), "auto:search")
        self.assertEqual(resolve_model("auto:reliable", True), "auto:search")

    def test_pinned_and_off(self):
        self.assertEqual(resolve_model("google/gemini-3.8-flash", True), "google/gemini-3.8-flash")
        self.assertEqual(resolve_model("auto:fast", False), "auto:fast")


class BuildPayloadTests(unittest.TestCase):
    def test_search_adds_grounding_tool_and_steers(self):
        payload = build_payload(Settings(web_search=True, model="auto:reliable"), PNG)
        self.assertEqual(payload["model"], "auto:search")
        self.assertEqual(payload["tools"][0]["function"]["name"], "google_search")
        self.assertEqual(payload["temperature"], 0)

    def test_no_search_no_tools_field(self):
        payload = build_payload(Settings(web_search=False), PNG)
        self.assertNotIn("tools", payload)
        self.assertEqual(payload["model"], "auto:reliable")

    def test_image_is_base64_data_url(self):
        payload = build_payload(Settings(), PNG)
        part = payload["messages"][1]["content"][1]
        self.assertTrue(part["image_url"]["url"].startswith("data:image/png;base64,"))
        encoded = part["image_url"]["url"].split(",", 1)[1]
        self.assertEqual(base64.b64decode(encoded), PNG)

    def test_empty_image_rejected(self):
        with self.assertRaises(ValueError):
            build_payload(Settings(), b"")


class AskGatewayTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(
            endpoint="http://127.0.0.1:3001/v1", api_key="freellmapi-testkey123", web_search=True
        )
        self.reports = []

    def _report(self, message):
        self.reports.append(message)

    def test_success(self):
        with mock.patch(
            "screenanswer.gateway._urlopen", return_value=ok_response()
        ) as fake:
            result = ask_gateway(self.settings, PNG, self._report)
        self.assertEqual(result.text.strip().splitlines()[-1], "ANSWER: 2")
        self.assertEqual(result.model, "google/gemini-3.8-flash")
        self.assertEqual(result.attempts, 1)
        self.assertEqual(result.request_id, "req-1")
        request = fake.call_args[0][0]
        self.assertEqual(request.full_url, "http://127.0.0.1:3001/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer freellmapi-testkey123")
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["tools"][0]["function"]["name"], "google_search")

    def test_no_search_model_fails_loudly(self):
        error = http_error(
            422,
            json.dumps({"error": {"code": "no_search_model", "message": "none enabled"}}).encode(),
        )
        with mock.patch("screenanswer.gateway._urlopen", side_effect=error):
            with self.assertRaises(GatewaySearchUnavailable):
                ask_gateway(self.settings, PNG, self._report)

    def test_auth_error(self):
        error = http_error(401, b'{"error": {"message": "bad key"}}')
        with mock.patch("screenanswer.gateway._urlopen", side_effect=error):
            with self.assertRaises(GatewayAuthError):
                ask_gateway(self.settings, PNG, self._report)

    def test_retries_transient_then_succeeds(self):
        transient = http_error(503, b'{"error": {"message": "busy"}}')
        with mock.patch(
            "screenanswer.gateway._urlopen",
            side_effect=[transient, ok_response()],
        ) as fake, mock.patch("screenanswer.gateway.time.sleep") as sleep:
            result = ask_gateway(self.settings, PNG, self._report)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(fake.call_count, 2)
        self.assertTrue(sleep.called)

    def test_rate_limit_respects_retry_after_then_fails(self):
        limited = http_error(
            429, b'{"error": {"message": "slow down"}}', headers={"Retry-After": "7"}
        )
        with mock.patch(
            "screenanswer.gateway._urlopen", side_effect=limited
        ), mock.patch("screenanswer.gateway.time.sleep") as sleep:
            with self.assertRaises(GatewayRateLimited):
                ask_gateway(self.settings, PNG, self._report)
        self.assertEqual(sleep.call_count, 2)  # between 3 attempts
        self.assertEqual(sleep.call_args_list[0][0][0], 7.0)

    def test_search_failures_are_not_retried_into_ungrounded_routes(self):
        error = http_error(
            422,
            json.dumps({"error": {"code": "no_search_model", "message": "none"}}).encode(),
        )
        with mock.patch(
            "screenanswer.gateway._urlopen", side_effect=error
        ) as fake:
            with self.assertRaises(GatewaySearchUnavailable):
                ask_gateway(self.settings, PNG, self._report)
        self.assertEqual(fake.call_count, 1)

    def test_unreachable_gateway(self):
        import urllib.error

        with mock.patch(
            "screenanswer.gateway._urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ), mock.patch("screenanswer.gateway.time.sleep"):
            with self.assertRaises(GatewayUpstreamError) as ctx:
                ask_gateway(self.settings, PNG, self._report)
        self.assertIn("Is FreeLLMAPI running?", str(ctx.exception))

    def test_response_size_cap(self):
        big = FakeResponse({"choices": [{"message": {"content": "x" * 10}}]})
        big._body = b"x" * (2 * 1024 * 1024 + 10)
        with mock.patch("screenanswer.gateway._urlopen", return_value=big):
            from screenanswer.gateway import GatewayResponseTooLarge

            with self.assertRaises(GatewayResponseTooLarge):
                ask_gateway(self.settings, PNG, self._report)

    def test_reports_are_redaction_friendly(self):
        with mock.patch("screenanswer.gateway._urlopen", return_value=ok_response()):
            ask_gateway(self.settings, PNG, self._report)
        joined = "\n".join(self.reports)
        self.assertNotIn("freellmapi-testkey123", joined)


if __name__ == "__main__":
    unittest.main()
