"""g4f provider management with automatic retry / fallback."""

from __future__ import annotations

import json
import logging
import os
import random
from typing import Any, List, Optional, Tuple

import g4f
from g4f.client import Client

from .helpers import is_valid_response, strip_markdown_fences

# ---------------------------------------------------------------------------
# Default provider names (resolved lazily)
#
# g4f renames/removes providers between releases, so the defaults are a
# *candidate* list: names that no longer exist are skipped silently.  Override
# at runtime with the ASIMTOOL_PROVIDERS environment variable, e.g.
# ``ASIMTOOL_PROVIDERS="Yqcloud,ChatgptFree"``.
# ---------------------------------------------------------------------------
DEFAULT_PROVIDER_NAMES: list[str] = [
    "Yqcloud",
    "ChatgptFree",
    "Free2GPT",
    "Aura",
]

# Kept as a last-resort pool: these are the historical defaults and still work
# on older g4f pins.
LEGACY_PROVIDER_NAMES: list[str] = [
    "OperaAria",
    "CohereForAI_C4AI_Command",
    "DeepSeek",
    "You",
]


# Groq chat models for the direct-API fallback, tried in order.  Pin a single
# one with GROQ_MODEL.
GROQ_CHAT_MODELS: list[str] = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]


def _provider_names_from_env() -> list[str]:
    raw = os.environ.get("ASIMTOOL_PROVIDERS", "").strip()
    return [n.strip() for n in raw.split(",") if n.strip()]


def _resolve_providers(names: list[str] | None = None) -> list:
    """Convert provider-name strings into ``g4f.Provider.*`` classes.

    Unknown names are skipped (g4f drops providers regularly).  When nothing
    resolves, the legacy name pool is tried before giving up.
    """
    names = list(names) if names else (_provider_names_from_env() or DEFAULT_PROVIDER_NAMES)
    providers = [cls for cls in (getattr(g4f.Provider, n, None) for n in names) if cls]

    if not providers and names != LEGACY_PROVIDER_NAMES:
        providers = [
            cls for cls in (getattr(g4f.Provider, n, None) for n in LEGACY_PROVIDER_NAMES) if cls
        ]

    if not providers:
        raise RuntimeError(
            "None of the requested providers could be resolved: "
            f"{names}. Set ASIMTOOL_PROVIDERS to valid g4f provider names."
        )
    return providers


# ---------------------------------------------------------------------------
# Public provider wrapper
# ---------------------------------------------------------------------------

class Provider:
    """Thin wrapper around a list of g4f providers.

    Usage::

        p = Provider()                       # use defaults
        p = Provider(["Yqcloud", "Aura"])    # custom list
    """

    def __init__(
        self,
        provider_names: list[str] | None = None,
        *,
        shuffle: bool = False,
    ):
        self.providers = _resolve_providers(provider_names)
        if shuffle:
            random.shuffle(self.providers)

    def __repr__(self) -> str:
        names = [getattr(p, "__name__", str(p)) for p in self.providers]
        return f"Provider({names})"


# ---------------------------------------------------------------------------
# Convenience callers
# ---------------------------------------------------------------------------

def _extract_text(response) -> str:
    """Pull plain-text content from a g4f response (str or dict)."""
    if isinstance(response, str) and response.strip():
        return response.strip()
    if isinstance(response, dict) and "choices" in response:
        return response["choices"][0]["message"]["content"].strip()
    return ""


def call_ai(
    prompt: str,
    *,
    model: str = "grok_3",
    provider: Provider | None = None,
    system: str | None = None,
) -> str:
    """Send *prompt* to g4f and return the first valid plain-text response.

    Tries each provider with the Client API first, then legacy fallback.
    If all g4f providers fail and ``GROQ_API_KEY`` is set, falls back to
    Groq's llama-3.3-70b-versatile as a last resort.

    Parameters
    ----------
    prompt : str
        The user message.
    model : str
        Name of the g4f model (attribute on ``g4f.models``).
    provider : Provider, optional
        Custom provider list; uses defaults if omitted.
    system : str, optional
        An optional system message prepended to the conversation.

    Returns
    -------
    str
        The AI response text.

    Raises
    ------
    RuntimeError
        When all providers fail.
    """
    provider = provider or Provider()
    model_obj = getattr(g4f.models, model, model)

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_err: Exception | None = None
    for prov in provider.providers:
        # Try Client API (preferred)
        try:
            client = Client()
            resp = client.chat.completions.create(
                model=model_obj,
                messages=messages,
                provider=prov,
            )
            if resp and resp.choices:
                text = resp.choices[0].message.content
                if text and text.strip() and is_valid_response(text.strip()):
                    return text.strip()
        except Exception as exc:
            last_err = exc

        # Try legacy API
        try:
            response = g4f.ChatCompletion.create(
                model=model_obj,
                messages=messages,
                provider=prov,
            )
            text = _extract_text(response)
            if text and is_valid_response(text):
                return text
        except Exception as exc:
            last_err = exc
            continue

    # Last resort: Groq API fallback
    groq_result = _groq_fallback(messages)
    if groq_result:
        return groq_result

    raise RuntimeError(f"All providers failed. Last error: {last_err}")


def _groq_fallback(messages: list[dict[str, str]], timeout_sec: int = 60) -> str | None:
    """Direct Groq API call as last-resort fallback.

    Uses ``GROQ_API_KEY`` from the environment and tries each model in
    :data:`GROQ_CHAT_MODELS` until one answers.  ``GROQ_MODEL`` pins a single
    model.  Returns the response text, or None when everything fails.
    """
    import requests as _req

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return None

    override = os.environ.get("GROQ_MODEL", "").strip()
    models = [override] if override else GROQ_CHAT_MODELS
    base = os.environ.get("GROQ_API_BASE", "https://api.groq.com/openai/v1").rstrip("/")

    for model_name in models:
        try:
            resp = _req.post(
                f"{base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "messages": messages,
                    "max_tokens": 4096,
                },
                timeout=timeout_sec,
            )
            if resp.status_code == 200:
                content = (
                    resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                )
                if content:
                    return content
            else:
                logging.debug("[Groq fallback] %s HTTP %d: %s", model_name, resp.status_code,
                              resp.text[:200])
        except Exception as e:
            logging.debug("[Groq fallback] %s error: %s", model_name, e)
    return None


def call_ai_json(
    prompt: str,
    *,
    model: str = "grok_3",
    provider: Provider | None = None,
) -> Any:
    """Like :func:`call_ai` but parses the response as JSON.

    Automatically strips markdown code fences before parsing.
    """
    raw = call_ai(prompt, model=model, provider=provider)
    cleaned = strip_markdown_fences(raw)
    return json.loads(cleaned)
