"""Bulk API-key management for the FreeLLMAPI gateway's admin API.

The gateway (localhost:3001) is where provider keys live. Its dashboard API
lets an authenticated client register keys: POST /api/auth/login issues a
session token, then POST /api/keys {platform, key, label?} stores one key.
Screen Answer uses this to offer bulk paste — one key per line — and pushes
each key to the user's own gateway. Provider keys are NEVER written to
Screen Answer's config; they are sent to the configured gateway only.

Line syntax (one key per line):
    AIzaSy...                      -> platform auto-detected (google)
    sk-or-v1-...                   -> auto-detected (openrouter)
    zhipu:abc123                   -> explicit platform prefix
    zhipu=abc123                   -> same, alternate separator
    # comment / blank lines        -> ignored
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

# Platform ids the gateway's admin API accepts (server/src/routes/keys.ts
# PLATFORMS). The short list covers the free-tier providers we recommend.
KNOWN_PLATFORMS: Tuple[str, ...] = (
    "google",
    "groq",
    "openrouter",
    "github",
    "zhipu",
    "nvidia",
    "mistral",
    "cerebras",
    "cohere",
    "huggingface",
    "siliconflow",
    "cloudflare",
    "ollama",
    "kilo",
    "aihorde",
)

# Longest-prefix match first.
_KEY_PREFIXES: Tuple[Tuple[str, str], ...] = (
    ("github_pat_", "github"),
    ("sk-or-v1-", "openrouter"),
    ("sk-or-", "openrouter"),
    ("gsk_", "groq"),
    ("ghp_", "github"),
    ("gho_", "github"),
    ("ghu_", "github"),
    ("ghs_", "github"),
    ("ghr_", "github"),
    ("AIza", "google"),
)

_urlopen = urllib.request.urlopen  # test seam


class AdminApiError(Exception):
    """Readable failure talking to the gateway's admin API."""

    def __init__(self, message: str, status: int = 0) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def gateway_base(endpoint: str) -> str:
    """`http://127.0.0.1:3001/v1` -> `http://127.0.0.1:3001` (admin API root)."""
    base = (endpoint or "").strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[: -len("/v1")]
    return base or "http://127.0.0.1:3001"


def detect_platform(key: str) -> Optional[str]:
    """Guess the provider from a key's shape; None when ambiguous (`sk-...`)."""
    key = key.strip()
    for prefix, platform in _KEY_PREFIXES:
        if key.startswith(prefix):
            return platform
    return None


def parse_key_line(line: str, assume_platform: Optional[str] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Parse one line -> (platform, key, error). Exactly one of the trio set."""
    text = line.strip()
    if not text or text.startswith("#"):
        return (None, None, None)
    platform = None
    key = text
    for sep in (":", "="):
        head, sep2, tail = text.partition(sep)
        head = head.strip()
        # Only treat as a prefix when the head is a known platform id —
        # real keys contain ':'/'=' far less often than the head here would.
        if sep2 and tail.strip() and head.lower() in KNOWN_PLATFORMS:
            platform = head.lower()
            key = tail.strip()
            break
    if platform is None:
        platform = detect_platform(key)
    if platform is None:
        platform = (assume_platform or "").strip().lower() or None
    if platform is None:
        return (None, None, "could not detect provider — use platform:key or pick one above")
    if platform not in KNOWN_PLATFORMS:
        return (None, None, "unknown provider '%s'" % platform)
    if not key:
        return (None, None, "empty key")
    return (platform, key, None)


def parse_keys_text(
    text: str, assume_platform: Optional[str] = None
) -> Tuple[List[Tuple[str, str]], List[Tuple[int, str]]]:
    """Bulk-parse a paste box. Returns ([(platform, key)], [(line_no, error)])."""
    parsed: List[Tuple[str, str]] = []
    errors: List[Tuple[int, str]] = []
    for index, line in enumerate((text or "").splitlines(), start=1):
        platform, key, error = parse_key_line(line, assume_platform)
        if error:
            errors.append((index, error))
        elif platform and key:
            parsed.append((platform, key))
    return parsed, errors


class AdminClient:
    """Minimal client for the gateway dashboard API (login + add keys)."""

    def __init__(self, base_url: str, opener=None) -> None:
        self.base_url = gateway_base(base_url)
        self._opener = opener or _urlopen
        self.token: Optional[str] = None

    # ------------------------------------------------------------------ http

    def _request(self, path: str, payload: Dict[str, Any], auth: bool = True) -> Dict[str, Any]:
        url = self.base_url + path
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if auth:
            if not self.token:
                raise AdminApiError("Not logged in to the gateway dashboard.", 401)
            headers["Authorization"] = "Bearer " + self.token
        request = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with self._opener(request, timeout=15) as response:
                body = response.read(256 * 1024)
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                raw = exc.read(64 * 1024).decode("utf-8", "replace")
                parsed = json.loads(raw)
                detail = (
                    (parsed.get("error") or {}).get("message")
                    if isinstance(parsed, dict)
                    else ""
                ) or raw[:200]
            except Exception:
                detail = ""
            if exc.code == 401:
                raise AdminApiError("Gateway dashboard login rejected (401).", 401)
            raise AdminApiError(detail or "gateway error %d" % exc.code, exc.code)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise AdminApiError(
                "Could not reach the gateway at %s (%s)." % (self.base_url, getattr(exc, "reason", exc))
            )
        try:
            return json.loads(body.decode("utf-8", "replace"))
        except ValueError:
            return {}

    # ------------------------------------------------------------------- api

    def login(self, email: str, password: str) -> str:
        """POST /api/auth/login -> session token (kept in memory only)."""
        payload = self._request(
            "/api/auth/login", {"email": email, "password": password}, auth=False
        )
        token = payload.get("token")
        if not token:
            raise AdminApiError("Login succeeded but no session token was returned.")
        self.token = str(token)
        return self.token

    def add_key(self, platform: str, key: str, label: str = "screen-answer") -> Dict[str, Any]:
        """POST /api/keys — store one provider key on the gateway."""
        return self._request("/api/keys", {"platform": platform, "key": key, "label": label})
