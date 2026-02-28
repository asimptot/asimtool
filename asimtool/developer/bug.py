"""Bug description improver — structured template formatting."""

from __future__ import annotations

import re

from ..core.provider import Provider, call_ai


def improve_bug_description(
    description: str,
    *,
    provider: Provider | None = None,
) -> str:
    """Improve and structure a bug description using an industry-standard template.

    Parameters
    ----------
    description : str
        Raw bug report text from a user or tester.
    provider : Provider, optional

    Returns
    -------
    str
        Formatted bug report with HTML ``<b>`` tags for headings.

    Example
    -------
    >>> from asimtool.developer import improve_bug_description
    >>> result = improve_bug_description("login button not working after update")
    >>> print(result[:80])
    """
    if not description.strip():
        raise ValueError("Bug description cannot be empty.")

    prompt = (
        "Check and improve the following bug details. Provide a corrected version with title, priority (1-5), "
        "and severity (1-5). Priority 1 is highest. Please do not write anything and just send me what you changed. "
        "Do not use ** . Please apply in the following template after getting result: "
        "<b>Title:</b> <title here><br>"
        "<b>Priority:</b> <priority here><br>"
        "<b>Severity:</b> <severity here><br>"
        "<b>Description:</b> Provide a brief summary of the bug, including its impact and any relevant context.<br>"
        "<b>Prerequisites:</b> List any necessary setup or conditions needed before reproducing the bug.<br>"
        "<b>Steps to Reproduce:</b> Describe the steps to reproduce the issue without numbering.<br>"
        "<b>Expected Result:</b> Describe what you expected to happen.<br>"
        "<b>Actual Result:</b> Describe what actually happened.<br>"
        "<b>Recovery State:</b> Explain how to continue using the application after the bug occurs.<br>"
        "<b>Reproducibility Rate:</b> Rate on a scale of 1/5 to 5/5.<br>"
        "<b>Attachments:</b> List any files, screenshots, or logs that are relevant.<br>"
        "The returned result cannot start with space character. "
    )

    combined = f"{prompt}\n\n{description}"
    result = call_ai(combined, model="gpt_4_5", provider=provider)

    # If the AI didn't use HTML bold tags, add them
    if "<b>Title:</b>" not in result:
        _fields = [
            "Title", "Priority", "Severity", "Description",
            "Prerequisites", "Steps to Reproduce", "Expected Result",
            "Actual Result", "Recovery State", "Reproducibility Rate",
            "Attachments",
        ]
        for field in _fields:
            result = re.sub(
                rf"(?mi)^{field}:\s*(.*)",
                rf"<b>{field}:</b> \1<br>",
                result,
            )

    # Clean trailing <br>
    result = re.sub(r"(<br>\s*)+$", "", result)
    return result
