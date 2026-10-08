"""Tests for the v1 answer parser (ported v1.7 semantics)."""

import unittest

from screenanswer.parser import (
    NEUTRAL_RGB,
    OPTION_RGB,
    parse_option,
    result_rgb,
)


class ParseOptionTests(unittest.TestCase):
    def test_numeric_answer_line(self):
        self.assertEqual(parse_option("SOLUTION: work\nANSWER: 3"), 3)

    def test_letter_answers_map_to_positions(self):
        self.assertEqual(parse_option("ANSWER: A"), 1)
        self.assertEqual(parse_option("ANSWER: B"), 2)
        self.assertEqual(parse_option("ANSWER: C"), 3)
        self.assertEqual(parse_option("ANSWER: D"), 4)

    def test_final_answer_beats_plain_answer(self):
        self.assertEqual(parse_option("ANSWER: 1\nFinal ANSWER: 2"), 2)

    def test_correct_answer_prefix_accepted(self):
        self.assertEqual(parse_option("Correct answer: 4"), 4)

    def test_ambiguous_answers_neutral(self):
        self.assertIsNone(parse_option("ANSWER: 1\nANSWER: 2"))

    def test_digits_elsewhere_are_ignored(self):
        self.assertIsNone(parse_option("The value 42 matters"))
        self.assertEqual(parse_option("value 42 then\nANSWER: 1"), 1)

    def test_answer_zero_is_neutral(self):
        self.assertIsNone(parse_option("ANSWER: 0"))

    def test_empty_and_none_are_neutral(self):
        self.assertIsNone(parse_option(""))
        self.assertIsNone(parse_option(None))

    def test_short_single_digit_response(self):
        self.assertEqual(parse_option("3"), 3)

    def test_multiple_final_agree(self):
        self.assertEqual(parse_option("Final answer: 2\nFINAL ANSWER: 2"), 2)


class ResultColorTests(unittest.TestCase):
    def test_option_colors(self):
        self.assertEqual(result_rgb(1), OPTION_RGB[1])
        self.assertEqual(result_rgb(4), OPTION_RGB[4])

    def test_neutral(self):
        self.assertEqual(result_rgb(None), NEUTRAL_RGB)
        self.assertEqual(result_rgb(0), NEUTRAL_RGB)
        self.assertEqual(result_rgb(9), NEUTRAL_RGB)


if __name__ == "__main__":
    unittest.main()
