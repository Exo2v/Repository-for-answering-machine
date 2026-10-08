"""Tests for bulk API-key management (gateway admin API client + parsing)."""

import json
import unittest
import urllib.error
from unittest import mock

from screenanswer.admin_api import (
    AdminApiError,
    AdminClient,
    detect_platform,
    gateway_base,
    parse_key_line,
    parse_keys_text,
)


class FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode()

    def read(self, limit=-1):
        return self._body if limit < 0 else self._body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class DetectPlatformTests(unittest.TestCase):
    def test_prefixes(self):
        self.assertEqual(detect_platform("AIzaSyFakeKey"), "google")
        self.assertEqual(detect_platform("gsk_fake"), "groq")
        self.assertEqual(detect_platform("sk-or-v1-abc"), "openrouter")
        self.assertEqual(detect_platform("sk-or-abc"), "openrouter")
        self.assertEqual(detect_platform("ghp_ABC"), "github")
        self.assertEqual(detect_platform("github_pat_ABC"), "github")

    def test_ambiguous_and_unknown(self):
        self.assertIsNone(detect_platform("sk-something-else"))
        self.assertIsNone(detect_platform("randomvalue123"))


class ParseKeyLineTests(unittest.TestCase):
    def test_explicit_platform_prefix(self):
        self.assertEqual(parse_key_line("zhipu:abc123"), ("zhipu", "abc123", None))
        self.assertEqual(parse_key_line("google=key1"), ("google", "key1", None))
        self.assertEqual(parse_key_line("  OpenRouter : sk-or-x  "), ("openrouter", "sk-or-x", None))

    def test_auto_detect(self):
        self.assertEqual(parse_key_line("AIzaXyz"), ("google", "AIzaXyz", None))

    def test_assume_platform_fallback(self):
        self.assertEqual(
            parse_key_line("sk-ambiguous", assume_platform="groq"), ("groq", "sk-ambiguous", None)
        )

    def test_unmarked_ambiguous_gives_error(self):
        platform, key, error = parse_key_line("sk-ambiguous")
        self.assertIsNone(platform)
        self.assertIn("could not detect", error)

    def test_unknown_platform_prefix(self):
        platform, key, error = parse_key_line("notaprovider:key1")
        self.assertIsNone(platform)
        self.assertIn("could not detect", error)

    def test_comments_and_blanks(self):
        self.assertEqual(parse_key_line("# a comment"), (None, None, None))
        self.assertEqual(parse_key_line("   "), (None, None, None))

    def test_unknown_explicit_platform_errors(self):
        platform, key, error = parse_key_line("foo:bar")
        # 'foo' is not a known platform and 'foo:bar' is not a key shape ->
        # unmarked-key error, not silently accepted.
        self.assertIsNone(platform)
        self.assertIsNotNone(error)


class ParseKeysTextTests(unittest.TestCase):
    def test_bulk_parse(self):
        text = "\n".join(
            [
                "# my keys",
                "AIzaGoogle1",
                "gsk_groq1",
                "",
                "zhipu:zkey1",
                "sk-mystery",
            ]
        )
        parsed, errors = parse_keys_text(text)
        self.assertEqual(
            parsed,
            [("google", "AIzaGoogle1"), ("groq", "gsk_groq1"), ("zhipu", "zkey1")],
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0][0], 6)  # 1-based line number

    def test_assume_applies_only_to_unmarked(self):
        parsed, errors = parse_keys_text("plainkey1\nzhipu:marked", assume_platform="groq")
        self.assertEqual(parsed, [("groq", "plainkey1"), ("zhipu", "marked")])
        self.assertEqual(errors, [])


class AdminClientTests(unittest.TestCase):
    def test_gateway_base_strips_v1(self):
        self.assertEqual(gateway_base("http://127.0.0.1:3001/v1"), "http://127.0.0.1:3001")
        self.assertEqual(gateway_base("http://127.0.0.1:3001/v1/"), "http://127.0.0.1:3001")
        self.assertEqual(gateway_base("http://host:3001"), "http://host:3001")

    def test_login_and_add_key_requests(self):
        captured = []

        def fake(request, timeout=0):
            captured.append((request.full_url, request.get_header("Authorization"), request.data))
            if request.full_url.endswith("/api/auth/login"):
                return FakeResponse({"token": "sess-123", "email": "a@b.c"})
            return FakeResponse({"id": 7, "platform": "google", "maskedKey": "AIza…yz"})

        client = AdminClient("http://127.0.0.1:3001/v1", opener=fake)
        token = client.login("a@b.c", "pw")
        self.assertEqual(token, "sess-123")

        result = client.add_key("google", "AIzaFake", label="screen-answer")
        self.assertEqual(result["id"], 7)

        self.assertEqual(captured[0][0], "http://127.0.0.1:3001/api/auth/login")
        self.assertIsNone(captured[0][1])
        login_body = json.loads(captured[0][2].decode())
        self.assertEqual(login_body, {"email": "a@b.c", "password": "pw"})

        self.assertEqual(captured[1][0], "http://127.0.0.1:3001/api/keys")
        self.assertEqual(captured[1][1], "Bearer sess-123")
        add_body = json.loads(captured[1][2].decode())
        self.assertEqual(add_body["platform"], "google")
        self.assertEqual(add_body["key"], "AIzaFake")

    def test_add_key_without_login_raises(self):
        client = AdminClient("http://127.0.0.1:3001/v1", opener=lambda *a, **k: FakeResponse({}))
        with self.assertRaises(AdminApiError):
            client.add_key("google", "AIzaFake")

    def test_login_401_maps_to_auth_error(self):
        def fake(request, timeout=0):
            raise urllib.error.HTTPError(
                request.full_url, 401, "nope", {}, mock.Mock(read=lambda n: b"")
            )

        client = AdminClient("http://127.0.0.1:3001", opener=fake)
        with self.assertRaises(AdminApiError):
            client.login("a@b.c", "wrong")

    def test_unreachable_gateway_maps_to_error(self):
        def fake(request, timeout=0):
            raise urllib.error.URLError("refused")

        client = AdminClient("http://127.0.0.1:3001", opener=fake)
        with self.assertRaises(AdminApiError):
            client.login("a@b.c", "pw")


class SettingsKeysTabWiringTests(unittest.TestCase):
    def test_settings_window_builds_keys_tab(self):
        import inspect

        from screenanswer.settings_gui import SettingsWindow

        source = inspect.getsource(SettingsWindow)
        self.assertIn("_build_keys_tab", source)
        self.assertIn("API keys (bulk)", source)
        self.assertIn("_push_keys", source)
        self.assertIn("AdminClient", source)


if __name__ == "__main__":
    unittest.main()
