"""Specification sheet validator."""

from __future__ import annotations

from ..core.provider import Provider, call_ai


def validate_specsheet(
    specsheet: str,
    *,
    provider: Provider | None = None,
) -> str:
    """Validate a specification document from a tester's perspective.

    Parameters
    ----------
    specsheet : str
        The specification text to validate.
    provider : Provider, optional

    Returns
    -------
    str
        Analysis including questions for developers and business team.

    Example
    -------
    >>> from asimtool.developer import validate_specsheet
    >>> result = validate_specsheet("The system shall process orders within 5 seconds…")
    >>> print(result[:120])
    """
    if not specsheet.strip():
        raise ValueError("Specsheet text is required.")

    prompt = (
        "Please validate the following specsheet on my behalf using I language as the tester. Evaluate "
        "functionality only impacts on other components. Include the following details: "
        f"\n\nSpecsheet:\n{specsheet}\n\n"
        "Questions for Developers:\n- Determine the questions that can be asked to the developers?\n\n"
        "Questions for Business Team:\n- Determine the questions that can be asked to the business team?\n\n"
        "Analyze like a tester and identify the problems."
    )

    return call_ai(prompt, model="grok_3", provider=provider)
