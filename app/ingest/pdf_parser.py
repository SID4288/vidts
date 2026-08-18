"""PDF parser for creating generic Document objects."""

from __future__ import annotations

import uuid
from pathlib import Path

from pypdf import PdfReader

from app import PDFParseError
from app.ingest.models import Document
from app.ingest.page_extractor import PageExtractor


class PDFParser:
    """Parses PDF files into document domain models."""

    def __init__(self, max_pages: int | None = None, page_extractor: PageExtractor | None = None) -> None:
        self.max_pages = max_pages
        self.page_extractor = page_extractor or PageExtractor()

    def parse(self, source_path: str | Path) -> Document:
        path = Path(source_path)
        if not path.exists():
            raise PDFParseError(f"PDF file not found: {path}")

        try:
            reader = PdfReader(str(path))
        except Exception as exc:  # pragma: no cover - defensive path
            raise PDFParseError(f"Failed to open PDF: {path}") from exc

        try:
            pages = self.page_extractor.extract_pages(reader, max_pages=self.max_pages)
            raw_title = getattr(reader.metadata, "title", None) if reader.metadata else None
            title = raw_title or path.stem
            metadata = {
                "num_pages": len(reader.pages),
                "is_encrypted": bool(reader.is_encrypted),
            }
            return Document(
                id=str(uuid.uuid4()),
                source_path=path,
                title=title,
                pages=pages,
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover - defensive path
            raise PDFParseError(f"Failed while parsing PDF contents: {path}") from exc
