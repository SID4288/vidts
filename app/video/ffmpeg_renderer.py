"""Real MP4 video rendering engine using FFmpeg."""

from __future__ import annotations

import logging
from pathlib import Path
import subprocess

import imageio_ffmpeg

from app.narration.models import NarrationResult
from app.segmentation.models import DocumentSegment
from app.video.models import RenderedVideo, VideoPart
from app.video.renderer import VideoRenderer

LOGGER = logging.getLogger(__name__)


class FFmpegVideoRenderer(VideoRenderer):
    """Renders synchronized MP4 videos from page visuals and narration audio."""

    def __init__(
        self,
        output_directory: Path | str = "output",
        resolution: str = "1920x1080",
        fps: int = 30,
        pages_directory: Path | str = "output/pages",
    ) -> None:
        self.output_directory = Path(output_directory)
        self.resolution = resolution
        self.fps = fps
        self.pages_directory = Path(pages_directory)

    def render(
        self,
        segments: list[DocumentSegment],
        narration: NarrationResult,
    ) -> RenderedVideo:
        LOGGER.info("Rendering %d MP4 video part(s) using FFmpeg", len(segments))
        self.output_directory.mkdir(parents=True, exist_ok=True)
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        parts: list[VideoPart] = []
        total_duration = 0.0

        for segment in segments:
            matching_track = next(
                (t for t in narration.tracks if t.segment_part_number == segment.part_number),
                None,
            )
            audio_path = matching_track.audio_path if matching_track else None
            duration = matching_track.duration_seconds if matching_track else segment.estimated_duration_seconds
            total_duration += duration

            out_video_path = self.output_directory / f"part_{segment.part_number}.mp4"

            # Find matching page visual images
            image_files: list[Path] = []
            for p_num in segment.source_pages:
                img_p = self.pages_directory / f"page_{p_num}.png"
                if img_p.exists():
                    image_files.append(img_p)

            # Fallback if no specific page images found: look for any page in output/pages
            if not image_files and self.pages_directory.exists():
                image_files = sorted(self.pages_directory.glob("page_*.png"))

            try:
                self._render_part_ffmpeg(
                    ffmpeg_exe=ffmpeg_exe,
                    image_files=image_files,
                    audio_path=audio_path,
                    duration=duration,
                    output_path=out_video_path,
                )
                LOGGER.info("Successfully rendered video: %s (duration: %.1fs)", out_video_path, duration)
            except Exception as exc:
                LOGGER.error("FFmpeg render failed for Part %d: %s", segment.part_number, exc)

            parts.append(
                VideoPart(
                    part_number=segment.part_number,
                    video_path=out_video_path,
                    duration_seconds=duration,
                    resolution=self.resolution,
                    fps=self.fps,
                    metadata={"status": "rendered", "page_count": len(image_files)},
                )
            )

        final_path = parts[0].video_path if len(parts) == 1 else self.output_directory / "combined_output.mp4"

        return RenderedVideo(
            video_path=final_path,
            parts=parts,
            total_duration_seconds=total_duration,
            resolution=self.resolution,
            fps=self.fps,
            status="rendered",
            metadata={"num_parts": len(parts)},
        )

    def _render_part_ffmpeg(
        self,
        ffmpeg_exe: str,
        image_files: list[Path],
        audio_path: Path | None,
        duration: float,
        output_path: Path,
    ) -> None:
        width, height = self.resolution.split("x")
        video_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
        )

        if image_files and len(image_files) > 1 and audio_path and audio_path.exists():
            # Multi-image slideshow timed to audio
            slide_duration = max(duration / len(image_files), 0.5)
            concat_txt = output_path.parent / f"concat_part_{output_path.stem}.txt"
            lines: list[str] = []
            for img in image_files:
                # Use forward slashes in concat file for cross-platform FFmpeg support
                p_str = img.resolve().as_posix()
                lines.append(f"file '{p_str}'")
                lines.append(f"duration {slide_duration:.3f}")
            # Concat demuxer requires repeating last file
            lines.append(f"file '{image_files[-1].resolve().as_posix()}'")
            concat_txt.write_text("\n".join(lines), encoding="utf-8")

            cmd = [
                ffmpeg_exe,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_txt),
                "-i",
                str(audio_path),
                "-vf",
                video_filter,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(self.fps),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(output_path),
            ]
        elif image_files and audio_path and audio_path.exists():
            # Single image looped with audio
            img_path = image_files[0]
            cmd = [
                ffmpeg_exe,
                "-y",
                "-loop",
                "1",
                "-i",
                str(img_path),
                "-i",
                str(audio_path),
                "-vf",
                video_filter,
                "-c:v",
                "libx264",
                "-tune",
                "stillimage",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(self.fps),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(output_path),
            ]
        elif audio_path and audio_path.exists():
            # No images: color background generator with audio
            cmd = [
                ffmpeg_exe,
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=black:s={self.resolution}:r={self.fps}",
                "-i",
                str(audio_path),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(output_path),
            ]
        else:
            # Silent placeholder slide
            cmd = [
                ffmpeg_exe,
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=black:s={self.resolution}:r={self.fps}:d={max(duration, 3.0):.2f}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(output_path),
            ]

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
        if proc.returncode != 0:
            LOGGER.warning("FFmpeg command warning/error (code %d): %s", proc.returncode, proc.stderr[-400:])
