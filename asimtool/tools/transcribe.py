"""Audio transcription using the Groq Whisper API."""

from __future__ import annotations

import os
from pathlib import Path

import requests


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
        Path to the audio file (mp3, wav, m4a, ogg, webm, etc.).
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
        files = {"file": (path.name, f, "audio/mpeg")}
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
