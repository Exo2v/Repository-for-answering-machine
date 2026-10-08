import base64
import ctypes
import io
import inspect
import json
import os
import queue
import struct
import sys
import tempfile
import types
import unittest
import urllib.error
import zlib
from unittest.mock import MagicMock, patch

from answer_tray import (
    _encode_rgb_png,
    API_KEY_ENV_VARS,
    APINEX_ENDPOINT,
    APINEX_FREE_VISION_MODELS,
    DEFAULT_APINEX_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_MISTRAL_MODEL,
    DEFAULT_OPENROUTER_MODEL,
    OTTERARY_CONFIG_DIRECTORY,
    OTTERARY_SYSTEM_INSTRUCTION,
    OTTERARY_WIN7_CONFIG_DIRECTORY,
    LASSO_APINEX_VISION_MODELS,
    LASSO_CONFIG_DIRECTORY,
    LASSOV2_CONFIG_DIRECTORY,
    LASSOWIN7_CONFIG_DIRECTORY,
    LASSV27_CONFIG_DIRECTORY,
    OLLAMA_ENDPOINT,
    GEMINI_API_BASE_URL,
    OPENROUTER_FREE_VISION_REASONING_MODELS,
    ScreenAnswerApp,
    WindowsTray,
    _powershell_string_literal,
    _run_diagnostic_console_child,
    OPENROUTER_ENDPOINT,
    MISTRAL_OCR_ENDPOINT,
    MISTRAL_OCR_MODEL,
    _extract_mistral_ocr_markdown,
    _extract_mistral_text,
    ask_apinex,
    ask_gemini,
    ask_mistral,
    ask_ollama,
    ask_openrouter,
    default_provider_for_executable,
    diagnostic_console_available_for_executable,
    diagnostics_mode_enabled,
    diagnostics_page_available,
    ensure_lasso1_config,
    ensure_lasso_multi_provider_config,
    ensure_otterary_config,
    is_lasso1_executable,
    is_lassv7_executable,
    is_otterary_executable,
    is_otterary_win7_executable,
    hotkey_specs_for_variant,
    hotkey_event_for_id,
    lasso_app_name_for_executable,
    lasso_config_directory_for_executable,
    lasso1_config_path,
    lasso1_config_template,
    lasso_multi_provider_config_template,
    is_lasso_multi_provider_executable,
    main,
    load_portable_config,
    load_otterary_config,
    otterary_config_directory_for_executable,
    otterary_config_path,
    otterary_config_template,
    parse_option,
    provider_labels_for_executable,
    provider_requires_api_key,
    resolve_api_key,
    schedule_lasso1_self_cleanup,
    self_destruct_config_directory_for_executable,
    save_lasso1_config,
    save_lasso_multi_provider_config,
    save_otterary_config,
    should_open_lasso_settings_on_startup,
    pix2text_bundle_importable,
    run_pix2text_ocr,
    save_portable_config,
    valid_model_name,
    valid_lasso_multi_provider_model,
)


class DiagnosticsModeTests(unittest.TestCase):
    def test_diagnostic_mode_is_enabled_by_exe_name_or_flag(self):
        self.assertTrue(
            diagnostics_mode_enabled((), "ScreenAnswer-Diagnostic.exe")
        )
        self.assertTrue(diagnostics_mode_enabled(("--diagnostics",), "python.exe"))
        self.assertFalse(diagnostics_mode_enabled((), "ScreenAnswer.exe"))
        self.assertFalse(diagnostics_mode_enabled(("--diagnostics",), "LassV7.exe"))
        self.assertTrue(diagnostics_page_available((), "Lasso1.exe"))
        self.assertTrue(diagnostics_page_available((), "LassV7.exe"))
        self.assertTrue(diagnostics_page_available((), "LassoV2.exe"))
        self.assertTrue(diagnostics_page_available((), "LassV27.exe"))
        self.assertTrue(
            diagnostics_page_available((), "ScreenAnswer-Diagnostic.exe")
        )
        self.assertFalse(diagnostics_page_available((), "ScreenAnswer.exe"))


