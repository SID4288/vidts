"""Integration and orchestrator tests for the vidts pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.analysis.document_analyzer import DocumentAnalyzer
from app.config import AppConfig, NarrationSettings
from app.ingest.models import Document, DocumentPage, DocumentType
from app.ingest.pdf_parser import PDFParser
from app.main import build_parser, run_cli
from app.narration.edge_tts_narrator import EdgeTTSNarrator
from app.narration.models import AudioTrack, NarrationResult
from app.narration.narrator import PlaceholderNarrator
from app.pipeline import Pipeline, PipelineResult
from app.recap.recap_generator import RecapGenerator
from app.segmentation.models import DocumentSegment
from app.segmentation.segmenter import Segmenter
from app.video.ffmpeg_renderer import FFmpegVideoRenderer
from app.video.renderer import PlaceholderVideoRenderer
from tests.test_recap import MockLLMProvider


def test_pipeline_end_to_end_with_mocks(tmp_path: Path) -> None:
    config = AppConfig()
    config.output.directory = str(tmp_path)

    mock_parser = MagicMock(spec=PDFParser)
    sample_doc = Document(
        id="test-doc",
        source_path=Path("sample.pdf"),
        title="Integration Test Document",
        document_type=DocumentType.GENERAL,
        pages=[
            DocumentPage(page_number=1, text="First page content."),
            DocumentPage(page_number=2, text="Second page content."),
        ],
    )
    mock_parser.parse.return_value = sample_doc

    mock_llm = MockLLMProvider(response_text="Full pipeline summary script.")
    pipeline = Pipeline(
        config=config,
        parser=mock_parser,
        analyzer=DocumentAnalyzer(),
        recap_generator=RecapGenerator(llm_provider=mock_llm),
        segmenter=Segmenter(settings=config.segmentation),
        narrator=PlaceholderNarrator(output_directory=tmp_path),
        renderer=PlaceholderVideoRenderer(output_directory=tmp_path),
    )

    result: PipelineResult = pipeline.run("fake_path.pdf")

    assert result.document.title == "Integration Test Document"
    assert result.analysis is not None
    assert result.recap.title == "Recap: Integration Test Document"
    assert len(result.segments) >= 1
    assert len(result.narration.tracks) == len(result.segments)
    assert result.video.video_path is not None
    assert result.video.status == "placeholder_ready"


def test_pipeline_from_config_factory() -> None:
    config = AppConfig()
    pipeline = Pipeline.from_config(config)
    assert isinstance(pipeline.narrator, EdgeTTSNarrator)
    assert isinstance(pipeline.renderer, FFmpegVideoRenderer)


def test_edge_tts_narrator_mock(tmp_path: Path) -> None:
    narrator = EdgeTTSNarrator(
        output_directory=tmp_path,
        settings=NarrationSettings(voice="en-US-ChristopherNeural"),
    )
    segments = [
        DocumentSegment(
            part_number=1,
            title="Part 1",
            script="This is a test script.",
            estimated_duration_seconds=5.0,
        )
    ]

    with patch("app.narration.edge_tts_narrator._synthesize_async") as mock_synth:
        result = narrator.narrate(segments)
        assert len(result.tracks) == 1
        assert result.tracks[0].segment_part_number == 1
        assert result.engine == "edge-tts"
        mock_synth.assert_called_once()


def test_ffmpeg_renderer_mock(tmp_path: Path) -> None:
    renderer = FFmpegVideoRenderer(output_directory=tmp_path, pages_directory=tmp_path / "pages")
    segments = [
        DocumentSegment(
            part_number=1,
            title="Part 1",
            script="Test",
            source_pages=[1],
            estimated_duration_seconds=5.0,
        )
    ]
    narration = NarrationResult(
        tracks=[
            AudioTrack(
                track_id="t1",
                segment_part_number=1,
                audio_path=tmp_path / "part_1_audio.mp3",
                duration_seconds=5.0,
            )
        ],
        total_duration_seconds=5.0,
    )

    with patch.object(renderer, "_render_part_ffmpeg") as mock_render:
        rendered = renderer.render(segments, narration)
        assert len(rendered.parts) == 1
        assert rendered.status == "rendered"
        mock_render.assert_called_once()


def test_cli_parser_help() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--help"])
    assert exc.value.code == 0


def test_cli_no_args_shows_help(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run_cli([])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower() or "vidts" in captured.out.lower()


def test_cli_nonexistent_pdf() -> None:
    exit_code = run_cli(["does_not_exist_file.pdf"])
    assert exit_code == 1
