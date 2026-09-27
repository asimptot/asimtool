"""Text extraction from PDF, DOCX, and images (OCR via Groq vision API)."""

from __future__ import annotations

import base64
import io
import logging
import os
import re
import tempfile
from pathlib import Path


# Groq vision models, tried in order.  The Llama 4 Scout / Llama 3.2 vision
# models were decommissioned by Groq, so the list is refreshed regularly.
# Override the first entry with the GROQ_OCR_MODEL environment variable.
_GROQ_VISION_MODELS = [
    model
    for model in [
        os.getenv("GROQ_OCR_MODEL", "").strip(),
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
    ]
    if model
]

_OCR_PROMPT = (
    "Extract and return ALL text visible in this image, exactly as it appears. "
    "Preserve line breaks and formatting as much as possible. "
    "Do not summarize, translate, or add any commentary."
)


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


def _fix_char_spacing(text: str) -> str:
    """Fix pypdf per-character spacing: 'W o r k  H i s t o r y' → 'Work History'."""
    result = []
    for line in text.split('\n'):
        tokens = [t for t in line.split(' ') if t]
        if not tokens:
            result.append(line)
            continue
        single = sum(1 for t in tokens if len(t) == 1)
        if len(tokens) >= 3 and single / len(tokens) >= 0.5:
            words = re.split(r' {2,}', line)
            fixed = ' '.join(w.replace(' ', '') for w in words if w.strip())
            result.append(fixed)
        else:
            result.append(line)
    return '\n'.join(result)


def _extract_pdf(path: Path) -> str:
    """Extract text from a PDF using pypdf, with OCR fallback for scanned PDFs."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf is required for PDF extraction: pip install pypdf")

    pdf_bytes = path.read_bytes()
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        t = page.extract_text()
        if t and t.strip():
            pages.append(t.strip())

    text = "\n\n".join(pages).strip()
    text = _fix_char_spacing(text)

    # If minimal text extracted, try OCR fallback
    if len(text) < 100:
        ocr_text = _ocr_pdf_pages(pdf_bytes)
        if ocr_text:
            return ocr_text

    if not text:
        raise ValueError("No text found in PDF.")
    return text


def _ocr_pdf_pages(pdf_bytes: bytes) -> str:
    """Render each PDF page as an image and OCR via Groq vision API.

    Used as a fallback when pypdf cannot extract text (image-based / scanned PDFs).
    """
    try:
        import fitz  # pymupdf
    except ImportError:
        logging.warning("[OCR] pymupdf not installed — pip install pymupdf")
        return ""

    try:
        import requests
        from PIL import Image
    except ImportError:
        logging.warning("[OCR] requests and Pillow required for OCR")
        return ""

    groq_api_key = os.getenv("GROQ_API_KEY", "")
    if not groq_api_key:
        logging.warning("[OCR] GROQ_API_KEY not set")
        return ""

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_texts = []

    for page_num, page in enumerate(doc):
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")

        img = Image.open(io.BytesIO(img_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        if max(img.size) > 1536:
            img.thumbnail((1536, 1536), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        data_uri = f"data:image/jpeg;base64,{b64}"

        text = None
        for model_name in _GROQ_VISION_MODELS:
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_name,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": _OCR_PROMPT},
                                {"type": "image_url", "image_url": {"url": data_uri}},
                            ],
                        }],
                        "max_tokens": 2048,
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    text = resp.json()["choices"][0]["message"]["content"].strip()
                    break
            except Exception:
                continue

        if text:
            page_texts.append(text)

    doc.close()
    return "\n\n".join(page_texts)


def _extract_docx(path: Path) -> str:
    """Extract text from a DOCX using python-docx (with XML fallback)."""
    try:
        from docx import Document
        from docx.oxml.ns import qn as _qn
        from docx.text.paragraph import Paragraph as _Paragraph
        doc = Document(str(path))
        paras = [_Paragraph(p_el, doc) for p_el in doc.element.body.iter(_qn('w:p'))]
        text = "\n".join(p.text for p in paras if p.text.strip()).strip()
        text = _fix_char_spacing(text)
        if text:
            return text
    except ImportError:
        pass

    # Fallback: pure-Python XML parsing (no extra deps)
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
    """OCR an image using Groq vision API (with g4f fallback)."""
    import requests
    from PIL import Image

    # Try Groq vision API first
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    if groq_api_key:
        try:
            img = Image.open(str(path))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            if max(img.size) > 1536:
                img.thumbnail((1536, 1536), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode()
            data_uri = f"data:image/jpeg;base64,{b64}"

            for model_name in _GROQ_VISION_MODELS:
                try:
                    resp = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {groq_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model_name,
                            "messages": [{
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": _OCR_PROMPT},
                                    {"type": "image_url", "image_url": {"url": data_uri}},
                                ],
                            }],
                            "max_tokens": 2048,
                        },
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        text = resp.json()["choices"][0]["message"]["content"].strip()
                        if text and text != "No text found.":
                            return text
                except Exception:
                    continue
        except Exception:
            pass

    # Fallback: g4f vision provider (name varies between g4f releases)
    try:
        import g4f
        vision = None
        for name in ("PollinationsAI", "Blackbox", "Chatgpt4o", "DeepSeek"):
            vision = getattr(g4f.Provider, name, None)
            if vision is not None:
                break
        with open(str(path), "rb") as img_file:
            response = g4f.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": _OCR_PROMPT}],
                image=img_file,
                provider=vision,
            )

        text = ""
        if isinstance(response, str):
            text = response.strip()
        elif isinstance(response, dict) and "choices" in response:
            text = response["choices"][0]["message"]["content"].strip()

        if text:
            return text
    except Exception:
        pass

    raise RuntimeError("Could not extract text from image.")
