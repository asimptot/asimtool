"""Agent-mode code assistant — read-only tool calling over a local project.

Unlike :func:`asimtool.developer.ask_about_code`, which needs the caller to
paste file contents, :func:`ask_about_project` lets the model explore a folder
on disk using four **read-only** tools: ``list_dir``, ``read_file``, ``grep``
and ``git_diff``.  Nothing is ever written, executed or modified.
"""

from __future__ import annotations

import fnmatch
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from ..core.helpers import extract_json_object
from ..core.provider import Provider, call_ai

DEFAULT_IGNORES = (
    ".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv",
    ".env", "dist", "build", ".mypy_cache", ".pytest_cache", ".idea", ".vscode",
)

DEFAULT_MAX_FILE_CHARS = 20_000
DEFAULT_MAX_RESULTS = 200

AGENT_SYSTEM_PROMPT = (
    "You are an expert coding agent working inside a user's local project. "
    "You can inspect the project with read-only tools, then answer.\n\n"
    "TOOLS (call by returning a single JSON object, nothing else):\n"
    '{{"tool": "list_dir", "path": "."}}                 — list a directory\n'
    '{{"tool": "read_file", "path": "src/app.py", "start": 1, "end": 400}}\n'
    '{{"tool": "grep", "pattern": "def login", "glob": "*.py"}}\n'
    '{{"tool": "git_diff", "staged": false}}\n\n'
    "RULES:\n"
    "- To answer, FIRST call a tool to gather real evidence, then reply with "
    "the final answer as plain markdown text (no JSON, no tool call).\n"
    "- Call only ONE tool per message and wait for its result.\n"
    "- Use relative paths from the project root. Never use '..' to escape it.\n"
    "- You may not write, edit, delete, or execute anything.\n"
    "- Cite exact file paths (and line numbers when known) in your answer.\n"
    "- If the answer is not in the project, say so plainly."
)


# ---------------------------------------------------------------------------
# Read-only tool implementations
# ---------------------------------------------------------------------------

def _safe_path(root: Path, rel: str) -> Path:
    """Resolve *rel* inside *root*, refusing anything that escapes it."""
    rel = (rel or ".").strip() or "."
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise PermissionError(f"Path outside the project root is not allowed: {rel}")
    return candidate


def _is_ignored(name: str, ignores: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(name, pat) or name == pat for pat in ignores)


def _tool_list_dir(root: Path, args: Dict[str, Any], ignores: tuple[str, ...]) -> str:
    target = _safe_path(root, str(args.get("path") or "."))
    if not target.is_dir():
        return f"ERROR: not a directory: {args.get('path')}"

    entries = []
    for child in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        if child.name in ignores:
            continue
        entries.append(f"{child.name}/" if child.is_dir() else child.name)

    shown = entries[:300]
    suffix = f"\n... (+{len(entries) - len(shown)} more)" if len(entries) > len(shown) else ""
    header = target.relative_to(root).as_posix() if target != root else "."
    return f"{header}/:\n" + "\n".join(shown) + suffix


def _tool_read_file(root: Path, args: Dict[str, Any], max_chars: int) -> str:
    target = _safe_path(root, str(args.get("path") or ""))
    if not target.is_file():
        return f"ERROR: file not found: {args.get('path')}"

    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"ERROR: cannot read file: {exc}"

    lines = text.splitlines()
    start = max(int(args.get("start") or 1), 1)
    end = min(int(args.get("end") or len(lines)), start + 1999)
    selected = lines[start - 1:end]

    numbered = "\n".join(f"{start + i:>5}| {line}" for i, line in enumerate(selected))
    if len(numbered) > max_chars:
        numbered = numbered[:max_chars] + "\n[truncated]"

    return (
        f"{target.relative_to(root).as_posix()} (lines {start}-{start + len(selected) - 1} "
        f"of {len(lines)}):\n{numbered}"
    )


