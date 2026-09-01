
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.analysis.document_analyzer import DocumentAnalyzer
from app.analysis.models import DocumentAnalysis
from app.config import AppConfig
from app.ingest.models import Document
from app.ingest.page_extractor import PageExtractor
from app.ingest.pdf_parser import PDFParser
from app.llm.groq import GroqProvider
from app.narration.edge_tts_narrator import EdgeTTSNarrator
from app.narration.models import NarrationResult
from app.narration.narrator import Narrator, PlaceholderNarrator
from app.recap.models import Recap
from app.recap.recap_generator import RecapGenerator
from app.segmentation.models import DocumentSegment
from app.segmentation.segmenter import Segmenter
from app.video.ffmpeg_renderer import FFmpegVideoRenderer
from app.video.models import RenderedVideo
from app.video.renderer import VideoRenderer

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineResult:
    document: Document
    analysis: DocumentAnalysis
    recap: Recap
    segments: list[DocumentSegment]
    narration: NarrationResult
    video: RenderedVideo


class Pipeline:
    """Coordinates all pipeline stages via dependency-injected components."""

    def __init__(
        self,
        *,
        config: AppConfig,
        parser: PDFParser,
        analyzer: DocumentAnalyzer,
        recap_generator: RecapGenerator,
        segmenter: Segmenter,
        narrator: Narrator,
        renderer: VideoRenderer,
    ) -> None:
        self.config = config
        self.parser = parser
        self.analyzer = analyzer
        self.recap_generator = recap_generator
        self.segmenter = segmenter
        self.narrator = narrator
        self.renderer = renderer

    @classmethod
    def from_config(cls, config: AppConfig) -> Pipeline:
        llm_provider = GroqProvider(
            model=config.llm.model,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            timeout_seconds=config.llm.timeout_seconds,
        )
        out_dir = Path(config.output.directory)
        pages_dir = out_dir / "pages"

        # Determine narrator based on config
        if config.narration.engine == "edge-tts":
            narrator: Narrator = EdgeTTSNarrator(
                output_directory=out_dir,
                settings=config.narration,
            )
        else:
            narrator = PlaceholderNarrator(output_directory=out_dir)

        # Build FFmpeg video renderer
        renderer: VideoRenderer = FFmpegVideoRenderer(
            output_directory=out_dir,
            resolution=config.video.resolution,
            fps=config.video.fps,
            pages_directory=pages_dir,
        )

        return cls(
            config=config,
            parser=PDFParser(
                max_pages=config.document.max_pages,
                page_extractor=PageExtractor(image_output_dir=pages_dir),
            ),
            analyzer=DocumentAnalyzer(),
            recap_generator=RecapGenerator(
                llm_provider=llm_provider,
                prompt_path="prompts/recap.txt",
            ),
            segmenter=Segmenter(settings=config.segmentation),
            narrator=narrator,
            renderer=renderer,
        )

    def run(
        self,
        pdf_path: str | Path,
        progress_callback: Callable[[int, str, str], None] | None = None,
    ) -> PipelineResult:
        """Run the six-stage pipeline and optionally report each stage before it starts."""
        path = Path(pdf_path)
        if progress_callback:
            progress_callback(1, "Ingest", "Extracting pages and rendering images")
        LOGGER.info("Stage 1/6 ingest: parsing and extracting pages from %s", path)
        document = self.parser.parse(path)

        if progress_callback:
            progress_callback(2, "Analysis", "Analyzing document structure and content density")
        LOGGER.info("Stage 2/6 analysis: analyzing document structure and content density")
        analysis = self.analyzer.analyze(document)

        if progress_callback:
            progress_callback(3, "Recap", "Generating narration script via LLM")
        LOGGER.info("Stage 3/6 recap: generating narration script via LLM")
        recap = self.recap_generator.generate(document=document, analysis=analysis)

        if progress_callback:
            progress_callback(4, "Segmentation", "Calculating pacing and scene segment mapping")
        LOGGER.info("Stage 4/6 segmentation: calculating pacing and video segments")
        segments = self.segmenter.segment(recap=recap, total_pages=len(document.pages))

        if progress_callback:
            progress_callback(5, "Narration", "Synthesizing voiceover audio clips")
        LOGGER.info("Stage 5/6 narration: synthesizing narration audio")
        narration = self.narrator.narrate(segments)

        if progress_callback:
            progress_callback(6, "Video", "Assembling scenes and rendering MP4 video")
        LOGGER.info("Stage 6/6 video: assembling and rendering final MP4 video")
        video = self.renderer.render(segments=segments, narration=narration)

        return PipelineResult(
            document=document,
            analysis=analysis,
            recap=recap,
            segments=segments,
            narration=narration,
            video=video,
        )
