"""Video renderer abstractions and placeholder implementations."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from app.narration.models import NarrationResult
from app.segmentation.models import DocumentSegment
from app.video.models import RenderedVideo, VideoPart

LOGGER = logging.getLogger(__name__)


class VideoRenderer(ABC):
    """Abstract interface for video rendering engines."""

    @abstractmethod
    def render(
        self,
        segments: list[DocumentSegment],
        narration: NarrationResult,
    ) -> RenderedVideo:
        """Renders video parts from segments and narration audio."""
        raise NotImplementedError


class PlaceholderVideoRenderer(VideoRenderer):
    """Placeholder video renderer simulating video generation for the skeleton."""

    def __init__(
        self,
        output_directory: Path | str = "output",
        resolution: str = "1920x1080",
        fps: int = 30,
    ) -> None:
        self.output_directory = Path(output_directory)
        self.resolution = resolution
        self.fps = fps

    def render(
        self,
        segments: list[DocumentSegment],
        narration: NarrationResult,
    ) -> RenderedVideo:
        LOGGER.info("Simulating video rendering for %d segment(s)", len(segments))
        self.output_directory.mkdir(parents=True, exist_ok=True)

        parts: list[VideoPart] = []
        total_duration = 0.0

        for segment in segments:
            matching_track = next(
                (t for t in narration.tracks if t.segment_part_number == segment.part_number),
                None,
            )
            duration = (
                matching_track.duration_seconds
                if matching_track
                else segment.estimated_duration_seconds
            )
            total_duration += duration

            part_path = self.output_directory / f"part_{segment.part_number}.mp4"
            parts.append(
                VideoPart(
                    part_number=segment.part_number,
                    video_path=part_path,
                    duration_seconds=duration,
                    resolution=self.resolution,
                    fps=self.fps,
                    metadata={"status": "placeholder"},
                )
            )

        final_path = (
            parts[0].video_path
            if len(parts) == 1
            else self.output_directory / "combined_output.mp4"
        )

        return RenderedVideo(
            video_path=final_path,
            parts=parts,
            total_duration_seconds=total_duration,
            resolution=self.resolution,
            fps=self.fps,
            status="placeholder_ready",
            metadata={"num_parts": len(parts)},
        )
