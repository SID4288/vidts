"""Narration generation interfaces and models."""

from __future__ import annotations

from app.narration.edge_tts_narrator import EdgeTTSNarrator
from app.narration.models import AudioTrack, NarrationResult, SceneAudio
from app.narration.narrator import Narrator, PlaceholderNarrator

__all__ = [
    "AudioTrack",
    "EdgeTTSNarrator",
    "NarrationResult",
    "Narrator",
    "PlaceholderNarrator",
    "SceneAudio",
]
