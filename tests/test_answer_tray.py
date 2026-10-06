import base64
import io
import json
import os
import struct
import tempfile
import types
import unittest
import urllib.error
import zlib
from unittest.mock import MagicMock, patch

from answer_tray import (
    _encode_rgb_png,
    DEFAULT_MISTRAL_MODEL,
    DEFAULT_GROQ_MODEL,
    GROQ_ENDPOINT,
    MISTRAL_OCR_ENDPOINT,
    MISTRAL_OCR_MODEL,
    _extract_gemini_text,
    _extract_mistral_ocr_markdown,
    _extract_mistral_text,
    ask_gemini,
    ask_mistral,
    ask_groq,
    default_provider_for_executable,
    diagnostics_mode_enabled,
    load_portable_config,
    parse_option,
    pix2text_bundle_importable,
    run_pix2text_ocr,
    save_portable_config,
    valid_model_name,
)


class DiagnosticsModeTests(unittest.TestCase):
    def test_diagnostic_mode_is_enabled_by_exe_name_or_flag(self):
        self.assertTrue(
            diagnostics_mode_enabled((), "ScreenAnswer-Diagnostic.exe")
        )
        self.assertTrue(diagnostics_mode_enabled(("--diagnostics",), "python.exe"))
        self.assertFalse(diagnostics_mode_enabled((), "ScreenAnswer.exe"))


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

    def test_extracts_candidate_text(self):
        payload = {
            "candidates": [
                {"content": {"parts": [{"text": "2"}, {"text": ""}]}}
            ]
        }
        self.assertEqual(_extract_gemini_text(payload), "2")
        self.assertEqual(_extract_gemini_text({"candidates": []}), "")
        self.assertEqual(
            _extract_gemini_text(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": "private thought", "thought": True},
                                    {"text": "ANSWER: B"},
                                ]
                            }
                        }
                    ]
                }
            ),
            "ANSWER: B",
        )


