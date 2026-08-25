"""Tests for PDF ingestion and parsing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app import PDFParseError
from app.ingest.models import Document, DocumentPage, DocumentType
from app.ingest.page_extractor import PageExtractor
from app.ingest.pdf_parser import PDFParser


def test_pdf_parser_nonexistent_file() -> None:
    parser = PDFParser()
    with pytest.raises(PDFParseError, match="PDF file not found"):
        parser.parse("non_existent_file.pdf")


def test_page_extractor_mock() -> None:
    mock_reader = MagicMock()
    mock_page_1 = MagicMock()
    mock_page_1.extract_text.return_value = "Page 1 sample content."
    mock_page_1.mediabox.width = 612.0
    mock_page_1.mediabox.height = 792.0

    mock_page_2 = MagicMock()
    mock_page_2.extract_text.return_value = "Page 2 sample content."
    mock_page_2.mediabox.width = 612.0
    mock_page_2.mediabox.height = 792.0

    mock_reader.pages = [mock_page_1, mock_page_2]

    extractor = PageExtractor()
    pages = extractor.extract_pages(mock_reader)

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[0].text == "Page 1 sample content."
    assert pages[0].width == 612.0
    assert pages[0].height == 792.0


def test_page_extractor_max_pages() -> None:
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Text"
    mock_page.mediabox = None
    mock_reader.pages = [mock_page, mock_page, mock_page]

    extractor = PageExtractor()
    pages = extractor.extract_pages(mock_reader, max_pages=2)
    assert len(pages) == 2


def test_document_model_creation() -> None:
    doc = Document(
        id="doc-123",
        source_path=Path("sample.pdf"),
        title="Sample Document",
        document_type=DocumentType.GENERAL,
        pages=[DocumentPage(page_number=1, text="Hello world")],
        metadata={"author": "Test Author"},
    )
    assert doc.id == "doc-123"
    assert doc.title == "Sample Document"
    assert len(doc.pages) == 1
    assert doc.metadata["author"] == "Test Author"
