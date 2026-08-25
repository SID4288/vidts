"""Utilities for loading and rendering prompt templates."""

from __future__ import annotations

from pathlib import Path


def load_prompt_template(path: str | Path) -> str:
    """Loads a prompt template from the given path."""
    file_path = Path(path)
    if not file_path.exists():
        return "Summarize the following document: {document_title}\n\n{document_text}"
    return file_path.read_text(encoding="utf-8")
