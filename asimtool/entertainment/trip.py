"""Trip planner — detailed itinerary as pipe-delimited table."""

from __future__ import annotations

from ..core.provider import Provider, call_ai


def plan_trip(
    location: str,
    start_date: str,
    end_date: str,
    *,
    provider: Provider | None = None,
) -> str:
    """Create a detailed trip plan for *location* between *start_date* and *end_date*.

    Parameters
    ----------
    location : str
        City or country (e.g. ``"Rome"``).
    start_date : str
        Start date string (e.g. ``"2025-07-01"``).
    end_date : str
        End date string (e.g. ``"2025-07-05"``).
    provider : Provider, optional

    Returns
    -------
    str
        Pipe-delimited table rows: Date | Activity | Description | Dining | Events.

    Example
    -------
    >>> from asimtool.entertainment import plan_trip
    >>> plan = plan_trip("Tokyo", "2025-08-01", "2025-08-05")
    >>> for row in plan.split("\\n")[:3]:
    ...     print(row)
    """
    if not location or not start_date or not end_date:
        raise ValueError("Location and date range are required.")

    prompt = (
        f"Create a detailed trip plan for {location} from {start_date} to {end_date}. "
        f"Include where to eat and drink locally, as well as special locations to visit. "
        "Format your response STRICTLY as a pipe-delimited table with NO headers or titles. "
        "Each line must follow this exact format:\n"
        "Date | Activity/Location | Description/Notes | Dining Options | Events/Highlights\n\n"
        "Example format:\n"
        "Day 1 | Museum Visit | Explore local art | Traditional Restaurant | Opening Festival\n"
        "Day 2 | City Tour | Walking tour of downtown | Local Cafe | Street Market\n\n"
        "Provide ONLY the data rows separated by pipe characters (|), with one row per day or activity. "
        "Do NOT include markdown formatting, table headers, or any other text."
    )

    return call_ai(prompt, model="grok_3", provider=provider)
