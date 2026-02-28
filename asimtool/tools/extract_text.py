"""Text extraction from PDF, DOCX, and images (OCR via GPT-4o vision)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import g4f


def extract_text(file_path: str) -> str:
    """Extract text from a PDF, DOCX, or image file.

    Supported formats:
    - **PDF**: uses ``pypdf``
    - **DOCX**: pure-Python XML parsing (no binary deps)
    - **Images** (jpg, png, gif, webp, bmp, tiff): GPT-4o vision OCR via g4f

    Parameters
    ----------
    file_path : str
        Absolute or relative path to the file.

    Returns
    -------
    str
        Extracted text content.

    Raises
    ------
    FileNotFoundError
        If file doesn't exist.
    ValueError
        If file type is unsupported.

    Example
    -------
    >>> from asimtool.tools import extract_text
    >>> text = extract_text("document.pdf")
    >>> print(text[:200])
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower().lstrip(".")

    if ext == "pdf":
        return _extract_pdf(path)
    elif ext == "docx":
        return _extract_docx(path)
    elif ext in {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "tif"}:
        return _extract_image(path)
    else:
        raise ValueError(
            f"Unsupported file type: .{ext}. Supported: pdf, docx, jpg, png, gif, webp, bmp, tiff."
        )


def _extract_pdf(path: Path) -> str:
    """Extract text from a PDF using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf is required for PDF extraction: pip install pypdf")

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        t = page.extract_text()
        if t and t.strip():
            pages.append(t.strip())

    text = "\n\n".join(pages).strip()
    if not text:
        raise ValueError("No text found in PDF.")
    return text


def _extract_docx(path: Path) -> str:
    """Extract text from a DOCX using built-in zipfile + xml."""
    import zipfile
    import xml.etree.ElementTree as ET

    with zipfile.ZipFile(str(path), "r") as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for para in tree.findall(".//w:p", ns):
        runs = "".join(r.text or "" for r in para.findall(".//w:t", ns))
        if runs.strip():
            paragraphs.append(runs)

    text = "\n".join(paragraphs).strip()
    if not text:
        raise ValueError("No text found in DOCX.")
    return text


def _extract_image(path: Path) -> str:
    """OCR an image using GPT-4o vision via g4f."""
    prompt = (
        "Extract and return ALL text visible in this image, exactly as it appears. "
        "Preserve line breaks and formatting as much as possible. "
        "Do not summarize, translate, or add any commentary. "
        "If there is no text in the image, respond with exactly: No text found."
    )

    with open(str(path), "rb") as img_file:
        response = g4f.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            image=img_file,
            provider=g4f.Provider.OperaAria,
        )

    text = ""
    if isinstance(response, str):
        text = response.strip()
    elif isinstance(response, dict) and "choices" in response:
        text = response["choices"][0]["message"]["content"].strip()

    if not text:
        raise RuntimeError("Could not extract text from image.")
    return text
