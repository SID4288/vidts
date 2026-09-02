"""Page extraction and visual rendering abstractions for PDF ingestion."""

from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader

from app.ingest.models import DocumentPage

LOGGER = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF

    HAS_PYMUPDF = True
except ImportError:  # pragma: no cover
    HAS_PYMUPDF = False


class PageExtractor:
    """Extracts per-page text, dimensions, and visual slide images from a PDF."""

    def __init__(self, image_output_dir: Path | str | None = None) -> None:
        self.image_output_dir = Path(image_output_dir) if image_output_dir else Path("output/pages")

    def extract_pages(
        self,
        reader: PdfReader,
        max_pages: int | None = None,
        source_path: Path | None = None,
    ) -> list[DocumentPage]:
        pages: list[DocumentPage] = []
        doc_fitz = None
        if HAS_PYMUPDF and source_path and source_path.exists():
            try:
                doc_fitz = fitz.open(str(source_path))
                self.image_output_dir.mkdir(parents=True, exist_ok=True)
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("Could not open PDF with PyMuPDF for visual extraction: %s", exc)

        for index, page in enumerate(reader.pages, start=1):
            if max_pages is not None and index > max_pages:
                break
            text = page.extract_text() or ""
            mediabox = page.mediabox
            width = float(mediabox.width) if mediabox else None
            height = float(mediabox.height) if mediabox else None
            image_path: Path | None = None

            # Render page visual image if PyMuPDF is available
            if doc_fitz and (index - 1) < len(doc_fitz):
                try:
                    fitz_page = doc_fitz[index - 1]
                    pix = fitz_page.get_pixmap(dpi=150)
                    img_file = self.image_output_dir / f"page_{index}.png"
                    pix.save(str(img_file))
                    image_path = img_file
                except Exception as exc:  # pragma: no cover
                    LOGGER.warning("Failed to render page image for page %d: %s", index, exc)

            pages.append(
                DocumentPage(
                    page_number=index,
                    text=text,
                    image_path=image_path,
                    width=width,
                    height=height,
                )
            )

        if doc_fitz:
            doc_fitz.close()

        return pages