def _tool_grep(
    root: Path, args: Dict[str, Any], ignores: tuple[str, ...], max_results: int
) -> str:
    pattern = str(args.get("pattern") or "")
    if not pattern:
        return "ERROR: 'pattern' is required."
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        return f"ERROR: invalid regex: {exc}"

    glob = str(args.get("glob") or "*")
    hits: List[str] = []

    for path in sorted(root.rglob("*")):
        if len(hits) >= max_results:
            break
        if not path.is_file():
            continue
        if any(_is_ignored(part, ignores) for part in path.relative_to(root).parts):
            continue
        if not fnmatch.fnmatch(path.name, glob):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            if rx.search(line):
                hits.append(f"{path.relative_to(root).as_posix()}:{i}: {line.strip()[:200]}")
                if len(hits) >= max_results:
                    break

    if not hits:
        return f"No matches for /{pattern}/"
    return "\n".join(hits)


def _tool_git_diff(root: Path, args: Dict[str, Any]) -> str:
    cmd = ["git", "--no-pager", "diff", "--stat" if args.get("stat") else "--unified=3"]
    if args.get("staged"):
        cmd.append("--staged")
    try:
        proc = subprocess.run(
            cmd, cwd=str(root), capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"ERROR: git diff failed: {exc}"


def run_tool(
    tool: str,
    args: Dict[str, Any],
    root: str | os.PathLike,
    *,
    ignores: tuple[str, ...] = DEFAULT_IGNORES,
    max_file_chars: int = DEFAULT_MAX_FILE_CHARS,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> str:
    """Execute one read-only agent tool and return its textual result.

    Parameters
    ----------
    tool : str
        ``"list_dir"``, ``"read_file"``, ``"grep"`` or ``"git_diff"``.
    args : dict
        Tool arguments (see :data:`AGENT_SYSTEM_PROMPT`).
    root : str | PathLike
        Project root directory.
    ignores : tuple, optional
        Directory/file name patterns that are never traversed.
    max_file_chars, max_results : int, optional
        Output budgets for ``read_file`` and ``grep``.

    Returns
    -------
    str
        The tool output, or an ``ERROR: ...`` message on failure.
    """
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        return f"ERROR: project root not found: {root_path}"

    try:
        if tool == "list_dir":
            return _tool_list_dir(root_path, args, ignores)
        if tool == "read_file":
            return _tool_read_file(root_path, args, max_file_chars)
        if tool == "grep":
            return _tool_grep(root_path, args, ignores, max_results)
        if tool == "git_diff":
            return _tool_git_diff(root_path, args)
    except PermissionError as exc:
        return f"ERROR: {exc}"
    except ValueError as exc:
        return f"ERROR: invalid tool arguments: {exc}"

    return f"ERROR: unknown tool '{tool}'. Allowed: list_dir, read_file, grep, git_diff."


def _build_prompt(root: Path, question: str, transcript: List[str], *, final: bool) -> str:
    history = "\n\n".join(transcript) if transcript else "(no tool calls yet)"
    tail = (
        "You have used all your tool steps. Answer NOW using the evidence above, "
        "without requesting another tool call."
        if final
        else "Reply with either a single tool-call JSON object or your final markdown answer."
    )
    return (
        f"PROJECT ROOT: {root}\n"
        f"QUESTION: {question}\n\n"
        f"--- TRANSCRIPT ---\n{history}\n--- END TRANSCRIPT ---\n\n{tail}"
    )


TOOL_ALIASES = {
    "list_dir": "list_dir", "listdir": "list_dir", "list_directory": "list_dir",
    "ls": "list_dir", "dir": "list_dir",
    "read_file": "read_file", "readfile": "read_file", "read": "read_file",
    "open_file": "read_file", "cat": "read_file",
    "grep": "grep", "search": "grep", "find": "grep", "ripgrep": "grep",
    "git_diff": "git_diff", "gitdiff": "git_diff", "diff": "git_diff",
}


def _parse_tool_call(text: str) -> tuple[str, Dict[str, Any]] | None:
    """Return ``(tool, args)`` when *text* is a tool call, else ``None``.

    Accepts the documented ``{"tool": ..., ...}`` form as well as the
    shorthand ``{"list_dir": {"path": "."}}`` that free models often emit.
    """
    data = extract_json_object(text)
    if not isinstance(data, dict) or not data:
        return None

    raw_tool = str(data.get("tool") or data.get("name") or "").strip()
    tool = TOOL_ALIASES.get(raw_tool.lower(), "")
    if tool:
        args = data.get("arguments") if isinstance(data.get("arguments"), dict) else data
        return tool, args

    # Shorthand: a single key that names a tool, e.g. {"grep": {"pattern": "x"}}
    if len(data) == 1:
        key, value = next(iter(data.items()))
        tool = TOOL_ALIASES.get(str(key).strip().lower(), "")
        if tool:
            if isinstance(value, dict):
                return tool, value
            if isinstance(value, str):
                return tool, {"path": value}
            if value is True:
                return tool, {}
    return None


def ask_about_project(
    question: str,
    project_root: str | os.PathLike = ".",
    *,
    max_steps: int = 8,
    model: str = "gpt_4",
    provider: Provider | None = None,
    ignores: tuple[str, ...] = DEFAULT_IGNORES,
    on_tool_call=None,
) -> str:
    """Answer a question about a project on disk using read-only tools.

    The model explores the folder with ``list_dir`` / ``read_file`` / ``grep``
    / ``git_diff`` and then produces a final markdown answer.

    Parameters
    ----------
    question : str
        The question about the project.
    project_root : str | PathLike
        Directory the tools are restricted to. Defaults to the CWD.
    max_steps : int
        Maximum tool-calling rounds before the answer is forced (8).
    model : str
        g4f model used for each turn.
    provider : Provider, optional
    ignores : tuple, optional
        Names never traversed (see :data:`DEFAULT_IGNORES`).
    on_tool_call : callable, optional
        Callback ``fn(tool, args, result)`` invoked after every tool run —
        useful for logging or UI streaming.

    Returns
    -------
    str
        Markdown-formatted answer.

    Raises
    ------
    ValueError
        When *question* is empty or *project_root* is not a directory.
    RuntimeError
        When the model never produces an answer within *max_steps*.

    Example
    -------
    >>> from asimtool.developer import ask_about_project
    >>> answer = ask_about_project("Where is the DB connection set up?", ".")
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    root = Path(project_root).resolve()
    if not root.is_dir():
        raise ValueError(f"Project root is not a directory: {root}")

    transcript: List[str] = []

    for step in range(1, max_steps + 2):
        answer = call_ai(
            _build_prompt(root, question, transcript, final=step > max_steps),
            model=model,
            provider=provider,
            system=AGENT_SYSTEM_PROMPT,
        )

        call = _parse_tool_call(answer)
        if call is None:
            # A JSON object we cannot interpret is a malformed tool call, not
            # an answer — tell the model the exact expected shape and retry.
            if isinstance(extract_json_object(answer), dict) and step <= max_steps:
                transcript.append(
                    "TOOL CALL: (rejected — unrecognised format)\n"
                    'TOOL RESULT: Use exactly one of {"tool": "list_dir", "path": "."}, '
                    '{"tool": "read_file", "path": "file.py", "start": 1, "end": 200}, '
                    '{"tool": "grep", "pattern": "def ", "glob": "*.py"}, '
                    '{"tool": "git_diff", "staged": false} — or answer in plain markdown.'
                )
                continue
            return answer

        tool, args = call
        result = run_tool(tool, args, root, ignores=ignores)
        transcript.append(f"TOOL CALL: {tool}({args})\nTOOL RESULT:\n{result}")
        if on_tool_call is not None:
            on_tool_call(tool, args, result)

    raise RuntimeError(
        f"Model did not produce a final answer within {max_steps} tool steps."
    )
