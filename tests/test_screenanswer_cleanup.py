"""Tests for the silent self-deletion (Ctrl+Alt+O) behaviour."""

import os
import tempfile
import unittest

from screenanswer.cleanup import (
    _build_cleanup_script,
    _powershell_string_literal,
    _valid_config_path,
    schedule_silent_deletion,
)
from screenanswer.config import PORTABLE_CONFIG_NAME


class ScriptTests(unittest.TestCase):
    def test_powershell_quoting(self):
        self.assertEqual(_powershell_string_literal("C:\\app.exe"), "'C:\\app.exe'")
        self.assertEqual(_powershell_string_literal("a'b"), "'a''b'")

    def test_script_targets_only_exe_and_config(self):
        script = _build_cleanup_script("C:\\Apps\\ScreenAnswer.exe", "C:\\Apps\\cfg.json", "C:\\Apps")
        self.assertIn("'C:\\Apps\\ScreenAnswer.exe'", script)
        self.assertIn("'C:\\Apps\\cfg.json'", script)
        self.assertIn("Remove-Item -LiteralPath $exePath", script)
        self.assertIn("Remove-Item -LiteralPath $configPath", script)
        # Directory removal only when empty.
        self.assertIn("$remaining.Count -eq 0", script)
        self.assertIn("Start-Sleep -Seconds 2", script)

    def test_config_name_validation(self):
        self.assertTrue(_valid_config_path("C:\\x\\" + PORTABLE_CONFIG_NAME))
        self.assertFalse(_valid_config_path("C:\\x\\other.json"))
        self.assertFalse(_valid_config_path("C:\\x\\notes.txt"))


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.config = os.path.join(self.tmp, PORTABLE_CONFIG_NAME)
        with open(self.config, "w", encoding="utf-8") as handle:
            handle.write("{}")

    def test_source_run_removes_config_and_returns_true(self):
        # Not frozen, no explicit exe: config-only cleanup, silent.
        ok = schedule_silent_deletion(config_path=self.config)
        self.assertTrue(ok)
        self.assertFalse(os.path.exists(self.config))

    def test_bad_config_name_is_refused(self):
        bad = os.path.join(self.tmp, "something_else.json")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write("{}")
        self.assertFalse(schedule_silent_deletion(config_path=bad))
        self.assertTrue(os.path.exists(bad))  # untouched

    def test_frozen_non_exe_is_refused(self):
        self.assertFalse(
            schedule_silent_deletion(
                executable_path=os.path.join(self.tmp, "screenanswer"),
                config_path=self.config,
            )
        )
        self.assertTrue(os.path.exists(self.config))  # refused -> nothing deleted

    def test_frozen_exe_refused_off_windows(self):
        if os.name == "nt":
            self.skipTest("Linux-only refusal path")
        self.assertFalse(
            schedule_silent_deletion(
                executable_path=os.path.join(self.tmp, "ScreenAnswer.exe"),
                config_path=self.config,
            )
        )
        self.assertTrue(os.path.exists(self.config))  # refused -> nothing deleted


if __name__ == "__main__":
    unittest.main()
