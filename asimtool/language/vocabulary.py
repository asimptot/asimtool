"""Vocabulary builder — word meanings and example sentences."""

from __future__ import annotations

import json
from typing import Dict, List, Optional

from ..core.helpers import strip_markdown_fences
from ..core.provider import Provider, call_ai


def build_vocabulary(
    words: str | List[str],
    word_language: str = "English",
    meaning_language: str = "English",
    *,
    provider: Provider | None = None,
) -> List[Dict[str, str]]:
    """Return meaning + example for each word.

    Parameters
    ----------
    words : str | list[str]
        Comma/newline-separated string, or list of words. Max 20.
    word_language : str
        Language the words are in (e.g. ``"German"``).
    meaning_language : str
        Language the meanings should be written in.
    provider : Provider, optional

    Returns
    -------
    list[dict]
        Each dict has ``word``, ``meaning``, ``example``.

    Example
    -------
    >>> from asimtool.language import build_vocabulary
    >>> result = build_vocabulary("Hund, Katze", "German", "English")
    >>> for w in result:
    ...     print(w["word"], "→", w["meaning"])
    """
    if isinstance(words, str):
        word_list = [w.strip() for w in words.replace(",", "\n").splitlines() if w.strip()]
    else:
        word_list = [w.strip() for w in words if w.strip()]

    if not word_list:
        raise ValueError("Please provide at least one word.")

    word_list = word_list[:20]
    formatted = "\n".join(f"- {w}" for w in word_list)

    prompt = (
        f"You are a language learning assistant.\n\n"
        f"The user is learning {word_language}. For each word below, provide:\n"
        f"1. Its meaning explained in {meaning_language} (clear and concise, 1-2 sentences)\n"
        f"2. One natural example sentence written in {word_language} (the word's original language)\n\n"
        f"Words ({word_language}):\n{formatted}\n\n"
        f"Return ONLY valid JSON — an array with one object per word, no extra text:\n"
        f'[\n  {{\n    "word": "original word",\n    "meaning": "meaning in {meaning_language}",\n'
        f'    "example": "example sentence in {word_language}"\n  }}\n]'
    )

    raw = call_ai(prompt, model="gpt-4o", provider=provider)
    content = strip_markdown_fences(raw)
    result = json.loads(content)

    if not isinstance(result, list) or len(result) == 0:
        raise ValueError("Empty or invalid vocabulary response.")

    return result
