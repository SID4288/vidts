"""High-quality Text-to-Speech narration provider using edge-tts."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import re
import subprocess
import uuid

import edge_tts
import imageio_ffmpeg

from app.config import NarrationSettings
from app.narration.models import AudioTrack, NarrationResult
from app.narration.narrator import Narrator
from app.segmentation.models import DocumentSegment

LOGGER = logging.getLogger(__name__)


def get_audio_duration(audio_path: Path) -> float:
    """Extracts duration in seconds of an audio file using FFmpeg."""
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        result = subprocess.run(
            [ffmpeg_exe, "-i", str(audio_path)],
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
        if match:
            hours, minutes, seconds = match.groups()
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except Exception as exc:  # pragma: no cover
        LOGGER.debug("Could not determine exact audio duration with ffmpeg: %s", exc)
    return 0.0


async def _synthesize_async(
    text: str,
    output_file: Path,
    voice: str,
    rate: str,
    volume: str,
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, volume=volume)
    await communicate.save(str(output_file))


class EdgeTTSNarrator(Narrator):
    """Generates natural neural audio narration using Microsoft Edge TTS."""

    def __init__(
        self,
        output_directory: Path | str = "output",
        settings: NarrationSettings | None = None,
    ) -> None:
        self.output_directory = Path(output_directory)
        self.settings = settings or NarrationSettings()

    def narrate(self, segments: list[DocumentSegment]) -> NarrationResult:
        LOGGER.info(
            "Generating real neural narration for %d segment(s) using voice '%s'",
            len(segments),
            self.settings.voice,
        )
        self.output_directory.mkdir(parents=True, exist_ok=True)
        tracks: list[AudioTrack] = []
        total_duration = 0.0

        for segment in segments:
            track_id = f"track_{segment.part_number}_{uuid.uuid4().hex[:8]}"
            audio_path = self.output_directory / f"part_{segment.part_number}_audio.mp3"

            text_to_speak = segment.script.strip()
            if not text_to_speak:
                text_to_speak = f"Part {segment.part_number} narration summary."

            try:
                # Run async TTS generator in sync flow
                asyncio.run(
                    _synthesize_async(
                        text=text_to_speak,
                        output_file=audio_path,
                        voice=self.settings.voice,
                        rate=self.settings.rate,
                        volume=self.settings.volume,
                    )
                )
                duration = get_audio_duration(audio_path)
                if duration <= 0.0:
                    # Fallback duration calculation (~150 words per minute)
                    duration = (len(text_to_speak.split()) / 150.0) * 60.0
                LOGGER.info(
                    "Generated narration audio for Part %d: %s (duration: %.1fs)",
                    segment.part_number,
                    audio_path,
                    duration,
                )
            except Exception as exc:
                LOGGER.error("Failed to generate edge-tts audio for Part %d: %s", segment.part_number, exc)
                audio_path = None
                duration = segment.estimated_duration_seconds or 10.0

            total_duration += duration
            tracks.append(
                AudioTrack(
                    track_id=track_id,
                    segment_part_number=segment.part_number,
                    audio_path=audio_path,
                    duration_seconds=duration,
                    audio_format="mp3",
                    metadata={
                        "voice": self.settings.voice,
                        "words": len(text_to_speak.split()),
                    },
                )
            )

        return NarrationResult(
            tracks=tracks,
            total_duration_seconds=total_duration,
            engine="edge-tts",
        )
