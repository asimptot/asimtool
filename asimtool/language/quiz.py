"""Vocabulary quiz generation with level-adaptive difficulty."""

from __future__ import annotations

import json
import random
import time
from typing import Dict, List, Optional

from ..core.helpers import strip_markdown_fences
from ..core.provider import Provider, call_ai

# Topic pool for variety
_TOPICS: List[str] = [
    "daily life", "food and drinks", "travel and tourism", "work and business",
    "education and school", "nature and environment", "technology", "sports and hobbies",
    "health and medicine", "family and relationships", "shopping and money",
    "weather and seasons", "animals", "transportation", "home and furniture",
    "clothing and fashion", "art and culture", "emotions and feelings",
]

_WORD_TYPES: List[str] = ["noun", "verb", "adjective", "adverb", "common phrase"]

# CEFR level descriptions
_LEVEL_DESCS = {
    "A1": "very basic, beginner level",
    "A2": "elementary, simple everyday",
    "B1": "intermediate, common",
    "B2": "upper-intermediate, familiar",
    "C1": "advanced, nuanced",
    "C2": "proficiency level, sophisticated",
}

# Distractor strategy per level range
_OPTION_STRATEGIES = {
    "easy": (
        "Wrong options MUST be from COMPLETELY DIFFERENT categories "
        "(e.g., if word is animal, wrong options should be objects/actions/colors, NOT other animals). "
        "This makes it easier for beginners."
    ),
    "medium": (
        "Wrong options should be from the SAME CATEGORY but clearly different "
        "(e.g., if word is 'cat', wrong options can be 'dog', 'bird', 'fish'). "
        "Requires understanding context."
    ),
    "hard": (
        "Wrong options should have SIMILAR MEANINGS or subtle differences "
        "(e.g., if word is 'happy', wrong options should be 'joyful', 'content', 'cheerful'). "
        "Tests nuanced understanding."
    ),
}

# Language display name → native name
_LANGUAGE_MAP = {
    "English": "English",
    "German": "Deutsch",
    "French": "Français",
    "Italian": "Italiano",
    "Dutch": "Nederlands",
    "Spanish": "Español",
    "Swedish": "Svenska",
    "Turkish": "Türkçe",
}

# Browser language code → full language name
_CODE_TO_LANG = {
    "tr": "Turkish", "en": "English", "de": "German", "fr": "French",
    "nl": "Dutch", "es": "Spanish", "sv": "Swedish", "it": "Italian",
}


def generate_quiz(
    language: str,
    level: str = "A1",
    options_language: str = "English",
    *,
    provider: Provider | None = None,
) -> Dict:
    """Generate a vocabulary MCQ with four options.

    Parameters
    ----------
    language : str
        The quiz word language (e.g. ``"German"``).
    level : str
        CEFR level ``"A1"`` – ``"C2"``.
    options_language : str
        Language in which the answer options are written (e.g. ``"Turkish"``).
    provider : Provider, optional
        Custom provider list.

    Returns
    -------
    dict
        ``{"word": str, "options": [str, str, str, str], "correct": int}``

    Example
    -------
    >>> from asimtool.language import generate_quiz
    >>> q = generate_quiz("German", "A2", "English")
    >>> print(q["word"], q["options"])
    """
    if not language:
        raise ValueError("Quiz language is required.")

    target_lang = _LANGUAGE_MAP.get(language, language)
    opts_lang = options_language if options_language not in _CODE_TO_LANG else _CODE_TO_LANG[options_language]

    random.seed(int(time.time() * 1000))
    selected_topic = random.choice(_TOPICS)
    selected_type = random.choice(_WORD_TYPES)
    level_desc = _LEVEL_DESCS.get(level, "common")

    if level in ("A1", "A2"):
        option_strategy = _OPTION_STRATEGIES["easy"]
    elif level in ("B1", "B2"):
        option_strategy = _OPTION_STRATEGIES["medium"]
    else:
        option_strategy = _OPTION_STRATEGIES["hard"]

    # Turkish-specific example to ensure proper characters
    example_json = ""
    if opts_lang == "Turkish":
        example_json = (
            '\nExample for Turkish:\n'
            '{\n  "word": "Katze",\n  "options": ["kedi", "köpek", "kuş", "balık"],\n  "correct": 0\n}\n'
            'Note: See how "köpek" has ö and "kuş" has ş - ALWAYS use these characters!\n'
        )

    prompt = (
        f"Generate a vocabulary quiz question for {target_lang} language learners.\n\n"
        f"Requirements:\n"
        f"- Topic: {selected_topic}\n"
        f"- Word type: {selected_type}\n"
        f"- Difficulty: {level} ({level_desc})\n"
        f"- Question word language: {target_lang}\n"
        f"- Answer options language: {opts_lang}\n\n"
        f"OPTION DIFFICULTY STRATEGY:\n{option_strategy}\n\n"
        f"CRITICAL: Use proper native characters (UTF-8) for {opts_lang}. DO NOT use ASCII replacements.\n"
        f"For Turkish: MUST use İ,I,i,ı,Ç,ç,Ğ,ğ,Ö,ö,Ş,ş,Ü,ü\n"
        f"For German: ä,ö,ü,Ä,Ö,Ü,ß\n"
        f"For French: é,è,ê,ç,à,ù,É,È,Ê,Ç,À,Ù\n\n"
        f"{example_json}\n"
        f"Choose a DIFFERENT, RANDOM word from this topic that fits the level.\n"
        f"Return ONLY valid UTF-8 encoded JSON (no markdown, no explanations):\n\n"
        f'{{\n  "word": "the word in {target_lang}",\n'
        f'  "options": ["correct {opts_lang} translation", "wrong 1 in {opts_lang}", '
        f'"wrong 2 in {opts_lang}", "wrong 3 in {opts_lang}"],\n  "correct": 0\n}}\n\n'
        f"Rules:\n"
        f"- Pick a unique {selected_type} related to {selected_topic}\n"
        f"- Must be appropriate for {level} level learners\n"
        f"- The word must be in {target_lang}\n"
        f"- All 4 options MUST use native alphabet correctly\n"
        f"- First option in array must be the correct translation\n"
        f"- IMPORTANT: Follow the option difficulty strategy above\n"
        f"- Return ONLY the JSON object"
    )

    raw = call_ai(prompt, model="grok_3", provider=provider)
    content = strip_markdown_fences(raw)
    quiz_data = json.loads(content)

    # Validate
    for key in ("word", "options", "correct"):
        if key not in quiz_data:
            raise ValueError(f"Missing key '{key}' in quiz response.")
    if len(quiz_data["options"]) != 4:
        raise ValueError("Quiz must have exactly 4 options.")

    # Shuffle options while tracking the correct answer
    options = list(quiz_data["options"])
    correct_answer = options[quiz_data["correct"]]
    random.shuffle(options)
    new_correct_index = options.index(correct_answer)

    return {
        "word": quiz_data["word"],
        "options": options,
        "correct": new_correct_index,
    }
