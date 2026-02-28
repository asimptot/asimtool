"""Text and word translation using AI."""

from __future__ import annotations

from ..core.provider import Provider, call_ai
from ..core.helpers import strip_quotes


def translate(
    text: str,
    target_language: str,
    *,
    provider: Provider | None = None,
) -> str:
    """Translate *text* into *target_language*.

    Parameters
    ----------
    text : str
        Source text to translate.
    target_language : str
        Target language name (e.g. ``"French"``, ``"Turkish"``).
    provider : Provider, optional
        Custom provider list.

    Returns
    -------
    str
        Translated text.

    Example
    -------
    >>> from asimtool.language import translate
    >>> translate("Hello, how are you?", "Turkish")
    'Merhaba, nasılsın?'
    """
    if not text.strip():
        raise ValueError("No text provided.")
    if not target_language.strip():
        raise ValueError("No target language provided.")

    prompt = (
        f"Translate the following sentence into {target_language}. "
        f"Provide an accurate and natural translation. "
        f"Do not add comments or explanations. "
        f"Return only the translated text. "
        f"Sentence: '{text}'"
    )

    result = call_ai(prompt, model="grok_3", provider=provider)
    return strip_quotes(result)


def translate_word(
    word: str,
    source_lang: str,
    target_lang: str,
    *,
    provider: Provider | None = None,
) -> str:
    """Translate a single word with explanation.

    Parameters
    ----------
    word : str
        The word to translate.
    source_lang : str
        Source language name.
    target_lang : str
        Target language name.

    Returns
    -------
    str
        Translation with explanation.
    """
    if not word.strip():
        raise ValueError("Word cannot be empty.")

    prompt = (
        f"Translate the word '{word}' from {source_lang} to {target_lang}. "
        f"Provide the translation and a brief explanation of usage."
    )

    return call_ai(prompt, model="grok_3", provider=provider)
