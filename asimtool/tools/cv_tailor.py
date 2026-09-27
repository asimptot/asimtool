"""CV tailoring — adapt a CV/resume to a specific job description."""

from __future__ import annotations

import re

from ..core.provider import Provider, call_ai
from .extract_text import extract_text


def tailor_cv(
    cv_text: str = "",
    job_description: str = "",
    *,
    cv_file: str = "",
    provider: Provider | None = None,
) -> str:
    """Tailor a CV to a job description using AI.

    Parameters
    ----------
    cv_text : str
        Plain text of the CV. If empty, *cv_file* is used instead.
    job_description : str
        The job description to tailor the CV towards.
    cv_file : str
        Path to a PDF or DOCX CV file (used when *cv_text* is empty).
    provider : Provider, optional

    Returns
    -------
    str
        Updated CV text tailored to the job description.

    Example
    -------
    >>> from asimtool.tools import tailor_cv
    >>> result = tailor_cv(cv_text="...", job_description="...")
    >>> print(result[:200])
    """
    if not cv_text and cv_file:
        cv_text = extract_text(cv_file)

    if not cv_text or not cv_text.strip():
        raise ValueError("CV text is required (provide cv_text or cv_file).")
    if not job_description or not job_description.strip():
        raise ValueError("Job description is required.")

    prompt = (
        "You are an expert CV/resume writer and career coach.\n\n"
        "Your task is to tailor the candidate's CV to the job description below, "
        "making it a strong match for the role without fabricating any experience or skills.\n\n"
        "Instructions:\n"
        "- Reorder and rephrase bullet points to highlight the most relevant experience first.\n"
        "- Mirror keywords and terminology from the job description naturally.\n"
        "- Strengthen weak or vague phrases with concrete, impactful language.\n"
        "- Remove or de-emphasize experience that is clearly irrelevant to this role.\n"
        "- Keep the same sections and overall structure of the original CV.\n"
        "- Do NOT invent qualifications, degrees, or experiences that are not in the original CV.\n"
        "- Output the full updated CV text, ready to copy-paste.\n\n"
        f"--- JOB DESCRIPTION ---\n{job_description}\n\n"
        f"--- ORIGINAL CV ---\n{cv_text}\n\n"
        "--- UPDATED CV ---"
    )

    result = call_ai(prompt, model="gpt_4_5", provider=provider)

    # Strip trailing AI commentary
    result = re.sub(
        r'\n+(?:This (?:updated|tailored|revised)|I have (?:tailored|updated|revised)|The (?:updated|tailored)).*$',
        '', result, flags=re.IGNORECASE | re.DOTALL
    ).strip()

    return result
