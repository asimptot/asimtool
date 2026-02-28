"""Image to prompt — analyse an image and return an AI generation prompt."""

from __future__ import annotations

import base64
import os
from pathlib import Path

import requests


# MIME type mapping
_MIME_MAP = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png", "webp": "image/webp",
    "gif": "image/gif", "bmp": "image/bmp",
}


def image_to_prompt(
    image_path: str,
    *,
    api_url: str | None = None,
    api_origin: str | None = None,
    api_referer: str | None = None,
    max_size_mb: int = 10,
) -> str:
    """Analyse an image and return an AI-ready generation prompt.

    By default reads API endpoints from environment variables
    ``I2P_API_URL``, ``I2P_API_ORIGIN``, ``I2P_API_REFERER``.

    Parameters
    ----------
    image_path : str
        Path to the image file.
    api_url : str, optional
        Vision API endpoint. Falls back to ``$I2P_API_URL``.
    api_origin : str, optional
        Origin header. Falls back to ``$I2P_API_ORIGIN``.
    api_referer : str, optional
        Referer header. Falls back to ``$I2P_API_REFERER``.
    max_size_mb : int
        Maximum file size in megabytes (default 10).

    Returns
    -------
    str
        A descriptive prompt generated from the image.

    Raises
    ------
    ValueError
        If the file type is unsupported or the image is too large.
    RuntimeError
        If the API call fails.

    Example
    -------
    >>> from asimtool.tools import image_to_prompt
    >>> prompt = image_to_prompt("photo.jpg")
    >>> print(prompt[:100])
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {image_path}")

    ext = path.suffix.lower().lstrip(".")
    mime = _MIME_MAP.get(ext)
    if not mime:
        raise ValueError(f"Unsupported image type: .{ext}")

    img_bytes = path.read_bytes()
    if len(img_bytes) > max_size_mb * 1024 * 1024:
        raise ValueError(f"Image too large (max {max_size_mb} MB).")

    url = api_url or os.getenv("I2P_API_URL", "")
    origin = api_origin or os.getenv("I2P_API_ORIGIN", "")
    referer = api_referer or os.getenv("I2P_API_REFERER", "")

    if not url:
        raise RuntimeError(
            "Image-to-prompt service not configured. "
            "Set I2P_API_URL environment variable or pass api_url."
        )

    b64 = base64.b64encode(img_bytes).decode()
    data_uri = f"data:{mime};base64,{b64}"

    resp = requests.post(
        url,
        json={"base64Url": data_uri, "imageModelId": "", "language": "en"},
        headers={
            "Content-Type": "application/json",
            "Origin": origin,
            "Referer": referer,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        },
        timeout=90,
    )

    if resp.status_code == 429:
        raise RuntimeError("Rate limited — please try again in a moment.")
    if resp.status_code == 451:
        raise ValueError("Image contains inappropriate content.")
    if resp.status_code != 200:
        raise RuntimeError(f"Prompt generation failed (HTTP {resp.status_code}).")

    data = resp.json()
    prompt_text = data.get("prompt", "").strip()
    if not prompt_text:
        raise RuntimeError("Empty prompt returned from API.")

    return prompt_text
