"""Test case generator — requirements → markdown table of test cases."""

from __future__ import annotations

from ..core.helpers import normalize_text
from ..core.provider import Provider, call_ai


def generate_test_cases(
    requirements: str,
    risk: str = "",
    code: str = "",
    *,
    provider: Provider | None = None,
) -> str:
    """Generate system-level test cases as a markdown table.

    Parameters
    ----------
    requirements : str
        Functional requirements text.
    risk : str
        Risk analysis notes (optional).
    code : str
        Related source code (optional).
    provider : Provider, optional

    Returns
    -------
    str
        Markdown table with columns: Test Case ID | Steps | Expected Outcome | Details

    Example
    -------
    >>> from asimtool.developer import generate_test_cases
    >>> table = generate_test_cases("User must log in with email and password.")
    >>> print(table[:120])
    """
    requirements = normalize_text(requirements)
    risk = normalize_text(risk)
    code = normalize_text(code)

    prompt = (
        "You are a testing expert. Based on the following requirements, risk notes, and optional code, generate a "
        "clean markdown table of unique system-level test cases. Cover happy and unhappy flows, boundary conditions, "
        "and error handling. Each row must be a distinct test case targeting a specific behavior. Do not include "
        "any explanations, comments, assumed specs, unit test summaries, code snippets, or extra text. Only return "
        "a single markdown table with the exact header:  'Test Case ID | Steps | Expected Outcome | Details' "
        "- Use diverse, action-based phrasing in the **Steps** column such as 'Check that...', 'Navigate to...', "
        "'Open...', 'Modify...', or 'Select...'. Do not use 'Verify' under any circumstance. "
        "- Ensure Steps sound like realistic user or tester actions, not generic test summaries. "
        "- Use 'it should' in the **Expected Outcome**. "
        "- Use 'I' language in the **Details** to emphasize the test case importance. "
        "- Do not repeat headers or include any extra lines. "
        "- Test Case IDs must begin with 'TC-1', 'TC-2', and so on. "
        "- Ensure clean formatting, no duplicated headers, and no extra output besides the markdown table."
    )

    combined = (
        f"{prompt}\n\nRequirements:\n{requirements}"
        f"\n\nRisk:\n{risk}\n\nCode:\n{code}"
    )

    return call_ai(combined, model="gpt_4_5", provider=provider)
