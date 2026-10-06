import struct
import unittest
import zlib

from answer_tray import _encode_rgb_png, _extract_gemini_text, parse_option


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
