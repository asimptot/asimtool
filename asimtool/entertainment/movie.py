"""Movie / TV series recommender by genre."""

from __future__ import annotations

import re
from typing import Dict, List

from ..core.provider import Provider, call_ai


def recommend(
    media_type: str = "movie",
    genre: str = "drama",
    *,
    provider: Provider | None = None,
) -> List[Dict]:
    """Recommend movies or series sorted by IMDB rating.

    Parameters
    ----------
    media_type : str
        ``"movie"`` or ``"series"``.
    genre : str
        Genre name (e.g. ``"sci-fi"``, ``"comedy"``).
    provider : Provider, optional

    Returns
    -------
    list[dict]
        Each dict has ``title``, ``year``, ``rating``.

    Example
    -------
    >>> from asimtool.entertainment import recommend_movie
    >>> items = recommend_movie("movie", "sci-fi")
    >>> for m in items[:3]:
    ...     print(f"{m['title']} ({m['year']}) - {m['rating']}")
    """
    if not media_type or not genre:
        raise ValueError("Media type and genre are required.")

    prompt = (
        f"Please recommend 10 actual {media_type}s in the genre of {genre}, "
        f"sorted by IMDB rating from high to low. "
        f"Please just return the result for the last 10 years and do not share your own sentences. "
        f"Return each title, year, and IMDB rating in this format: 'Title (Year) - IMDb rating: Rating'."
    )

    raw = call_ai(prompt, model="grok_3", provider=provider)

    parsed: List[Dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or not line[0].isdigit():
            continue

        match = re.match(
            r"^\d+\.\s*(.*?)\s\((\d{4})\)\s*-\s*IMDb rating:\s*(\d+\.\d+)",
            line,
        )
        if match:
            title, year, rating = match.groups()
            parsed.append({"title": title.strip(), "year": year, "rating": float(rating)})
        else:
            fallback = re.match(
                r"^\d+\.\s*(.*?)\s\((\d{4})\)\s*-\s*IMDb rating:\s*(\d+\.\d+)?",
                line,
            )
            if fallback:
                title, year, rating = fallback.groups()
                parsed.append({
                    "title": title.strip(),
                    "year": year,
                    "rating": float(rating) if rating else None,
                })
            else:
                parsed.append({"title": line, "year": None, "rating": None})

    parsed.sort(
        key=lambda x: x["rating"] if isinstance(x["rating"], (int, float)) else -1,
        reverse=True,
    )
    return parsed
