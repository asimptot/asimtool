"""Audio transcription using the Groq Whisper API."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path

import requests

# Containers Whisper accepts, mapped to the MIME type we send.
# iOS Voice Memos recordings (.m4a/.m4r/.aac/.caf) are AAC and need an
# explicit type — the stdlib often guesses "application/octet-stream".
AUDIO_MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".m4r": "audio/mp4",
    ".aac": "audio/aac",
    ".caf": "audio/x-caf",
    ".mp4": "audio/mp4",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".opus": "audio/opus",
    ".webm": "audio/webm",
    ".flac": "audio/flac",
    ".mpga": "audio/mpeg",
    ".amr": "audio/amr",
    ".3gp": "audio/3gpp",
}


def _mime_for(path: Path) -> str:
    """Best-effort MIME type for an audio file."""
    suffix = path.suffix.lower()
    if suffix in AUDIO_MIME_TYPES:
        return AUDIO_MIME_TYPES[suffix]
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def transcribe(
    audio_path: str,
    *,
    api_key: str | None = None,
    language: str | None = None,
    model: str = "whisper-large-v3",
) -> str:
    """Transcribe an audio file using Groq's Whisper API.

    Groq's free tier allows ~14 400 requests/day.

    Parameters
    ----------
    audio_path : str
        Path to the audio file. MP3, WAV, M4A/M4R/AAC/CAF (iOS Voice Memos),
        OGG, OPUS, WEBM and FLAC are supported.
    api_key : str, optional
        Groq API key. Falls back to ``$GROQ_API_KEY``.
    language : str, optional
        BCP-47 hint (e.g. ``"en"``, ``"nl"``, ``"tr"``).
    model : str
        Whisper model name (default ``"whisper-large-v3"``).

    Returns
    -------
    str
        Transcribed text.

    Example
    -------
    >>> from asimtool.tools import transcribe
    >>> text = transcribe("meeting.mp3", language="en")
    >>> print(text[:200])
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    key = api_key or os.getenv("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY not configured. Set it as an environment variable or pass api_key."
        )

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {key}"}

    with open(str(path), "rb") as f:
        files = {"file": (path.name, f, _mime_for(path))}
        data = {"model": model, "response_format": "json"}
        if language:
            data["language"] = language

        resp = requests.post(url, headers=headers, files=files, data=data, timeout=30)

    if resp.status_code == 200:
        return resp.json().get("text", "")

    # Parse error
    error_msg = resp.text
    try:
        error_msg = resp.json().get("error", {}).get("message", error_msg)
    except Exception:
        pass
    raise RuntimeError(f"Transcription failed ({resp.status_code}): {error_msg}")
