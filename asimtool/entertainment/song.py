"""Song lyrics generator."""

from __future__ import annotations

from ..core.provider import Provider, call_ai


def generate_lyrics(
    title: str,
    genre: str = "pop",
    mood: str = "uplifting and hopeful",
    language: str = "English",
    seed: str = "",
    *,
    provider: Provider | None = None,
) -> str:
    """Generate song lyrics for a given title, genre, and mood.

    Parameters
    ----------
    title : str
        Song title.
    genre : str
        Music genre (e.g. ``"rock"``, ``"pop"``, ``"jazz"``).
    mood : str
        Mood description (e.g. ``"melancholic"``, ``"upbeat"``).
    language : str
        Lyrics language (e.g. ``"English"``, ``"Turkish"``).
    seed : str
        Optional seed lines for lyrical inspiration.
    provider : Provider, optional

    Returns
    -------
    str
        Complete song lyrics with section labels ([Verse 1], [Chorus], etc.).

    Example
    -------
    >>> from asimtool.entertainment import generate_lyrics
    >>> lyrics = generate_lyrics("Moonlight", genre="ballad", mood="romantic")
    >>> print(lyrics[:120])
    """
    if not title.strip():
        raise ValueError("Song title is required.")

    seed_line = f'\n\nUse this as lyrical inspiration (1-2 seed lines): "{seed}"' if seed else ""

    prompt = (
        f'Write complete, original song lyrics for a {genre} song called "{title}".\n\n'
        f"Style: {genre}\n"
        f"Mood/Theme: {mood}\n"
        f"Language: {language}{seed_line}\n\n"
        "Requirements:\n"
        "- Write ONLY the lyrics — no commentary, no explanations\n"
        "- Include labeled sections: [Verse 1], [Chorus], [Verse 2], [Bridge], [Outro]\n"
        "- Each section should be 4-8 lines\n"
        "- The chorus must be catchy and memorable, repeated at least twice\n"
        f"- Match the tone and vocabulary to the mood: {mood}\n"
        f"- Write naturally in {language}\n"
        "- Do NOT include stage directions or notes in parentheses\n\n"
        "Begin the lyrics now:"
    )

    return call_ai(prompt, model="gpt-4o-mini", provider=provider)
