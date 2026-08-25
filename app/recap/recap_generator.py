"""Generates document recaps using an LLM provider and external prompt templates."""

from __future__ import annotations

import logging
from pathlib import Path

from app.analysis.models import DocumentAnalysis
from app.ingest.models import Document
from app.llm.base import LLMProvider
from app.recap.models import Recap, RecapSection
from app.recap.prompts import load_prompt_template

LOGGER = logging.getLogger(__name__)


class RecapGenerator:
    """Orchestrates recap generation using LLMProvider."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        prompt_path: str | Path = "prompts/recap.txt",
        words_per_minute: int = 150,
    ) -> None:
        self.llm_provider = llm_provider
        self.prompt_path = prompt_path
        self.words_per_minute = words_per_minute

    def generate(self, document: Document, analysis: DocumentAnalysis) -> Recap:
        """Generates a structured recap from document text and analysis context."""
        template = load_prompt_template(self.prompt_path)
        combined_text = " ".join(page.text for page in document.pages if page.text)
        truncated_text = combined_text[:4000] if combined_text else "No text extracted."

        prompt = template.format(
            title=document.title,
            document_type=analysis.document_type.value,
            summary=analysis.summary,
            text=truncated_text,
        )

        LOGGER.debug("Generating recap using LLM prompt (length: %s chars)", len(prompt))
        raw_output = self.llm_provider.generate(prompt=prompt)
        if not raw_output.strip():
            raw_output = (
                f"This is a recap of {document.title}. "
                f"The document covers key themes including {', '.join(analysis.key_topics)}."
            )

        word_count = len(raw_output.split())
        estimated_duration = (word_count / max(self.words_per_minute, 1)) * 60.0

        section = RecapSection(
            title="Main Summary",
            content=raw_output,
            key_takeaways=analysis.key_topics,
        )

        return Recap(
            title=f"Recap: {document.title}",
            summary=analysis.summary or f"Recap of {document.title}",
            sections=[section],
            raw_script=raw_output,
            estimated_duration_seconds=estimated_duration,
            metadata={"word_count": word_count, "model": getattr(self.llm_provider, "model", "custom")},
        )