class Lasso1ModeTests(unittest.TestCase):
    def test_lasso_executables_keep_diagnostics_on_demand_not_autostarted(self):
        self.assertTrue(is_lasso1_executable("Lasso1.exe"))
        self.assertTrue(is_lasso1_executable("LassV7.exe"))
        self.assertTrue(is_lasso1_executable("LassoV2.exe"))
        self.assertTrue(is_lasso1_executable("LassV27.exe"))
        self.assertTrue(is_lassv7_executable("LassV7.exe"))
        self.assertTrue(is_lassv7_executable("LassV27.exe"))
        self.assertFalse(is_lassv7_executable("Lasso1.exe"))
        self.assertFalse(is_lassv7_executable("LassoV2.exe"))
        self.assertFalse(is_lasso1_executable("ScreenAnswer.exe"))
        self.assertEqual(
            provider_labels_for_executable("Lasso1.exe"),
            {"openrouter": "OpenRouter"},
        )
        self.assertEqual(
            provider_labels_for_executable("LassV7.exe"),
            {"openrouter": "OpenRouter"},
        )
        self.assertEqual(default_provider_for_executable("Lasso1.exe"), "openrouter")
        self.assertEqual(default_provider_for_executable("LassV7.exe"), "openrouter")
        self.assertEqual(default_provider_for_executable("LassoV2.exe"), "openrouter")
        self.assertEqual(default_provider_for_executable("LassV27.exe"), "openrouter")
        self.assertEqual(lasso_config_directory_for_executable("Lasso1.exe"), "Lasso1")
        self.assertEqual(lasso_config_directory_for_executable("LassV7.exe"), "LassV7")
        self.assertEqual(lasso_app_name_for_executable("Lasso1.exe"), "Lasso1")
        self.assertEqual(lasso_app_name_for_executable("LassV7.exe"), "LassV7")
        self.assertEqual(
            lasso_config_directory_for_executable("LassoV2.exe"),
            LASSOV2_CONFIG_DIRECTORY,
        )
        self.assertEqual(
            lasso_config_directory_for_executable("LassV27.exe"),
            LASSV27_CONFIG_DIRECTORY,
        )
        self.assertEqual(lasso_app_name_for_executable("LassoV2.exe"), "LassoV2")
        self.assertEqual(lasso_app_name_for_executable("LassV27.exe"), "LassV27")
        self.assertEqual(
            provider_labels_for_executable("LassoV2.exe"),
            {"openrouter": "OpenRouter"},
        )
        self.assertEqual(
            provider_labels_for_executable("LassV27.exe"),
            {"openrouter": "OpenRouter"},
        )
        self.assertFalse(diagnostics_mode_enabled(("--diagnostics",), "Lasso1.exe"))
        self.assertFalse(diagnostics_mode_enabled(("--diagnostics",), "LassV7.exe"))
        self.assertFalse(diagnostics_mode_enabled(("--diagnostics",), "LassoV2.exe"))
        self.assertFalse(diagnostics_mode_enabled(("--diagnostics",), "LassV27.exe"))

    def test_lasso_only_delete_hotkey_and_config_only_model_default(self):
        ordinary_hotkeys = hotkey_specs_for_variant(False)
        lasso_hotkeys = hotkey_specs_for_variant(True)
        self.assertEqual([spec[1] for spec in ordinary_hotkeys], ["Ctrl+Alt+S", "Ctrl+Alt+Q"])
        self.assertEqual(
            [spec[1] for spec in lasso_hotkeys],
            ["Ctrl+Alt+S", "Ctrl+Alt+Q", "Ctrl+Alt+O"],
        )
        self.assertEqual(lasso1_config_template()["models"]["openrouter"], DEFAULT_OPENROUTER_MODEL)
        self.assertEqual(hotkey_event_for_id(3, True), ("silent_delete",))
        self.assertIsNone(hotkey_event_for_id(3, False))
        self.assertEqual(hotkey_event_for_id(1, True), ("capture", "Ctrl+Alt+S"))

    def test_first_run_config_uses_variant_folder_with_default_model_and_blank_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = lasso1_config_path(directory)
            self.assertEqual(path, os.path.join(directory, "Lasso1", "config.json"))
            with patch("answer_tray.LASSOV7_MODE", True):
                lassv7_path = lasso1_config_path(directory)
            self.assertEqual(lassv7_path, os.path.join(directory, "LassV7", "config.json"))
            self.assertEqual(
                lasso1_config_path(directory, "LassoV2.exe"),
                os.path.join(directory, LASSOV2_CONFIG_DIRECTORY, "config.json"),
            )
            self.assertEqual(
                lasso1_config_path(directory, "LassV27.exe"),
                os.path.join(directory, LASSV27_CONFIG_DIRECTORY, "config.json"),
            )
            for executable_name in ("LassoV2.exe", "LassV27.exe"):
                new_path = lasso1_config_path(directory, executable_name)
                self.assertTrue(ensure_lasso1_config(new_path))
                with open(new_path, "r", encoding="utf-8") as config_file:
                    new_config = json.load(config_file)
                self.assertEqual(new_config["api_keys"], {"openrouter": ""})
                self.assertEqual(
                    new_config["models"]["openrouter"], DEFAULT_OPENROUTER_MODEL
                )
                self.assertIs(new_config["allow_screenshot_uploads"], False)

            self.assertTrue(ensure_lasso1_config(path))
            with open(path, "r", encoding="utf-8") as config_file:
                config = json.load(config_file)

            self.assertEqual(config, lasso1_config_template())
            self.assertEqual(config["provider"], "openrouter")
            self.assertEqual(config["api_keys"], {"openrouter": ""})
            self.assertEqual(
                config["models"], {"openrouter": DEFAULT_OPENROUTER_MODEL}
            )
            self.assertIs(config["allow_screenshot_uploads"], False)
            self.assertNotIn("_instructions", config)

            config["allow_screenshot_uploads"] = True
            with open(path, "w", encoding="utf-8") as config_file:
                json.dump(config, config_file)
            self.assertFalse(ensure_lasso1_config(path))
            with open(path, "r", encoding="utf-8") as config_file:
                self.assertIs(json.load(config_file)["allow_screenshot_uploads"], True)

    def test_lasso_settings_window_has_diagnostics_button_but_no_model_control(self):
        labels = []
        diagnostic_commands = []

        class FakeWidget:
            def pack(self, *args, **kwargs):
                return None

            def winfo_reqwidth(self):
                return 440

            def winfo_reqheight(self):
                return 320

        class FakeVariable:
            def __init__(self, value=None):
                self.value = value

            def get(self):
                return self.value

            def set(self, value):
                self.value = value

        def make_widget(*args, **kwargs):
            if "text" in kwargs:
                labels.append(str(kwargs["text"]))
            if kwargs.get("text") == "Diagnostics":
                diagnostic_commands.append(kwargs.get("command"))
            return FakeWidget()

        fake_tkinter = types.ModuleType("tkinter")
        fake_tkinter.Frame = make_widget
        fake_tkinter.Label = make_widget
        fake_tkinter.Entry = make_widget
        fake_tkinter.Checkbutton = make_widget
        fake_tkinter.Button = make_widget
        fake_tkinter.StringVar = FakeVariable
        fake_tkinter.BooleanVar = FakeVariable

        app = object.__new__(ScreenAnswerApp)
        app.root = MagicMock()
        app.root.winfo_screenwidth.return_value = 1024
        app.root.winfo_screenheight.return_value = 768
        app.api_key = ""
        app.config_path = "Lasso1/config.json"
        app.privacy_acknowledged = False
        app.save_settings = MagicMock()
        app.hide_window = MagicMock()
        app.show_diagnostics = MagicMock()
        app._privacy_changed = MagicMock()

        with patch.dict("sys.modules", {"tkinter": fake_tkinter}):
            app._build_lasso1_window()

        self.assertFalse(hasattr(app, "model_var"))
        self.assertNotIn("model", " ".join(labels).lower())
        self.assertIn("Diagnostics", labels)
        self.assertEqual(len(diagnostic_commands), 1)
        diagnostic_commands[0]()
        app.show_diagnostics.assert_called_once_with()

    def test_missing_or_unapproved_models_migrate_and_valid_free_custom_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "Lasso1", "config.json")
            os.makedirs(os.path.dirname(path))
            blank_config = {
                "provider": "openrouter",
                "api_keys": {"openrouter": ""},
                "models": {"openrouter": ""},
                "allow_screenshot_uploads": False,
            }
            with open(path, "w", encoding="utf-8") as config_file:
                json.dump(blank_config, config_file)
            self.assertFalse(ensure_lasso1_config(path))
            with open(path, "r", encoding="utf-8") as config_file:
                migrated_blank = json.load(config_file)
            self.assertEqual(
                migrated_blank["models"]["openrouter"], DEFAULT_OPENROUTER_MODEL
            )
            self.assertEqual(migrated_blank["api_keys"]["openrouter"], "")
            self.assertIs(migrated_blank["allow_screenshot_uploads"], False)

            default_config = {
                "provider": "openrouter",
                "api_keys": {"openrouter": "saved-key"},
                "models": {"openrouter": DEFAULT_OPENROUTER_MODEL},
                "allow_screenshot_uploads": True,
            }
            with open(path, "w", encoding="utf-8") as config_file:
                json.dump(default_config, config_file)
            self.assertFalse(ensure_lasso1_config(path))
            with open(path, "r", encoding="utf-8") as config_file:
                retained_default = json.load(config_file)
            self.assertEqual(
                retained_default["models"]["openrouter"], DEFAULT_OPENROUTER_MODEL
            )

            legacy_custom_config = {
                "provider": "openrouter",
                "api_key": "saved-key",
                "model": "custom/legacy-vision-model",
                "allow_screenshot_uploads": True,
            }
            with open(path, "w", encoding="utf-8") as config_file:
                json.dump(legacy_custom_config, config_file)
            self.assertFalse(ensure_lasso1_config(path))
            with open(path, "r", encoding="utf-8") as config_file:
                migrated_legacy = json.load(config_file)
            self.assertEqual(
                migrated_legacy["models"]["openrouter"],
                DEFAULT_OPENROUTER_MODEL,
            )
            self.assertEqual(migrated_legacy["api_key"], "saved-key")
            self.assertNotIn("model", migrated_legacy)
            self.assertIs(migrated_legacy["allow_screenshot_uploads"], False)

            custom_config = {
                "provider": "openrouter",
                "api_keys": {"openrouter": "saved-key"},
                "models": {"openrouter": "custom/vision-model"},
                "allow_screenshot_uploads": True,
            }
            with open(path, "w", encoding="utf-8") as config_file:
                json.dump(custom_config, config_file)
            self.assertFalse(ensure_lasso1_config(path))
            with open(path, "r", encoding="utf-8") as config_file:
                migrated_paid = json.load(config_file)
            self.assertEqual(
                migrated_paid["models"]["openrouter"], DEFAULT_OPENROUTER_MODEL
            )
            self.assertEqual(migrated_paid["api_keys"]["openrouter"], "saved-key")
            self.assertIs(migrated_paid["allow_screenshot_uploads"], False)

            allowed_free_model = sorted(OPENROUTER_FREE_VISION_REASONING_MODELS)[1]
            allowed_config = {
                "provider": "openrouter",
                "api_keys": {"openrouter": "saved-key"},
                "models": {"openrouter": allowed_free_model},
                "allow_screenshot_uploads": True,
            }
            with open(path, "w", encoding="utf-8") as config_file:
                json.dump(allowed_config, config_file)
            self.assertFalse(ensure_lasso1_config(path))
            with open(path, "r", encoding="utf-8") as config_file:
                preserved_free = json.load(config_file)
            self.assertEqual(preserved_free["models"]["openrouter"], allowed_free_model)
            self.assertEqual(preserved_free["api_keys"]["openrouter"], "saved-key")
            self.assertIs(preserved_free["allow_screenshot_uploads"], True)

    def test_config_loader_keeps_only_openrouter_and_requires_boolean_consent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "config.json")
            with patch.multiple(
                "answer_tray",
                LASSO1_MODE=True,
                APP_DEFAULT_PROVIDER="openrouter",
                PROVIDER_LABELS={"openrouter": "OpenRouter"},
            ):
                with open(path, "w", encoding="utf-8") as config_file:
                    json.dump(
                        {
                            "provider": "groq",
                            "api_keys": {
                                "openrouter": "config-key",
                                "gemini": "ignored-key",
                                "mistral": "ignored-key",
                                "groq": "ignored-key",
                            },
                            "models": {
                                "openrouter": DEFAULT_OPENROUTER_MODEL,
                                "gemini": "ignored-model",
                            },
                            "allow_screenshot_uploads": True,
                        },
                        config_file,
                    )
                loaded = load_portable_config(path)
                self.assertEqual(loaded["provider"], "openrouter")
                self.assertEqual(loaded["api_keys"], {"openrouter": "config-key"})
                self.assertEqual(
                    loaded["models"],
                    {"openrouter": DEFAULT_OPENROUTER_MODEL},
                )
                self.assertIs(loaded["allow_screenshot_uploads"], True)

                with open(path, "w", encoding="utf-8") as config_file:
                    json.dump(
                        {"allow_screenshot_uploads": 1},
                        config_file,
                    )
                loaded_blank = load_portable_config(path)
                self.assertIs(loaded_blank["allow_screenshot_uploads"], False)
                self.assertEqual(
                    loaded_blank["models"],
                    {"openrouter": DEFAULT_OPENROUTER_MODEL},
                )

    def test_lasso1_uses_config_key_even_when_environment_key_exists(self):
        configured_key, source = resolve_api_key(
            "openrouter",
            {"openrouter": "config-key"},
            {"OPENROUTER_API_KEY": "environment-key"},
            lasso1_mode=True,
        )
        self.assertEqual(configured_key, "config-key")
        self.assertEqual(source, "Lasso1 config file")
        self.assertEqual(
            resolve_api_key(
                "openrouter",
                {},
                {"OPENROUTER_API_KEY": "environment-key"},
                lasso1_mode=True,
            ),
            ("", "not configured"),
        )
        self.assertEqual(
            resolve_api_key(
                "openrouter",
                {"openrouter": "config-key"},
                {"OPENROUTER_API_KEY": "environment-key"},
                lasso1_mode=False,
            ),
            ("environment-key", "environment variable"),
        )

    def test_first_run_gui_stays_hidden_and_diagnostics_remain_on_demand(self):
        class FakeStringVar:
            def __init__(self, value=""):
                self.value = value

            def set(self, value):
                self.value = value

            def get(self):
                return self.value

        tkinter_module = types.ModuleType("tkinter")
        tkinter_module.StringVar = FakeStringVar
        root = MagicMock()
        tray = MagicMock()

        with tempfile.TemporaryDirectory() as directory:
            config_path = os.path.join(directory, "Lasso1", "config.json")
            self.assertTrue(ensure_lasso1_config(config_path))
            with patch.multiple(
                "answer_tray",
                LASSO1_MODE=True,
                LASSOV7_MODE=False,
                APP_NAME="Lasso1",
                APP_VERSION="lasso1",
                APP_DEFAULT_PROVIDER="openrouter",
                PROVIDER_LABELS={"openrouter": "OpenRouter"},
                API_KEY_ENV_VARS={"openrouter": "OPENROUTER_API_KEY"},
                DEFAULT_MODELS={"openrouter": DEFAULT_OPENROUTER_MODEL},
            ):
                with patch("answer_tray.portable_config_path", return_value=config_path):
                    with patch("answer_tray.diagnostics_mode_enabled", return_value=True):
                        with patch("answer_tray.WindowsTray", return_value=tray) as tray_class:
                            with patch.object(
                                ScreenAnswerApp, "_build_lasso1_window"
                            ) as lasso_window:
                                with patch.object(
                                    ScreenAnswerApp, "_build_window"
                                ) as build_window:
                                    with patch.dict(
                                        "sys.modules", {"tkinter": tkinter_module}
                                    ):
                                        with patch.dict(
                                            os.environ,
                                            {"OPENROUTER_API_KEY": "environment-key"},
                                        ):
                                            app = ScreenAnswerApp(root)

        self.assertEqual(app.provider, "openrouter")
        self.assertEqual(app.api_key, "")
        self.assertEqual(app.api_key_source, "not configured")
        self.assertEqual(app.model, DEFAULT_OPENROUTER_MODEL)
        self.assertFalse(app.privacy_acknowledged)
        self.assertTrue(app.diagnostics_enabled)
        self.assertFalse(app.diagnostics_auto_open)
        lasso_window.assert_called_once_with()
        build_window.assert_not_called()
        tray_class.assert_called_once_with(
            app.events,
            diagnostics_enabled=True,
            settings_enabled=False,
            lasso1_mode=True,
            lassv7_mode=False,
            diagnostic_console_enabled=False,
        )
        tray.show_balloon.assert_called_once()
        root.deiconify.assert_not_called()
        self.assertEqual([call.args[0] for call in root.after.call_args_list], [100])

    def test_gui_save_persists_key_and_consent_then_closes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = lasso1_config_path(directory)
            ensure_lasso1_config(path)
            app = object.__new__(ScreenAnswerApp)
            app.lasso1_mode = True
            app.api_key_var = MagicMock()
            app.api_key_var.get.return_value = "saved-openrouter-key"
            app.privacy_var = MagicMock()
            app.privacy_var.get.return_value = False
            app.config_path = path
            app.api_keys = {"openrouter": ""}
            app.models = {"openrouter": DEFAULT_OPENROUTER_MODEL}
            app.api_key_sources = {"openrouter": "not configured"}
            app.portable_config = {}
            app.status_var = MagicMock()
            app.tray = MagicMock()
            app.hide_window = MagicMock()
            app.show_window = MagicMock()
            app._show_error = MagicMock()
            app._log_diagnostic = MagicMock()

            self.assertTrue(app.save_settings())
            self.assertFalse(app.privacy_acknowledged)
            app.hide_window.assert_called_once_with()
            app._show_error.assert_not_called()
            with open(path, "r", encoding="utf-8") as config_file:
                saved = json.load(config_file)
            self.assertEqual(
                saved["api_keys"], {"openrouter": "saved-openrouter-key"}
            )
            self.assertEqual(
                saved["models"], {"openrouter": DEFAULT_OPENROUTER_MODEL}
            )
            self.assertIs(saved["allow_screenshot_uploads"], False)

            app.hide_window.reset_mock()
            app.privacy_var.get.return_value = True
            self.assertTrue(app.save_settings())
            self.assertTrue(app.privacy_acknowledged)
            app.hide_window.assert_called_once_with()
            with open(path, "r", encoding="utf-8") as config_file:
                saved = json.load(config_file)
            self.assertIs(saved["allow_screenshot_uploads"], True)

    def test_apinex_and_ollama_upload_notices_explain_data_paths(self):
        app = object.__new__(ScreenAnswerApp)
        app.form_ocr_backend = "provider"
        apinex_notice = app._consent_text("apinex")
        self.assertIn("through APInex", apinex_notice)
        self.assertIn("upstream vision model", apinex_notice)
        self.assertIn("free allowance", apinex_notice)
        self.assertIn("Do not upload sensitive screens", apinex_notice)
        self.assertIn("No web search or tools", apinex_notice)

        ollama_notice = app._consent_text("ollama")
        self.assertIn("local Ollama server", ollama_notice)
        self.assertIn("127.0.0.1:11434", ollama_notice)
        self.assertIn("does not send it to a cloud model API", ollama_notice)

        openrouter_notice = app._consent_text("openrouter")
        self.assertIn("through OpenRouter", openrouter_notice)
        self.assertIn("Host data terms apply", openrouter_notice)
        self.assertIn("Do not upload sensitive screens", openrouter_notice)
        self.assertIn("no separate OCR service", openrouter_notice)
        self.assertIn("live web search", openrouter_notice)

        app.form_ocr_backend = "pix2text"
        local_ocr_notice = app._consent_text("apinex")
        self.assertIn("OCR text", local_ocr_notice)
        self.assertIn("through APInex", local_ocr_notice)
        self.assertIn("do not upload sensitive screens", local_ocr_notice)
        local_ollama_notice = app._consent_text("ollama")
        self.assertIn("Pix2Text reads locally", local_ollama_notice)
        self.assertIn("127.0.0.1:11434", local_ollama_notice)

    def test_lasso1_settings_window_can_be_shown_on_demand(self):
        app = object.__new__(ScreenAnswerApp)
        app.lasso1_mode = True
        app.root = MagicMock()
        app.api_entry = MagicMock()

        app.show_window()

        app.root.deiconify.assert_called_once_with()
        app.root.lift.assert_called_once_with()
        app.root.focus_force.assert_called_once_with()
        app.api_entry.focus_set.assert_called_once_with()

    def test_capture_is_blocked_until_config_consent_is_true(self):
        app = object.__new__(ScreenAnswerApp)
        app.lasso1_mode = True
        app.busy = False
        app.api_key = "config-key"
        app.privacy_acknowledged = False
        app.provider = "openrouter"
        app.status_var = MagicMock()
        app.tray = MagicMock()
        app._log_diagnostic = MagicMock()
        app.show_window = MagicMock()

        app._start_capture("test")

        self.assertFalse(app.busy)
        app.tray.show_balloon.assert_called_once()
        self.assertIn("choose Open", app.tray.show_balloon.call_args.args[1])
        self.assertIn("consent", app.tray.show_balloon.call_args.args[1])
        app.show_window.assert_not_called()

    def test_capture_falls_back_to_default_for_a_blank_lasso_model_without_prompting(self):
        app = object.__new__(ScreenAnswerApp)
        app.lasso1_mode = True
        app.lassv7_mode = False
        app.busy = False
        app.api_key = "config-key"
        app.model = ""
        app.models = {"openrouter": ""}
        app.privacy_acknowledged = True
        app.provider = "openrouter"
        app.ocr_backend = "provider"
        app.diagnostics_enabled = False
        app.status_var = MagicMock()
        app.tray = MagicMock()
        app.root = MagicMock()
        app._result_generation = 0
        app._fade_job = None
        app._log_diagnostic = MagicMock()

        with patch("answer_tray.threading.Thread") as thread_class:
            app._start_capture("test")

        self.assertTrue(app.busy)
        self.assertEqual(app.model, DEFAULT_OPENROUTER_MODEL)
        self.assertEqual(app.models["openrouter"], DEFAULT_OPENROUTER_MODEL)
        app.tray.show_balloon.assert_not_called()
        thread_class.return_value.start.assert_called_once_with()

    def test_lasso1_context_menu_exposes_config_file_folder_and_self_destruct_actions(self):
        app_name_patch = patch("answer_tray.APP_NAME", "Lasso1")
        app_name_patch.start()
        self.addCleanup(app_name_patch.stop)

        class Point(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        tray = object.__new__(WindowsTray)
        tray.settings_enabled = False
        tray.lasso1_mode = True
        tray.diagnostics_enabled = True
        tray.events = MagicMock()
        tray._user32 = MagicMock()
        tray._user32.CreatePopupMenu.return_value = 1
        tray._user32.TrackPopupMenu.return_value = 105

        def show_menu():
            WindowsTray._show_context_menu(
                tray,
                1,
                Point,
                101,
                102,
                103,
                104,
                105,
                107,
                106,
                0,
                0x0800,
                0x0100,
                0x0002,
                0,
            )

        show_menu()
        labels = [
            call.args[3]
            for call in tray._user32.AppendMenuW.call_args_list
            if call.args[3]
        ]
        self.assertIn("Open", labels)
        self.assertIn("Open Lasso1 config file", labels)
        self.assertIn("Open Lasso1 config folder", labels)
        self.assertIn("Self-destruct Lasso1…", labels)
        self.assertNotIn("Open Screen Answer", labels)
        self.assertIn("Show diagnostics", labels)
        tray.events.put.assert_called_once_with(("open_config_folder",))

        tray.events.put.reset_mock()
        tray._user32.TrackPopupMenu.return_value = 104
        show_menu()
        tray.events.put.assert_called_once_with(("show_diagnostics",))

        tray.events.put.reset_mock()
        tray._user32.TrackPopupMenu.return_value = 107
        show_menu()
        tray.events.put.assert_called_once_with(("open_config_file",))

        tray.events.put.reset_mock()
        tray._user32.TrackPopupMenu.return_value = 102
        show_menu()
        tray.events.put.assert_called_once_with(("open",))

        tray.events.put.reset_mock()
        tray._user32.TrackPopupMenu.return_value = 106
        show_menu()
        tray.events.put.assert_called_once_with(("self_destruct",))

        tray._user32.AppendMenuW.reset_mock()
        tray._user32.TrackPopupMenu.return_value = 0
        with patch("answer_tray.APP_NAME", "LassV7"):
            show_menu()
        lassv7_labels = [
            call.args[3]
            for call in tray._user32.AppendMenuW.call_args_list
            if call.args[3]
        ]
        self.assertIn("Open LassV7 config file", lassv7_labels)
        self.assertIn("Open LassV7 config folder", lassv7_labels)
        self.assertIn("Self-destruct LassV7…", lassv7_labels)

    def test_lassv7_result_feedback_is_limited_to_the_tray_color(self):
        app = object.__new__(ScreenAnswerApp)
        app.lassv7_mode = True
        app.busy = True
        app._result_generation = 0
        app._fade_job = None
        app.root = MagicMock()
        app.tray = MagicMock()
        app.status_var = MagicMock()
        app._log_diagnostic = MagicMock()

        with patch("answer_tray.APP_NAME", "LassV7"):
            app._set_result(3)

        app.tray.set_state.assert_called_once()
        self.assertEqual(app.tray.set_state.call_args.args[0], (67, 160, 71))
        app.status_var.set.assert_not_called()

    def test_lassv7_tray_changes_color_without_tooltips_or_popups(self):
        class NotifyIconData(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("hWnd", ctypes.c_void_p),
                ("uID", ctypes.c_uint),
                ("uFlags", ctypes.c_uint),
                ("uCallbackMessage", ctypes.c_uint),
                ("hIcon", ctypes.c_void_p),
                ("szTip", ctypes.c_wchar * 128),
                ("dwState", ctypes.c_uint),
                ("dwStateMask", ctypes.c_uint),
                ("szInfo", ctypes.c_wchar * 256),
                ("uTimeoutOrVersion", ctypes.c_uint),
                ("szInfoTitle", ctypes.c_wchar * 64),
                ("dwInfoFlags", ctypes.c_uint),
            ]

        tray = object.__new__(WindowsTray)
        tray.lassv7_mode = True
        tray.suppress_tray_feedback = True
        tray.hwnd = 1
        tray._nid = NotifyIconData()
        tray._nid_type = NotifyIconData
        tray._lock = MagicMock()
        tray._create_icon = MagicMock(return_value=17)
        tray._shell32 = MagicMock()

        tray.set_state((67, 160, 71), "Option 3")
        self.assertEqual(tray._nid.hIcon, 17)
        self.assertEqual(tray._nid.uFlags, 0x00000001 | 0x00000002)
        self.assertEqual(tray._nid.szTip, "")
        tray._shell32.Shell_NotifyIconW.reset_mock()
        tray.show_balloon("LassV7", "capturing")
        tray._shell32.Shell_NotifyIconW.assert_not_called()

        tray.lassv7_mode = False
        tray.suppress_tray_feedback = False
        tray._nid = NotifyIconData()
        tray.set_state((67, 160, 71), "Option 3")
        self.assertEqual(tray._nid.uFlags, 0x00000001 | 0x00000002 | 0x00000004)
        self.assertEqual(tray._nid.szTip, "Option 3")
        tray.show_balloon("Screen Answer", "still supported for other builds")
        self.assertEqual(tray._shell32.Shell_NotifyIconW.call_count, 2)

    def test_open_config_folder_uses_the_lasso1_appdata_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = os.path.join(directory, "Lasso1", "config.json")
            app = object.__new__(ScreenAnswerApp)
            app.lasso1_mode = True
            app.config_path = config_path
            app.tray = MagicMock()
            with patch("answer_tray.os.startfile", create=True) as startfile:
                self.assertTrue(app.open_lasso1_config_folder())
        startfile.assert_called_once_with(os.path.dirname(os.path.abspath(config_path)))

    def test_open_config_file_uses_the_lasso1_appdata_config_path(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = os.path.join(directory, "Lasso1", "config.json")
            app = object.__new__(ScreenAnswerApp)
            app.lasso1_mode = True
            app.config_path = config_path
            app.tray = MagicMock()
            with patch("answer_tray.os.startfile", create=True) as startfile:
                self.assertTrue(app.open_lasso1_config_file())
        startfile.assert_called_once_with(os.path.abspath(config_path))

    def test_silent_delete_hotkey_schedules_cleanup_without_prompt_or_notification(self):
        app = object.__new__(ScreenAnswerApp)
        app.lasso1_mode = True
        app.config_path = os.path.join("profile", "Lasso1", "config.json")
        app.tray = MagicMock()
        app.exit_app = MagicMock()
        app._log_diagnostic = MagicMock()

        with patch("answer_tray.ctypes.WinDLL", side_effect=AssertionError("unexpected prompt"), create=True):
            with patch("answer_tray.schedule_lasso1_self_cleanup", return_value=False) as cleanup:
                self.assertFalse(app.silent_delete())
                cleanup.assert_called_once_with(sys.executable, app.config_path)
                app.exit_app.assert_not_called()
                app.tray.show_balloon.assert_not_called()

            app.exit_app.reset_mock()
            with patch("answer_tray.schedule_lasso1_self_cleanup", return_value=True) as cleanup:
                self.assertTrue(app.silent_delete())
                cleanup.assert_called_once_with(sys.executable, app.config_path)
                app.exit_app.assert_called_once_with()
                app.tray.show_balloon.assert_not_called()

    def test_tray_menu_delete_still_requires_confirmation(self):
        app = object.__new__(ScreenAnswerApp)
        app.lasso1_mode = True
        app.config_path = os.path.join("profile", "Lasso1", "config.json")
        app.tray = MagicMock()
        app.exit_app = MagicMock()
        app._confirm_lasso1_self_destruct = MagicMock(return_value=False)

        with patch("answer_tray.schedule_lasso1_self_cleanup", return_value=True) as cleanup:
            self.assertFalse(app.self_destruct())
            cleanup.assert_not_called()
            app.exit_app.assert_not_called()

            app._confirm_lasso1_self_destruct.return_value = True
            cleanup.return_value = False
            self.assertFalse(app.self_destruct())
            cleanup.assert_called_once_with(sys.executable, app.config_path)
            app.exit_app.assert_not_called()
            app.tray.show_balloon.assert_called_once()

            app.tray.show_balloon.reset_mock()
            cleanup.return_value = True
            self.assertTrue(app.self_destruct())
            app.exit_app.assert_called_once_with()
            app.tray.show_balloon.assert_called_once()

    def test_native_self_destruct_confirmation_defaults_to_no(self):
        app = object.__new__(ScreenAnswerApp)
        app.lasso1_mode = True
        message_box = MagicMock(return_value=6)
        user32 = types.SimpleNamespace(MessageBoxW=message_box)
        with patch("answer_tray.ctypes.WinDLL", return_value=user32, create=True):
            self.assertTrue(app._confirm_lasso1_self_destruct())
        self.assertIn("cannot be undone", message_box.call_args.args[1])
        self.assertTrue(message_box.call_args.args[3] & 0x00000100)

        message_box.return_value = 7
        with patch("answer_tray.ctypes.WinDLL", return_value=user32, create=True):
            self.assertFalse(app._confirm_lasso1_self_destruct())

    def test_self_cleanup_scope_and_powershell_path_quoting_are_restricted(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = os.path.join(directory, "Lasso1", "config.json")
            wrong_executable = os.path.join(directory, "ScreenAnswer.exe")
            self.assertFalse(
                schedule_lasso1_self_cleanup(wrong_executable, config_path)
            )
            self.assertFalse(
                schedule_lasso1_self_cleanup(
                    os.path.join(directory, "LassoV2.exe"), config_path
                )
            )
            self.assertFalse(
                schedule_lasso1_self_cleanup(
                    os.path.join(directory, "LassV27.exe"),
                    os.path.join(directory, "LassV7", "config.json"),
                )
            )
        self.assertEqual(
            _powershell_string_literal("C:\\Users\\O'Neil\\Lasso1.exe"),
            "'C:\\Users\\O''Neil\\Lasso1.exe'",
        )

    def test_packaged_lasso1_build_check(self):
        with patch.multiple(
            "answer_tray",
            LASSO1_MODE=True,
            LASSOV7_MODE=False,
            APP_NAME="Lasso1",
            APP_DEFAULT_PROVIDER="openrouter",
            PROVIDER_LABELS={"openrouter": "OpenRouter"},
            API_KEY_ENV_VARS={"openrouter": "OPENROUTER_API_KEY"},
            DEFAULT_MODELS={"openrouter": DEFAULT_OPENROUTER_MODEL},
        ):
            with patch("sys.argv", ["Lasso1.exe", "--check-lasso1-build"]):
                self.assertEqual(main(), 0)

    def test_packaged_lassv7_build_check(self):
        with patch.multiple(
            "answer_tray",
            LASSO1_MODE=True,
            LASSOV7_MODE=True,
            APP_NAME="LassV7",
            APP_DEFAULT_PROVIDER="openrouter",
            PROVIDER_LABELS={"openrouter": "OpenRouter"},
            API_KEY_ENV_VARS={"openrouter": "OPENROUTER_API_KEY"},
            DEFAULT_MODELS={"openrouter": DEFAULT_OPENROUTER_MODEL},
        ):
            with patch("answer_tray.sys.version_info", (3, 8, 10, "final", 0)):
                with patch("answer_tray.struct.calcsize", return_value=4):
                    with patch("sys.argv", ["LassV7.exe", "--check-lassv7-build"]):
                        self.assertEqual(main(), 0)

    def test_packaged_lassov2_build_check(self):
        with patch.multiple(
            "answer_tray",
            LASSO1_MODE=True,
            LASSOV7_MODE=False,
            APP_NAME="LassoV2",
            APP_DEFAULT_PROVIDER="openrouter",
            PROVIDER_LABELS={"openrouter": "OpenRouter"},
            API_KEY_ENV_VARS={"openrouter": "OPENROUTER_API_KEY"},
            DEFAULT_MODELS={"openrouter": DEFAULT_OPENROUTER_MODEL},
        ):
            with patch("sys.argv", ["LassoV2.exe", "--check-lassov2-build"]):
                self.assertEqual(main(), 0)

    def test_packaged_lassv27_build_check(self):
        with patch.multiple(
            "answer_tray",
            LASSO1_MODE=True,
            LASSOV7_MODE=True,
            APP_NAME="LassV27",
            APP_DEFAULT_PROVIDER="openrouter",
            PROVIDER_LABELS={"openrouter": "OpenRouter"},
            API_KEY_ENV_VARS={"openrouter": "OPENROUTER_API_KEY"},
            DEFAULT_MODELS={"openrouter": DEFAULT_OPENROUTER_MODEL},
        ):
            with patch("answer_tray.sys.version_info", (3, 8, 10, "final", 0)):
                with patch("answer_tray.struct.calcsize", return_value=4):
                    with patch("sys.argv", ["LassV27.exe", "--check-lassv27-build"]):
                        self.assertEqual(main(), 0)


class NewLassoVariantTests(unittest.TestCase):
    def test_settings_prompts_at_startup_only_when_new_lasso_key_is_missing(self):
        self.assertTrue(should_open_lasso_settings_on_startup(True, ""))
        self.assertTrue(should_open_lasso_settings_on_startup(True, "  "))
        self.assertFalse(should_open_lasso_settings_on_startup(True, "saved-key"))
        self.assertFalse(should_open_lasso_settings_on_startup(False, ""))

    def test_lasso_and_lassowin7_expose_only_apinex_and_openrouter(self):
        expected = {"apinex": "APInex", "openrouter": "OpenRouter"}
        self.assertEqual(
            LASSO_APINEX_VISION_MODELS,
            frozenset((DEFAULT_APINEX_MODEL, "free/gemini-3.1-pro")),
        )
        self.assertTrue(valid_model_name("apinex", "free/gpt-6-luna"))
        self.assertFalse(valid_lasso_multi_provider_model("apinex", "free/gpt-6-luna"))
        for executable_name, directory in (
            ("Lasso.exe", LASSO_CONFIG_DIRECTORY),
            ("LassoWin7.exe", LASSOWIN7_CONFIG_DIRECTORY),
        ):
            self.assertTrue(is_lasso1_executable(executable_name))
            self.assertTrue(is_lasso_multi_provider_executable(executable_name))
            self.assertEqual(provider_labels_for_executable(executable_name), expected)
            self.assertEqual(default_provider_for_executable(executable_name), "apinex")
            self.assertEqual(lasso_config_directory_for_executable(executable_name), directory)
            self.assertEqual(lasso_app_name_for_executable(executable_name), "Lasso")
            self.assertTrue(diagnostic_console_available_for_executable(executable_name))
            self.assertFalse(diagnostics_page_available((), executable_name))
            self.assertFalse(diagnostics_mode_enabled((), executable_name))
        self.assertFalse(is_lassv7_executable("Lasso.exe"))
        self.assertTrue(is_lassv7_executable("LassoWin7.exe"))
        self.assertFalse(diagnostic_console_available_for_executable("LassoV2.exe"))

    def test_first_run_configs_are_variant_scoped_blank_and_consent_off(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = {
                "Lasso.exe": os.path.join(directory, "Lasso", "config.json"),
                "LassoWin7.exe": os.path.join(directory, "LassoWin7", "config.json"),
            }
            for executable_name, expected_path in paths.items():
                path = lasso1_config_path(directory, executable_name)
                self.assertEqual(path, expected_path)
                self.assertTrue(ensure_lasso_multi_provider_config(path))
                with open(path, "r", encoding="utf-8") as config_file:
                    config = json.load(config_file)
                self.assertEqual(config, lasso_multi_provider_config_template())
                self.assertEqual(config["provider"], "apinex")
                self.assertEqual(config["api_keys"], {"apinex": "", "openrouter": ""})
                self.assertEqual(
                    config["models"],
                    {"apinex": DEFAULT_APINEX_MODEL, "openrouter": DEFAULT_OPENROUTER_MODEL},
                )
                self.assertIs(config["allow_screenshot_uploads"], False)
            self.assertNotEqual(paths["Lasso.exe"], paths["LassoWin7.exe"])
            for old_name in ("Lasso1.exe", "LassV7.exe", "LassoV2.exe", "LassV27.exe"):
                self.assertNotEqual(
                    lasso1_config_path(directory, old_name),
                    paths["Lasso.exe"],
                )

    def test_invalid_provider_models_and_retired_groq_values_migrate_safely(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "Lasso", "config.json")
            os.makedirs(os.path.dirname(path))
            with open(path, "w", encoding="utf-8") as config_file:
                json.dump(
                    {
                        "provider": "groq",
                        "api_keys": {
                            "apinex": "keep-apinex-key",
                            "openrouter": "keep-openrouter-key",
                            "groq": "retired-groq-key",
                        },
                        "models": {
                            "apinex": "free/gpt-6-luna",
                            "openrouter": "google/gemma-4-31b-it:online",
                            "groq": "qwen/qwen3.8-27b",
                        },
                        "allow_screenshot_uploads": True,
                        "unexpected": "remove me",
                    },
                    config_file,
                )

            self.assertFalse(ensure_lasso_multi_provider_config(path))
            with open(path, "r", encoding="utf-8") as config_file:
                migrated = json.load(config_file)
            self.assertEqual(migrated["provider"], "apinex")
            self.assertEqual(
                migrated["api_keys"],
                {"apinex": "keep-apinex-key", "openrouter": "keep-openrouter-key"},
            )
            self.assertEqual(
                migrated["models"],
                {"apinex": DEFAULT_APINEX_MODEL, "openrouter": DEFAULT_OPENROUTER_MODEL},
            )
            self.assertIs(migrated["allow_screenshot_uploads"], False)
            self.assertNotIn("unexpected", migrated)
            self.assertNotIn("retired-groq-key", json.dumps(migrated))

    def test_save_accepts_only_curated_vision_models_and_selected_provider_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "Lasso", "config.json")
            models = {
                "apinex": "free/gemini-3.1-pro",
                "openrouter": "google/gemma-4-26b-a4b-it:free",
            }
            api_keys = {"apinex": "apinex-key", "openrouter": "openrouter-key"}
            save_lasso_multi_provider_config(path, "openrouter", api_keys, models, True)
            with open(path, "r", encoding="utf-8") as config_file:
                saved = json.load(config_file)
            self.assertEqual(saved["provider"], "openrouter")
            self.assertEqual(saved["api_keys"], api_keys)
            self.assertEqual(saved["models"], models)
            self.assertIs(saved["allow_screenshot_uploads"], True)

            with self.assertRaisesRegex(ValueError, "APInex model"):
                save_lasso_multi_provider_config(
                    path,
                    "apinex",
                    api_keys,
                    {"apinex": "free/gpt-6-luna", "openrouter": DEFAULT_OPENROUTER_MODEL},
                    True,
                )
            with self.assertRaisesRegex(ValueError, "OpenRouter model"):
                save_lasso_multi_provider_config(
                    path,
                    "openrouter",
                    api_keys,
                    {"apinex": DEFAULT_APINEX_MODEL, "openrouter": "google/gemma-4-31b-it"},
                    True,
                )
            with self.assertRaisesRegex(ValueError, "Choose APInex or OpenRouter"):
                save_lasso_multi_provider_config(path, "groq", api_keys, models, True)
            with self.assertRaisesRegex(ValueError, "APInex API key"):
                save_lasso_multi_provider_config(
                    path, "apinex", {"apinex": "", "openrouter": "key"}, models, True
                )

    def test_new_settings_form_has_provider_selector_but_no_model_control(self):
        labels = []
        entries = []
        buttons = []
        menus = []

        class FakeWidget:
            def pack(self, *args, **kwargs):
                return None

            def configure(self, *args, **kwargs):
                return None

            def winfo_reqwidth(self):
                return 480

            def winfo_reqheight(self):
                return 360

        class FakeVariable:
            def __init__(self, value=None):
                self.value = value

            def get(self):
                return self.value

            def set(self, value):
                self.value = value

        def make_widget(*args, **kwargs):
            if "text" in kwargs:
                labels.append(str(kwargs["text"]))
            if kwargs.get("text"):
                buttons.append(str(kwargs["text"]))
            return FakeWidget()

        def make_entry(*args, **kwargs):
            entries.append(kwargs)
            return FakeWidget()

        def make_menu(*args, **kwargs):
            menus.append(args)
            return FakeWidget()

        fake_tkinter = types.ModuleType("tkinter")
        fake_tkinter.Frame = make_widget
        fake_tkinter.Label = make_widget
        fake_tkinter.Entry = make_entry
        fake_tkinter.Checkbutton = make_widget
        fake_tkinter.Button = make_widget
        fake_tkinter.OptionMenu = make_menu
        fake_tkinter.StringVar = FakeVariable
        fake_tkinter.BooleanVar = FakeVariable

        app = object.__new__(ScreenAnswerApp)
        app.root = MagicMock()
        app.root.winfo_screenwidth.return_value = 1280
        app.root.winfo_screenheight.return_value = 900
        app.form_provider = "apinex"
        app.api_key = ""
        app.api_keys = {"apinex": "", "openrouter": ""}
        app.config_path = "C:/Users/test/AppData/Roaming/Lasso/config.json"
        app.form_ocr_backend = "provider"
        app.privacy_acknowledged = False
        app._consent_text = MagicMock(return_value="consent copy")
        app.save_settings = MagicMock()
        app.open_lasso1_config_file = MagicMock()
        app.open_diagnostic_console = MagicMock()
        app.hide_window = MagicMock()

        with patch.multiple(
            "answer_tray",
            PROVIDER_LABELS={"apinex": "APInex", "openrouter": "OpenRouter"},
            PROVIDER_BY_LABEL={"APInex": "apinex", "OpenRouter": "openrouter"},
        ):
            with patch.dict("sys.modules", {"tkinter": fake_tkinter}):
                app._build_lasso_multi_provider_window()

        self.assertEqual(len(entries), 1, "Only the API-key entry should be shown.")
        self.assertNotIn("Model:", labels)
        self.assertIn("Open config file", buttons)
        self.assertIn("Open diagnostic console", buttons)
        self.assertEqual(menus[0][2:], ("APInex", "OpenRouter"))
        self.assertIn("Model IDs are deliberately not shown or editable here", " ".join(labels))

    def test_save_persists_provider_and_key_but_consent_can_remain_off(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "Lasso", "config.json")
            ensure_lasso_multi_provider_config(path)
            app = object.__new__(ScreenAnswerApp)
            app.lasso1_mode = True
            app.lasso_multi_provider_mode = True
            app.form_provider = "apinex"
            app.api_key_var = MagicMock()
            app.api_key_var.get.return_value = "apinex-key"
            app.privacy_var = MagicMock()
            app.privacy_var.get.return_value = False
            app.config_path = path
            app.api_keys = {"apinex": "", "openrouter": ""}
            app.models = {"apinex": DEFAULT_APINEX_MODEL, "openrouter": DEFAULT_OPENROUTER_MODEL}
            app.api_key_sources = {"apinex": "not configured", "openrouter": "not configured"}
            app.portable_config = {}
            app.status_var = MagicMock()
            app.tray = MagicMock()
            app.hide_window = MagicMock()
            app.show_window = MagicMock()
            app._show_error = MagicMock()
            app._log_diagnostic = MagicMock()

            self.assertTrue(app.save_settings())
            app.hide_window.assert_called_once_with()
            app._show_error.assert_not_called()
            self.assertFalse(app.privacy_acknowledged)
            with open(path, "r", encoding="utf-8") as config_file:
                saved = json.load(config_file)
            self.assertEqual(saved["provider"], "apinex")
            self.assertEqual(saved["api_keys"]["apinex"], "apinex-key")
            self.assertEqual(saved["api_keys"]["openrouter"], "")
            self.assertIs(saved["allow_screenshot_uploads"], False)

    def test_diagnostic_console_is_created_only_after_explicit_request(self):
        app = object.__new__(ScreenAnswerApp)
        app.lasso_multi_provider_mode = True
        app.diagnostics_enabled = True
        app.diagnostic_console_lock = __import__("threading").RLock()
        app.diagnostic_console_process = None
        app.diagnostic_console_messages = queue.Queue(maxsize=2000)
        app.diagnostic_lines = ["startup diagnostic"]
        app._log_diagnostic = MagicMock()
        process = MagicMock()
        process.poll.return_value = None
        process.stdin = MagicMock()

        with patch("answer_tray.subprocess.Popen", return_value=process) as popen:
            with patch("answer_tray.threading.Thread") as thread_class:
                self.assertTrue(app.open_diagnostic_console())
                popen.assert_called_once()
                self.assertIn("--diagnostic-console-child", popen.call_args.args[0])
                self.assertIs(popen.call_args.kwargs["stdin"], __import__("subprocess").PIPE)
                self.assertEqual(app.diagnostic_console_messages.qsize(), 2)
                thread_class.return_value.start.assert_called_once_with()
                self.assertTrue(app.open_diagnostic_console())
                popen.assert_called_once()
                app._queue_diagnostic_console_line("later event")
                self.assertEqual(app.diagnostic_console_messages.qsize(), 3)
        app._log_diagnostic.assert_called_once_with("Separate diagnostic console opened on request.")

    def test_new_lasso_uses_console_instead_of_the_diagnostics_page(self):
        app = object.__new__(ScreenAnswerApp)
        app.diagnostics_enabled = True
        app.lasso_multi_provider_mode = True

        app.show_diagnostics()

        self.assertFalse(diagnostics_page_available((), "Lasso.exe"))
        self.assertFalse(diagnostics_page_available((), "LassoWin7.exe"))

    def test_diagnostic_console_writer_sends_one_line_at_a_time(self):
        app = object.__new__(ScreenAnswerApp)
        app.diagnostic_console_lock = __import__("threading").RLock()
        process = MagicMock()
        process.poll.side_effect = [None, 1]
        process.stdin = MagicMock()
        app.diagnostic_console_process = process
        messages = queue.Queue()
        messages.put("diagnostic event")

        app._diagnostic_console_writer(process, messages)

        process.stdin.write.assert_called_once_with("diagnostic event\n")
        process.stdin.flush.assert_called_once_with()
        process.stdin.close.assert_called_once_with()
        self.assertIsNone(app.diagnostic_console_process)

    def test_diagnostic_console_child_preserves_parent_stdin_pipe(self):
        import io
        from types import SimpleNamespace

        calls = []
        kernel32 = MagicMock()
        kernel32.GetStdHandle.side_effect = lambda handle: calls.append("get-stdin") or 12345
        kernel32.AllocConsole.side_effect = lambda: calls.append("alloc-console") or 1
        input_stream = io.StringIO("diagnostic event\\n")
        output_stream = MagicMock()
        msvcrt = SimpleNamespace(
            open_osfhandle=lambda handle, flags: calls.append(("pipe-handle", handle)) or 77
        )

        with patch("answer_tray.os.name", "nt"):
            with patch("answer_tray.ctypes.WinDLL", return_value=kernel32, create=True):
                with patch.dict("sys.modules", {"msvcrt": msvcrt}):
                    with patch("answer_tray.os.fdopen", return_value=input_stream) as fdopen:
                        with patch("builtins.open", return_value=output_stream):
                            self.assertEqual(_run_diagnostic_console_child(), 0)

        self.assertLess(calls.index("get-stdin"), calls.index("alloc-console"))
        self.assertIn(("pipe-handle", 12345), calls)
        fdopen.assert_called_once()
        self.assertTrue(any("diagnostic event\\n" in call.args[0] for call in output_stream.write.call_args_list))

    def test_tray_menu_can_open_console_and_child_cli_does_not_start_tray_app(self):
        class Point(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        tray = object.__new__(WindowsTray)
        tray.settings_enabled = False
        tray.lasso1_mode = True
        tray.diagnostics_enabled = True
        tray.diagnostic_console_enabled = True
        tray.events = MagicMock()
        tray._user32 = MagicMock()
        tray._user32.CreatePopupMenu.return_value = 1
        tray._user32.TrackPopupMenu.return_value = 108
        WindowsTray._show_context_menu(
            tray,
            1,
            Point,
            101,
            102,
            103,
            104,
            105,
            107,
            106,
            0,
            0x0800,
            0x0100,
            0x0002,
            0,
            108,
        )
        labels = [
            call.args[3]
            for call in tray._user32.AppendMenuW.call_args_list
            if call.args[3]
        ]
        self.assertIn("Open diagnostic console", labels)
        self.assertNotIn("Show diagnostics", labels)
        tray.events.put.assert_called_once_with(("open_diagnostic_console",))

        with patch("sys.argv", ["Lasso.exe", "--diagnostic-console-child"]):
            with patch("answer_tray._run_diagnostic_console_child", return_value=0) as child:
                self.assertEqual(main(), 0)
                child.assert_called_once_with()

    def test_packaged_windows11_and_windows7_build_checks(self):
        lasso_overrides = {
            "LASSO1_MODE": True,
            "LASSO_MULTI_PROVIDER_MODE": True,
            "LASSO_OPENROUTER_ONLY_MODE": False,
            "LASSOV7_MODE": False,
            "APP_NAME": "Lasso",
            "APP_DEFAULT_PROVIDER": "apinex",
            "PROVIDER_LABELS": {"apinex": "APInex", "openrouter": "OpenRouter"},
            "API_KEY_ENV_VARS": {"apinex": "APINEX_API_KEY", "openrouter": "OPENROUTER_API_KEY"},
            "DEFAULT_MODELS": {"apinex": DEFAULT_APINEX_MODEL, "openrouter": DEFAULT_OPENROUTER_MODEL},
        }
        with patch.multiple("answer_tray", **lasso_overrides):
            with patch("answer_tray.sys.version_info", (3, 11, 9, "final", 0)):
                with patch("answer_tray.struct.calcsize", return_value=8):
                    with patch("sys.argv", ["Lasso.exe", "--check-lasso-build"]):
                        self.assertEqual(main(), 0)

        lasso7_overrides = dict(lasso_overrides)
        lasso7_overrides["LASSOV7_MODE"] = True
        with patch.multiple("answer_tray", **lasso7_overrides):
            with patch("answer_tray.sys.version_info", (3, 8, 10, "final", 0)):
                with patch("answer_tray.struct.calcsize", return_value=4):
                    with patch("sys.argv", ["LassoWin7.exe", "--check-lassowin7-build"]):
                        self.assertEqual(main(), 0)


class StandardSettingsTests(unittest.TestCase):
    def test_switching_to_gemini_updates_key_model_and_data_consent(self):
        app = object.__new__(ScreenAnswerApp)
        app.form_provider = "apinex"
        app.form_ocr_backend = "provider"
        app.api_keys = {"apinex": "apinex-key", "gemini": ""}
        app.models = {"apinex": DEFAULT_APINEX_MODEL, "gemini": DEFAULT_GEMINI_MODEL}
        app.api_key_var = MagicMock()
        app.api_key_var.get.return_value = "apinex-key"
        app.model_var = MagicMock()
        app.model_var.get.return_value = DEFAULT_APINEX_MODEL
        app.api_key_label = MagicMock()
        app.api_entry = MagicMock()
        app.privacy_var = MagicMock()
        app.privacy_checkbutton = MagicMock()
        app._log_diagnostic = MagicMock()

        app._provider_changed("Google Gemini")

        self.assertEqual(app.form_provider, "gemini")
        self.assertEqual(app.api_keys["apinex"], "apinex-key")
        app.api_key_var.set.assert_called_once_with("")
        app.api_entry.configure.assert_called_once_with(state="normal")
        app.api_key_label.configure.assert_called_once_with(text="Google Gemini API key:")
        app.model_var.set.assert_called_once_with(DEFAULT_GEMINI_MODEL)
        app.privacy_var.set.assert_called_once_with(False)
        consent = app.privacy_checkbutton.configure.call_args.kwargs["text"]
        self.assertIn("directly to Google's Gemini API", consent)
        self.assertIn("billing", consent)

    def test_switching_to_ollama_disables_key_entry_and_resets_consent(self):
        app = object.__new__(ScreenAnswerApp)
        app.form_provider = "apinex"
        app.form_ocr_backend = "provider"
        app.api_keys = {"apinex": "apinex-key", "ollama": "stale-key"}
        app.models = {"apinex": DEFAULT_APINEX_MODEL, "ollama": DEFAULT_OLLAMA_MODEL}
        app.api_key_var = MagicMock()
        app.api_key_var.get.return_value = "apinex-key"
        app.model_var = MagicMock()
        app.model_var.get.return_value = DEFAULT_APINEX_MODEL
        app.api_key_label = MagicMock()
        app.api_entry = MagicMock()
        app.privacy_var = MagicMock()
        app.privacy_checkbutton = MagicMock()
        app._log_diagnostic = MagicMock()

        app._provider_changed("Ollama (local)")

        self.assertEqual(app.form_provider, "ollama")
        self.assertEqual(app.api_keys["ollama"], "")
        app.api_key_var.set.assert_called_once_with("")
        app.api_entry.configure.assert_called_once_with(state="disabled")
        app.api_key_label.configure.assert_called_once_with(
            text="Ollama local server — no API key required (127.0.0.1:11434):"
        )
        app.model_var.set.assert_called_once_with(DEFAULT_OLLAMA_MODEL)
        app.privacy_var.set.assert_called_once_with(False)

    def test_ollama_settings_save_without_key_and_close(self):
        app = object.__new__(ScreenAnswerApp)
        app.lasso1_mode = False
        app.form_provider = "ollama"
        app.form_ocr_backend = "provider"
        app.provider = "apinex"
        app.api_key = ""
        app.api_key_source = "not configured"
        app.api_keys = {"ollama": ""}
        app.api_key_sources = {}
        app.models = {"ollama": DEFAULT_OLLAMA_MODEL}
        app.privacy_var = MagicMock()
        app.privacy_var.get.return_value = True
        app.model_var = MagicMock()
        app.model_var.get.return_value = DEFAULT_OLLAMA_MODEL
        app.portable_var = MagicMock()
        app.portable_var.get.return_value = False
        app._config_has_key = False
        app.status_var = MagicMock()
        app.tray = MagicMock()
        app.hide_window = MagicMock()
        app.show_window = MagicMock()
        app._show_error = MagicMock()
        app._log_diagnostic = MagicMock()

        self.assertTrue(app.save_settings())

        self.assertEqual(app.provider, "ollama")
        self.assertEqual(app.model, DEFAULT_OLLAMA_MODEL)
        self.assertEqual(app.api_key, "")
        self.assertEqual(app.api_key_source, "local Ollama server (no API key required)")
        self.assertTrue(app.privacy_acknowledged)
        app.hide_window.assert_called_once_with()
        app.show_window.assert_not_called()
        app._show_error.assert_not_called()


class Pix2TextOCRTests(unittest.TestCase):
    def test_recognizes_text_formula_from_in_memory_png_and_logs_only_when_enabled(self):
        source_image = MagicMock()
        source_image.__enter__.return_value = source_image
        rgb_image = MagicMock()
        source_image.convert.return_value = rgb_image
        engine = MagicMock()
        markdown = "Question: $x^2 + 1 = 0$\nA. 1\nB. 2"
        engine.recognize_text_formula.return_value = markdown
        pillow_module = types.ModuleType("PIL")
        pillow_module.Image = types.SimpleNamespace(open=MagicMock(return_value=source_image))
        diagnostics = []
        png = b"private screenshot bytes"

        with patch.dict("sys.modules", {"PIL": pillow_module}):
            with patch("answer_tray._get_pix2text_engine", return_value=engine):
                result = run_pix2text_ocr(png, diagnostic=diagnostics.append)

        self.assertEqual(result, markdown)
        engine.recognize_text_formula.assert_called_once_with(rgb_image, return_text=True)
        self.assertEqual(pillow_module.Image.open.call_args.args[0].getvalue(), png)
        self.assertTrue(any("Pix2Text OCR Markdown (diagnostic-only" in line for line in diagnostics))
        self.assertTrue(any(markdown in line for line in diagnostics))
        self.assertTrue(any("finished in" in line for line in diagnostics))
        rgb_image.close.assert_called_once_with()

    def test_bundle_import_check_detects_the_pix2text_api_without_loading_weights(self):
        class FakePix2Text:
            @staticmethod
            def from_config(**kwargs):
                return None

            @staticmethod
            def recognize_text_formula(*args, **kwargs):
                return ""

        pix2text_module = types.ModuleType("pix2text")
        pix2text_module.Pix2Text = FakePix2Text
        with patch.dict("sys.modules", {"pix2text": pix2text_module}):
            self.assertTrue(pix2text_bundle_importable())

        with patch.dict("sys.modules", {"pix2text": None}):
            self.assertFalse(pix2text_bundle_importable())


class ParseOptionTests(unittest.TestCase):
    def test_accepts_single_digit(self):
        for option in range(1, 5):
            with self.subTest(option=option):
                self.assertEqual(parse_option(str(option)), option)

    def test_accepts_short_unambiguous_variants_and_lettered_choices(self):
        self.assertEqual(parse_option(" Option 2 "), 2)
        self.assertEqual(parse_option("Answer: 4."), 4)
        self.assertEqual(parse_option("option 3)"), 3)
        self.assertEqual(parse_option("Answer: B"), 2)
        self.assertEqual(parse_option("D"), 4)

    def test_extracts_explicit_final_answer_after_reasoning(self):
        response = (
            "TRANSCRIPTION: Find the integral.\n"
            "SOLUTION: Use substitution; 1 + 2 = 3 and check the sign.\n"
            "ANSWER: C"
        )
        self.assertEqual(parse_option(response), 3)
        self.assertEqual(parse_option("Work says answer: 1\nFinal answer: D"), 4)

    def test_neutral_for_no_answer_or_ambiguous_response(self):
        values = (
            "",
            "0",
            "5",
            "Option 1 or 2",
            "The answer is 3 because…",
            "maybe 4",
            "Calculation uses option 2 but gives no final label.",
            "FINAL ANSWER: 2\nFINAL ANSWER: 3",
            "ANSWER: 0",
        )
        for text in values:
            with self.subTest(text=text):
                self.assertIsNone(parse_option(text))

    def test_extracts_chat_content_without_exposing_separate_reasoning_fields(self):
        payload = {
            "choices": [
                {
                    "message": {
                        "content": "ANSWER: B",
                        "reasoning_content": "private chain of thought",
                    }
                }
            ]
        }
        self.assertEqual(_extract_mistral_text(payload), "ANSWER: B")
        self.assertEqual(_extract_mistral_text({"choices": []}), "")


class APInexRequestTests(unittest.TestCase):
    def test_sends_free_vision_request_with_base64_image_and_no_tools(self):
        image_bytes = b"synthetic screenshot bytes"
        final_text = (
            "TRANSCRIPTION: 1 + 1; choices A=1, B=2, C=3, D=4.\n"
            "SOLUTION: 1 + 1 = 2, so the second choice matches.\n"
            "ANSWER: B"
        )
        captured = []
        diagnostics = []
        response_payload = {
            "id": "apinex-request-1",
            "model": DEFAULT_APINEX_MODEL,
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": final_text,
                        "reasoning_content": "hidden reasoning must not be returned or logged",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 70,
                "total_tokens": 190,
                "cost_tokens": 0,
            },
        }

        class FakeResponse:
            status = 200
            headers = {"x-ratelimit-remaining": "4"}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(response_payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            captured.append(
                {
                    "url": request.full_url,
                    "authorization": request.get_header("Authorization"),
                    "body": json.loads(request.data.decode("utf-8")),
                    "timeout": timeout,
                }
            )
            return FakeResponse()

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            option, response_text = ask_apinex(
                "apinex-test-key",
                DEFAULT_APINEX_MODEL,
                image_bytes,
                diagnostic=diagnostics.append,
            )

        self.assertEqual(option, 2)
        self.assertEqual(response_text, final_text)
        self.assertEqual(len(captured), 1)
        request = captured[0]
        self.assertEqual(request["url"], APINEX_ENDPOINT)
        self.assertEqual(request["authorization"], "Bearer apinex-test-key")
        self.assertEqual(request["timeout"], 120)
        body = request["body"]
        self.assertEqual(body["model"], DEFAULT_APINEX_MODEL)
        self.assertEqual(body["max_tokens"], 2048)
        self.assertEqual(body["reasoning_effort"], "medium")
        self.assertNotIn("tools", body)
        self.assertNotIn("plugins", body)
        self.assertIn("Do not use live web search", body["messages"][0]["content"])
        content = body["messages"][1]["content"]
        self.assertEqual(content[1]["type"], "image_url")
        self.assertEqual(
            content[1]["image_url"]["url"],
            "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii"),
        )
        self.assertTrue(any("prompt_tokens=120" in line for line in diagnostics))
        self.assertFalse(any("hidden reasoning" in line for line in diagnostics))
        self.assertFalse(any("apinex-test-key" in line for line in diagnostics))

    def test_free_gpt_6_luna_alternative_is_allowlisted_and_receives_image(self):
        model = "free/gpt-6-luna"
        image_bytes = b"synthetic screenshot for GPT-6 Luna"
        captured = []

        class FakeResponse:
            status = 200
            headers = {}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(
                    {"choices": [{"message": {"content": "ANSWER: A"}}]}
                ).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            captured.append(
                {
                    "url": request.full_url,
                    "body": json.loads(request.data.decode("utf-8")),
                    "timeout": timeout,
                }
            )
            return FakeResponse()

        self.assertTrue(valid_model_name("apinex", model))
        self.assertIn(model, APINEX_FREE_VISION_MODELS)
        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            option, _ = ask_apinex("test-key", model, image_bytes)

        self.assertEqual(option, 1)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["url"], APINEX_ENDPOINT)
        self.assertEqual(captured[0]["timeout"], 120)
        body = captured[0]["body"]
        self.assertEqual(body["model"], model)
        image_part = body["messages"][1]["content"][1]
        self.assertEqual(image_part["type"], "image_url")
        self.assertEqual(
            image_part["image_url"]["url"],
            "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii"),
        )

    def test_local_ocr_is_context_and_only_one_apinex_request_is_made(self):
        calls = []
        transcript = "Question: x + 1 = 3\nA. 1\nB. 2"

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps({"choices": [{"message": {"content": "ANSWER: B"}}]}).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            calls.append((request.full_url, json.loads(request.data.decode("utf-8"))))
            return FakeResponse()

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            option, _ = ask_apinex(
                "key", DEFAULT_APINEX_MODEL, b"original screenshot", ocr_markdown=transcript
            )

        self.assertEqual(option, 2)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], APINEX_ENDPOINT)
        text_part, image_part = calls[0][1]["messages"][1]["content"]
        self.assertIn(transcript, text_part["text"])
        self.assertEqual(image_part["type"], "image_url")

    def test_retries_429_and_redacts_api_key_in_diagnostics(self):
        api_key = "apinex-secret-key"
        attempts = []
        diagnostics = []

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps({"choices": [{"message": {"content": "ANSWER: C"}}]}).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            attempts.append(request.full_url)
            if len(attempts) == 1:
                payload = {"error": {"message": "rate limit: " + api_key}}
                raise urllib.error.HTTPError(
                    request.full_url,
                    429,
                    "Too Many Requests",
                    {"Retry-After": "2", "X-RateLimit-Remaining": "0"},
                    io.BytesIO(json.dumps(payload).encode("utf-8")),
                )
            return FakeResponse()

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            with patch("answer_tray.time.sleep") as sleep:
                option, _ = ask_apinex(api_key, DEFAULT_APINEX_MODEL, b"image", diagnostics.append)

        self.assertEqual(option, 3)
        self.assertEqual(attempts, [APINEX_ENDPOINT, APINEX_ENDPOINT])
        sleep.assert_called_once_with(2.0)
        self.assertTrue(any("Retry-After=2" in line for line in diagnostics))
        self.assertTrue(any("[REDACTED API KEY]" in line for line in diagnostics))
        self.assertFalse(any(api_key in line for line in diagnostics))

    def test_rejects_non_allowlisted_or_paid_model_before_network_access(self):
        self.assertTrue(valid_model_name("apinex", DEFAULT_APINEX_MODEL))
        self.assertIn(DEFAULT_APINEX_MODEL, APINEX_FREE_VISION_MODELS)
        self.assertFalse(valid_model_name("apinex", "gemini-3.8-flash"))
        self.assertFalse(valid_model_name("apinex", "paid/gemini-3.8-flash"))
        with patch("answer_tray.urllib.request.urlopen") as urlopen:
            with self.assertRaisesRegex(RuntimeError, "curated free vision models"):
                ask_apinex("key", "paid/gemini-3.8-flash", b"image")
        urlopen.assert_not_called()


