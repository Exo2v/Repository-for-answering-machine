"""OpenAI-compatible gateway client (FreeLLMAPI by default).

This is the whole backend of v1: one POST to `/v1/chat/completions` with the
screenshot as a base64 `image_url` data URL and, when web search is enabled,
the `google_search` grounding pseudo-tool (FreeLLMAPI's Google provider turns
it into Gemini's native Google Search grounding). Grounded requests steer
`auto` models to `auto:search` so they can only land on search-capable
models; if none exist the gateway answers `no_search_model` and this client
fails loudly instead of degrading to an ungrounded answer (architecture §3).
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .config import Settings

MAX_API_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_API_ATTEMPTS = 3
MAX_RETRY_AFTER_SECONDS = 30
MAX_OUTPUT_TOKENS = 2048
RETRYABLE_HTTP_STATUSES = (500, 502, 503, 504)
PER_ATTEMPT_TIMEOUT_SECONDS = 120

GOOGLE_SEARCH_TOOL = {
    "type": "function",
    "function": {"name": "google_search", "parameters": {}},
}


class GatewayError(Exception):
    """Base class for gateway failures (all carry a user-facing message)."""

    def __init__(self, message: str, status: Optional[int] = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class GatewayAuthError(GatewayError):
    pass


class GatewayRateLimited(GatewayError):
    def __init__(self, message: str, retry_after: Optional[float]) -> None:
        super().__init__(message, status=429)
        self.retry_after = retry_after


class GatewaySearchUnavailable(GatewayError):
    """`no_search_model`: web search was requested but no search-capable route exists."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status=422)


class GatewayQuotaError(GatewayError):
    pass


class GatewayUpstreamError(GatewayError):
    pass


class GatewayResponseTooLarge(GatewayError):
    pass


@dataclass
class GatewayResult:
    text: str
    model: str
    usage: Dict[str, Any] = field(default_factory=dict)
    attempts: int = 1
    request_id: Optional[str] = None
    raw_finish_reason: Optional[str] = None


def resolve_model(model: str, web_search: bool) -> str:
    """Architecture §3.2: grounded `auto*` requests ride the search profile."""
    from .config import is_auto_model

    if web_search and is_auto_model(model):
        return "auto:search"
    return model.strip()


