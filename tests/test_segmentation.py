"""Tests for recap segmentation."""

from __future__ import annotations

import pytest

from app.config import SegmentationSettings
from app.recap.models import Recap, RecapSection
from app.segmentation.segmenter import Segmenter


def test_segmentation_single_part_when_within_limits() -> None:
    settings = SegmentationSettings(
        enabled=True,
        max_duration_minutes=10,
        max_script_words=1800,
    )
    segmenter = Segmenter(settings=settings)
    recap = Recap(
        title="Short Story",
        summary="Summary",
        sections=[RecapSection(title="S1", content="Text")],
        raw_script="This is a short script containing twenty words that easily fits within normal single video length limits.",
        estimated_duration_seconds=120.0,
    )

    segments = segmenter.segment(recap, total_pages=5)
    assert len(segments) == 1
    assert segments[0].part_number == 1
    assert "Complete" in segments[0].title
    assert segments[0].estimated_duration_seconds == 120.0


def test_segmentation_splits_when_duration_exceeded() -> None:
    settings = SegmentationSettings(
        enabled=True,
        max_duration_minutes=5,  # 300 seconds
        max_script_words=1800,
    )
    segmenter = Segmenter(settings=settings)
    # Long estimated duration of 900 seconds (15 mins -> 3 parts)
    long_script = "word " * 600
    recap = Recap(
        title="Long Lecture",
        summary="A long lecture recap",
        raw_script=long_script,
        estimated_duration_seconds=900.0,
    )

    segments = segmenter.segment(recap, total_pages=30)
    assert len(segments) >= 3
    assert segments[0].part_number == 1
    assert segments[1].part_number == 2
    assert "Part 1" in segments[0].title
    assert sum(s.estimated_duration_seconds for s in segments) == pytest.approx(900.0, rel=1e-2)


def test_segmentation_splits_when_word_count_exceeded() -> None:
    settings = SegmentationSettings(
        enabled=True,
        max_duration_minutes=60,
        max_script_words=100,  # small threshold
    )
    segmenter = Segmenter(settings=settings)
    long_script = " ".join([f"word{i}" for i in range(250)])
    recap = Recap(
        title="Wordy Story",
        summary="Summary",
        raw_script=long_script,
        estimated_duration_seconds=100.0,
    )

    segments = segmenter.segment(recap, total_pages=10)
    assert len(segments) >= 3


def test_segmentation_disabled_keeps_single_part() -> None:
    settings = SegmentationSettings(enabled=False, max_duration_minutes=1)
    segmenter = Segmenter(settings=settings)
    recap = Recap(
        title="Unsplit Video",
        summary="Summary",
        raw_script="word " * 500,
        estimated_duration_seconds=600.0,
    )
    segments = segmenter.segment(recap, total_pages=20)
    assert len(segments) == 1