class OllamaRequestTests(unittest.TestCase):
    def test_sends_raw_base64_image_to_loopback_without_api_key_or_tools(self):
        image_bytes = b"local synthetic screenshot"
        final_text = "TRANSCRIPTION: 2 + 2.\nSOLUTION: It equals 4.\nANSWER: D"
        captured = []
        diagnostics = []
        response_payload = {
            "model": DEFAULT_OLLAMA_MODEL,
            "message": {
                "role": "assistant",
                "content": final_text,
                "thinking": "private internal reasoning",
            },
            "done": True,
            "prompt_eval_count": 120,
            "eval_count": 70,
            "total_duration": 123456,
        }

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(response_payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            captured.append(
                {
                    "url": request.full_url,
                    "authorization": request.get_header("Authorization"),
                    "body": json.loads(request.data.decode("utf-8")),
                    "timeout": timeout,
                }
            )
            return FakeResponse()

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            option, response_text = ask_ollama(
                DEFAULT_OLLAMA_MODEL,
                image_bytes,
                diagnostic=diagnostics.append,
            )

        self.assertEqual(option, 4)
        self.assertEqual(response_text, final_text)
        self.assertEqual(len(captured), 1)
        request = captured[0]
        self.assertEqual(request["url"], OLLAMA_ENDPOINT)
        self.assertIsNone(request["authorization"])
        self.assertEqual(request["timeout"], 300)
        body = request["body"]
        self.assertEqual(body["model"], DEFAULT_OLLAMA_MODEL)
        self.assertIs(body["stream"], False)
        self.assertEqual(body["options"]["temperature"], 0)
        self.assertEqual(body["options"]["num_predict"], 2048)
        self.assertNotIn("tools", body)
        self.assertIn("Do not use live web search", body["messages"][0]["content"])
        self.assertEqual(
            body["messages"][1]["images"],
            [base64.b64encode(image_bytes).decode("ascii")],
        )
        self.assertNotIn("data:image/png", body["messages"][1]["images"][0])
        self.assertTrue(any("prompt_eval_count=120" in line for line in diagnostics))
        self.assertFalse(any("private internal reasoning" in line for line in diagnostics))

    def test_local_ollama_404_explains_how_to_pull_model(self):
        error_payload = {"error": "model 'qwen3-vl:8b' not found"}

        def fake_urlopen(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url,
                404,
                "Not Found",
                {},
                io.BytesIO(json.dumps(error_payload).encode("utf-8")),
            )

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaisesRegex(RuntimeError, "ollama pull qwen3-vl:8b"):
                ask_ollama(DEFAULT_OLLAMA_MODEL, b"image")

    def test_local_ollama_connection_failure_is_clear(self):
        with patch(
            "answer_tray.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Start Ollama"):
                ask_ollama(DEFAULT_OLLAMA_MODEL, b"image")


class ProviderRegistryTests(unittest.TestCase):
    def test_standard_app_exposes_direct_gemini_while_lasso_stays_restricted(self):
        providers = provider_labels_for_executable("ScreenAnswer.exe")
        self.assertEqual(
            providers,
            {
                "apinex": "APInex",
                "gemini": "Google Gemini",
                "ollama": "Ollama (local)",
                "mistral": "Mistral",
                "openrouter": "OpenRouter",
            },
        )
        self.assertNotIn("groq", providers)
        self.assertNotIn("gemini", provider_labels_for_executable("Lasso.exe"))
        self.assertEqual(
            API_KEY_ENV_VARS,
            {
                "apinex": "APINEX_API_KEY",
                "gemini": "GEMINI_API_KEY",
                "mistral": "MISTRAL_API_KEY",
                "openrouter": "OPENROUTER_API_KEY",
            },
        )
        self.assertTrue(valid_model_name("gemini", DEFAULT_GEMINI_MODEL))
        self.assertFalse(valid_model_name("gemini", "models/gemini-3.8-flash?key=bad"))
        self.assertEqual(default_provider_for_executable("ScreenAnswer.exe"), "apinex")
        self.assertEqual(default_provider_for_executable("ScreenAnswer-APInex.exe"), "apinex")
        self.assertEqual(default_provider_for_executable("ScreenAnswer-Ollama.exe"), "ollama")
        self.assertFalse(provider_requires_api_key("ollama"))
        self.assertTrue(provider_requires_api_key("apinex"))
        self.assertTrue(provider_requires_api_key("gemini"))
        self.assertEqual(
            resolve_api_key("gemini", {}, {"GEMINI_API_KEY": "gemini-env-key"}),
            ("gemini-env-key", "environment variable"),
        )
        self.assertEqual(
            resolve_api_key("gemini", {}, {"GOOGLE_API_KEY": "google-env-key"}),
            ("google-env-key", "environment variable (GOOGLE_API_KEY)"),
        )
        self.assertEqual(
            resolve_api_key("ollama", {"ollama": "must-be-ignored"}, {"OLLAMA_API_KEY": "ignored"}),
            ("", "local Ollama server (no API key required)"),
        )
        self.assertEqual(
            provider_labels_for_executable("LassoV2.exe"),
            {"openrouter": "OpenRouter"},
        )

    def test_build_smoke_check_covers_new_providers(self):
        with patch("sys.argv", ["ScreenAnswer-Diagnostic.exe", "--check-apinex-ollama"]):
            self.assertEqual(main(), 0)


class OtteraryVariantTests(unittest.TestCase):
    def test_builds_are_isolated_to_gemini_and_openrouter(self):
        expected = {"openrouter": "OpenRouter", "gemini": "Google Gemini"}
        for executable_name, config_directory in (
            ("Otterary.exe", OTTERARY_CONFIG_DIRECTORY),
            ("OtteraryWin7.exe", OTTERARY_WIN7_CONFIG_DIRECTORY),
        ):
            self.assertTrue(is_otterary_executable(executable_name))
            self.assertEqual(provider_labels_for_executable(executable_name), expected)
            self.assertEqual(default_provider_for_executable(executable_name), "openrouter")
            self.assertEqual(
                otterary_config_directory_for_executable(executable_name), config_directory
            )
            self.assertEqual(
                self_destruct_config_directory_for_executable(executable_name), config_directory
            )
            self.assertTrue(diagnostic_console_available_for_executable(executable_name))
            self.assertFalse(diagnostics_page_available((), executable_name))
            self.assertFalse(diagnostics_mode_enabled(("--diagnostics",), executable_name))
            self.assertIn("Ctrl+Alt+O", hotkey_specs_for_variant(True)[-1][1])
            self.assertFalse(is_lasso1_executable(executable_name))
            self.assertFalse(is_lasso_multi_provider_executable(executable_name))
        self.assertFalse(is_otterary_win7_executable("Otterary.exe"))
        self.assertTrue(is_otterary_win7_executable("OtteraryWin7.exe"))
        self.assertFalse(is_otterary_executable("Lasso.exe"))

    def test_first_run_configs_are_separate_blank_and_consent_off(self):
        with tempfile.TemporaryDirectory() as directory:
            expected_paths = {
                "Otterary.exe": os.path.join(directory, "Otterary", "config.json"),
                "OtteraryWin7.exe": os.path.join(directory, "OtteraryWin7", "config.json"),
            }
            for executable_name, expected_path in expected_paths.items():
                path = otterary_config_path(directory, executable_name)
                self.assertEqual(path, expected_path)
                self.assertTrue(ensure_otterary_config(path))
                with open(path, "r", encoding="utf-8") as config_file:
                    raw_config = json.load(config_file)
                self.assertEqual(raw_config, otterary_config_template())
                self.assertEqual(raw_config["api_keys"], {"openrouter": "", "gemini": ""})
                self.assertIs(raw_config["allow_screenshot_uploads"], False)
                self.assertNotIn("ocr_backend", raw_config)
                self.assertNotIn("OCR", json.dumps(raw_config))
                self.assertEqual(load_otterary_config(path), otterary_config_template())
            self.assertNotEqual(expected_paths["Otterary.exe"], expected_paths["OtteraryWin7.exe"])

    def test_saved_provider_and_models_ignore_environment_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = otterary_config_path(directory, "Otterary.exe")
            ensure_otterary_config(path)
            keys = {"openrouter": "openrouter-saved", "gemini": "gemini-saved"}
            models = {
                "openrouter": DEFAULT_OPENROUTER_MODEL,
                "gemini": DEFAULT_GEMINI_MODEL,
            }
            save_otterary_config(path, "gemini", keys, models, True)
            loaded = load_otterary_config(path)
            self.assertEqual(loaded["provider"], "gemini")
            self.assertEqual(loaded["api_keys"], keys)
            self.assertEqual(loaded["models"], models)
            self.assertIs(loaded["allow_screenshot_uploads"], True)
            self.assertEqual(
                resolve_api_key(
                    "gemini",
                    loaded["api_keys"],
                    {"GEMINI_API_KEY": "environment-key"},
                    lasso1_mode=True,
                    config_label="Otterary",
                ),
                ("gemini-saved", "Otterary config file"),
            )
            with self.assertRaisesRegex(ValueError, "API key is required"):
                save_otterary_config(path, "openrouter", {"openrouter": ""}, models, True)
            with self.assertRaisesRegex(ValueError, "valid OpenRouter model"):
                save_otterary_config(
                    path,
                    "openrouter",
                    {"openrouter": "openrouter-key"},
                    {"openrouter": "openai/gpt-4o", "gemini": DEFAULT_GEMINI_MODEL},
                    True,
                )

    def test_first_run_opens_settings_but_not_console_and_ignores_environment_keys(self):
        class FakeStringVar:
            def __init__(self, value=""):
                self.value = value

            def get(self):
                return self.value

            def set(self, value):
                self.value = value

        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = otterary_config_path(directory, "Otterary.exe")
            root = MagicMock()
            root.after = MagicMock()
            tray = MagicMock()
            tkinter_module = types.SimpleNamespace(StringVar=FakeStringVar)
            overrides = {
                "OTTERARY_MODE": True,
                "OTTERARY_WIN7_MODE": False,
                "LASSO1_MODE": False,
                "LASSO_MULTI_PROVIDER_MODE": False,
                "LASSO_OPENROUTER_ONLY_MODE": False,
                "LASSOV7_MODE": False,
                "APP_NAME": "Otterary",
                "APP_VERSION": "1.0.0",
                "APP_DEFAULT_PROVIDER": "openrouter",
                "PROVIDER_LABELS": {"openrouter": "OpenRouter", "gemini": "Google Gemini"},
                "API_KEY_ENV_VARS": {
                    "openrouter": "OPENROUTER_API_KEY",
                    "gemini": "GEMINI_API_KEY",
                },
                "DEFAULT_MODELS": {
                    "openrouter": DEFAULT_OPENROUTER_MODEL,
                    "gemini": DEFAULT_GEMINI_MODEL,
                },
            }
            with patch.multiple("answer_tray", **overrides):
                with patch("answer_tray.portable_config_path", return_value=path):
                    with patch("answer_tray.diagnostics_mode_enabled", return_value=False):
                        with patch("answer_tray.WindowsTray", return_value=tray) as tray_class:
                            with patch.object(
                                ScreenAnswerApp, "_build_otterary_window"
                            ) as build_window:
                                with patch.dict("sys.modules", {"tkinter": tkinter_module}):
                                    with patch.dict(
                                        os.environ,
                                        {"GEMINI_API_KEY": "environment-key"},
                                    ):
                                        app = ScreenAnswerApp(root)

        self.assertEqual(app.provider, "openrouter")
        self.assertEqual(app.api_key, "")
        self.assertEqual(app.api_key_sources["gemini"], "not configured")
        self.assertEqual(app.ocr_backend, "provider")
        self.assertFalse(app.privacy_acknowledged)
        self.assertTrue(app.prompt_for_otterary_setup)
        self.assertFalse(app.diagnostics_auto_open)
        self.assertTrue(app.diagnostics_enabled)
        self.assertIsNone(app.diagnostic_console_process)
        build_window.assert_called_once_with()
        tray_class.assert_called_once()
        self.assertTrue(tray_class.call_args.kwargs["suppress_tray_feedback"])
        self.assertTrue(tray_class.call_args.kwargs["diagnostic_console_enabled"])
        self.assertEqual([call.args[0] for call in root.after.call_args_list], [100, 0])

    def test_otterary_ui_console_and_prompts_avoid_backend_wording(self):
        ui_source = inspect.getsource(ScreenAnswerApp._build_otterary_window)
        consent_source = inspect.getsource(ScreenAnswerApp._otterary_consent_text)
        self.assertNotIn("OCR", ui_source)
        self.assertNotIn("OCR", consent_source)
        self.assertNotIn("open_diagnostic_console", ui_source)
        self.assertNotIn("OCR", OTTERARY_SYSTEM_INSTRUCTION)
        self.assertFalse(diagnostics_page_available((), "Otterary.exe"))
        repo_root = os.path.dirname(os.path.dirname(__file__))
        with open(os.path.join(repo_root, "docs", "otterary.md"), "r", encoding="utf-8") as guide:
            guide_text = guide.read()
        with open(
            os.path.join(repo_root, ".github", "workflows", "windows-release.yml"),
            "r",
            encoding="utf-8",
        ) as workflow:
            workflow_text = workflow.read()
        otterary_release = workflow_text.split("  release-otterary:\n", 1)[1].split(
            "  release-lasso3:\n", 1
        )[0]
        self.assertNotIn("OCR", guide_text.upper())
        self.assertNotIn("OCR", otterary_release.upper())

    def test_packaged_windows11_and_windows7_smoke_checks(self):
        overrides = {
            "OTTERARY_MODE": True,
            "OTTERARY_WIN7_MODE": False,
            "APP_NAME": "Otterary",
            "APP_VERSION": "1.0.0",
            "APP_DEFAULT_PROVIDER": "openrouter",
            "PROVIDER_LABELS": {"openrouter": "OpenRouter", "gemini": "Google Gemini"},
            "API_KEY_ENV_VARS": {
                "openrouter": "OPENROUTER_API_KEY",
                "gemini": "GEMINI_API_KEY",
            },
            "DEFAULT_MODELS": {
                "openrouter": DEFAULT_OPENROUTER_MODEL,
                "gemini": DEFAULT_GEMINI_MODEL,
            },
        }
        with patch.multiple("answer_tray", **overrides):
            with patch("answer_tray.sys.version_info", (3, 11, 9, "final", 0)):
                with patch("answer_tray.struct.calcsize", return_value=8):
                    with patch("sys.argv", ["Otterary.exe", "--check-otterary-build"]):
                        self.assertEqual(main(), 0)

        win7_overrides = dict(overrides)
        win7_overrides["OTTERARY_WIN7_MODE"] = True
        with patch.multiple("answer_tray", **win7_overrides):
            with patch("answer_tray.sys.version_info", (3, 8, 10, "final", 0)):
                with patch("answer_tray.struct.calcsize", return_value=4):
                    with patch(
                        "sys.argv",
                        ["OtteraryWin7.exe", "--check-otterarywin7-build"],
                    ):
                        self.assertEqual(main(), 0)

    def test_otterary_console_is_explicit_and_its_intro_avoids_backend_wording(self):
        app = object.__new__(ScreenAnswerApp)
        app.lasso_multi_provider_mode = False
        app.otterary_mode = True
        app.diagnostics_enabled = True
        app.diagnostic_console_lock = MagicMock()
        app.diagnostic_console_process = None
        app.diagnostic_lines = ["OpenRouter request completed."]
        app._log_diagnostic = MagicMock()
        app.status_var = MagicMock()
        process = MagicMock()
        process.poll.return_value = None

        with patch("answer_tray.subprocess.Popen", return_value=process) as popen:
            with patch("answer_tray.threading.Thread") as thread_class:
                self.assertTrue(app.open_diagnostic_console())

        popen.assert_called_once()
        thread_class.assert_called_once()
        thread_class.return_value.start.assert_called_once_with()
        messages = []
        while not app.diagnostic_console_messages.empty():
            messages.append(app.diagnostic_console_messages.get_nowait())
        self.assertTrue(any("Console opened on request" in line for line in messages))
        self.assertTrue(any("OpenRouter request completed" in line for line in messages))
        self.assertFalse(any("OCR" in line.upper() for line in messages))

    def test_otterary_tray_menu_has_on_demand_console_and_self_delete(self):
        class Point(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        tray = object.__new__(WindowsTray)
        tray.settings_enabled = True
        tray.lasso1_mode = False
        tray.self_destruct_enabled = True
        tray.diagnostics_enabled = True
        tray.diagnostic_console_enabled = True
        tray.events = MagicMock()
        tray._user32 = MagicMock()
        tray._user32.CreatePopupMenu.return_value = 1
        tray._user32.TrackPopupMenu.return_value = 108
        with patch("answer_tray.APP_NAME", "Otterary"):
            WindowsTray._show_context_menu(
                tray,
                1,
                Point,
                101,
                102,
                103,
                104,
                105,
                107,
                106,
                0,
                0x0800,
                0x0100,
                0x0002,
                0,
                108,
            )
        labels = [
            call.args[3]
            for call in tray._user32.AppendMenuW.call_args_list
            if call.args[3]
        ]
        self.assertIn("Open Otterary", labels)
        self.assertIn("Open diagnostic console", labels)
        self.assertIn("Self-destruct Otterary…", labels)
        self.assertNotIn("Show diagnostics", labels)
        tray.events.put.assert_called_once_with(("open_diagnostic_console",))

    def test_otterary_silent_delete_uses_its_private_config_path_without_prompt(self):
        app = object.__new__(ScreenAnswerApp)
        app.lasso1_mode = False
        app.otterary_mode = True
        app.self_destruct_enabled = True
        app.config_path = os.path.join("profile", "Otterary", "config.json")
        app.tray = MagicMock()
        app.exit_app = MagicMock()
        app._log_diagnostic = MagicMock()
        with patch("answer_tray.ctypes.WinDLL", side_effect=AssertionError("unexpected prompt"), create=True):
            with patch("answer_tray.schedule_lasso1_self_cleanup", return_value=True) as cleanup:
                self.assertTrue(app.silent_delete())
        cleanup.assert_called_once_with(sys.executable, app.config_path)
        app.exit_app.assert_called_once_with()
        app.tray.show_balloon.assert_not_called()

    def test_otterary_tray_suppresses_tooltips_and_notifications_but_keeps_color(self):
        class NotifyIconData(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("hWnd", ctypes.c_void_p),
                ("uID", ctypes.c_uint),
                ("uFlags", ctypes.c_uint),
                ("uCallbackMessage", ctypes.c_uint),
                ("hIcon", ctypes.c_void_p),
                ("szTip", ctypes.c_wchar * 128),
                ("dwState", ctypes.c_uint),
                ("dwStateMask", ctypes.c_uint),
                ("szInfo", ctypes.c_wchar * 256),
                ("uTimeoutOrVersion", ctypes.c_uint),
                ("szInfoTitle", ctypes.c_wchar * 64),
                ("dwInfoFlags", ctypes.c_uint),
            ]

        tray = object.__new__(WindowsTray)
        tray.suppress_tray_feedback = True
        tray.hwnd = 1
        tray._nid = NotifyIconData()
        tray._nid_type = NotifyIconData
        tray._lock = MagicMock()
        tray._create_icon = MagicMock(return_value=17)
        tray._shell32 = MagicMock()
        tray.set_state((67, 160, 71), "Option 3")
        self.assertEqual(tray._nid.hIcon, 17)
        self.assertEqual(tray._nid.uFlags, 0x00000001 | 0x00000002)
        tray._shell32.Shell_NotifyIconW.reset_mock()
        tray.show_balloon("Otterary", "Answer 3")
        tray._shell32.Shell_NotifyIconW.assert_not_called()

    def test_requests_use_only_selected_provider_without_tools_or_auxiliary_text(self):
        gemini_payload = {
            "candidates": [{"content": {"parts": [{"text": "ANSWER: 2"}]}}]
        }
        with patch("answer_tray._gemini_post_json", return_value=gemini_payload) as post:
            option, _ = ask_gemini(
                "gemini-key",
                DEFAULT_GEMINI_MODEL,
                b"image",
                system_instruction=OTTERARY_SYSTEM_INSTRUCTION,
            )
        self.assertEqual(option, 2)
        gemini_body = post.call_args.args[2]
        self.assertNotIn("OCR", json.dumps(gemini_body))
        self.assertNotIn("tools", gemini_body)

        openrouter_payload = {
            "model": DEFAULT_OPENROUTER_MODEL,
            "choices": [{"message": {"content": "ANSWER: 1"}}],
        }
        diagnostics = []
        with patch("answer_tray._openrouter_post_json", return_value=openrouter_payload) as post:
            option, _ = ask_openrouter(
                "openrouter-key",
                DEFAULT_OPENROUTER_MODEL,
                b"image",
                diagnostic=diagnostics.append,
                system_instruction=OTTERARY_SYSTEM_INSTRUCTION,
                omit_ocr_diagnostics=True,
            )
        self.assertEqual(option, 1)
        openrouter_body = post.call_args.args[1]
        self.assertNotIn("OCR", json.dumps(openrouter_body))
        self.assertNotIn("tools", openrouter_body)
        self.assertFalse(any("OCR" in line for line in diagnostics))


class GeminiRequestTests(unittest.TestCase):
    def test_direct_gemini_sends_png_once_and_omits_thought_parts(self):
        image_bytes = b"direct Gemini screenshot"
        final_text = "TRANSCRIPTION: sample question.\nSOLUTION: the answer is C.\nANSWER: C"
        captured = []
        diagnostics = []
        response_payload = {
            "modelVersion": DEFAULT_GEMINI_MODEL,
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [
                            {"text": "private internal thought", "thought": True},
                            {"text": final_text},
                        ],
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 50,
                "candidatesTokenCount": 20,
                "totalTokenCount": 70,
            },
        }

        class FakeResponse:
            status = 200
            headers = {}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(response_payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            captured.append(
                {
                    "url": request.full_url,
                    "api_key": request.get_header("X-goog-api-key"),
                    "authorization": request.get_header("Authorization"),
                    "body": json.loads(request.data.decode("utf-8")),
                    "timeout": timeout,
                }
            )
            return FakeResponse()

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            option, response_text = ask_gemini(
                "private-gemini-key",
                DEFAULT_GEMINI_MODEL,
                image_bytes,
                diagnostic=diagnostics.append,
                ocr_markdown="OCR transcript example",
            )

        self.assertEqual(option, 3)
        self.assertEqual(response_text, final_text)
        self.assertEqual(len(captured), 1)
        request = captured[0]
        self.assertEqual(
            request["url"],
            GEMINI_API_BASE_URL + "/models/" + DEFAULT_GEMINI_MODEL + ":generateContent",
        )
        self.assertNotIn("?key=", request["url"])
        self.assertEqual(request["api_key"], "private-gemini-key")
        self.assertIsNone(request["authorization"])
        self.assertEqual(request["timeout"], 60)
        body = request["body"]
        self.assertIn("Do not use live web search", body["systemInstruction"]["parts"][0]["text"])
        self.assertIn("OCR transcript example", body["contents"][0]["parts"][0]["text"])
        self.assertEqual(
            body["contents"][0]["parts"][1]["inlineData"],
            {
                "mimeType": "image/png",
                "data": base64.b64encode(image_bytes).decode("ascii"),
            },
        )
        self.assertEqual(body["generationConfig"]["maxOutputTokens"], 2048)
        self.assertNotIn("tools", body)
        self.assertNotIn("googleSearch", body)
        self.assertFalse(any("private-gemini-key" in line for line in diagnostics))
        self.assertFalse(any("private internal thought" in line for line in diagnostics))
        self.assertTrue(any("total tokens=70" in line for line in diagnostics))

    def test_rejects_invalid_model_before_network_access(self):
        with patch("answer_tray.urllib.request.urlopen") as urlopen:
            with self.assertRaisesRegex(RuntimeError, "valid Google Gemini model"):
                ask_gemini("key", "free/gemini-3.8-flash", b"image")
        urlopen.assert_not_called()

    def test_rate_limit_429_is_not_retried(self):
        calls = []

        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "Too Many Requests",
                {},
                io.BytesIO(b'{"error":{"message":"quota exceeded"}}'),
            )

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            with patch("answer_tray.time.sleep") as sleep:
                with self.assertRaisesRegex(RuntimeError, "No automatic retry was sent"):
                    ask_gemini("key", DEFAULT_GEMINI_MODEL, b"image")
        self.assertEqual(len(calls), 1)
        sleep.assert_not_called()

    def test_retries_temporary_server_error_with_bounded_attempts(self):
        calls = []
        response_payload = {
            "candidates": [{"content": {"parts": [{"text": "ANSWER: A"}]}}]
        }

        class FakeResponse:
            status = 200
            headers = {}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(response_payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise urllib.error.HTTPError(request.full_url, 503, "Unavailable", {}, io.BytesIO(b""))
            return FakeResponse()

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            with patch("answer_tray.time.sleep") as sleep:
                option, _ = ask_gemini("key", DEFAULT_GEMINI_MODEL, b"image")
        self.assertEqual(option, 1)
        self.assertEqual(len(calls), 2)
        sleep.assert_called_once_with(1)


class MistralRequestTests(unittest.TestCase):
    def test_ocr_then_reasoned_vision_chat_without_search_tools(self):
        image_bytes = b"fake png bytes"
        markdown = "Question: compute 1 + 1.\nA. 1\nB. 2\nC. 3\nD. 4"
        final_text = (
            "TRANSCRIPTION: compute 1 + 1; choices A=1, B=2, C=3, D=4.\n"
            "SOLUTION: 1 + 1 = 2, so the second choice matches.\n"
            "ANSWER: B"
        )
        captured = []
        responses = {
            MISTRAL_OCR_ENDPOINT: {
                "model": MISTRAL_OCR_MODEL,
                "pages": [{"index": 0, "markdown": markdown}],
            },
            "https://api.mistral.ai/v1/chat/completions": {
                "id": "mistral-request-1",
                "model": DEFAULT_MISTRAL_MODEL,
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "thinking",
                                    "text": "hidden reasoning must not leak",
                                    "thinking": [{"type": "text", "text": "hidden reasoning"}],
                                },
                                {"type": "text", "text": final_text},
                            ],
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 900,
                    "completion_tokens": 400,
                    "total_tokens": 1300,
                },
            },
        }

        class FakeResponse:
            status = 200

            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(self.payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            captured.append(
                {
                    "url": request.full_url,
                    "authorization": request.get_header("Authorization"),
                    "body": json.loads(request.data.decode("utf-8")),
                    "timeout": timeout,
                }
            )
            return FakeResponse(responses[request.full_url])

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            option, response_text = ask_mistral(
                "mistral-test-key", DEFAULT_MISTRAL_MODEL, image_bytes
            )

        self.assertEqual(option, 2)
        self.assertEqual(response_text, final_text)
        self.assertNotIn("hidden reasoning", response_text)
        self.assertEqual(len(captured), 2)
        ocr_call, chat_call = captured
        self.assertEqual(ocr_call["url"], MISTRAL_OCR_ENDPOINT)
        self.assertEqual(ocr_call["authorization"], "Bearer mistral-test-key")
        self.assertEqual(ocr_call["timeout"], 60)
        self.assertEqual(ocr_call["body"]["model"], MISTRAL_OCR_MODEL)
        self.assertEqual(
            ocr_call["body"]["document"]["image_url"],
            "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii"),
        )
        self.assertEqual(chat_call["url"], "https://api.mistral.ai/v1/chat/completions")
        self.assertEqual(chat_call["timeout"], 60)
        self.assertEqual(chat_call["body"]["model"], DEFAULT_MISTRAL_MODEL)
        self.assertEqual(chat_call["body"]["reasoning_effort"], "high")
        self.assertEqual(chat_call["body"]["max_tokens"], 4096)
        self.assertNotIn("tools", chat_call["body"])
        content = chat_call["body"]["messages"][1]["content"]
        self.assertIn(markdown, content[0]["text"])
        self.assertEqual(content[1]["type"], "image_url")
        self.assertEqual(
            content[1]["image_url"],
            "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii"),
        )

    def test_local_pix2text_transcript_skips_mistral_ocr_request(self):
        calls = []
        captured_chat = {}
        markdown = "Question: $\\int_0^1 x^2 dx$\nA. 1/2\nB. 1/3"
        response_payload = {
            "choices": [{"message": {"role": "assistant", "content": "ANSWER: B"}}]
        }

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(response_payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            captured_chat["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        image_bytes = b"original screenshot"
        diagnostics = []
        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            option, _ = ask_mistral(
                "key",
                DEFAULT_MISTRAL_MODEL,
                image_bytes,
                diagnostic=diagnostics.append,
                local_ocr_markdown=markdown,
            )

        self.assertEqual(option, 2)
        self.assertEqual(calls, ["https://api.mistral.ai/v1/chat/completions"])
        content = captured_chat["body"]["messages"][1]["content"]
        self.assertIn(markdown, content[0]["text"])
        self.assertEqual(
            content[1]["image_url"],
            "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii"),
        )
        self.assertTrue(any("Skipping separate Mistral OCR request" in line for line in diagnostics))

    def test_ocr_extractor_returns_first_page_markdown(self):
        payload = {
            "pages": [
                {"markdown": "  integral\noptions  "},
                {"markdown": "second page"},
            ]
        }
        self.assertEqual(_extract_mistral_ocr_markdown(payload), "integral\noptions")
        self.assertEqual(_extract_mistral_ocr_markdown({"pages": []}), "")
        self.assertEqual(_extract_mistral_ocr_markdown({"pages": [{"text": "no markdown"}]}), "")

    def test_diagnostics_include_ocr_and_final_text_but_redact_key(self):
        secret = "mistral-secret-key"
        markdown = "Question contains " + secret + " and an integral."
        final_text = "TRANSCRIPTION: " + secret + "\nSOLUTION: compute carefully.\nANSWER: 2"
        diagnostic_lines = []
        responses = {
            MISTRAL_OCR_ENDPOINT: {"pages": [{"markdown": markdown}]},
            "https://api.mistral.ai/v1/chat/completions": {
                "choices": [{"message": {"role": "assistant", "content": final_text}}]
            },
        }

        class FakeResponse:
            status = 200

            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(self.payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            return FakeResponse(responses[request.full_url])

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            option, response_text = ask_mistral(
                secret,
                DEFAULT_MISTRAL_MODEL,
                b"image",
                diagnostic=diagnostic_lines.append,
            )

        self.assertEqual(option, 2)
        self.assertEqual(response_text, final_text)
        self.assertTrue(any("Mistral OCR pages[0].markdown" in line for line in diagnostic_lines))
        self.assertTrue(any("Question contains [REDACTED API KEY]" in line for line in diagnostic_lines))
        self.assertTrue(any("final response (diagnostic-only" in line for line in diagnostic_lines))
        self.assertTrue(any("ANSWER: 2" in line for line in diagnostic_lines))
        self.assertFalse(any(secret in line for line in diagnostic_lines))

    def test_ocr_failure_falls_back_to_original_image(self):
        calls = []
        diagnostic_lines = []
        chat_payload = {
            "choices": [
                {"message": {"role": "assistant", "content": "SOLUTION: read image.\nANSWER: 1"}}
            ]
        }

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(chat_payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            if request.full_url == MISTRAL_OCR_ENDPOINT:
                raise urllib.error.HTTPError(
                    request.full_url,
                    402,
                    "Payment Required",
                    None,
                    io.BytesIO(b'{"error":{"message":"OCR access unavailable"}}'),
                )
            return FakeResponse()

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            option, _ = ask_mistral(
                "key", DEFAULT_MISTRAL_MODEL, b"image", diagnostic=diagnostic_lines.append
            )

        self.assertEqual(option, 1)
        self.assertEqual(calls, [MISTRAL_OCR_ENDPOINT, "https://api.mistral.ai/v1/chat/completions"])
        self.assertTrue(
            any("continuing with direct screenshot vision input" in line for line in diagnostic_lines)
        )

    def test_retries_temporary_chat_error_after_ocr_succeeds(self):
        calls = []
        chat_attempts = [0]
        diagnostics = []
        responses = {
            MISTRAL_OCR_ENDPOINT: {"pages": [{"markdown": "Question and choices"}]},
            "https://api.mistral.ai/v1/chat/completions": {
                "choices": [{"message": {"role": "assistant", "content": "ANSWER: D"}}]
            },
        }

        class FakeResponse:
            status = 200

            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(self.payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            if request.full_url == MISTRAL_OCR_ENDPOINT:
                return FakeResponse(responses[request.full_url])
            chat_attempts[0] += 1
            if chat_attempts[0] == 1:
                raise urllib.error.HTTPError(
                    request.full_url,
                    503,
                    "Service Unavailable",
                    None,
                    io.BytesIO(b'{"message":"temporarily busy"}'),
                )
            return FakeResponse(responses[request.full_url])

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            with patch("answer_tray.time.sleep") as sleep:
                option, _ = ask_mistral(
                    "key", DEFAULT_MISTRAL_MODEL, b"image", diagnostic=diagnostics.append
                )

        self.assertEqual(option, 4)
        self.assertEqual(calls, [
            MISTRAL_OCR_ENDPOINT,
            "https://api.mistral.ai/v1/chat/completions",
            "https://api.mistral.ai/v1/chat/completions",
        ])
        sleep.assert_called_once_with(1)
        self.assertTrue(any("chat error detail: temporarily busy" in line for line in diagnostics))
        self.assertTrue(any("recognized option position 4" in line for line in diagnostics))


    def test_retries_mistral_429_using_retry_after_header(self):
        calls = []
        chat_attempts = [0]
        diagnostics = []
        ocr_payload = {"pages": [{"markdown": "one question"}]}
        chat_payload = {
            "choices": [{"message": {"role": "assistant", "content": "ANSWER: C"}}]
        }

        class FakeResponse:
            status = 200

            def __init__(self, payload):
                self.payload = payload
                self.headers = {"X-RateLimit-Remaining": "5"}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(self.payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            if request.full_url == MISTRAL_OCR_ENDPOINT:
                return FakeResponse(ocr_payload)
            chat_attempts[0] += 1
            if chat_attempts[0] == 1:
                raise urllib.error.HTTPError(
                    request.full_url,
                    429,
                    "Too Many Requests",
                    {"Retry-After": "3", "X-RateLimit-Remaining": "0"},
                    io.BytesIO(b'{"message":"rate limit exceeded"}'),
                )
            return FakeResponse(chat_payload)

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            with patch("answer_tray.time.sleep") as sleep:
                option, _ = ask_mistral(
                    "key", DEFAULT_MISTRAL_MODEL, b"image", diagnostic=diagnostics.append
                )

        self.assertEqual(option, 3)
        self.assertEqual(chat_attempts[0], 2)
        sleep.assert_called_once_with(3.0)
        self.assertTrue(any("Retry-After=3" in line for line in diagnostics))
        self.assertTrue(any("retrying in 3.0 second(s)" in line for line in diagnostics))
        self.assertEqual(len(calls), 3)

    def test_does_not_retry_before_a_long_retry_after_window(self):
        calls = []
        diagnostics = []
        ocr_payload = {"pages": [{"markdown": "one question"}]}

        class FakeResponse:
            status = 200

            def __init__(self, payload):
                self.payload = payload
                self.headers = {}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(self.payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            if request.full_url == MISTRAL_OCR_ENDPOINT:
                return FakeResponse(ocr_payload)
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "Too Many Requests",
                {"Retry-After": "60"},
                io.BytesIO(b'{"message":"rate limit exceeded"}'),
            )

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            with patch("answer_tray.time.sleep") as sleep:
                with self.assertRaisesRegex(RuntimeError, "rate-limited or reached its usage quota"):
                    ask_mistral(
                        "key", DEFAULT_MISTRAL_MODEL, b"image", diagnostic=diagnostics.append
                    )

        self.assertEqual(len(calls), 2)
        sleep.assert_not_called()
        self.assertTrue(
            any("longer than the 30-second automatic retry limit" in line for line in diagnostics)
        )


class OpenRouterRequestTests(unittest.TestCase):
    def test_direct_vision_request_uses_base64_image_without_search_or_ocr(self):
        image_bytes = b"fake OpenRouter screenshot"
        final_text = (
            "TRANSCRIPTION: compute 1 + 1; choices A=1, B=2, C=3, D=4.\n"
            "SOLUTION: 1 + 1 = 2, so the second choice matches.\n"
            "ANSWER: B"
        )
        captured = []
        diagnostics = []
        response_payload = {
            "id": "openrouter-request-1",
            "model": DEFAULT_OPENROUTER_MODEL,
            "provider": "Google AI Studio",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": final_text,
                        "reasoning": "hidden reasoning must not be returned or logged",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 70,
                "total_tokens": 190,
                "cost": 0.0,
            },
        }

        class FakeResponse:
            status = 200
            headers = {"X-RateLimit-Remaining": "5"}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(response_payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            captured.append(
                {
                    "url": request.full_url,
                    "authorization": request.get_header("Authorization"),
                    "body": json.loads(request.data.decode("utf-8")),
                    "timeout": timeout,
                }
            )
            return FakeResponse()

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            option, response_text = ask_openrouter(
                "openrouter-test-key",
                DEFAULT_OPENROUTER_MODEL,
                image_bytes,
                diagnostic=diagnostics.append,
            )

        self.assertEqual(option, 2)
        self.assertEqual(response_text, final_text)
        self.assertEqual(len(captured), 1)
        request = captured[0]
        self.assertEqual(request["url"], OPENROUTER_ENDPOINT)
        self.assertEqual(request["authorization"], "Bearer openrouter-test-key")
        self.assertEqual(request["timeout"], 60)
        body = request["body"]
        self.assertEqual(body["model"], DEFAULT_OPENROUTER_MODEL)
        self.assertEqual(body["max_tokens"], 4096)
        self.assertEqual(body["reasoning"], {"effort": "medium", "exclude": True})
        self.assertNotIn("tools", body)
        self.assertNotIn("plugins", body)
        self.assertIn("Do not use live web search", body["messages"][0]["content"])
        content = body["messages"][1]["content"]
        self.assertEqual(content[1]["type"], "image_url")
        self.assertEqual(
            content[1]["image_url"]["url"],
            "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii"),
        )
        self.assertTrue(any("no separate OCR API is used" in line for line in diagnostics))
        self.assertTrue(any("routed_provider=Google AI Studio" in line for line in diagnostics))
        self.assertTrue(any("request cost" in line for line in diagnostics))
        self.assertFalse(any("hidden reasoning" in line for line in diagnostics))
        self.assertFalse(any("openrouter-test-key" in line for line in diagnostics))

    def test_local_ocr_is_optional_context_and_no_second_api_is_called(self):
        calls = []
        transcript = "Question: x + 1 = 3\nA. 1\nB. 2"

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(
                    {"choices": [{"message": {"content": "ANSWER: B"}}]}
                ).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            calls.append((request.full_url, json.loads(request.data.decode("utf-8"))))
            return FakeResponse()

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            option, _ = ask_openrouter(
                "key", DEFAULT_OPENROUTER_MODEL, b"original screenshot", ocr_markdown=transcript
            )

        self.assertEqual(option, 2)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], OPENROUTER_ENDPOINT)
        text_part, image_part = calls[0][1]["messages"][1]["content"]
        self.assertIn(transcript, text_part["text"])
        self.assertEqual(image_part["type"], "image_url")

    def test_retries_rate_limit_and_redacts_api_key_in_diagnostics(self):
        api_key = "openrouter-secret-key"
        attempts = []
        diagnostics = []

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(
                    {"choices": [{"message": {"content": "ANSWER: C"}}]}
                ).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            attempts.append(request.full_url)
            if len(attempts) == 1:
                error_payload = {"error": {"code": 429, "message": "rate limit: " + api_key}}
                raise urllib.error.HTTPError(
                    request.full_url,
                    429,
                    "Too Many Requests",
                    {"Retry-After": "2", "X-RateLimit-Remaining": "0"},
                    io.BytesIO(json.dumps(error_payload).encode("utf-8")),
                )
            return FakeResponse()

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            with patch("answer_tray.time.sleep") as sleep:
                option, _ = ask_openrouter(
                    api_key, DEFAULT_OPENROUTER_MODEL, b"image", diagnostics.append
                )

        self.assertEqual(option, 3)
        self.assertEqual(attempts, [OPENROUTER_ENDPOINT, OPENROUTER_ENDPOINT])
        sleep.assert_called_once_with(2.0)
        self.assertTrue(any("Retry-After=2" in line for line in diagnostics))
        self.assertTrue(any("retrying in 2.0 second(s)" in line for line in diagnostics))
        self.assertTrue(any("[REDACTED API KEY]" in line for line in diagnostics))
        self.assertFalse(any(api_key in line for line in diagnostics))

    def test_rejects_paid_or_unapproved_model_before_any_network_request(self):
        self.assertTrue(valid_model_name("openrouter", DEFAULT_OPENROUTER_MODEL))
        self.assertFalse(valid_model_name("openrouter", "google/gemini-3.8-flash"))
        self.assertFalse(valid_model_name("openrouter", "openai/gpt-oss-120b:free"))
        self.assertFalse(valid_model_name("openrouter", "openrouter/free"))
        self.assertFalse(valid_model_name("openrouter", "google/model:online"))
        self.assertFalse(valid_model_name("openrouter", "model?bad"))
        with patch("answer_tray.urllib.request.urlopen") as urlopen:
            for rejected_model in (
                "google/gemini-3.8-flash",
                "openai/gpt-oss-120b:free",
                "openrouter/free",
                "google/model:online",
                "model?bad",
            ):
                with self.assertRaisesRegex(RuntimeError, "free vision allowlist"):
                    ask_openrouter("key", rejected_model, b"image")
        urlopen.assert_not_called()

    def test_packaged_diagnostic_smoke_check_recognizes_openrouter(self):
        with patch("sys.argv", ["ScreenAnswer-Diagnostic.exe", "--check-openrouter-support"]):
            self.assertEqual(main(), 0)

    def test_handles_inference_error_returned_inside_http_200_response(self):
        diagnostics = []
        response_payload = {
            "error": {
                "code": 503,
                "message": "No provider is currently available.",
                "metadata": {"error_type": "provider_unavailable"},
            }
        }

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
            with self.assertRaisesRegex(RuntimeError, "inference error"):
                ask_openrouter(
                    "key", DEFAULT_OPENROUTER_MODEL, b"image", diagnostics.append
                )

        self.assertTrue(any("provider_unavailable" in line for line in diagnostics))
        self.assertTrue(any("No provider is currently available" in line for line in diagnostics))


class PortableConfigTests(unittest.TestCase):
    def test_saves_and_loads_apinex_key_and_model_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "screen_answer_config.json")
            save_portable_config("example-key", DEFAULT_APINEX_MODEL, path)
            self.assertEqual(
                load_portable_config(path),
                {
                    "provider": "apinex",
                    "api_keys": {"apinex": "example-key"},
                    "models": {"apinex": DEFAULT_APINEX_MODEL},
                    "ocr_backend": "provider",
                },
            )

    def test_saves_supported_keys_models_and_ignores_retired_providers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "screen_answer_config.json")
            save_portable_config(
                path=path,
                provider="mistral",
                api_keys={
                    "gemini": "direct-gemini-key",
                    "apinex": "apinex-key",
                    "ollama": "must-not-be-saved",
                    "mistral": "mistral-key",
                    "groq": "retired-groq-key",
                    "openrouter": "openrouter-key",
                },
                models={
                    "gemini": "gemini-3.8-flash",
                    "apinex": DEFAULT_APINEX_MODEL,
                    "ollama": DEFAULT_OLLAMA_MODEL,
                    "mistral": "ministral-14b-2512",
                    "groq": "qwen/qwen3.8-27b",
                    "openrouter": DEFAULT_OPENROUTER_MODEL,
                },
                ocr_backend="pix2text",
            )
            self.assertEqual(
                load_portable_config(path),
                {
                    "provider": "mistral",
                    "api_keys": {
                        "apinex": "apinex-key",
                        "gemini": "direct-gemini-key",
                        "mistral": "mistral-key",
                        "openrouter": "openrouter-key",
                    },
                    "models": {
                        "apinex": DEFAULT_APINEX_MODEL,
                        "gemini": DEFAULT_GEMINI_MODEL,
                        "ollama": DEFAULT_OLLAMA_MODEL,
                        "mistral": DEFAULT_MISTRAL_MODEL,
                        "openrouter": DEFAULT_OPENROUTER_MODEL,
                    },
                    "ocr_backend": "pix2text",
                },
            )
            with open(path, "r", encoding="utf-8") as config_file:
                saved = json.load(config_file)
            self.assertEqual(saved["api_keys"]["gemini"], "direct-gemini-key")
            self.assertNotIn("groq", saved["api_keys"])
            self.assertNotIn("ollama", saved["api_keys"])
            self.assertEqual(saved["models"]["gemini"], DEFAULT_GEMINI_MODEL)
            self.assertNotIn("groq", saved["models"])

    def test_old_google_and_groq_credentials_are_scrubbed_not_reused_for_apinex(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "screen_answer_config.json")
            with open(path, "w", encoding="utf-8") as config_file:
                json.dump(
                    {
                        "provider": "google",
                        "api_keys": {
                            "google": "old-google-secret",
                            "groq": "old-groq-secret",
                            "mistral": "keep-mistral-key",
                            "openrouter": "keep-openrouter-key",
                        },
                        "models": {
                            "google": "gemini-3.8-flash",
                            "groq": "qwen/qwen3.8-27b",
                            "mistral": "ministral-14b-2512",
                            "openrouter": DEFAULT_OPENROUTER_MODEL,
                        },
                    },
                    config_file,
                )

            migrated = load_portable_config(path)
            self.assertEqual(migrated["provider"], "apinex")
            self.assertEqual(
                migrated["api_keys"],
                {"mistral": "keep-mistral-key", "openrouter": "keep-openrouter-key"},
            )
            self.assertNotIn("apinex", migrated["api_keys"])
            self.assertEqual(migrated["models"]["mistral"], DEFAULT_MISTRAL_MODEL)
            self.assertEqual(migrated["models"]["openrouter"], DEFAULT_OPENROUTER_MODEL)

            with open(path, "r", encoding="utf-8") as config_file:
                scrubbed = json.load(config_file)
            serialized = json.dumps(scrubbed)
            self.assertNotIn("old-google-secret", serialized)
            self.assertNotIn("old-groq-secret", serialized)
            self.assertNotIn("google", scrubbed["api_keys"])
            self.assertNotIn("google", scrubbed["models"])
            self.assertNotIn("groq", scrubbed["api_keys"])
            self.assertEqual(scrubbed["provider"], "apinex")

    def test_legacy_flat_google_key_and_model_are_discarded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "screen_answer_config.json")
            with open(path, "w", encoding="utf-8") as config_file:
                json.dump({"api_key": "old-google-key", "model": "gemini-3.8-flash"}, config_file)

            migrated = load_portable_config(path)
            self.assertEqual(migrated["provider"], "apinex")
            self.assertEqual(migrated["api_keys"], {})
            self.assertEqual(migrated["models"], {})
            with open(path, "r", encoding="utf-8") as config_file:
                scrubbed = json.load(config_file)
            self.assertNotIn("old-google-key", json.dumps(scrubbed))
            self.assertNotIn("api_key", scrubbed)
            self.assertNotIn("model", scrubbed)

    def test_ollama_never_stores_or_resolves_an_api_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "screen_answer_config.json")
            save_portable_config(
                path=path,
                provider="ollama",
                api_key="should-not-be-saved",
                model=DEFAULT_OLLAMA_MODEL,
                api_keys={"ollama": "also-ignored"},
            )
            with open(path, "r", encoding="utf-8") as config_file:
                saved = json.load(config_file)
            self.assertNotIn("ollama", saved["api_keys"])
            self.assertNotIn("should-not-be-saved", json.dumps(saved))
        self.assertEqual(
            resolve_api_key(
                "ollama",
                {"ollama": "old-key"},
                {"OLLAMA_API_KEY": "environment-key"},
            ),
            ("", "local Ollama server (no API key required)"),
        )

    def test_invalid_apinex_and_ollama_models_fall_back_to_safe_names(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "screen_answer_config.json")
            with open(path, "w", encoding="utf-8") as config_file:
                json.dump(
                    {
                        "provider": "apinex",
                        "api_keys": {"apinex": "apinex-key"},
                        "models": {
                            "apinex": "paid/gemini-3.8-flash",
                            "gemini": "models/gemini-3.8-flash?invalid",
                            "ollama": "qwen3-vl:8b?invalid",
                        },
                    },
                    config_file,
                )
            loaded = load_portable_config(path)
        self.assertEqual(loaded["models"]["apinex"], DEFAULT_APINEX_MODEL)
        self.assertEqual(loaded["models"]["gemini"], DEFAULT_GEMINI_MODEL)
        self.assertEqual(loaded["models"]["ollama"], DEFAULT_OLLAMA_MODEL)

    def test_missing_or_invalid_config_falls_back_to_empty_apinex_settings(self):
        empty_config = {
            "provider": "apinex",
            "api_keys": {},
            "models": {},
            "ocr_backend": "provider",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "missing.json")
            self.assertEqual(load_portable_config(path), empty_config)
            with open(path, "w", encoding="utf-8") as config_file:
                config_file.write("not json")
            self.assertEqual(load_portable_config(path), empty_config)


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
