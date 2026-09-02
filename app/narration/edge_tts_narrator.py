"""High-quality Text-to-Speech narration provider using edge-tts with per-scene synchronization."""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
import uuid
from pathlib import Path

import edge_tts
import imageio_ffmpeg

from app.config import NarrationSettings
from app.narration.models import AudioTrack, NarrationResult, SceneAudio
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


def _combine_audio_clips(ffmpeg_exe: str, audio_files: list[Path], output_combined: Path) -> None:
    """Combines multiple MP3 audio files into a single master MP3 using FFmpeg concat."""
    if not audio_files:
        return
    if len(audio_files) == 1:
        # Copy single file directly
        output_combined.write_bytes(audio_files[0].read_bytes())
        return

    concat_file = output_combined.parent / f"concat_{output_combined.stem}.txt"
    lines = [f"file '{p.resolve().as_posix()}'" for p in audio_files]
    concat_file.write_text("\n".join(lines), encoding="utf-8")

    cmd = [
        ffmpeg_exe,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(output_combined),
    ]
    subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )


class EdgeTTSNarrator(Narrator):
    """Generates natural neural audio narration with scene-level precision."""

    def __init__(
        self,
        output_directory: Path | str = "output",
        settings: NarrationSettings | None = None,
    ) -> None:
        self.output_directory = Path(output_directory)
        self.settings = settings or NarrationSettings()

    def narrate(self, segments: list[DocumentSegment]) -> NarrationResult:
        LOGGER.info(
            "Synthesizing scene-by-scene narration using natural voice '%s'",
            self.settings.voice,
        )
        self.output_directory.mkdir(parents=True, exist_ok=True)
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        tracks: list[AudioTrack] = []
        total_duration = 0.0

        for segment in segments:
            track_id = f"track_{segment.part_number}_{uuid.uuid4().hex[:8]}"
            master_audio_path = self.output_directory / f"part_{segment.part_number}_audio.mp3"

            scene_audios: list[SceneAudio] = []
            synthesized_files: list[Path] = []
            segment_duration = 0.0

            if segment.scenes:
                LOGGER.info(
                    "Synthesizing %d individual scene audio clips for Part %d",
                    len(segment.scenes),
                    segment.part_number,
                )
                for scene in segment.scenes:
                    scene_path = (
                        self.output_directory
                        / f"part_{segment.part_number}_scene_{scene.scene_index}.mp3"
                    )
                    text_to_speak = scene.narration_text.strip()
                    if not text_to_speak:
                        text_to_speak = f"Page {scene.page_number}."

                    final_scene_file: Path | None = scene_path
                    try:
                        asyncio.run(
                            _synthesize_async(
                                text=text_to_speak,
                                output_file=scene_path,
                                voice=self.settings.voice,
                                rate=self.settings.rate,
                                volume=self.settings.volume,
                            )
                        )
                        dur = get_audio_duration(scene_path)
                        if dur <= 0.0:
                            dur = (len(text_to_speak.split()) / 150.0) * 60.0
                    except Exception as exc:
                        LOGGER.error(
                            "TTS failed for scene %d (page %d): %s",
                            scene.scene_index,
                            scene.page_number,
                            exc,
                        )
                        dur = (len(text_to_speak.split()) / 150.0) * 60.0
                        final_scene_file = None

                    if final_scene_file and final_scene_file.exists():
                        synthesized_files.append(final_scene_file)

                    scene_audios.append(
                        SceneAudio(
                            scene_index=scene.scene_index,
                            page_number=scene.page_number,
                            audio_path=final_scene_file,
                            duration_seconds=dur,
                        )
                    )
                    segment_duration += dur

                # Combine all scenes into master segment audio
                if synthesized_files:
                    _combine_audio_clips(ffmpeg_exe, synthesized_files, master_audio_path)
            else:
                # Fallback for monolithic segment without scenes
                text_to_speak = segment.script.strip() or f"Part {segment.part_number} narration."
                try:
                    asyncio.run(
                        _synthesize_async(
                            text=text_to_speak,
                            output_file=master_audio_path,
                            voice=self.settings.voice,
                            rate=self.settings.rate,
                            volume=self.settings.volume,
                        )
                    )
                    segment_duration = get_audio_duration(master_audio_path)
                except Exception as exc:
                    LOGGER.error(
                        "TTS failed for monolithic segment %d: %s", segment.part_number, exc
                    )
                    segment_duration = (len(text_to_speak.split()) / 150.0) * 60.0

            total_duration += segment_duration
            tracks.append(
                AudioTrack(
                    track_id=track_id,
                    segment_part_number=segment.part_number,
                    audio_path=master_audio_path if master_audio_path.exists() else None,
                    duration_seconds=segment_duration,
                    audio_format="mp3",
                    scenes=scene_audios,
                    metadata={
                        "voice": self.settings.voice,
                        "scenes_synthesized": len(scene_audios),
                    },
                )
            )

        return NarrationResult(
            tracks=tracks,
            total_duration_seconds=total_duration,
            engine="edge-tts",
        )
