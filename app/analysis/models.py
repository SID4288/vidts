from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ingest.models import DocumentSection, DocumentType


@dataclass(slots=True)
class DocumentAnalysis:
    """Represents high-level structural and semantic document insights."""

    title: str
    document_type: DocumentType = DocumentType.GENERAL
    sections: list[DocumentSection] = field(default_factory=list)
    key_topics: list[str] = field(default_factory=list)
    is_primarily_visual: bool = False
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
