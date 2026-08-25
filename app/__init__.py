"""Core package for vidts."""

from __future__ import annotations


class VidtsError(Exception):
    """Base exception for all application errors."""


class PDFParseError(VidtsError):
    """Raised when PDF parsing fails."""


class LLMError(VidtsError):
    """Raised when an LLM provider call fails."""


class SegmentationError(VidtsError):
    """Raised when segmentation cannot complete safely."""


class VideoRenderError(VidtsError):
    """Raised when video rendering fails."""


__all__ = [
    "VidtsError",
    "PDFParseError",
    "LLMError",
    "SegmentationError",
    "VideoRenderError",
]
