"""NewAPI provider compatibility helpers.

This module centralizes provider alias handling and common error parsing so
different call points can share the same fallback behavior.
"""

from __future__ import annotations

import os
import re
from typing import Dict, Optional

NEWAPI_PROVIDER = "newapi"
LEGACY_DOUBAO_PROVIDER = "doubao"
NEWAPI_KEY_ENV = "ARK_API_KEY"
NEWAPI_MODEL_ENV = "ARK_MODEL"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


NEWAPI_BASE_URL = (
    os.getenv("NEWAPI_BASE_URL")
    or os.getenv("DOUBAO_BASE_URL")
    or os.getenv("ARK_BASE_URL")
    or "http://111.230.37.43:3000/v1"
)
DEFAULT_NEWAPI_MODEL = (
    os.getenv("NEWAPI_DEFAULT_MODEL")
    or "doubao-seed-2-0-lite-260215"
)
DEFAULT_NEWAPI_MAX_COMPLETION_TOKENS = _env_int("NEWAPI_MAX_COMPLETION_TOKENS", 64000)
DEFAULT_NEWAPI_ENABLE_THINKING = _env_bool("NEWAPI_ENABLE_THINKING", default=False)


def normalize_provider(provider: Optional[str]) -> str:
    value = (provider or "").strip().lower()
    if value == LEGACY_DOUBAO_PROVIDER:
        return NEWAPI_PROVIDER
    return value or "openrouter"


def is_newapi_provider(provider: Optional[str]) -> bool:
    return normalize_provider(provider) == NEWAPI_PROVIDER


def build_newapi_extra_body(
    max_completion_tokens: Optional[int] = None,
    enable_reasoning: Optional[bool] = None,
) -> Dict[str, object]:
    body: Dict[str, object] = {
        "max_completion_tokens": int(max_completion_tokens or DEFAULT_NEWAPI_MAX_COMPLETION_TOKENS)
    }
    reasoning = DEFAULT_NEWAPI_ENABLE_THINKING if enable_reasoning is None else bool(enable_reasoning)
    if reasoning:
        body["thinking"] = {"type": "enabled"}
        body["reasoning_effort"] = "medium"
    return body


def is_unsupported_reasoning_args_error(error: Exception) -> bool:
    text = str(error).lower()
    keywords = ("thinking", "reasoning_effort")
    if not any(key in text for key in keywords):
        return False
    return (
        "unrecognized request arguments supplied" in text
        or "unknown parameter" in text
        or "unsupported parameter" in text
    )


def extract_completion_tokens_cap(error: Exception) -> Optional[int]:
    text = str(error)
    patterns = [
        r"supports at most\s+(\d+)\s+completion tokens",
        r"supports at most\s+(\d+)\s+tokens",
        r"max_tokens is too large.*?at most\s+(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
    return None

