"""Text-to-Speech via edge-tts (Microsoft Neural TTS voices)."""

from __future__ import annotations

import asyncio
import io

_EDGE_TTS_VOICES = {
    "tr": "tr-TR-EmelNeural",
    "en": "en-US-JennyNeural",
    "nl": "nl-NL-ColetteNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "it": "it-IT-ElsaNeural",
    "es": "es-ES-ElviraNeural",
    "sv": "sv-SE-SofieNeural",
    "ar": "ar-SA-ZariyahNeural",
    "ja": "ja-JP-NanamiNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "pt": "pt-BR-FranciscaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "ko": "ko-KR-SunHiNeural",
}


def text_to_speech(
    text: str,
    lang: str = "en",
    rate: float = 0.0,
    output_file: str = "",
) -> bytes:
    """Convert text to speech using Microsoft Neural TTS voices.

    Parameters
    ----------
    text : str
        Text to convert to speech (max 2000 chars).
    lang : str
        Language code (e.g. ``"en"``, ``"tr"``, ``"nl"``, ``"de"``).
    rate : float
        Speech rate adjustment (-1.0 to 1.0). 0 is normal speed.
    output_file : str
        Optional path to save the MP3 file. If empty, returns bytes only.

    Returns
    -------
    bytes
        MP3 audio data.

    Raises
    ------
    ImportError
        If ``edge-tts`` is not installed.
    ValueError
        If text is empty.
    RuntimeError
        If TTS generation fails.

    Example
    -------
    >>> from asimtool.tools import text_to_speech
    >>> audio = text_to_speech("Hello world!", lang="en")
    >>> with open("output.mp3", "wb") as f:
    ...     f.write(audio)
    """
    try:
        import edge_tts
    except ImportError:
        raise ImportError("edge-tts is required for TTS: pip install edge-tts")

    if not text or not text.strip():
        raise ValueError("Text cannot be empty.")

    text = text[:2000]

    lang_base = lang.split("-")[0].lower()
    voice = _EDGE_TTS_VOICES.get(lang_base, "en-US-JennyNeural")

    rate_pct = int(rate * 100)
    rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"

    async def _generate():
        communicate = edge_tts.Communicate(text, voice, rate=rate_str)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data

    try:
        audio = asyncio.run(_generate())
    except RuntimeError:
        # If already in an event loop, use nest_asyncio or create new loop
        loop = asyncio.new_event_loop()
        try:
            audio = loop.run_until_complete(_generate())
        finally:
            loop.close()

    if not audio:
        raise RuntimeError("TTS generation returned empty audio.")

    if output_file:
        with open(output_file, "wb") as f:
            f.write(audio)

    return audio
