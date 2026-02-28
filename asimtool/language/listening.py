"""Listening comprehension exercise generation."""

from __future__ import annotations

import json
from typing import Dict, Optional

from ..core.helpers import strip_markdown_fences
from ..core.provider import Provider, call_ai

# BCP-47 → full language name
_LANG_MAP = {
    "nl-NL": "Dutch", "en-GB": "English", "en-US": "English",
    "fr-FR": "French", "de-DE": "German", "it-IT": "Italian",
    "es-ES": "Spanish", "sv-SE": "Swedish", "tr-TR": "Turkish",
}

# Level-specific complexity + distractor rules
_LEVEL_CONFIG = {
    "A1": {
        "desc": "very short and simple (3-4 sentences, basic vocabulary, present tense only, common everyday words)",
        "distractor": "The wrong answer options should be clearly different from the correct answer — simple, obviously wrong distractors.",
    },
    "A2": {
        "desc": "short and straightforward (5-6 sentences, elementary vocabulary, present and past tense)",
        "distractor": "Wrong options should be plausible at a surface level but clearly different from the passage content.",
    },
    "B1": {
        "desc": "medium complexity (7-9 sentences, varied vocabulary, mixed tenses)",
        "distractor": "Wrong options should be somewhat plausible — similar topic but different meaning, requiring careful listening.",
    },
    "B2": {
        "desc": "upper-intermediate (10-12 sentences, rich vocabulary, complex sentences, nuanced ideas)",
        "distractor": "Wrong options should be tricky — use near-synonyms, partially true statements, or subtle factual differences.",
    },
    "C1": {
        "desc": "advanced and sophisticated (13-16 sentences, academic or professional vocabulary, varied structures, implied meanings)",
        "distractor": "Wrong options must be highly deceptive — partially correct, require inference, or contain subtle logical traps.",
    },
    "C2": {
        "desc": "mastery level (17-20 sentences, native-speed complexity, idiomatic expressions, abstract reasoning, dense information)",
        "distractor": "Wrong options must be extremely challenging — practically indistinguishable without perfect comprehension.",
    },
}


def generate_listening(
    language: str = "English",
    level: str = "B1",
    num_questions: int = 5,
    *,
    provider: Provider | None = None,
) -> Dict:
    """Generate a listening comprehension passage + MCQ.

    Parameters
    ----------
    language : str
        Target language or BCP-47 locale code (e.g. ``"de-DE"`` or ``"German"``).
    level : str
        CEFR level ``"A1"`` – ``"C2"``.
    num_questions : int
        Number of comprehension questions.
    provider : Provider, optional

    Returns
    -------
    dict
        ``{"passage": str, "questions": [{"question", "options", "correct_index"}, ...]}``

    Example
    -------
    >>> from asimtool.language import generate_listening
    >>> ex = generate_listening("French", "B1", 3)
    >>> print(ex["passage"][:80])
    """
    lang_name = _LANG_MAP.get(language, language)
    cfg = _LEVEL_CONFIG.get(level, _LEVEL_CONFIG["B1"])
    level_desc = cfg["desc"]
    distractor_instruction = cfg["distractor"]

    prompt = (
        f"Create a listening comprehension exercise in {lang_name} at CEFR level {level}.\n\n"
        f"Requirements:\n"
        f"- Write a passage that is {level_desc}.\n"
        f"- Choose an interesting, varied topic randomly (e.g. travel, science, daily life, "
        f"culture, environment, technology, history, food, health, sports).\n"
        f"- Write exactly {num_questions} multiple-choice questions about the passage.\n"
        f"- Each question must have exactly 4 options (A, B, C, D). Only one option is correct.\n"
        f"- DISTRACTOR RULE: {distractor_instruction}\n\n"
        f"Return ONLY valid JSON in this exact format, no extra text:\n"
        f'{{\n  "passage": "The full passage text here.",\n  "questions": [\n    {{\n'
        f'      "question": "Question text here?",\n'
        f'      "options": ["Option A", "Option B", "Option C", "Option D"],\n'
        f'      "correct_index": 0\n    }}\n  ]\n}}\n\n'
        f"correct_index is 0-based (0=A, 1=B, 2=C, 3=D)."
    )

    raw = call_ai(prompt, model="gpt-4o", provider=provider)
    content = strip_markdown_fences(raw)
    exercise = json.loads(content)

    if "passage" not in exercise or "questions" not in exercise:
        raise ValueError("Invalid listening exercise response.")
    if len(exercise["questions"]) == 0:
        raise ValueError("No questions generated.")

    return exercise
