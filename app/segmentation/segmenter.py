"""Intelligent segmentation logic for deciding video parts."""

from __future__ import annotations

import logging
import math

from app.config import SegmentationSettings
from app.recap.models import Recap
from app.segmentation.models import DocumentSegment

LOGGER = logging.getLogger(__name__)


class Segmenter:
    """Segments a recap into one or more video parts based on length constraints."""

    def __init__(self, settings: SegmentationSettings | None = None) -> None:
        self.settings = settings or SegmentationSettings()

    def segment(self, recap: Recap, total_pages: int = 1) -> list[DocumentSegment]:
        """Evaluates constraints and partitions recap into single or multi-part segments."""
        max_duration_seconds = self.settings.max_duration_minutes * 60
        max_words = self.settings.max_script_words
        words = recap.raw_script.split()
        total_words = len(words)

        needs_split = False
        if self.settings.enabled:
            if recap.estimated_duration_seconds > max_duration_seconds:
                needs_split = True
            elif total_words > max_words:
                needs_split = True
            elif (
                self.settings.max_pages_per_video is not None
                and total_pages > self.settings.max_pages_per_video
            ):
                needs_split = True

        all_pages = list(range(1, max(total_pages + 1, 2)))

        if not needs_split:
            LOGGER.info("Document fits within constraints; producing a single video part")
            return [
                DocumentSegment(
                    part_number=1,
                    title=f"{recap.title} - Complete",
                    script=recap.raw_script,
                    source_pages=all_pages,
                    estimated_duration_seconds=recap.estimated_duration_seconds,
                    metadata={"split_reason": "none", "part_count": 1},
                )
            ]

        # Calculate number of parts needed
        duration_parts = math.ceil(recap.estimated_duration_seconds / max(max_duration_seconds, 1))
        word_parts = math.ceil(total_words / max(max_words, 1))
        page_parts = (
            math.ceil(total_pages / self.settings.max_pages_per_video)
            if self.settings.max_pages_per_video
            else 1
        )
        num_parts = max(duration_parts, word_parts, page_parts, 2)
        LOGGER.info("Splitting recap into %d parts based on constraints", num_parts)

        segments: list[DocumentSegment] = []
        words_per_part = math.ceil(total_words / num_parts) if total_words > 0 else 0
        pages_per_part = math.ceil(len(all_pages) / num_parts) if all_pages else 1

        for part_idx in range(num_parts):
            start_w = part_idx * words_per_part
            end_w = min((part_idx + 1) * words_per_part, total_words)
            part_script = " ".join(words[start_w:end_w])

            start_p = part_idx * pages_per_part
            end_p = min((part_idx + 1) * pages_per_part, len(all_pages))
            part_pages = all_pages[start_p:end_p] or [1]

            part_duration = (
                (len(part_script.split()) / max(total_words, 1)) * recap.estimated_duration_seconds
                if total_words > 0
                else recap.estimated_duration_seconds / num_parts
            )

            segments.append(
                DocumentSegment(
                    part_number=part_idx + 1,
                    title=f"{recap.title} - Part {part_idx + 1}",
                    script=part_script,
                    source_pages=part_pages,
                    estimated_duration_seconds=part_duration,
                    metadata={"split_reason": "constraint_exceeded", "part_count": num_parts},
                )
            )

        return segments
