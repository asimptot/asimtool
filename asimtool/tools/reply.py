"""Reply suggestion — generate professional response for a conversation."""

from __future__ import annotations

from ..core.provider import Provider, call_ai


def suggest_reply(
    messages: list[str],
    tone: str = "formal",
    custom_prompt: str = "",
    *,
    provider: Provider | None = None,
) -> str:
    """Suggest a professional reply for a conversation thread.

    The language of the reply is auto-detected from the latest messages.

    Parameters
    ----------
    messages : list[str]
        Conversation messages in order (alternating Person A / Person B).
        At least one message is required (up to 3).
    tone : str
        Tone of the reply (``"formal"``, ``"friendly"``, ``"casual"``, ``"human"``).
    custom_prompt : str
        Optional idea to incorporate into the reply.
    provider : Provider, optional

    Returns
    -------
    str
        Suggested reply text.

    Example
    -------
    >>> from asimtool.tools import suggest_reply
    >>> reply = suggest_reply(["Can we reschedule the meeting?"], tone="formal")
    >>> print(reply)
    """
    if not messages or not messages[0].strip():
        raise ValueError("At least one message is required.")

    # Detect language from the latest content
    try:
        import langdetect
        lang_sample = " ".join(filter(None, messages[1:] + ([custom_prompt] if custom_prompt else []))) or messages[0]
        lang_code = langdetect.detect(lang_sample)
    except Exception:
        lang_code = "en"

    # langdetect confuses Dutch with Afrikaans — remap af → nl
    if lang_code == "af":
        lang_code = "nl"

    lang_name_map = {
        "nl": "Dutch", "en": "English", "de": "German", "fr": "French",
        "es": "Spanish", "it": "Italian", "tr": "Turkish", "sv": "Swedish",
        "pt": "Portuguese", "ru": "Russian", "pl": "Polish", "ar": "Arabic",
        "zh-cn": "Chinese", "ja": "Japanese",
    }
    lang_name = lang_name_map.get(lang_code, lang_code.upper())

    # Build dialogue
    input1 = messages[0] if len(messages) >= 1 else ""
    input2 = messages[1] if len(messages) >= 2 else ""
    input3 = messages[2] if len(messages) >= 3 else ""

    if input3:
        responder = "Person B"
        dialogue = f"Person A: {input1}\nPerson B: {input2}\nPerson A: {input3}\n"
    elif input2:
        responder = "Person A"
        dialogue = f"Person A: {input1}\nPerson B: {input2}\n"
    else:
        responder = "Person B"
        dialogue = f"Person A: {input1}\n"

    if tone == "human":
        base_prompt = (
            f"You are {responder} in a real conversation. "
            f"Language: {lang_name} — reply ONLY in {lang_name}. "
            "Your reply must sound like a real human typed it — casual, natural, imperfect. "
            "Do NOT follow strict grammar rules. Use lowercase starts, contractions, relaxed punctuation. "
            "You may add natural fillers or small imperfections — like a real person texting. "
            "STRICT RULES: "
            "Do NOT repeat, echo, paraphrase, or reference what was just said to you. "
            "Get straight to your reply — no filler openers like 'Sure!', 'Of course!', 'Great!', 'Absolutely!' unless it fits naturally. "
            "If the context calls for it, ask a follow-up question — like a real person would. "
            "Never mention 'Person A' or 'Person B' in your reply. "
            "The output must NOT look AI-generated at all. "
            "Keep it to 1-2 sentences — focused, human, direct."
        )
    else:
        base_prompt = (
            f"You are {responder} in a real conversation. "
            f"Language: {lang_name} — reply ONLY in {lang_name}. "
            f"Tone: {tone}, natural and human — never robotic. "
            "STRICT RULES: "
            "Do NOT repeat, echo, paraphrase, or reference what was just said to you. "
            "Get straight to your reply — no filler openers like 'Sure!', 'Of course!', 'Great!', 'Absolutely!' unless it fits naturally. "
            "If the context calls for it, ask a follow-up question — like a real person would. "
            "Never mention 'Person A' or 'Person B' in your reply. "
            "Keep it to 1-2 sentences — focused, human, direct."
        )

    dialogue += f"\nWrite ONLY {responder}'s reply. Do NOT repeat or summarize what was said — just respond naturally as a human would."
    if custom_prompt:
        dialogue += f" Use this idea as loose inspiration (don't copy it literally): '{custom_prompt}'."

    final_prompt = base_prompt + "\n\nConversation:\n" + dialogue

    return call_ai(final_prompt, model="gpt-4o", provider=provider)
