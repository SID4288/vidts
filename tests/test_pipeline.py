"""Integration and orchestrator tests for the vidts pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.analysis.document_analyzer import DocumentAnalyzer
from app.config import AppConfig
from app.ingest.models import Document, DocumentPage, DocumentType
from app.ingest.pdf_parser import PDFParser
from app.main import build_parser, run_cli
from app.narration.narrator import PlaceholderNarrator
from app.pipeline import Pipeline, PipelineResult
from app.recap.recap_generator import RecapGenerator
from app.segmentation.segmenter import Segmenter
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
