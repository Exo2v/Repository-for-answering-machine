import base64
import io
import json
import os
import struct
import tempfile
import unittest
import urllib.error
import zlib
from unittest.mock import patch

from answer_tray import (
    _encode_rgb_png,
    _extract_gemini_text,
    ask_gemini,
    diagnostics_mode_enabled,
    load_portable_config,
    parse_option,
    save_portable_config,
)


class DiagnosticsModeTests(unittest.TestCase):
    def test_diagnostic_mode_is_enabled_by_exe_name_or_flag(self):
        self.assertTrue(
            diagnostics_mode_enabled((), "ScreenAnswer-Diagnostic.exe")
        )
        self.assertTrue(diagnostics_mode_enabled(("--diagnostics",), "python.exe"))
        self.assertFalse(diagnostics_mode_enabled((), "ScreenAnswer.exe"))


class ParseOptionTests(unittest.TestCase):
    def test_accepts_single_digit(self):
        for option in range(1, 5):
            with self.subTest(option=option):
                self.assertEqual(parse_option(str(option)), option)

    def test_accepts_short_unambiguous_variants(self):
        self.assertEqual(parse_option(" Option 2 "), 2)
        self.assertEqual(parse_option("Answer: 4."), 4)
        self.assertEqual(parse_option("option 3)"), 3)

    def test_neutral_for_no_answer_or_ambiguous_response(self):
        values = ("", "0", "5", "Option 1 or 2", "The answer is 3 because…", "maybe 4")
        for text in values:
            with self.subTest(text=text):
                self.assertIsNone(parse_option(text))

    def test_extracts_candidate_text(self):
        payload = {
            "candidates": [
                {"content": {"parts": [{"text": "2"}, {"text": ""}]}}
            ]
        }
        self.assertEqual(_extract_gemini_text(payload), "2")
        self.assertEqual(_extract_gemini_text({"candidates": []}), "")


class GeminiRequestTests(unittest.TestCase):
    def test_uses_screenshot_without_search_tools(self):
        image_bytes = b"fake png bytes"
        captured = {}
        response_payload = {
            "candidates": [
                {"content": {"parts": [{"text": "3"}]}}
            ]
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                encoded = json.dumps(response_payload).encode("utf-8")
                return encoded if limit < 0 else encoded[:limit]

        def fake_urlopen(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse()

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            option, response_text = ask_gemini("test-key", "gemini-3.8-flash", image_bytes)

        self.assertEqual(option, 3)
        self.assertEqual(response_text, "3")
        self.assertNotIn("tools", captured["body"])
        parts = captured["body"]["contents"][0]["parts"]
        self.assertEqual(parts[1]["inlineData"]["data"], base64.b64encode(image_bytes).decode("ascii"))

    def test_diagnostic_callback_omits_raw_model_response(self):
        private_response = "question text from the screenshot"
        response_payload = {
            "candidates": [
                {"content": {"parts": [{"text": private_response}]}}
            ]
        }
        diagnostic_lines = []

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(response_payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        with patch("answer_tray.urllib.request.urlopen", return_value=FakeResponse()):
            option, response_text = ask_gemini(
                "test-key", "gemini-3.8-flash", b"image", diagnostic=diagnostic_lines.append
            )

        self.assertIsNone(option)
        self.assertEqual(response_text, private_response)
        self.assertFalse(any(private_response in line for line in diagnostic_lines))
        self.assertFalse(any("test-key" in line for line in diagnostic_lines))
        self.assertTrue(any("raw text omitted" in line for line in diagnostic_lines))

    def test_retries_temporary_503_then_succeeds(self):
        response_payload = {
            "candidates": [{"content": {"parts": [{"text": "1"}]}}]
        }
        call_count = [0]

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(response_payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            call_count[0] += 1
            if call_count[0] == 1:
                raise urllib.error.HTTPError(
                    request.full_url, 503, "Service Unavailable", None, io.BytesIO()
                )
            return FakeResponse()

        diagnostic_lines = []
        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            with patch("answer_tray.time.sleep") as sleep:
                option, _ = ask_gemini(
                    "test-key",
                    "gemini-3.8-flash",
                    b"image",
                    diagnostic=diagnostic_lines.append,
                )

        self.assertEqual(option, 1)
        self.assertEqual(call_count[0], 2)
        sleep.assert_called_once_with(1)
        self.assertTrue(any("failed with status 503" in line for line in diagnostic_lines))
        self.assertTrue(any("retrying in 1 second" in line for line in diagnostic_lines))
        self.assertTrue(any("recognized option 1" in line for line in diagnostic_lines))
        self.assertFalse(any("test-key" in line for line in diagnostic_lines))

    def test_final_503_diagnostic_includes_provider_reason_without_key(self):
        provider_message = "temporary service failure test-key"
        diagnostic_lines = []
        call_count = [0]

        def fake_urlopen(request, timeout):
            call_count[0] += 1
            body = json.dumps(
                {"error": {"status": "UNAVAILABLE", "message": provider_message}}
            ).encode("utf-8")
            raise urllib.error.HTTPError(
                request.full_url, 503, "Service Unavailable", None, io.BytesIO(body)
            )

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            with patch("answer_tray.time.sleep"):
                with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
                    ask_gemini(
                        "test-key",
                        "gemini-3.8-flash",
                        b"image",
                        diagnostic=diagnostic_lines.append,
                    )

        self.assertEqual(call_count[0], 3)
        self.assertTrue(any("UNAVAILABLE" in line for line in diagnostic_lines))
        self.assertTrue(
            any(
                "temporary service failure [REDACTED API KEY]" in line
                for line in diagnostic_lines
            )
        )
        self.assertFalse(any("test-key" in line for line in diagnostic_lines))


class PortableConfigTests(unittest.TestCase):
    def test_saves_and_loads_key_and_model(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "screen_answer_config.json")
            save_portable_config("example-key", "gemini-3.8-flash", path)
            self.assertEqual(
                load_portable_config(path),
                {"api_key": "example-key", "model": "gemini-3.8-flash"},
            )

    def test_missing_or_invalid_config_falls_back_to_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "missing.json")
            self.assertEqual(load_portable_config(path), {})
            with open(path, "w", encoding="utf-8") as config_file:
                config_file.write("not json")
            self.assertEqual(load_portable_config(path), {})


class PngEncodingTests(unittest.TestCase):
    def test_converts_one_bgr_pixel_to_rgb_png(self):
        # One pixel: B=30, G=20, R=10, followed by one stride-padding byte.
        png = _encode_rgb_png(1, 1, bytes((30, 20, 10, 0)), stride=4)
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))

        offset = 8
        image_data = None
        image_header = None
        while offset < len(png):
            length = struct.unpack_from(">I", png, offset)[0]
            chunk_type = png[offset + 4 : offset + 8]
            data = png[offset + 8 : offset + 8 + length]
            if chunk_type == b"IHDR":
                image_header = data
            elif chunk_type == b"IDAT":
                image_data = zlib.decompress(data)
            offset += 12 + length

        self.assertEqual(struct.unpack(">IIBBBBB", image_header), (1, 1, 8, 2, 0, 0, 0))
        self.assertEqual(image_data, bytes((0, 10, 20, 30)))


if __name__ == "__main__":
    unittest.main()
