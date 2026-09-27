"""Grammar check / correction using AI."""

from __future__ import annotations

from ..core.provider import Provider, call_ai

# Map ISO 639-1 codes to full language names
_ISO_TO_LANG = {
    "nl": "Dutch", "en": "English", "de": "German", "fr": "French",
    "es": "Spanish", "it": "Italian", "pt": "Portuguese", "tr": "Turkish",
    "ru": "Russian", "ar": "Arabic", "zh": "Chinese", "ja": "Japanese",
    "ko": "Korean", "pl": "Polish", "sv": "Swedish", "da": "Danish",
    "no": "Norwegian", "fi": "Finnish", "cs": "Czech", "ro": "Romanian",
    "hu": "Hungarian", "el": "Greek", "uk": "Ukrainian", "hi": "Hindi",
    "id": "Indonesian", "th": "Thai", "vi": "Vietnamese",
}


def check_grammar(
    text: str,
    *,
    tone: str = "formal",
    provider: Provider | None = None,
) -> str:
    """Correct the grammar of *text* and return only the corrected version.

    Parameters
    ----------
    text : str
        The input text to correct.
    tone : str
        ``"formal"``, ``"informal"``, or ``"human"`` (makes text sound natural/human).
    provider : Provider, optional
        Custom provider list.

    Returns
    -------
    str
        Corrected text.

    Example
    -------
    >>> from asimtool.language import check_grammar
    >>> check_grammar("He go to school yesterday")
    'He went to school yesterday.'
    """
    if not text.strip():
        raise ValueError("Input text cannot be empty.")

    # Detect language for more accurate correction
    detected_lang = "unknown"
    try:
        from langdetect import detect as _detect_lang
        detected_lang = _detect_lang(text)
        # langdetect confuses Dutch with Afrikaans — remap af → nl
        if detected_lang == "af":
            detected_lang = "nl"
    except Exception:
        pass

    lang_name = _ISO_TO_LANG.get(detected_lang, detected_lang)
    if detected_lang != "unknown":
        lang_instruction = (
            f"The input language is {lang_name}. You MUST output ONLY in {lang_name}. "
            "Do NOT translate to any other language. Do NOT change the language under any circumstances."
        )
    else:
        lang_instruction = (
            "Return the corrected sentence in the same language as the input."
        )

    if tone == "human":
        instruction = (
            "You are a human text rewriter. Your ONLY job is to make the text sound like a real person typed it naturally.\n"
            f"{lang_instruction}\n"
            "Do NOT fix grammar, spelling, or punctuation errors — leave them as-is or even introduce small natural imperfections.\n"
            "Do NOT translate. Do NOT switch languages.\n"
            "Use a casual, natural human tone. You may start sentences with lowercase letters.\n"
            "Use natural fillers, contractions, and relaxed punctuation like a real person would.\n"
            "The output must NOT look AI-generated at all. Make it feel authentic and human.\n"
            "Return ONLY the rewritten text. No explanations, no quotes, no extra words."
        )
    elif tone == "informal":
        instruction = (
            "You are a grammar corrector. Your ONLY job is to fix grammar, spelling, and phrasing errors.\n"
            f"{lang_instruction}\n"
            "Do NOT translate. Do NOT switch languages. Use informal, casual tone.\n"
            "Return ONLY the corrected text. No explanations, no quotes, no extra words."
        )
    else:
        instruction = (
            "You are a grammar corrector. Your ONLY job is to fix grammar, spelling, and phrasing errors.\n"
            f"{lang_instruction}\n"
            "Do NOT translate. Do NOT switch languages. Use formal, professional tone.\n"
            "Return ONLY the corrected text. No explanations, no quotes, no extra words."
        )

    prompt = f"{instruction}\n\nINPUT TEXT:\n{text}"
    return call_ai(prompt, model="grok_3", provider=provider)
