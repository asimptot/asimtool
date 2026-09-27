"""Helper utility functions."""

import re
import unicodedata


def is_valid_response(text: str) -> bool:
    """Check if response text is valid (not CJK/fullwidth, not an HTML page).

    Some g4f providers occasionally return Chinese or Japanese text
    regardless of prompt language.  Others return a Cloudflare / captcha HTML
    page instead of an answer.  Both cases are rejected here so the retry
    loop can fall through to the next provider.
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

    # Reject provider error pages (Cloudflare challenge, captcha, raw HTML).
    lowered = text.lower()
    if lowered.lstrip().startswith(("<!doctype html", "<html")) or "</html>" in lowered:
        return False
    if "cf-browser-verification" in lowered or "just a moment..." in lowered:
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


def extract_json_object(text: str):
    """Extract the first balanced JSON object/array from an LLM response.

    Tries a fenced ```json block first, then falls back to a balanced-brace
    scan that is string/escape aware.  Returns ``None`` when nothing parses.
    """
    import json as _json

    if not text:
        return None

    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.S)
    if fence:
        try:
            return _json.loads(fence.group(1))
        except Exception:
            pass

    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return _json.loads(text[start:i + 1])
                    except Exception:
                        break
    return None


def make_links_clickable(text: str) -> str:
    """Convert URLs in text to clickable HTML links."""
    url_pattern = r"(https?://[^\s]+)"
    return re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', text)
