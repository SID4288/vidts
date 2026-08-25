from __future__ import annotations

import logging

from app.analysis.models import DocumentAnalysis
from app.ingest.models import Document, DocumentSection, DocumentType

LOGGER = logging.getLogger(__name__)

class DocumentAnalyzer:

    def analyze(self, document: Document) -> DocumentAnalysis:
        """Performs initial heuristic analysis (placeholder for future deep/LLM analysis)."""
        total_pages = len(document.pages)
        if total_pages == 0:
            LOGGER.warning("Analyzing document with 0 pages: %s", document.id)
            return DocumentAnalysis(
                title=document.title or "Untitled Document",
                document_type=DocumentType.UNKNOWN,
                sections=[],
                key_topics=[],
                is_primarily_visual=False,
                summary="Empty document",
            )

        # Heuristic check for visual vs text density
        total_text_length = sum(len(page.text.strip()) for page in document.pages)
        avg_text_length = total_text_length / total_pages
        is_primarily_visual = avg_text_length < 80

        # Heuristic document classification
        doc_type = DocumentType.GENERAL
        if is_primarily_visual:
            doc_type = DocumentType.COMIC
        elif any("chapter" in page.text.lower() for page in document.pages):
            doc_type = DocumentType.TEXTBOOK

        # Build initial basic sectioning
        sections: list[DocumentSection] = []
        if total_pages > 0:
            sections.append(
                DocumentSection(
                    title="Overview Section",
                    start_page=1,
                    end_page=total_pages,
                    text=" ".join(p.text for p in document.pages[:3]).strip(),
                )
            )

        return DocumentAnalysis(
            title=document.title or "Untitled Document",
            document_type=doc_type,
            sections=sections,
            key_topics=["Introduction", "Core Subject"],
            is_primarily_visual=is_primarily_visual,
            summary=f"Analysis of '{document.title}' ({total_pages} pages, type={doc_type.value}).",
            metadata={"avg_page_text_length": avg_text_length, "total_pages": total_pages},
        )
