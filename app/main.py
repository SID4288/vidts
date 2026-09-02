"""Command-line entrypoint for vidts."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from app import VidtsError
from app.config import AppConfig, load_config
from app.pipeline import Pipeline

LOGGER = logging.getLogger("vidts")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.main",
        description=(
            "vidts (Video Intelligent Document-to-Story): "
            "convert PDF documents into narrated recap videos (skeleton)."
        ),
    )
    parser.add_argument("pdf", nargs="?", help="Path to an input PDF file")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to YAML config file (default: config.yaml)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )
    return parser


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def run_cli(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)

    if not args.pdf:
        parser.print_help()
        return 0

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        LOGGER.error("Input file does not exist: %s", pdf_path)
        return 1
    if pdf_path.suffix.lower() != ".pdf":
        LOGGER.error("Input file must be a PDF: %s", pdf_path)
        return 1

    try:
        config: AppConfig = load_config(args.config)
        pipeline = Pipeline.from_config(config)
        result = pipeline.run(pdf_path)
        LOGGER.info("Pipeline completed in skeleton mode for document: %s", result.document.title)
        LOGGER.info("Generated %s segment(s)", len(result.segments))
        LOGGER.info("Narration outputs: %s", len(result.narration.tracks))
        LOGGER.info("Video output placeholder: %s", result.video.video_path)
        return 0
    except VidtsError as exc:
        LOGGER.error("Pipeline failed: %s", exc)
        return 1
    except Exception as exc:
        LOGGER.exception("Unexpected error occurred: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(run_cli())
