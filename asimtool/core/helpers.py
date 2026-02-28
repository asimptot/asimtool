"""Helper utility functions."""

import re
import unicodedata


def is_valid_response(text: str) -> bool:
    """Check if response text is valid (not CJK/fullwidth characters).

    Some g4f providers occasionally return Chinese or Japanese text
    regardless of prompt language.  This filter rejects such responses
    so the retry loop can fall through to the next provider.
    """
    if not text:
        return False

    text = unicodedata.normalize("NFKC", text)

    for char in text:
        if (
            "\u4e00" <= char <= "\u9fff"
            or "\u3400" <= char <= "\u4dbf"
            or "\u20000" <= char <= "\u2a6df"
            or "\u2a700" <= char <= "\u2b73f"
            or "\u2b740" <= char <= "\u2b81f"
            or "\u2b820" <= char <= "\u2ceaf"
            or "\u2ceb0" <= char <= "\u2ebef"
            or "\u3000" <= char <= "\u303f"
            or "\uff00" <= char <= "\uffef"
        ):
            return False
    return True


def normalize_text(text: str, max_len: int = 2000) -> str:
    """Normalise text with NFKC and limit length."""
    text = unicodedata.normalize("NFKC", text)
    return text[:max_len]


def strip_markdown_fences(raw: str) -> str:
    """Remove surrounding ```json ... ``` fences from AI responses."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    if raw.endswith("```"):
        raw = raw[:-3].strip()
    return raw


def strip_quotes(text: str) -> str:
    """Remove matching outer quotes from a string."""
    if len(text) >= 2:
        if (text[0] == text[-1]) and text[0] in ("'", '"'):
            return text[1:-1]
    return text
