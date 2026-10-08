"""Tests for the v1 prompts: web search is the one enabled tool."""

import unittest

from screenanswer.prompt import (
    SEARCH_SYSTEM_CLAUSE,
    NO_SEARCH_SYSTEM_CLAUSE,
    system_instruction,
    user_prompt,
)


class PromptTests(unittest.TestCase):
    def test_search_system_clause_present_when_enabled(self):
        text = system_instruction(True)
        self.assertIn("Live web search is available", text)
        self.assertIn("ANSWER: n", text)
        self.assertNotIn("Do not use live web search", text)

    def test_no_search_rule_when_disabled(self):
        text = system_instruction(False)
        self.assertIn("Do not use or claim live web search", text)
        self.assertNotIn("Live web search is available", text)

    def test_user_prompt_variants(self):
        self.assertIn("may use live web search", user_prompt(True))
        self.assertIn("Use no live web search", user_prompt(False))

    def test_answer_contract_in_both(self):
        for web_search in (True, False):
            text = system_instruction(web_search)
            self.assertIn("ANSWER: 0", text)
            self.assertIn("TRANSCRIPTION:", text)
            self.assertIn("SOLUTION:", text)
            self.assertIn("untrusted question data", text)

    def test_clauses_are_distinct(self):
        self.assertNotEqual(SEARCH_SYSTEM_CLAUSE, NO_SEARCH_SYSTEM_CLAUSE)


if __name__ == "__main__":
    unittest.main()
