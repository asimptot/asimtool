"""Pull request AI reviewer."""

from __future__ import annotations

from ..core.helpers import normalize_text
from ..core.provider import Provider, call_ai


def review_pull_request(
    pr_text: str,
    *,
    provider: Provider | None = None,
) -> str:
    """Review a pull request (including unified diffs) and return a professional comment.

    Parameters
    ----------
    pr_text : str
        The pull request content, which can include unified diff format.
    provider : Provider, optional

    Returns
    -------
    str
        A detailed review comment in first-person.

    Example
    -------
    >>> from asimtool.developer import review_pull_request
    >>> review = review_pull_request("+ def new_func(): ...")
    >>> print(review[:80])
    """
    pr_text = normalize_text(pr_text)

    prompt = (
        "Please review the following Pull Request on my behalf, using 'I' language as the reviewer. "
        "Write your review comment in a professional and constructive tone, as if it were part of a real code review. "
        "Identify one concrete issue or anomaly in the code or design — this can be architectural, functional, or stylistic. "
        "Explain *why* it is an issue and what the potential implications are. "
        "Formulate your feedback as a question or suggestion (e.g., 'Is this class still used?', 'I think this belongs in...'). "
        "Recommend a clear, actionable solution or alternative approach. "
        "Follow the style of thoughtful reviews that discuss ownership, nullability, reusability, and design intent. "
        "The Pull Request content may contain unified diff format. "
        "A line starting with '-' means the line was removed. "
        "A line starting with '+' means the line was added. "
        "Do NOT treat a removed line and an added line as if they both still exist — interpret them according to diff semantics. "
        "Do NOT add any introductory phrases such as 'Here's my review', "
        "'Okay', 'Sure', 'Your PR review is', or anything similar. "
        "Start directly with the review comment itself."
        f"\n\nPull Request:\n{pr_text}\n\n"
        "Provide your response as if you were leaving a single detailed review comment."
    )

    return call_ai(prompt, model="gpt_4_5", provider=provider)
