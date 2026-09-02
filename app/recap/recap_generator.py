from __future__ import annotations

import logging
import re
from pathlib import Path

from app.analysis.models import DocumentAnalysis
from app.ingest.models import Document
from app.llm.base import LLMProvider
from app.recap.models import Recap, RecapScene, RecapSection
from app.recap.prompts import load_prompt_template

LOGGER = logging.getLogger(__name__)


def _clean_narration_text(text: str) -> str:
    """Strips meta-narrator phrases that the LLM sometimes inserts despite the prompt."""
    # Remove leading phrases like "On this page, " or "Here we see "
    meta_patterns = [
        r"^(?:On this page,?\s*)",
        r"^(?:Here (?:we|you) (?:can )?see\s*,?\s*)",
        r"^(?:This page (?:shows|depicts|illustrates|introduces|presents)\s*,?\s*)",
        r"^(?:Let(?:'s| us) (?:look at|examine|explore|turn to)\s*,?\s*)",
        r"^(?:Moving (?:on )?to page \d+,?\s*)",
        r"^(?:Now,? (?:on|looking at) page \d+,?\s*)",
        r"^(?:As (?:we|you) can see (?:here|on this page)?,?\s*)",
    ]
    cleaned = text.strip()
    for pattern in meta_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    # Capitalize first letter after stripping
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def parse_scenes_from_script(raw_script: str, total_pages: int = 1) -> list[RecapScene]:
    """Extracts structured [Page N] scenes from generated narration text.

    Ensures that each scene maps to a valid page and that no page
    has duplicate scenes (keeps the longest narration if duplicates exist).
    """
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
        # Build a dict to deduplicate: keep the longest narration per page
        page_narrations: dict[int, str] = {}
        for p_str, text_content in matches:
            clean_text = _clean_narration_text(text_content)
            if not clean_text:
                continue
            try:
                p_num = int(p_str)
            except ValueError:
                continue

            # Clamp page number to valid range
            if total_pages > 0:
                p_num = max(1, min(p_num, total_pages))
            else:
                p_num = max(1, p_num)

            # Keep the longer narration if we already have one for this page
            if p_num not in page_narrations or len(clean_text) > len(page_narrations[p_num]):
                page_narrations[p_num] = clean_text

        # Build scenes sorted by page number for correct visual ordering
        for idx, p_num in enumerate(sorted(page_narrations.keys()), start=1):
            narration = page_narrations[p_num]
            scenes.append(
                RecapScene(
                    scene_index=idx,
                    page_number=p_num,
                    title=f"Scene {idx} (Page {p_num})",
                    narration_text=narration,
                    estimated_duration_seconds=(len(narration.split()) / 150.0) * 60.0,
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
            clean_para = _clean_narration_text(para)
            scenes.append(
                RecapScene(
                    scene_index=idx,
                    page_number=target_page,
                    title=f"Scene {idx} (Page {target_page})",
                    narration_text=clean_para,
                    estimated_duration_seconds=(len(clean_para.split()) / 150.0) * 60.0,
                )
            )

    return scenes


def ensure_page_coverage(
    scenes: list[RecapScene],
    document: Document,
    key_topics: list[str],
    words_per_minute: int,
) -> list[RecapScene]:
    """Return one ordered narration scene for every extracted document page.

    Local models can omit tags even when the prompt requests every page. Existing
    narration is retained, while a short neutral bridge is added for any missing
    page so the visual sequence never skips an extracted page.
    """
    if not document.pages:
        return scenes

    scenes_by_page = {scene.page_number: scene for scene in scenes}
    topic_phrase = ", ".join(key_topics[:3]) or "the document's main ideas"
    complete_scenes: list[RecapScene] = []

    for scene_index, page in enumerate(document.pages, start=1):
        existing = scenes_by_page.get(page.page_number)
        if existing:
            complete_scenes.append(
                RecapScene(
                    scene_index=scene_index,
                    page_number=page.page_number,
                    title=f"Scene {scene_index} (Page {page.page_number})",
                    narration_text=existing.narration_text,
                    estimated_duration_seconds=existing.estimated_duration_seconds,
                )
            )
            continue

        fallback_text = (
            f"This section extends the document's discussion of {topic_phrase}. "
            "It contributes context to the larger story being developed."
        )
        complete_scenes.append(
            RecapScene(
                scene_index=scene_index,
                page_number=page.page_number,
                title=f"Scene {scene_index} (Page {page.page_number})",
                narration_text=fallback_text,
                estimated_duration_seconds=(len(fallback_text.split()) / max(words_per_minute, 1))
                * 60,
            )
        )

    return complete_scenes


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
        # Use a generous budget so the LLM sees enough text per page to narrate accurately
        page_snippets: list[str] = []
        char_budget = (
            6000  # Stays comfortably within Groq request limits while preserving full context
        )
        current_chars = 0

        for page in document.pages:
            clean_page_text = page.text.strip()
            if clean_page_text:
                snippet = f"--- Page {page.page_number} ---\n{clean_page_text[:500]}"
                if current_chars + len(snippet) > char_budget:
                    break
                page_snippets.append(snippet)
                current_chars += len(snippet)

        combined_text = (
            "\n\n".join(page_snippets) if page_snippets else "No selectable text extracted."
        )

        prompt = template.format(
            title=document.title,
            document_type=analysis.document_type.value,
            summary=analysis.summary,
            text=combined_text,
        )

        LOGGER.info(
            "Generating scene-synchronized recap with %s "
            "(prompt length: %d chars; may take 30-90s on CPU)...",
            getattr(self.llm_provider, "model", "LLM"),
            len(prompt),
        )
        raw_output = self.llm_provider.generate(prompt=prompt)
        if not raw_output.strip():
            raw_output = (
                f"[Page 1]: This is an overview recap of {document.title}. "
                f"It covers key themes including {', '.join(analysis.key_topics)}."
            )

        scenes = ensure_page_coverage(
            parse_scenes_from_script(raw_output, total_pages=len(document.pages)),
            document=document,
            key_topics=analysis.key_topics,
            words_per_minute=self.words_per_minute,
        )
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
