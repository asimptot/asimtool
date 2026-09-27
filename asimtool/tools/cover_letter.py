"""Cover letter generation — a personalised letter from a CV + job description."""

from __future__ import annotations

import re
import unicodedata

from ..core.provider import Provider, call_ai
from .extract_text import extract_text

TONE_INSTRUCTIONS = {
    "professional": "Write in a formal, professional tone.",
    "enthusiastic": "Write with genuine enthusiasm and energy — show passion for the role.",
    "concise": "Be concise and to the point. Keep the letter under 300 words.",
}

COVER_LETTER_PROMPT = (
    "You are an expert career coach and professional writer.\n\n"
    "Write a compelling, personalised cover letter. Use ONLY experience and "
    "skills from the candidate's CV — do NOT invent anything.\n\n"
    "LANGUAGE — critical: Detect the language of the job description and write "
    "the ENTIRE cover letter in that same language. If the job description is in "
    "Dutch, write in Dutch. If it is in German, write in German. If it is in "
    "English, write in English. Never mix languages.\n\n"
    "Tone: {tone_instruction}\n\n"
    "FORMATTING — critical:\n"
    "- Separate every section with exactly ONE blank line.\n"
    "- Do NOT include labels, numbers, or headings of any kind.\n"
    "- Do NOT include a date.\n"
    "- NEVER put punctuation (commas, periods, etc.) on a separate line.\n"
    "- After \"Dear Hiring Manager,\" the NEXT line must be blank, then start "
    "the opening paragraph.\n\n"
    "Output in this exact order, each separated by a blank line:\n\n"
    "1. Candidate name on line 1, contact details on line 2.\n"
    "2. Salutation: Dear Hiring Manager,\n"
    "3. Opening paragraph (3-4 sentences): genuine excitement about the "
    "specific role and company.\n"
    "4. First body paragraph (3-4 sentences): most relevant achievements and "
    "experience.\n"
    "5. Second body paragraph (3-4 sentences): additional skills or culture fit.\n"
    "6. Closing paragraph (2-3 sentences): enthusiasm and availability for interview.\n"
    "7. Sign-off (e.g. Kind regards,)\n"
    "8. Candidate full name.\n\n"
    "--- JOB DESCRIPTION ---\n{job_description}\n\n"
    "--- CANDIDATE CV ---\n{cv_text}\n\n"
    "--- COVER LETTER ---"
)


def _clean_letter(text: str) -> str:
    """Normalise whitespace, drop punctuation-only lines, strip stray tags."""
    text = unicodedata.normalize("NFKC", text or "").strip()
    # Provider-internal conversation ids sometimes leak into the answer.
    text = re.sub(r"\s*#[A-Z]{2,}#[a-f0-9\-]{30,}#\s*$", "", text).strip()

    cleaned: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        if not any(c.isalnum() for c in stripped):
            continue  # punctuation-only line
        cleaned.append(line)

    return re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned)).strip()


def generate_cover_letter(
    job_description: str,
    *,
    cv_text: str = "",
    cv_file: str = "",
    tone: str = "professional",
    provider: Provider | None = None,
) -> str:
    """Generate a personalised cover letter for a job.

    The letter is written in the language of the job description.

    Parameters
    ----------
    job_description : str
        The full job advertisement text.
    cv_text : str
        Plain text of the CV. If empty, *cv_file* is read instead.
    cv_file : str
        Path to a PDF/DOCX CV file (used when *cv_text* is empty).
    tone : str
        ``"professional"``, ``"enthusiastic"`` or ``"concise"``.
    provider : Provider, optional

    Returns
    -------
    str
        The formatted cover letter.

    Raises
    ------
    ValueError
        When the CV text or the job description is missing.

    Example
    -------
    >>> from asimtool.tools import generate_cover_letter
    >>> letter = generate_cover_letter("Python developer at Acme...", cv_file="cv.pdf")
    >>> print(letter)
    """
    if not job_description or not job_description.strip():
        raise ValueError("Job description is required.")
    if not cv_text and cv_file:
        cv_text = extract_text(cv_file)
    if not cv_text or not cv_text.strip():
        raise ValueError("CV text is required (provide cv_text or cv_file).")

    tone_instruction = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["professional"])

    result = call_ai(
        COVER_LETTER_PROMPT.format(
            tone_instruction=tone_instruction,
            job_description=job_description,
            cv_text=cv_text,
        ),
        model="gpt_4_5",
        provider=provider,
    )
    return _clean_letter(result)
