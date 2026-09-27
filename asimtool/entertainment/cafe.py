"""Venue finder — meeting point between two postal codes."""

from __future__ import annotations

from ..core.provider import Provider, call_ai


def find_venue(
    zip_code_1: str,
    zip_code_2: str,
    country_1: str = "",
    country_2: str = "",
    venue_type: str = "cafe",
    *,
    provider: Provider | None = None,
) -> str:
    """Find a meeting venue at the midpoint between two postal codes.

    Parameters
    ----------
    zip_code_1 : str
        First person's postal code.
    zip_code_2 : str
        Second person's postal code.
    country_1 : str
        Country for the first postal code.
    country_2 : str
        Country for the second postal code.
    venue_type : str
        Type of venue (``"cafe"``, ``"restaurant"``, etc.).
    provider : Provider, optional

    Returns
    -------
    str
        Formatted text with City, Venue, and Address.

    Example
    -------
    >>> from asimtool.entertainment import find_venue
    >>> result = find_venue("10115", "80331", "Germany", "Germany", "cafe")
    >>> print(result)
    """
    prompt = (
        f"I will be meeting you between the postcodes from {country_1} {zip_code_1} "
        f"and from {country_2} {zip_code_2}. "
        f"Can you recommend me a {venue_type} for the meeting? Please find the approximate middle point "
        "between these two postcodes by calculating their geographical coordinates. "
        "Once you find the middle point, provide the city, venue name, and full address of a venue in that area. "
        "Format your response exactly like this (without any markdown ** or bold formatting):\n"
        "City: [city name]\n"
        "Venue: [venue name]\n"
        "Address: [full address]\n\n"
        "Do not include any extra text, greetings, or explanations."
    )

    return call_ai(prompt, model="grok_3", provider=provider)
