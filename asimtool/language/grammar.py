"""Grammar check / correction using AI."""

from __future__ import annotations

from ..core.provider import Provider, call_ai


def check_grammar(
    text: str,
    *,
    tone: str = "formal",
    provider: Provider | None = None,
) -> str:
    """Correct the grammar of *text* and return only the corrected version.

    Parameters
    ----------
    text : str
        The input text to correct.
    tone : str
        ``"formal"`` or ``"informal"``.
    provider : Provider, optional
        Custom provider list.

    Returns
    -------
    str
        Corrected text.

    Example
    -------
    >>> from asimtool.language import check_grammar
    >>> check_grammar("He go to school yesterday")
    'He went to school yesterday.'
    """
    if not text.strip():
        raise ValueError("Input text cannot be empty.")

    if tone == "informal":
        instruction = (
            "Write informally in the following sentence and return only the corrected version. "
            "Please also consider the logic of sentences. Return only the context not your personal words! "
            "Do not use quotes. "
            "Return the corrected sentence in the same language as the input."
        )
    else:
        instruction = (
            "Write formally in the following sentence and return only the corrected version. "
            "Please also consider the logic of sentences. Return only the context not your personal words! "
            "Do not use quotes. "
            "Return the corrected sentence in the same language as the input."
        )

    prompt = f"{instruction}: '{text}'"
    return call_ai(prompt, model="grok_3", provider=provider)
