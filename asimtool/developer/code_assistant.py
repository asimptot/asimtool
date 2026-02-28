"""Code assistant — answer questions about a project's source code."""

from __future__ import annotations

from typing import Dict, List

from ..core.provider import Provider, call_ai


def ask_about_code(
    question: str,
    files_context: List[Dict[str, str]],
    *,
    max_total_chars: int = 200_000,
    provider: Provider | None = None,
) -> str:
    """Answer a question about user-provided source files.

    Parameters
    ----------
    question : str
        The question about the codebase.
    files_context : list[dict]
        List of ``{"path": "src/main.py", "content": "..."}`` dicts.
    max_total_chars : int
        Character budget for file contents.
    provider : Provider, optional

    Returns
    -------
    str
        Markdown-formatted answer.

    Example
    -------
    >>> from asimtool.developer import ask_about_code
    >>> files = [{"path": "app.py", "content": "from flask import Flask\\napp = Flask(__name__)"}]
    >>> answer = ask_about_code("What framework is this?", files)
    """
    if not question.strip():
        raise ValueError("Question cannot be empty.")
    if not files_context:
        raise ValueError("No project files provided.")

    parts: list[str] = []
    total = 0
    for f in files_context:
        path = f.get("path", "")
        content = f.get("content", "")
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else "txt"
        entry = f"### {path}\n```{ext}\n{content}\n```\n\n"
        if total + len(entry) > max_total_chars:
            parts.append(f"### {path}\n[truncated — context limit reached]\n\n")
            break
        parts.append(entry)
        total += len(entry)

    context_str = "".join(parts)

    prompt = (
        "You are an expert code assistant similar to GitHub Copilot Chat. "
        "The user has provided their project files below. "
        "Answer their question accurately and specifically, referencing exact file paths when relevant. "
        "Use markdown with proper fenced code blocks for any code snippets.\n\n"
        f"--- PROJECT FILES ({len(files_context)} files) ---\n"
        f"{context_str}"
        f"--- END OF PROJECT FILES ---\n\n"
        f"Question: {question}"
    )

    return call_ai(prompt, model="gpt_4", provider=provider)
