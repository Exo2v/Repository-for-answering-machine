"""Tests for v1 settings: validation, env keys, sidecar, session-only consent."""

import json
import os
import tempfile
import unittest
from unittest import mock

from screenanswer.config import (
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL,
    DEFAULT_SEARCH_MODEL,
    Settings,
    is_auto_model,
    load_settings,
    remove_sidecar,
    save_settings,
    valid_endpoint,
    valid_model_name,
)


class ValidationTests(unittest.TestCase):
    def test_model_names(self):
        self.assertTrue(valid_model_name("auto"))
        self.assertTrue(valid_model_name("auto:search"))
        self.assertTrue(valid_model_name("auto:reliable"))
        self.assertTrue(valid_model_name("google/gemini-3.8-flash"))
        self.assertTrue(valid_model_name("free/gemini-3.8-flash"))
        self.assertFalse(valid_model_name(""))
        self.assertFalse(valid_model_name("bad model!"))
        self.assertFalse(valid_model_name("x" * 200))

    def test_auto_detection(self):
        self.assertTrue(is_auto_model("auto"))
        self.assertTrue(is_auto_model("AUTO:SMART"))
        self.assertFalse(is_auto_model("google/gemini-3.8-flash"))
        self.assertFalse(is_auto_model("automatic"))

    def test_endpoints(self):
        self.assertTrue(valid_endpoint("http://127.0.0.1:3001/v1"))
        self.assertTrue(valid_endpoint("https://gateway.example/v1/"))
        self.assertFalse(valid_endpoint("ftp://x/v1"))
        self.assertFalse(valid_endpoint(""))


class RequestModelTests(unittest.TestCase):
    def test_search_steers_auto_models(self):
        settings = Settings(model="auto:reliable", web_search=True)
        self.assertEqual(settings.request_model(), DEFAULT_SEARCH_MODEL)

    def test_search_keeps_pinned_models(self):
        settings = Settings(model="google/gemini-3.8-flash", web_search=True)
        self.assertEqual(settings.request_model(), "google/gemini-3.8-flash")

    def test_no_search_keeps_model(self):
        settings = Settings(model="auto:fast", web_search=False)
        self.assertEqual(settings.request_model(), "auto:fast")

    def test_chat_url(self):
        settings = Settings(endpoint="http://127.0.0.1:3001/v1/")
        self.assertEqual(
            settings.chat_completions_url(),
            "http://127.0.0.1:3001/v1/chat/completions",
        )


class SidecarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "screen_answer_config.json")

    def tearDown(self):
        remove_sidecar(self.path)

    def test_no_sidecar_written_when_portable_off(self):
        settings = Settings(save_to_file=False)
        self.assertEqual(save_settings(settings, self.path), "")
        self.assertFalse(os.path.exists(self.path))

    def test_round_trip(self):
        settings = Settings(
            endpoint="https://gateway.example/v1",
            api_key="freellmapi-abc12345",
            model="auto:search",
            web_search=False,
            save_to_file=True,
        )
        written = save_settings(settings, self.path)
        self.assertEqual(written, self.path)
        loaded = load_settings(self.path)
        self.assertEqual(loaded.endpoint, "https://gateway.example/v1")
        self.assertEqual(loaded.api_key, "freellmapi-abc12345")
        self.assertEqual(loaded.model, "auto:search")
        self.assertFalse(loaded.web_search)
        self.assertTrue(loaded.save_to_file)

    def test_upload_consent_never_persisted(self):
        settings = Settings(save_to_file=True, allow_uploads=True)
        save_settings(settings, self.path)
        with open(self.path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertNotIn("allow_uploads", data)
        self.assertFalse(load_settings(self.path).allow_uploads)

    def test_invalid_values_fall_back(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(
                {"endpoint": "ftp://bad", "model": "bad model!", "web_search": "yes"},
                handle,
            )
        loaded = load_settings(self.path)
        self.assertEqual(loaded.endpoint, DEFAULT_ENDPOINT)
        self.assertEqual(loaded.model, DEFAULT_MODEL)
        self.assertTrue(loaded.web_search)  # non-bool ignored, default kept

    def test_env_key_overrides_sidecar(self):
        settings = Settings(save_to_file=True, api_key="from-file")
        save_settings(settings, self.path)
        with mock.patch.dict(os.environ, {"FREELLMAPI_API_KEY": "from-env"}):
            loaded = load_settings(self.path)
        self.assertEqual(loaded.api_key, "from-env")

    def test_defaults(self):
        settings = Settings()
        self.assertEqual(settings.endpoint, DEFAULT_ENDPOINT)
        self.assertEqual(settings.model, DEFAULT_MODEL)
        self.assertTrue(settings.web_search)
        self.assertFalse(settings.allow_uploads)


if __name__ == "__main__":
    unittest.main()