def build_payload(
    settings: Settings,
    png_bytes: bytes,
    user_text: Optional[str] = None,
    system_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the chat/completions body. Pure and unit-testable."""
    from .prompt import system_instruction, user_prompt

    if not png_bytes:
        raise ValueError("png_bytes must not be empty")
    encoded = base64.b64encode(png_bytes).decode("ascii")
    payload: Dict[str, Any] = {
        "model": resolve_model(settings.model, settings.web_search),
        "messages": [
            {
                "role": "system",
                "content": system_text
                if system_text is not None
                else system_instruction(settings.web_search),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_text
                        if user_text is not None
                        else user_prompt(settings.web_search),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64," + encoded},
                    },
                ],
            },
        ],
        "temperature": 0,
        "max_tokens": MAX_OUTPUT_TOKENS,
    }
    if settings.web_search:
        # The one enabled tool. Omitted entirely when search is off — the
        # request body carries no tools/plugins field, matching the prompts.
        payload["tools"] = [GOOGLE_SEARCH_TOOL]
    return payload


# Indirection so tests can patch the transport.
_urlopen = urllib.request.urlopen


def _retry_after_seconds(headers: Any, attempt: int) -> float:
    retry_after = None
    try:
        retry_after = headers.get("Retry-After") if headers is not None else None
    except AttributeError:
        retry_after = None
    if retry_after:
        try:
            value = float(retry_after)
        except (TypeError, ValueError):
            value = 0.0
        return max(0.0, min(value, MAX_RETRY_AFTER_SECONDS))
    return float(min(2 ** attempt, MAX_RETRY_AFTER_SECONDS))


def _error_from_body(status: int, body: bytes) -> GatewayError:
    message = ""
    code = ""
    try:
        data = json.loads(body.decode("utf-8", "replace"))
        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict):
            message = str(error.get("message") or "")
            code = str(error.get("code") or "")
        elif isinstance(error, str):
            message = error
    except ValueError:
        message = body[:300].decode("utf-8", "replace")
    if code == "no_search_model" or "no_search_model" in message:
        return GatewaySearchUnavailable(
            "Web search was requested but the gateway has no search-capable "
            "model enabled (no_search_model). Add a Google-family vision model "
            "to the search chain, or turn web search off."
        )
    if status in (401, 403):
        return GatewayAuthError("Gateway rejected the API key (HTTP %d). %s" % (status, message))
    if status == 402:
        return GatewayQuotaError("Gateway account/quota error (HTTP 402). %s" % message)
    if status == 429:
        return GatewayRateLimited(
            "The gateway rate limit was hit (HTTP 429). %s" % message, retry_after=None
        )
    return GatewayUpstreamError("Gateway error (HTTP %d). %s" % (status, message))


def _extract_text(data: Dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise GatewayUpstreamError("The gateway returned no choices.")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # content-parts form
        parts = [p.get("text", "") for p in content if isinstance(p, dict)]
        return "".join(parts)
    raise GatewayUpstreamError("The gateway response had no text content.")


def ask_gateway(
    settings: Settings,
    png_bytes: bytes,
    report: Optional[Callable[[str], None]] = None,
) -> GatewayResult:
    """Send one screenshot question through the gateway and return the answer text.

    Retries transient failures up to MAX_API_ATTEMPTS with bounded backoff;
    `Retry-After` is honoured within a cap. Search failures are never retried
    into a different (ungrounded) route.
    """

    def say(message: str) -> None:
        if report is not None:
            report(message)

    payload = build_payload(settings, png_bytes)
    body = json.dumps(payload).encode("utf-8")
    url = settings.chat_completions_url()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "ScreenAnswer/1.0",
    }
    if settings.api_key:
        headers["Authorization"] = "Bearer " + settings.api_key

    last_error: Optional[GatewayError] = None
    for attempt in range(1, MAX_API_ATTEMPTS + 1):
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        say(
            "Gateway request attempt %d/%d -> %s (model=%s, search=%s)"
            % (attempt, MAX_API_ATTEMPTS, url, payload["model"], settings.web_search)
        )
        try:
            with _urlopen(request, timeout=PER_ATTEMPT_TIMEOUT_SECONDS) as response:
                raw = response.read(MAX_API_RESPONSE_BYTES + 1)
                if len(raw) > MAX_API_RESPONSE_BYTES:
                    raise GatewayResponseTooLarge(
                        "The gateway response exceeded the 2 MiB safety cap."
                    )
                data = json.loads(raw.decode("utf-8", "replace"))
                text = _extract_text(data)
                result = GatewayResult(
                    text=text,
                    model=str(data.get("model") or payload["model"]),
                    usage=data.get("usage") if isinstance(data.get("usage"), dict) else {},
                    attempts=attempt,
                    request_id=getattr(response, "headers", {}).get("x-request-id"),
                )
                say(
                    "Gateway OK on attempt %d (served model: %s, usage: %s)"
                    % (attempt, result.model, json.dumps(result.usage, sort_keys=True)[:200])
                )
                return result
        except urllib.error.HTTPError as exc:
            raw = b""
            try:
                raw = exc.read(MAX_API_RESPONSE_BYTES)
            except OSError:
                raw = b""
            error = _error_from_body(exc.code, raw)
            if isinstance(error, GatewayRateLimited):
                last_error = error
            if isinstance(error, GatewaySearchUnavailable):
                say("Gateway refused the grounded request: %s" % error.message)
                raise error
            if exc.code in RETRYABLE_HTTP_STATUSES or exc.code == 429:
                last_error = error
                delay = _retry_after_seconds(getattr(exc, "headers", None), attempt)
                say(
                    "Transient gateway error (HTTP %d); waiting %.1fs before retry"
                    % (exc.code, delay)
                )
                if attempt < MAX_API_ATTEMPTS:
                    time.sleep(delay)
                    continue
                if exc.code == 429:
                    raise GatewayRateLimited(
                        "The gateway rate limit did not clear after %d attempts. %s"
                        % (MAX_API_ATTEMPTS, error.message),
                        retry_after=delay,
                    )
                raise GatewayUpstreamError(
                    "The gateway kept failing after %d attempts. %s"
                    % (MAX_API_ATTEMPTS, error.message),
                    status=exc.code,
                )
            say("Gateway rejected the request: %s" % error.message)
            raise error
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = GatewayUpstreamError(
                "Could not reach the gateway at %s (%s). Is FreeLLMAPI running?"
                % (url, getattr(exc, "reason", exc))
            )
            say("Gateway unreachable: %s" % last_error.message)
            if attempt < MAX_API_ATTEMPTS:
                time.sleep(min(2 ** attempt, MAX_RETRY_AFTER_SECONDS))
                continue
            raise last_error
        except ValueError as exc:
            raise GatewayUpstreamError("The gateway returned invalid JSON (%s)." % exc)

    if last_error is not None:
        raise last_error
    raise GatewayUpstreamError("The gateway request failed.")
