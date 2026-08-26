"""Generates document recaps with scene-by-scene visual-voice synchronization."""

from __future__ import annotations

import logging
from pathlib import Path
import re

from app.analysis.models import DocumentAnalysis
from app.ingest.models import Document
from app.llm.base import LLMProvider
from app.recap.models import Recap, RecapScene, RecapSection
from app.recap.prompts import load_prompt_template

LOGGER = logging.getLogger(__name__)


def parse_scenes_from_script(raw_script: str, total_pages: int = 1) -> list[RecapScene]:
    """Extracts structured [Page N] scenes from generated narration text."""
    scenes: list[RecapScene] = []
    
    # Pattern 1: Matches [Page 1]: Narration... or [Page 1] Narration...
    pattern = re.compile(
        r"\[(?:Page|Slide)\s*(\d+)\]\s*:?\s*(.*?)(?=\[(?:Page|Slide)\s*\d+\]|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    matches = pattern.findall(raw_script)

    # Pattern 2: Fallback to "Page 1: Narration..."
    if not matches:
        pattern2 = re.compile(
            r"(?:^|\n)(?:Page|Slide)\s*(\d+)\s*:?\s*(.*?)(?=(?:\n(?:Page|Slide)\s*\d+)|\Z)",
            re.DOTALL | re.IGNORECASE,
        )
        matches = pattern2.findall(raw_script)

    if matches:
        for idx, (p_str, text_content) in enumerate(matches, start=1):
            clean_text = text_content.strip()
            if clean_text:
                try:
                    p_num = int(p_str)
                except ValueError:
                    p_num = min(idx, total_pages)
                
                # Clamp page number to valid range
                p_num = max(1, min(p_num, total_pages if total_pages > 0 else 1))
                scenes.append(
                    RecapScene(
                        scene_index=idx,
                        page_number=p_num,
                        title=f"Scene {idx} (Page {p_num})",
                        narration_text=clean_text,
                        estimated_duration_seconds=(len(clean_text.split()) / 150.0) * 60.0,
                    )
                )

    # Fallback if LLM produced unstructured paragraphs: split paragraphs and map to pages
    if not scenes:
        paragraphs = [p.strip() for p in raw_script.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [raw_script.strip()] if raw_script.strip() else ["Summary narration."]

        num_pages_to_map = max(total_pages, 1)
        for idx, para in enumerate(paragraphs, start=1):
            target_page = ((idx - 1) % num_pages_to_map) + 1
            scenes.append(
                RecapScene(
                    scene_index=idx,
                    page_number=target_page,
                    title=f"Scene {idx} (Page {target_page})",
                    narration_text=para,
                    estimated_duration_seconds=(len(para.split()) / 150.0) * 60.0,
                )
            )

    return scenes


class RecapGenerator:
    """Orchestrates recap generation using LLMProvider with scene-by-scene synchronization."""

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
        """Generates a structured, scene-anchored recap from document pages."""
        template = load_prompt_template(self.prompt_path)

        # Build page-tagged excerpts for LLM context
        page_snippets: list[str] = []
        char_budget = 4500
        current_chars = 0

        for page in document.pages:
            clean_page_text = page.text.strip()
            if clean_page_text:
                snippet = f"--- Page {page.page_number} ---\n{clean_page_text[:500]}"
                if current_chars + len(snippet) > char_budget:
                    break
                page_snippets.append(snippet)
                current_chars += len(snippet)

        combined_text = "\n\n".join(page_snippets) if page_snippets else "No selectable text extracted."

        prompt = template.format(
            title=document.title,
            document_type=analysis.document_type.value,
            summary=analysis.summary,
            text=combined_text,
        )

        LOGGER.info(
            "Generating scene-synchronized recap with %s (prompt length: %d chars; may take 30-90s on CPU)...",
            getattr(self.llm_provider, "model", "LLM"),
            len(prompt),
        )
        raw_output = self.llm_provider.generate(prompt=prompt)
        if not raw_output.strip():
            raw_output = (
                f"[Page 1]: This is an overview recap of {document.title}. "
                f"It covers key themes including {', '.join(analysis.key_topics)}."
            )

        scenes = parse_scenes_from_script(raw_output, total_pages=len(document.pages))
        total_words = sum(len(s.narration_text.split()) for s in scenes)
        estimated_duration = (total_words / max(self.words_per_minute, 1)) * 60.0

        section = RecapSection(
            title="Main Summary",
            content=raw_output,
            key_takeaways=analysis.key_topics,
        )

        return Recap(
            title=f"Recap: {document.title}",
            summary=analysis.summary or f"Recap of {document.title}",
            sections=[section],
            scenes=scenes,
            raw_script=raw_output,
            estimated_duration_seconds=estimated_duration,
            metadata={
                "word_count": total_words,
                "scene_count": len(scenes),
                "model": getattr(self.llm_provider, "model", "custom"),
            },
        )
