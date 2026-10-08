"""Settings for Screen Answer v1.

One backend: an OpenAI-compatible gateway (FreeLLMAPI by default). Secrets
come from the environment when possible; the optional portable sidecar is
plaintext and opt-in (never written silently, consent is never persisted).
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

DEFAULT_ENDPOINT = "http://127.0.0.1:3001/v1"
DEFAULT_MODEL = "auto:reliable"
DEFAULT_SEARCH_MODEL = "auto:search"
PORTABLE_CONFIG_NAME = "screen_answer_config.json"

ENDPOINT_ENV = "SCREENANSWER_ENDPOINT"
MODEL_ENV = "SCREENANSWER_MODEL"
API_KEY_ENV = "FREELLMAPI_API_KEY"  # freellmapi unified key
API_KEY_ENV_ALIAS = "SCREENANSWER_API_KEY"

# Model strings we accept: routing profiles (`auto`, `auto:search`, ...) and
# pinned catalog IDs (`google/gemini-3.8-flash`, `free/gemini-3.8-flash`, ...).
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")

# `auto` and its steering suffixes; anything else is treated as a pinned ID.
AUTO_MODEL_RE = re.compile(r"^auto(?:[:][A-Za-z0-9_-]{1,64})?$", re.IGNORECASE)


def is_auto_model(model: str) -> bool:
    return bool(AUTO_MODEL_RE.match((model or "").strip()))


def valid_model_name(model: str) -> bool:
    return bool(MODEL_RE.match((model or "").strip()))


def normalize_endpoint(value: str) -> str:
    endpoint = (value or "").strip().rstrip("/")
    if not endpoint:
        return DEFAULT_ENDPOINT
    return endpoint


def valid_endpoint(value: str) -> bool:
    endpoint = (value or "").strip().rstrip("/")
    return endpoint.startswith("http://") or endpoint.startswith("https://")


@dataclass
class Settings:
    endpoint: str = DEFAULT_ENDPOINT
    api_key: str = ""
    model: str = DEFAULT_MODEL
    web_search: bool = True
    save_to_file: bool = False
    # Session-only: upload consent is never persisted (project privacy rule).
    allow_uploads: bool = field(default=False, compare=False)

    def request_model(self) -> str:
        """The model string actually sent (search steering, architecture §3.2)."""
        if self.web_search and is_auto_model(self.model):
            return DEFAULT_SEARCH_MODEL
        return self.model

    def chat_completions_url(self) -> str:
        return normalize_endpoint(self.endpoint) + "/chat/completions"


def load_settings(path: Optional[str] = None) -> Settings:
    """Load settings from the sidecar (if any), then apply environment keys.

    Unknown/invalid fields fall back to safe defaults; upload consent is
    always reset to False.
    """
    settings = Settings()
    config_path = path or portable_config_path()
    data: Dict[str, Any] = {}
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if isinstance(loaded, dict):
            data = loaded
    except (OSError, ValueError):
        data = {}

    endpoint = data.get("endpoint")
    if isinstance(endpoint, str) and valid_endpoint(endpoint):
        settings.endpoint = normalize_endpoint(endpoint)
    model = data.get("model")
    if isinstance(model, str) and valid_model_name(model):
        settings.model = model.strip()
    if isinstance(data.get("web_search"), bool):
        settings.web_search = data["web_search"]
    settings.save_to_file = bool(data.get("save_to_file", False))
    key = data.get("api_key")
    if isinstance(key, str) and key.strip():
        settings.api_key = key.strip()

    env_key = os.environ.get(API_KEY_ENV) or os.environ.get(API_KEY_ENV_ALIAS)
    if env_key:
        settings.api_key = env_key.strip()
    env_endpoint = os.environ.get(ENDPOINT_ENV)
    if env_endpoint and valid_endpoint(env_endpoint):
        settings.endpoint = normalize_endpoint(env_endpoint)
    env_model = os.environ.get(MODEL_ENV)
    if env_model and valid_model_name(env_model):
        settings.model = env_model.strip()

    settings.allow_uploads = False
    return settings


def save_settings(settings: Settings, path: Optional[str] = None) -> str:
    """Atomically write the sidecar only when portable saving is enabled.

    Returns the sidecar path when a file was written, else "".
    """
    if not settings.save_to_file:
        return ""
    config_path = path or portable_config_path()
    payload = {
        "endpoint": normalize_endpoint(settings.endpoint),
        "model": settings.model if valid_model_name(settings.model) else DEFAULT_MODEL,
        "web_search": bool(settings.web_search),
        "save_to_file": True,
        "api_key": settings.api_key,
    }
    directory = os.path.dirname(os.path.abspath(config_path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".screen_answer_", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_path, config_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return config_path


def remove_sidecar(path: Optional[str] = None) -> None:
    config_path = path or portable_config_path()
    try:
        os.remove(config_path)
    except OSError:
        pass


def portable_config_path() -> str:
    return os.path.join(os.getcwd(), PORTABLE_CONFIG_NAME)
