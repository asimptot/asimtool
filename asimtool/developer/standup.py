"""Standup summary generator — notes → spoken-style standup update."""

from __future__ import annotations

from ..core.helpers import normalize_text
from ..core.provider import Provider, call_ai


def generate_standup(
    notes: str,
    commit: str = "",
    *,
    provider: Provider | None = None,
) -> str:
    """Convert free-text notes into a natural standup summary.

    Parameters
    ----------
    notes : str
        Free-text developer notes.
    commit : str
        Optional recent code commit text.
    provider : Provider, optional

    Returns
    -------
    str
        Spoken-style standup sentences (no bullets, no lists).

    Example
    -------
    >>> from asimtool.developer import generate_standup
    >>> summary = generate_standup("Fixed login bug, started payment feature")
    >>> print(summary[:100])
    """
    text = normalize_text(notes)
    if commit:
        text += f"\n\nCode:\n{commit}"

    if not text.strip():
        raise ValueError("No input received.")

    prompt = (
        "You are an AI that converts notes or free-text input into short, natural, spoken-style "
        "English statements suitable for a Daily Standup meeting.\n\n"
        "For each topic mentioned, produce 1–2 sentence updates that a developer could say aloud.\n"
        "Do NOT add intro phrases like \"Here's your update\".\n"
        "Start directly with the content.\n\n"
        "Do not use bullet points. Do not list tasks.\n"
        "Provide flowing standup-ready sentences.\n\n"
        f"Input:\n{text}"
    )

    return call_ai(prompt, model="gpt_4_5", provider=provider)
