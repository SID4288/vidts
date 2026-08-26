"""Data models for document recap segmentation and video parts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.recap.models import RecapScene


@dataclass(slots=True)
class DocumentSegment:
    """Represents a discrete part/segment planned for video generation."""

    part_number: int
    title: str
    script: str
    source_pages: list[int] = field(default_factory=list)
    scenes: list[RecapScene] = field(default_factory=list)
    estimated_duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
