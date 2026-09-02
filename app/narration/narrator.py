"""Narration generator abstractions and placeholder implementations."""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.narration.models import AudioTrack, NarrationResult
from app.segmentation.models import DocumentSegment

LOGGER = logging.getLogger(__name__)


class Narrator(ABC):
    """Abstract interface for text-to-speech narration providers."""

    @abstractmethod
    def narrate(self, segments: list[DocumentSegment]) -> NarrationResult:
        """Generates narration audio tracks for the given segments."""
        raise NotImplementedError


class PlaceholderNarrator(Narrator):
    """Placeholder narration engine that simulates audio creation for the skeleton."""

    def __init__(self, output_directory: Path | str = "output") -> None:
        self.output_directory = Path(output_directory)

    def narrate(self, segments: list[DocumentSegment]) -> NarrationResult:
        LOGGER.info("Generating placeholder narration metadata for %d segments", len(segments))
        tracks: list[AudioTrack] = []
        total_duration = 0.0

        for segment in segments:
            track_id = f"track_{segment.part_number}_{uuid.uuid4().hex[:8]}"
            audio_path = self.output_directory / f"part_{segment.part_number}_audio.mp3"
            duration = segment.estimated_duration_seconds or 10.0
            total_duration += duration

            tracks.append(
                AudioTrack(
                    track_id=track_id,
                    segment_part_number=segment.part_number,
                    audio_path=audio_path,
                    duration_seconds=duration,
                    audio_format="mp3",
                    metadata={"status": "placeholder", "words": len(segment.script.split())},
                )
            )

        return NarrationResult(
            tracks=tracks,
            total_duration_seconds=total_duration,
            engine="placeholder",
        )
