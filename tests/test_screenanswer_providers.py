"""Tests for the providers/model-status listing (gateway + panel data)."""

import json
import unittest
import urllib.error
from unittest import mock

from screenanswer import gateway as gw
from screenanswer.config import Settings

from test_screenanswer_gateway import FakeResponse, http_error


SAMPLE_PAYLOAD = {
    "object": "list",
    "data": [
        {
            "id": "auto",
            "object": "model",
            "owned_by": "freellmapi",
            "name": "Auto (fastest available model)",
            "context_window": 200000,
            "available": True,
            "unavailable_reason": None,
        },
        {
            "id": "auto:reliable",
            "object": "model",
            "owned_by": "freellmapi",
            "name": "Auto: Reliable (named fallback chain)",
            "context_window": 200000,
            "available": True,
        },
        {
            "id": "google/gemini-2.5-flash",
            "object": "model",
            "owned_by": "google",
            "name": "Gemini 2.5 Flash",
            "context_window": 1048576,
            "available": True,
            "unavailable_reason": None,
            "execution_status": "ready",
            "supported_parameters": ["tools"],
        },
        {
            "id": "openai/gpt-4o-mini",
            "object": "model",
            "owned_by": "openai",
            "name": "GPT-4o mini",
            "context_length": 128000,
            "available": False,
            "unavailable_reason": "exhausted",
            "execution_status": "exhausted",
        },
        {
            "id": "zai/glm-4.6v-flash",
            "object": "model",
            "owned_by": "zai",
            "name": "GLM-4.6V Flash",
            "available": False,
            "unavailable_reason": "no_key",
            "execution_status": "needsKey",
        },
    ],
}


class ParseModelRowsTests(unittest.TestCase):
    def test_statuses_and_router_flags(self):
        rows = gw.parse_model_rows(SAMPLE_PAYLOAD)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(by_id["auto"]["status"], "router")
        self.assertEqual(by_id["auto:reliable"]["status"], "router")
        self.assertEqual(by_id["google/gemini-2.5-flash"]["status"], "ready")
        self.assertTrue(by_id["google/gemini-2.5-flash"]["available"])
        self.assertEqual(by_id["openai/gpt-4o-mini"]["status"], "exhausted")
        self.assertEqual(by_id["zai/glm-4.6v-flash"]["status"], "needsKey")
        self.assertEqual(by_id["zai/glm-4.6v-flash"]["reason"], "no_key")

    def test_context_window_falls_back_to_context_length(self):
        rows = gw.parse_model_rows(SAMPLE_PAYLOAD)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(by_id["google/gemini-2.5-flash"]["context_window"], 1048576)
        self.assertEqual(by_id["openai/gpt-4o-mini"]["context_window"], 128000)

    def test_unknown_status_and_garbage_rows(self):
        rows = gw.parse_model_rows(
            {
                "data": [
                    {"id": "mystery/model", "execution_status": "weird", "available": 1},
                    "not-a-dict",
                    {},
                ]
            }
        )
        self.assertEqual(len(rows), 2)  # non-dict rows are skipped
        self.assertEqual(rows[0]["status"], "unknown")
        self.assertTrue(rows[0]["available"])
        self.assertEqual(rows[1]["id"], "")
        self.assertEqual(rows[1]["status"], "unknown")

    def test_empty_payload(self):
        self.assertEqual(gw.parse_model_rows({}), [])
        self.assertEqual(gw.parse_model_rows({"data": None}), [])


class ListModelsTests(unittest.TestCase):
    def settings(self):
        return Settings(
            endpoint="http://localhost:8000/v1",
            api_key="sk-key",
            model="google/gemini-2.5-flash",
        )

    def test_request_and_rows(self):
        captured = {}

        def fake(request, timeout=0):
            captured["url"] = request.full_url
            captured["auth"] = request.get_header("Authorization")
            return FakeResponse(SAMPLE_PAYLOAD)

        with mock.patch("screenanswer.gateway._urlopen", side_effect=fake):
            rows = gw.list_models(self.settings())
        self.assertEqual(len(rows), 5)
        self.assertEqual(captured["url"], "http://localhost:8000/v1/models")
        self.assertEqual(captured["auth"], "Bearer sk-key")

    def test_filter_query_params(self):
        captured = {}

        def fake(request, timeout=0):
            captured["url"] = request.full_url
            return FakeResponse({"data": []})

        with mock.patch("screenanswer.gateway._urlopen", side_effect=fake):
            rows = gw.list_models(self.settings(), execution_status="ready", available=True)
        self.assertEqual(rows, [])
        self.assertIn("execution_status=ready", captured["url"])
        self.assertIn("available=true", captured["url"])

    def test_http_401_raises_auth_error(self):
        with mock.patch(
            "screenanswer.gateway._urlopen", side_effect=http_error(401, b"bad")
        ):
            with self.assertRaises(gw.GatewayAuthError):
                gw.list_models(self.settings())

    def test_upstream_error_raises_gateway_error(self):
        with mock.patch(
            "screenanswer.gateway._urlopen",
            side_effect=urllib.error.URLError("down"),
        ):
            with self.assertRaises(gw.GatewayUpstreamError):
                gw.list_models(self.settings())


class ProvidersPanelContractTests(unittest.TestCase):
    def test_status_colors_cover_every_label(self):
        from screenanswer.providers_gui import STATUS_COLORS, STATUS_LABELS

        self.assertEqual(set(STATUS_COLORS), set(STATUS_LABELS))
        for status in ("ready", "exhausted", "needsKey", "router", "unknown"):
            self.assertIn(status, STATUS_COLORS)

    def test_panel_import_is_headless_safe(self):
        import screenanswer.providers_gui as mod

        self.assertTrue(hasattr(mod, "ProvidersWindow"))
        self.assertTrue(hasattr(mod.ProvidersWindow, "build"))
        self.assertTrue(hasattr(mod.ProvidersWindow, "refresh"))

    def test_settings_window_accepts_providers_button(self):
        import inspect

        from screenanswer.settings_gui import SettingsWindow

        self.assertIn("on_providers", inspect.signature(SettingsWindow.__init__).parameters)


class AppProvidersWiringTests(unittest.TestCase):
    def test_run_app_opens_providers_window(self):
        import inspect

        from screenanswer import __main__

        source = inspect.getsource(__main__._run_app)
        self.assertIn("on_providers=open_providers", source)
        self.assertIn("ProvidersWindow", source)
        self.assertIn("providers_holder", source)


if __name__ == "__main__":
    unittest.main()
