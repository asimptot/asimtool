"""News aggregation + AI-powered translation and summarisation."""

from __future__ import annotations

from typing import List

import feedparser

from ..core.provider import Provider, call_ai

# Country → Google News RSS URL mapping
_RSS_FEEDS = {
    "United States":  "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "United Kingdom": "https://news.google.com/rss?hl=en-GB&gl=GB&ceid=GB:en",
    "France":         "https://news.google.com/rss?hl=fr-FR&gl=FR&ceid=FR:fr",
    "Germany":        "https://news.google.com/rss?hl=de-DE&gl=DE&ceid=DE:de",
    "Turkey":         "https://news.google.com/rss?hl=tr-TR&gl=TR&ceid=TR:tr",
    "Netherlands":    "https://news.google.com/rss?hl=nl-NL&gl=NL&ceid=NL:nl",
    "Spain":          "https://news.google.com/rss?hl=es-ES&gl=ES&ceid=ES:es",
    "Sweden":         "https://news.google.com/rss?hl=sv-SE&gl=SE&ceid=SE:sv",
    "Italy":          "https://news.google.com/rss?hl=it-IT&gl=IT&ceid=IT:it",
}


def get_news(
    country: str,
    language: str,
    language_level: str = "B1",
    *,
    max_items: int = 10,
    provider: Provider | None = None,
) -> List[str]:
    """Fetch top headlines from *country*, summarise them in *language* at *language_level*.

    Parameters
    ----------
    country : str
        Country name (e.g. ``"Germany"``).
    language : str
        Target summary language (e.g. ``"Turkish"``).
    language_level : str
        CEFR level (``"A1"`` – ``"C2"``).
    max_items : int
        Number of headlines to fetch (default 10).
    provider : Provider, optional
        Custom provider list.

    Returns
    -------
    list[str]
        List of translated/summarised news lines.

    Example
    -------
    >>> from asimtool.language import get_news
    >>> items = get_news("Germany", "English", "B1")
    >>> for item in items[:3]:
    ...     print(item)
    """
    if not country or not language:
        raise ValueError("Country and language are required.")

    feed_url = _RSS_FEEDS.get(country)
    if not feed_url:
        available = ", ".join(sorted(_RSS_FEEDS.keys()))
        raise ValueError(
            f"No RSS feed for '{country}'. Available: {available}"
        )

    feed = feedparser.parse(feed_url)
    titles = [entry.title for entry in feed.entries[:max_items]]

    if not titles:
        raise RuntimeError(f"No headlines found for {country}.")

    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))

    prompt = (
        f"You are a news writer creating short tweet-style news summaries. "
        f"Below are the top {len(titles)} news headlines from {country}:\n\n"
        f"{numbered}\n\n"
        f"For each news item, write a concise, engaging tweet-style summary in {language} "
        f"suitable for language level {language_level}. "
        f"Each summary should be 1-2 sentences maximum, clear and easy to understand. "
        f"Write each news item on a separate line without numbering. "
        f"Do not include any extra text, explanations, or the original English titles. "
        f"Just provide the {language} summaries, one per line."
    )

    raw = call_ai(prompt, model="grok_3", provider=provider)
    return [line.strip() for line in raw.split("\n") if line.strip()]
