"""Resume / JD file -> plain text conversion.

Responsible for:
- PDF text extraction via pdfplumber (primary) and pymupdf (fallback).
- DOCX text extraction via python-docx.
- Returning clean UTF-8 text with no LLM involvement.
- Raising structured ParseError for unreadable / unsupported files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import pdfplumber
import pymupdf  # type: ignore[import-untyped]
from docx import Document  # type: ignore[import-untyped]


class ParseError(Exception):
    """Raised when a file cannot be read or is in an unsupported format."""

    def __init__(self, file_path: str | Path, reason: str) -> None:
        self.file_path = str(file_path)
        self.reason = reason
        super().__init__(f"Cannot parse {file_path}: {reason}")


SUPPORTED_EXTENSIONS: set[str] = {".pdf", ".docx", ".doc", ".txt", ".md"}


def validate_file(file_path: str | Path) -> Path:
    """Return a resolved Path or raise ParseError for unsupported/missing files."""
    p = Path(file_path)
    if not p.exists():
        raise ParseError(p, "file not found")
    if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ParseError(
            p,
            f"unsupported extension '{p.suffix}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )
    return p.resolve()


def extract_pdf_text(file_path: Path) -> str:
    """Extract text from PDF using pdfplumber with pymupdf fallback."""
    try:
        with pdfplumber.open(file_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n\n".join(pages)
        if text.strip():
            return text
    except Exception:
        pass

    # Fallback: pymupdf
    try:
        doc = pymupdf.open(file_path)
        pages = [page.get_text() for page in doc]
        doc.close()
        text = "\n\n".join(pages)
        if text.strip():
            return text
    except Exception as exc:
        raise ParseError(file_path, f"pdfplumber and pymupdf both failed: {exc}") from exc

    raise ParseError(file_path, "PDF contained no extractable text (scanned image? OCR needed)")


def extract_docx_text(file_path: Path) -> str:
    """Extract text from a .docx file using python-docx."""
    try:
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n\n".join(paragraphs)
        if text.strip():
            return text
    except Exception as exc:
        raise ParseError(file_path, f"python-docx failed: {exc}") from exc

    raise ParseError(file_path, "DOCX contained no extractable text")


def parse(file_path: str | Path) -> str:
    """Parse a resume or JD file and return plain text.

    Raises:
        ParseError: if the file is missing, unsupported, or unreadable.
    """
    p = validate_file(file_path)
    suffix = p.suffix.lower()

    if suffix == ".pdf":
        return extract_pdf_text(p)
    if suffix in {".docx", ".doc"}:
        return extract_docx_text(p)
    if suffix in {".txt", ".md"}:
        try:
            return p.read_text(encoding="utf-8")
        except Exception as exc:
            raise ParseError(p, f"failed to read text file: {exc}") from exc

    # This should never happen due to validate_file, but belt-and-suspenders.
    raise ParseError(p, f"unhandled extension '{suffix}'")
