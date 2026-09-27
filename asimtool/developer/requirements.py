"""Requirements validator — optionally compared against code commits."""

from __future__ import annotations

from ..core.helpers import normalize_text
from ..core.provider import Provider, call_ai


def validate_requirements(
    requirements: str,
    risk: str = "",
    commit: str = "",
    *,
    provider: Provider | None = None,
) -> str:
    """Validate requirements (with optional commit diff for comparison).

    Parameters
    ----------
    requirements : str
        The requirements text.
    risk : str
        Risk description.
    commit : str
        Optional code commit / diff for cross-validation.
    provider : Provider, optional

    Returns
    -------
    str
        Validation analysis with issues and questions.

    Example
    -------
    >>> from asimtool.developer import validate_requirements
    >>> result = validate_requirements("Login must support 2FA", risk="Security")
    >>> print(result[:100])
    """
    requirements = normalize_text(requirements)
    risk = normalize_text(risk)
    commit = normalize_text(commit)

    if commit:
        prompt = (
            f"Validate the following commit against the specified requirements and risk. Assess whether "
            f"it meets the overall system-level architecture and design. Evaluate functionality only impacts on other "
            f"components. Include the following details:\n\n"
            f"Requirements:\n{requirements}\n\n"
            f"Risk:\n{risk}\n\n"
            f"Code:\n{commit}\n\n"
            f"Issues Identified:\n- Identify specific lines of code that may present potential problems, "
            f"focusing on integration points, edge cases, and dependencies.\n\n"
            f"Approved Changes:\n- List and describe the changes that meet the requirements and risk, including positive impacts on system stability.\n\n"
            f"Questions:\n- Questions to ask a developer regarding impact on system-level functionality, edge cases, and interactions."
        )
    else:
        prompt = (
            f"Please validate the following requirements using I language as the tester. "
            f"Evaluate functionality only impacts on other components.\n\n"
            f"Requirements:\n{requirements}\n\n"
            f"Risk:\n{risk}\n\n"
            f"Issues Identified:\n- Identify and quote specific lines of code that may present potential problems, "
            f"focusing on system-level interactions, boundary conditions, and integration dependencies.\n\n"
            f"Questions:\n- Questions to ask a developer about overall system behavior, "
            f"including integration, edge cases, and areas where further testing is needed."
        )

    return call_ai(prompt, model="gpt_4_5", provider=provider)
