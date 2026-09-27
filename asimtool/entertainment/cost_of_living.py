"""Cost of living comparison — AI-powered year-over-year price analysis."""

from __future__ import annotations

import datetime

from ..core.provider import Provider, call_ai


def compare_cost_of_living(
    country: str,
    salary_current: str = "",
    salary_previous: str = "",
    *,
    provider: Provider | None = None,
) -> str:
    """Compare cost of living in a country between this year and last year.

    Parameters
    ----------
    country : str
        Country name to analyze.
    salary_current : str
        Optional current monthly salary (local currency).
    salary_previous : str
        Optional previous year monthly salary (local currency).
    provider : Provider, optional

    Returns
    -------
    str
        Pipe-delimited table of price comparisons by category.

    Example
    -------
    >>> from asimtool.entertainment import compare_cost_of_living
    >>> result = compare_cost_of_living("Netherlands")
    >>> print(result[:200])
    """
    if not country.strip():
        raise ValueError("Country is required.")

    current_year = datetime.datetime.now().year
    previous_year = current_year - 1

    salary_part = ""
    if salary_current and salary_previous:
        salary_part = (
            f"\n\nAlso, the user earned {salary_previous} (local currency) per month in {previous_year} "
            f"and earns {salary_current} per month in {current_year}. "
            "Calculate their purchasing power change: can they buy more or less with their salary now? "
            "Show a summary row at the end with the purchasing power analysis."
        )

    prompt = (
        f"Compare the cost of living in {country} between {previous_year} and {current_year}. "
        "Use your knowledge of typical prices in this country. "
        "Cover these categories: Groceries (bread, milk, eggs, rice, chicken, fruits, vegetables), "
        "Dining (inexpensive restaurant, mid-range restaurant, fast food), "
        "Transport (monthly pass, taxi 1km, gasoline 1L), "
        "Utilities (electricity+heating+water for 85m2 apartment, internet), "
        "Rent (1-bedroom city center, 1-bedroom outside center), "
        "Other (gym membership, cinema ticket, clothing). "
        f"\nFormat your response STRICTLY as a pipe-delimited table. "
        f"Each line must follow this exact format:\n"
        f"Category | Item | {previous_year} Price | {current_year} Price | Change %\n\n"
        "Use local currency. Show realistic average prices. "
        "Change % should be calculated as ((new-old)/old)*100, with + or - sign. "
        "Provide ONLY the data rows separated by pipe characters (|). "
        "Do NOT include markdown formatting, table headers, or any other text."
        f"{salary_part}"
    )

    return call_ai(prompt, model="gpt_4_5", provider=provider)
