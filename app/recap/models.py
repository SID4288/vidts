"""Data models for document recap and narration scripts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RecapScene:
    """Represents a discrete slide/scene paired with a specific PDF page."""

    scene_index: int
    page_number: int
    title: str
    narration_text: str
    estimated_duration_seconds: float = 0.0


@dataclass(slots=True)
class RecapSection:
    """Represents a thematic section in a structured recap."""

    title: str
    content: str
    key_takeaways: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Recap:
    """Represents the complete generated recap for a document."""

    title: str
    summary: str
    sections: list[RecapSection] = field(default_factory=list)
    scenes: list[RecapScene] = field(default_factory=list)
    raw_script: str = ""
    estimated_duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
