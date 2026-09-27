"""Utility tools — text extraction, transcription, chat, replies, CV, cover letter, TTS."""

from .extract_text import extract_text
from .transcribe import transcribe
from .chat import Chat
from .reply import suggest_reply
from .image_to_prompt import image_to_prompt
from .cv_tailor import tailor_cv
from .cover_letter import generate_cover_letter
from .tts import text_to_speech

__all__ = [
    "extract_text",
    "transcribe",
    "Chat",
    "suggest_reply",
    "image_to_prompt",
    "tailor_cv",
    "generate_cover_letter",
    "text_to_speech",
]
