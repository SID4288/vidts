"""Data models for narration and speech generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AudioTrack:
    """Represents a generated narration audio track for a segment."""

    track_id: str
    segment_part_number: int
    audio_path: Path | None = None
    duration_seconds: float = 0.0
    audio_format: str = "mp3"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NarrationResult:
    """Aggregates all narration audio tracks for a pipeline run."""

    tracks: list[AudioTrack] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    engine: str = "placeholder"
