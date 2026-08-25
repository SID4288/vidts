"""Data models for video rendering output."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class VideoPart:
    """Represents a rendered video file for a specific segment/part."""

    part_number: int
    video_path: Path | None = None
    duration_seconds: float = 0.0
    resolution: str = "1920x1080"
    fps: int = 30
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RenderedVideo:
    """Represents the complete video rendering result."""

    video_path: Path | None = None
    parts: list[VideoPart] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    resolution: str = "1920x1080"
    fps: int = 30
    status: str = "placeholder"
    metadata: dict[str, Any] = field(default_factory=dict)
