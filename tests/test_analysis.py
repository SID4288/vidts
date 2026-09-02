"""Tests for document analyzer."""

from __future__ import annotations

from pathlib import Path

from app.analysis.document_analyzer import DocumentAnalyzer
from app.ingest.models import Document, DocumentPage, DocumentType


def test_analyzer_empty_document() -> None:
    analyzer = DocumentAnalyzer()
    doc = Document(
        id="empty-doc",
        source_path=Path("empty.pdf"),
        title="Empty",
        pages=[],
    )
    analysis = analyzer.analyze(doc)
    assert analysis.document_type == DocumentType.UNKNOWN
    assert len(analysis.sections) == 0
    assert not analysis.is_primarily_visual


def test_analyzer_text_dense_document() -> None:
    analyzer = DocumentAnalyzer()
    pages = [
        DocumentPage(
            page_number=1, text="Chapter 1: Deep diving into quantum physics with formulas... " * 10
        ),
        DocumentPage(
            page_number=2, text="Continuing Chapter 1 analysis of wave particle duality... " * 10
        ),
    ]
    doc = Document(
        id="text-doc",
        source_path=Path("textbook.pdf"),
        title="Physics 101",
        pages=pages,
    )
    analysis = analyzer.analyze(doc)
    assert analysis.document_type == DocumentType.TEXTBOOK
    assert not analysis.is_primarily_visual
    assert len(analysis.sections) > 0
    assert analysis.title == "Physics 101"


def test_analyzer_visual_heavy_document() -> None:
    analyzer = DocumentAnalyzer()
    pages = [
        DocumentPage(page_number=1, text="Boom!"),
        DocumentPage(page_number=2, text="..."),
    ]
    doc = Document(
        id="comic-doc",
        source_path=Path("comic.pdf"),
        title="Superhero Comic",
        pages=pages,
    )
    analysis = analyzer.analyze(doc)
    assert analysis.document_type == DocumentType.COMIC
    assert analysis.is_primarily_visual
