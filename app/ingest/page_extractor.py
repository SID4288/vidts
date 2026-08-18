"""Page extraction abstractions for PDF ingestion.

This module is intentionally simple for the skeleton and keeps OCR as a future extension.
"""

from __future__ import annotations

from pypdf import PdfReader

from app.ingest.models import DocumentPage


class PageExtractor:
    """Extracts per-page text and dimensions from a PDF reader."""

    def extract_pages(self, reader: PdfReader, max_pages: int | None = None) -> list[DocumentPage]:
        pages: list[DocumentPage] = []
        for index, page in enumerate(reader.pages, start=1):
            if max_pages is not None and index > max_pages:
                break
            text = page.extract_text() or ""
            mediabox = page.mediabox
            width = float(mediabox.width) if mediabox else None
            height = float(mediabox.height) if mediabox else None
            pages.append(
                DocumentPage(
                    page_number=index,
                    text=text,
                    image_path=None,
                    width=width,
                    height=height,
                )
            )
        return pages
