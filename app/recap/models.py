"""Data models for document recap and narration scripts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RecapSection:
    """Represents a section in a structured recap."""

    title: str
    content: str
    key_takeaways: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Recap:
    """Represents the complete generated recap for a document."""

    title: str
    summary: str
    sections: list[RecapSection] = field(default_factory=list)
    raw_script: str = ""
    estimated_duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
