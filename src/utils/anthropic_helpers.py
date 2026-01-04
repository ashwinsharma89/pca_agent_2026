"""Safe Anthropic client factory helpers.

These helpers centralize optional Anthropic dependency handling so that
projects can gracefully fall back when the SDK is not available or when
unsupported keyword arguments (e.g., ``proxies``) raise ``TypeError`` in
certain environments.
"""
from __future__ import annotations

import os
from typing import Optional

from loguru import logger

try:  # pragma: no cover - optional dependency
    from anthropic import Anthropic, AsyncAnthropic
    _ANTHROPIC_AVAILABLE = True
except Exception as exc:  # pragma: no cover - optional dependency
    Anthropic = AsyncAnthropic = None  # type: ignore
    _ANTHROPIC_AVAILABLE = False
    logger.debug(f"Anthropic SDK unavailable: {exc}")


PROXIES_ERROR_HINT = (
    "Anthropic client failed due to an unsupported 'proxies' argument. "
    "Set ANTHROPIC_API_KEY only when the SDK supports proxies in this environment."
)


def _log_client_error(exc: Exception) -> None:
    message = str(exc)
    if "proxies" in message.lower():
        logger.warning(PROXIES_ERROR_HINT)
    else:
        logger.warning(f"Anthropic client initialization error: {exc}")


def create_anthropic_client(api_key: Optional[str] = None):
    """Create a synchronous Anthropic client or return ``None`` on failure."""
    if not _ANTHROPIC_AVAILABLE:
        return None

    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None

    try:
        # Try without any proxy settings first
        return Anthropic(api_key=key, max_retries=2)
    except TypeError as exc:
        # If proxies argument causes issues, try basic initialization
        if "proxies" in str(exc).lower():
            try:
                return Anthropic(api_key=key)
            except Exception as inner_exc:
                _log_client_error(inner_exc)
                return None
        _log_client_error(exc)
        return None
    except Exception as exc:  # pragma: no cover - environment specific
        _log_client_error(exc)
        return None


def create_async_anthropic_client(api_key: Optional[str] = None):
    """Create an asynchronous Anthropic client or return ``None`` on failure."""
    if not _ANTHROPIC_AVAILABLE:
        return None

    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None

    try:
        return AsyncAnthropic(api_key=key)
    except Exception as exc:  # pragma: no cover - environment specific
        _log_client_error(exc)
        return None


def call_anthropic_http(api_key: str, model: str, messages: list, max_tokens: int = 4000) -> dict:
    """
    Make a raw HTTP request to Anthropic API to bypass SDK/Proxy issues.
    """
    import requests
    import json
    
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages
    }
    
    try:
        logger.info(f"Anthropic HTTP call - Model: {model}, API Key (prefix): {api_key[:12]}...")
        response = requests.post(url, headers=headers, json=payload, timeout=180)  # 3 min for Sonnet 4.5
        response.raise_for_status()
        
        data = response.json()
        content = data['content'][0]['text']
        usage = data.get('usage', {})
        
        return {
            'content': content,
            'usage': usage
        }
    except Exception as e:
        logger.error(f"Raw Anthropic HTTP call failed: {e}")
        if hasattr(e, 'response') and e.response:
             logger.error(f"Response: {e.response.text}")
        raise e
