"""Segmentation interfaces and models."""

from __future__ import annotations

from app.segmentation.models import DocumentSegment
from app.segmentation.segmenter import Segmenter

__all__ = [
    "DocumentSegment",
    "Segmenter",
]
