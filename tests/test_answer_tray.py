import base64
import json
import os
import struct
import tempfile
import unittest
import zlib
from unittest.mock import patch

from answer_tray import (
    _encode_rgb_png,
    _extract_gemini_text,
    ask_gemini,
    load_portable_config,
    parse_option,
    save_portable_config,
)


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
