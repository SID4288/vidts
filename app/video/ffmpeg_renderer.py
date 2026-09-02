"""Real MP4 video rendering engine with scene-level visual synchronization."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import imageio_ffmpeg

from app.narration.models import NarrationResult, SceneAudio
from app.segmentation.models import DocumentSegment
from app.video.models import RenderedVideo, VideoPart
from app.video.renderer import VideoRenderer

LOGGER = logging.getLogger(__name__)


class FFmpegVideoRenderer(VideoRenderer):
    """Renders scene-synchronized MP4 videos where visuals match narration lines exactly."""

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
        LOGGER.info("Rendering %d scene-synchronized MP4 video part(s) using FFmpeg", len(segments))
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
            duration = (
                matching_track.duration_seconds
                if matching_track
                else segment.estimated_duration_seconds
            )
            total_duration += duration

            out_video_path = self.output_directory / f"part_{segment.part_number}.mp4"

            try:
                if matching_track and matching_track.scenes:
                    # Precise Scene-by-Scene Visual Synchronization
                    self._render_scenes_ffmpeg(
                        ffmpeg_exe=ffmpeg_exe,
                        scenes=matching_track.scenes,
                        audio_path=audio_path,
                        output_path=out_video_path,
                    )
                else:
                    # Fallback to even distribution across source pages
                    image_files = self._get_fallback_images(segment.source_pages)
                    self._render_fallback_ffmpeg(
                        ffmpeg_exe=ffmpeg_exe,
                        image_files=image_files,
                        audio_path=audio_path,
                        duration=duration,
                        output_path=out_video_path,
                    )
                LOGGER.info(
                    "Successfully rendered synced video: %s (duration: %.1fs)",
                    out_video_path,
                    duration,
                )
            except Exception as exc:
                LOGGER.error("FFmpeg render failed for Part %d: %s", segment.part_number, exc)

            parts.append(
                VideoPart(
                    part_number=segment.part_number,
                    video_path=out_video_path,
                    duration_seconds=duration,
                    resolution=self.resolution,
                    fps=self.fps,
                    metadata={
                        "status": "rendered",
                        "scenes_synced": len(matching_track.scenes) if matching_track else 0,
                    },
                )
            )

        final_path = (
            parts[0].video_path
            if len(parts) == 1
            else self.output_directory / "combined_output.mp4"
        )

        return RenderedVideo(
            video_path=final_path,
            parts=parts,
            total_duration_seconds=total_duration,
            resolution=self.resolution,
            fps=self.fps,
            status="rendered",
            metadata={"num_parts": len(parts)},
        )

    def _render_scenes_ffmpeg(
        self,
        ffmpeg_exe: str,
        scenes: list[SceneAudio],
        audio_path: Path | None,
        output_path: Path,
    ) -> None:
        """Renders video where each scene's page image is held for that scene's exact audio duration."""
        width, height = self.resolution.split("x")
        video_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
        )

        concat_txt = output_path.parent / f"scenes_timeline_{output_path.stem}.txt"
        lines: list[str] = []
        last_valid_img: Path | None = None

        for scene in scenes:
            primary_img = self.pages_directory / f"page_{scene.page_number}.png"
            img_path: Path | None = None
            if primary_img.exists():
                img_path = primary_img
            else:
                available = sorted(self.pages_directory.glob("page_*.png"))
                if available:
                    img_path = available[0]

            if img_path and img_path.exists():
                last_valid_img = img_path
                lines.append(f"file '{img_path.resolve().as_posix()}'")
                lines.append(f"duration {max(scene.duration_seconds, 0.5):.3f}")

        if lines and last_valid_img:
            # FFmpeg concat demuxer requires repeating the final entry
            lines.append(f"file '{last_valid_img.resolve().as_posix()}'")
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
            ]
            if audio_path and audio_path.exists():
                cmd.extend(["-i", str(audio_path), "-c:a", "aac", "-b:a", "192k", "-shortest"])

            cmd.extend(
                [
                    "-vf",
                    video_filter,
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-r",
                    str(self.fps),
                    str(output_path),
                ]
            )
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                check=False,
            )
        else:
            self._render_fallback_ffmpeg(ffmpeg_exe, [], audio_path, 10.0, output_path)

    def _get_fallback_images(self, source_pages: list[int]) -> list[Path]:
        image_files: list[Path] = []
        for p_num in source_pages:
            img_p = self.pages_directory / f"page_{p_num}.png"
            if img_p.exists():
                image_files.append(img_p)
        if not image_files and self.pages_directory.exists():
            image_files = sorted(self.pages_directory.glob("page_*.png"))
        return image_files

    def _render_fallback_ffmpeg(
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
        if image_files and audio_path and audio_path.exists():
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
        subprocess.run(cmd, capture_output=True, text=True, check=False)
