"""Tests for the v1 PNG encoder (the Windows capture path is exercised in CI)."""

import unittest

from screenanswer.capture import CaptureUnavailable, encode_rgb_png


class EncodePngTests(unittest.TestCase):
    def test_encodes_valid_png_signature(self):
        png = encode_rgb_png(2, 2, bytes(range(12)), stride=6)
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertIn(b"IHDR", png)
        self.assertIn(b"IDAT", png)
        self.assertTrue(png.endswith(b"IEND" + b"\xaeB`\x82"))

    def test_incomplete_rows_rejected(self):
        with self.assertRaises(CaptureUnavailable):
            encode_rgb_png(2, 2, bytes(6), stride=6)

    def test_invalid_dimensions_rejected(self):
        with self.assertRaises(CaptureUnavailable):
            encode_rgb_png(0, 2, b"", stride=6)

    def test_stride_padding_is_skipped(self):
        # Row is 6 real bytes + 2 pad bytes per row; padding must not leak in.
        rows = bytes([255, 0, 0, 0, 255, 0, 99, 99]) + bytes([0, 0, 255, 255, 255, 255, 99, 99])
        png = encode_rgb_png(2, 2, rows, stride=8)
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
