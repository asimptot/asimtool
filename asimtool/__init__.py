"""
asimtool — AI-powered developer & language toolkit.

A standalone Python package extracted from the AsimAI project.
Wraps g4f providers for grammar checking, translation, quizzes,
bug-report formatting, PR reviews, trip planning, and much more.

Quick start
-----------
>>> import asimtool
>>> corrected = asimtool.check_grammar("me go store yesterday")
>>> translated = asimtool.translate("Hello world", "German")
>>> quiz = asimtool.generate_quiz("German", "A2", "English")
"""

__version__ = "0.1.0"

# ── Language ────────────────────────────────────────────────────
from .language.grammar import check_grammar
from .language.translate import translate, translate_word
from .language.news import get_news
from .language.quiz import generate_quiz
from .language.vocabulary import build_vocabulary
from .language.listening import generate_listening

# ── Developer ───────────────────────────────────────────────────
from .developer.bug import improve_bug_description
from .developer.testcases import generate_test_cases
from .developer.pr_review import review_pull_request
from .developer.specsheet import validate_specsheet
from .developer.requirements import validate_requirements
from .developer.code_assistant import ask_about_code
from .developer.standup import generate_standup

# ── Entertainment ───────────────────────────────────────────────
from .entertainment.movie import recommend as recommend_movie
from .entertainment.trip import plan_trip
from .entertainment.cafe import find_venue
from .entertainment.song import generate_lyrics
from .entertainment.solar import optimize_solar

# ── Tools ───────────────────────────────────────────────────────
from .tools.extract_text import extract_text
from .tools.transcribe import transcribe
from .tools.chat import Chat
from .tools.reply import suggest_reply
from .tools.image_to_prompt import image_to_prompt

# ── Core (advanced usage) ──────────────────────────────────────
from .core.provider import Provider, call_ai, call_ai_json

__all__ = [
    # Language
    "check_grammar", "translate", "translate_word",
    "get_news", "generate_quiz", "build_vocabulary", "generate_listening",
    # Developer
    "improve_bug_description", "generate_test_cases", "review_pull_request",
    "validate_specsheet", "validate_requirements", "ask_about_code", "generate_standup",
    # Entertainment
    "recommend_movie", "plan_trip", "find_venue", "generate_lyrics", "optimize_solar",
    # Tools
    "extract_text", "transcribe", "Chat", "suggest_reply", "image_to_prompt",
    # Core
    "Provider", "call_ai", "call_ai_json",
]