class GeminiRequestTests(unittest.TestCase):
    def test_uses_screenshot_without_search_tools(self):
        image_bytes = b"fake png bytes"
        captured = {}
        response_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    "TRANSCRIPTION: a question with choices A-D.\n"
                                    "SOLUTION: calculate and verify the value.\n"
                                    "ANSWER: C"
                                )
                            }
                        ]
                    }
                }
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
        self.assertIn("ANSWER: C", response_text)
        self.assertNotIn("tools", captured["body"])
        self.assertEqual(captured["body"]["generationConfig"]["maxOutputTokens"], 2048)
        parts = captured["body"]["contents"][0]["parts"]
        self.assertEqual(parts[1]["inlineData"]["data"], base64.b64encode(image_bytes).decode("ascii"))

    def test_attaches_local_ocr_transcript_and_original_image(self):
        captured = {}
        response_payload = {
            "candidates": [{"content": {"parts": [{"text": "ANSWER: B"}]}}]
        }
        markdown = "Calculate $2 + 2$.\nA. 3\nB. 4"

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def read(self, limit=-1):
                data = json.dumps(response_payload).encode("utf-8")
                return data if limit < 0 else data[:limit]

        def fake_urlopen(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        image_bytes = b"original screenshot"
        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            option, _ = ask_gemini(
                "key", "gemini-3.8-flash", image_bytes, ocr_markdown=markdown
            )

        parts = captured["body"]["contents"][0]["parts"]
        self.assertEqual(option, 2)
        self.assertIn(markdown, parts[0]["text"])
        self.assertIn("verify it against the attached original screenshot", parts[0]["text"])
        self.assertEqual(
            parts[1]["inlineData"]["data"],
            base64.b64encode(image_bytes).decode("ascii"),
        )

    def test_diagnostic_callback_shows_final_model_text_but_redacts_key(self):
        private_response = (
            "TRANSCRIPTION: question text from the screenshot.\n"
            "SOLUTION: concise calculation.\n"
            "ANSWER: A"
        )
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

        self.assertEqual(option, 1)
        self.assertEqual(response_text, private_response)
        self.assertTrue(any("final response (diagnostic-only" in line for line in diagnostic_lines))
        self.assertTrue(any("TRANSCRIPTION: question text" in line for line in diagnostic_lines))
        self.assertTrue(any("ANSWER: A" in line for line in diagnostic_lines))
        self.assertFalse(any("test-key" in line for line in diagnostic_lines))

    def test_diagnostics_explain_empty_response_structure(self):
        response_payload = {
            "promptFeedback": {
                "blockReason": "SAFETY",
                "safetyRatings": [
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "probability": "HIGH"}
                ],
            },
            "usageMetadata": {
                "promptTokenCount": 320,
                "candidatesTokenCount": 0,
                "totalTokenCount": 320,
            },
            "modelVersion": "gemini-3.8-flash-test",
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
        self.assertEqual(response_text, "")
        self.assertTrue(any("candidate_count=0" in line for line in diagnostic_lines))
        self.assertTrue(any("block_reason=SAFETY" in line for line in diagnostic_lines))
        self.assertTrue(any("HARM_CATEGORY_DANGEROUS_CONTENT:HIGH" in line for line in diagnostic_lines))
        self.assertTrue(any("candidatesTokenCount=0" in line for line in diagnostic_lines))
        self.assertFalse(any("test-key" in line for line in diagnostic_lines))

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
        self.assertTrue(any("recognized option position 1" in line for line in diagnostic_lines))
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


class GroqRequestTests(unittest.TestCase):
    def test_direct_vision_request_uses_image_url_without_ocr_or_tools(self):
        image_bytes = b"fake png bytes"
        final_text = (
            "TRANSCRIPTION: compute 1 + 1; choices A=1, B=2, C=3, D=4.\n"
            "SOLUTION: 1 + 1 = 2, so the second choice matches.\n"
            "ANSWER: B"
        )
        captured = []
        diagnostics = []
        response_payload = {
            "id": "groq-request-1",
            "model": DEFAULT_GROQ_MODEL,
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
            "usage": {"prompt_tokens": 100, "completion_tokens": 80, "total_tokens": 180},
        }

        class FakeResponse:
            status = 200
            headers = {"x-ratelimit-remaining-tokens": "1000"}

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
            option, response_text = ask_groq(
                "groq-test-key", DEFAULT_GROQ_MODEL, image_bytes, diagnostics.append
            )

        self.assertEqual(option, 2)
        self.assertEqual(response_text, final_text)
        self.assertNotIn("hidden reasoning", response_text)
        self.assertEqual(len(captured), 1)
        request = captured[0]
        self.assertEqual(request["url"], GROQ_ENDPOINT)
        self.assertEqual(request["authorization"], "Bearer groq-test-key")
        self.assertEqual(request["timeout"], 60)
        body = request["body"]
        self.assertEqual(body["model"], DEFAULT_GROQ_MODEL)
        self.assertEqual(body["max_completion_tokens"], 4096)
        self.assertEqual(body["reasoning_effort"], "high")
        self.assertEqual(body["reasoning_format"], "hidden")
        self.assertNotIn("tools", body)
        self.assertNotIn("tool_choice", body)
        self.assertIn("Do not use live web search", body["messages"][0]["content"])
        content = body["messages"][1]["content"]
        self.assertEqual(content[1]["type"], "image_url")
        self.assertEqual(
            content[1]["image_url"]["url"],
            "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii"),
        )
        self.assertTrue(any("no separate OCR API is used" in line for line in diagnostics))
        self.assertFalse(any("hidden reasoning" in line for line in diagnostics))

    def test_optional_local_ocr_transcript_is_context_only(self):
        captured = []
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
            captured.append((request.full_url, json.loads(request.data.decode("utf-8"))))
            return FakeResponse()

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            option, _ = ask_groq("key", DEFAULT_GROQ_MODEL, b"image", ocr_markdown=transcript)

        self.assertEqual(option, 2)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0], GROQ_ENDPOINT)
        self.assertIn(transcript, captured[0][1]["messages"][1]["content"][0]["text"])

    def test_retries_bounded_429_using_retry_after(self):
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
                raise urllib.error.HTTPError(
                    request.full_url,
                    429,
                    "Too Many Requests",
                    {"Retry-After": "2", "x-ratelimit-remaining-tokens": "0"},
                    io.BytesIO(b'{"error":{"message":"rate limit exceeded"}}'),
                )
            return FakeResponse()

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            with patch("answer_tray.time.sleep") as sleep:
                option, _ = ask_groq("key", DEFAULT_GROQ_MODEL, b"image", diagnostics.append)

        self.assertEqual(option, 3)
        self.assertEqual(attempts, [GROQ_ENDPOINT, GROQ_ENDPOINT])
        sleep.assert_called_once_with(2.0)
        self.assertTrue(any("Retry-After=2" in line for line in diagnostics))
        self.assertTrue(any("retrying in 2.0 second(s)" in line for line in diagnostics))

    def test_auth_error_diagnostics_redact_api_key(self):
        api_key = "groq-secret-key"
        diagnostics = []

        def fake_urlopen(request, timeout):
            raise urllib.error.HTTPError(
                GROQ_ENDPOINT,
                401,
                "Unauthorized",
                None,
                io.BytesIO(
                    json.dumps({"error": {"message": "invalid key " + api_key}}).encode("utf-8")
                ),
            )

        with patch("answer_tray.urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaisesRegex(RuntimeError, "Groq rejected the API key"):
                ask_groq(api_key, DEFAULT_GROQ_MODEL, b"image", diagnostics.append)

        self.assertTrue(any("[REDACTED API KEY]" in line for line in diagnostics))
        self.assertFalse(any(api_key in line for line in diagnostics))

    def test_model_namespaced_id_and_groq_executable_default(self):
        self.assertTrue(valid_model_name("groq", DEFAULT_GROQ_MODEL))
        self.assertFalse(valid_model_name("gemini", DEFAULT_GROQ_MODEL))
        self.assertFalse(valid_model_name("groq", "qwen/model?bad"))
        self.assertEqual(default_provider_for_executable("ScreenAnswer-Groq.exe"), "groq")
        self.assertEqual(default_provider_for_executable("ScreenAnswer.exe"), "gemini")


class PortableConfigTests(unittest.TestCase):
    def test_saves_and_loads_key_and_model(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "screen_answer_config.json")
            save_portable_config("example-key", "gemini-3.8-flash", path)
            self.assertEqual(
                load_portable_config(path),
                {
                    "provider": "gemini",
                    "api_keys": {"gemini": "example-key"},
                    "models": {"gemini": "gemini-3.8-flash"},
                    "ocr_backend": "provider",
                },
            )

    def test_saves_all_providers_and_migrates_legacy_gemini_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "screen_answer_config.json")
            save_portable_config(
                path=path,
                provider="mistral",
                api_keys={
                    "gemini": "gemini-key",
                    "mistral": "mistral-key",
                    "groq": "groq-key",
                },
                models={
                    "gemini": "gemini-3.8-flash",
                    "mistral": "ministral-14b-2512",
                    "groq": DEFAULT_GROQ_MODEL,
                },
                ocr_backend="pix2text",
            )
            self.assertEqual(
                load_portable_config(path),
                {
                    "provider": "mistral",
                    "api_keys": {
                        "gemini": "gemini-key",
                        "mistral": "mistral-key",
                        "groq": "groq-key",
                    },
                    "models": {
                        "gemini": "gemini-3.8-flash",
                        "mistral": "mistral-medium-latest",
                        "groq": DEFAULT_GROQ_MODEL,
                    },
                    "ocr_backend": "pix2text",
                },
            )
            with open(path, "w", encoding="utf-8") as config_file:
                json.dump({"api_key": "legacy-key", "model": "gemini-3.8-flash"}, config_file)
            self.assertEqual(
                load_portable_config(path),
                {
                    "provider": "gemini",
                    "api_keys": {"gemini": "legacy-key"},
                    "models": {"gemini": "gemini-3.8-flash"},
                    "ocr_backend": "provider",
                },
            )

    def test_missing_or_invalid_config_falls_back_to_empty(self):
        empty_config = {
            "provider": "gemini",
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


    def test_groq_executable_defaults_to_groq_but_keeps_gemini_legacy_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "screen_answer_config.json")
            with patch("answer_tray.APP_DEFAULT_PROVIDER", "groq"):
                self.assertEqual(load_portable_config(path)["provider"], "groq")
                with open(path, "w", encoding="utf-8") as config_file:
                    json.dump({"api_key": "old-gemini-key", "model": "gemini-3.8-flash"}, config_file)
                migrated = load_portable_config(path)

        self.assertEqual(migrated["provider"], "gemini")
        self.assertEqual(migrated["api_keys"], {"gemini": "old-gemini-key"})
        self.assertEqual(migrated["models"], {"gemini": "gemini-3.8-flash"})


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
