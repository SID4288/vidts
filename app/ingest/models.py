"""Core document ingestion models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class DocumentType(str, Enum):
    UNKNOWN = "unknown"
    COMIC = "comic"
    TEXTBOOK = "textbook"
    EDUCATIONAL = "educational"
    RESEARCH_PAPER = "research_paper"
    NOVEL = "novel"
    GENERAL = "general"


@dataclass(slots=True)
class DocumentPage:
    page_number: int
    text: str = ""
    image_path: Path | None = None
    width: float | None = None
    height: float | None = None


@dataclass(slots=True)
class DocumentSection:
    title: str
    start_page: int
    end_page: int
    text: str


@dataclass(slots=True)
class Document:
    id: str
    source_path: Path
    title: str
    document_type: DocumentType = DocumentType.UNKNOWN
    pages: list[DocumentPage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
