"""Application configuration loading and typed settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class LLMSettings:
    provider: str = "ollama"
    model: str = "llama3.2"
    base_url: str = "http://localhost:11434"
    timeout_seconds: int = 300


@dataclass(slots=True)
class DocumentSettings:
    max_pages: int | None = None


@dataclass(slots=True)
class SegmentationSettings:
    enabled: bool = True
    max_duration_minutes: int = 10
    max_script_words: int = 1800
    max_pages_per_video: int | None = None


@dataclass(slots=True)
class NarrationSettings:
    engine: str = "edge-tts"
    voice: str = "en-US-ChristopherNeural"
    rate: str = "+0%"
    volume: str = "+0%"


@dataclass(slots=True)
class OutputSettings:
    directory: str = "output"


@dataclass(slots=True)
class VideoSettings:
    resolution: str = "1920x1080"
    fps: int = 30


@dataclass(slots=True)
class AppConfig:
    llm: LLMSettings = field(default_factory=LLMSettings)
    document: DocumentSettings = field(default_factory=DocumentSettings)
    segmentation: SegmentationSettings = field(default_factory=SegmentationSettings)
    narration: NarrationSettings = field(default_factory=NarrationSettings)
    output: OutputSettings = field(default_factory=OutputSettings)
    video: VideoSettings = field(default_factory=VideoSettings)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AppConfig":
        llm = LLMSettings(**raw.get("llm", {}))
        document = DocumentSettings(**raw.get("document", {}))
        segmentation = SegmentationSettings(**raw.get("segmentation", {}))
        narration = NarrationSettings(**raw.get("narration", {}))
        output = OutputSettings(**raw.get("output", {}))
        video = VideoSettings(**raw.get("video", {}))
        return cls(
            llm=llm,
            document=document,
            segmentation=segmentation,
            narration=narration,
            output=output,
            video=video,
        )


def load_config(config_path: str | Path = "config.yaml") -> AppConfig:
    path = Path(config_path)
    if not path.exists():
        return AppConfig()

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return AppConfig()
    if not isinstance(data, dict):
        raise ValueError("config.yaml must contain a top-level mapping")
    return AppConfig.from_dict(data)
