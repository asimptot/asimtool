"""g4f provider management with automatic retry / fallback."""

from __future__ import annotations

import json
import random
from typing import Any, List, Optional, Tuple

import g4f
from g4f.client import Client

from .helpers import is_valid_response, strip_markdown_fences

# ---------------------------------------------------------------------------
# Default provider names (resolved lazily)
# ---------------------------------------------------------------------------
DEFAULT_PROVIDER_NAMES: list[str] = [
    "OperaAria",
    "AnyProvider",
    "Yqcloud",
    "TeachAnything",
    "Mintlify",
]


def _resolve_providers(names: list[str] | None = None) -> list:
    """Convert provider-name strings into ``g4f.Provider.*`` classes."""
    names = names or DEFAULT_PROVIDER_NAMES
    providers = []
    for name in names:
        cls = getattr(g4f.Provider, name, None)
        if cls is not None:
            providers.append(cls)
    if not providers:
        raise RuntimeError(
            f"None of the requested providers could be resolved: {names}"
        )
    return providers


# ---------------------------------------------------------------------------
# Public provider wrapper
# ---------------------------------------------------------------------------

class Provider:
    """Thin wrapper around a list of g4f providers.

    Usage::

        p = Provider()                       # use defaults
        p = Provider(["OperaAria", "Yqcloud"])  # custom list
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

    raise RuntimeError(f"All providers failed. Last error: {last_err}")


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
