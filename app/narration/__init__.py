"""Narration generation interfaces and models."""

from __future__ import annotations

from app.narration.models import AudioTrack, NarrationResult
from app.narration.narrator import Narrator, PlaceholderNarrator

__all__ = [
    "AudioTrack",
    "NarrationResult",
    "Narrator",
    "PlaceholderNarrator",
]
