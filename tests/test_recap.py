"""Tests for recap generation and LLM interactions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

from app.analysis.models import DocumentAnalysis
from app.ingest.models import Document, DocumentPage, DocumentType
from app.llm.base import LLMProvider
from app.recap.recap_generator import (
    RecapGenerator,
    _clean_narration_text,
    parse_scenes_from_script,
)

T = TypeVar("T")


class MockLLMProvider(LLMProvider):
    """Mock LLM provider returning controlled responses without external network calls."""

    def __init__(self, response_text: str = "This is a mocked recap of the document.") -> None:
        self.response_text = response_text
        self.last_prompt: str | None = None

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        self.last_prompt = prompt
        return self.response_text

    def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> T:
        self.last_prompt = prompt
        if hasattr(response_model, "from_dict"):
            return response_model.from_dict({"title": "Mock", "summary": self.response_text})  # type: ignore[no-any-return]
        return response_model(title="Mock", summary=self.response_text)  # type: ignore[call-arg]


def test_recap_generator_with_mock_llm() -> None:
    mock_llm = MockLLMProvider(
        response_text="[Page 1]: Bone forms the skeletal framework of all vertebrates.\n[Page 2]: The inorganic portion of bone matrix is composed mainly of crystalline calcium."
    )
    generator = RecapGenerator(llm_provider=mock_llm, words_per_minute=100)

    doc = Document(
        id="doc-1",
        source_path=Path("sample.pdf"),
        title="Test Document",
        pages=[
            DocumentPage(page_number=1, text="Sample page 1 text."),
            DocumentPage(page_number=2, text="Sample page 2 text."),
        ],
    )
    analysis = DocumentAnalysis(
        title="Test Document",
        document_type=DocumentType.GENERAL,
        summary="A test document summary.",
        key_topics=["Topic A", "Topic B"],
    )

    recap = generator.generate(document=doc, analysis=analysis)

    assert recap.title == "Recap: Test Document"
    assert len(recap.scenes) == 2
    assert recap.scenes[0].page_number == 1
    assert "Bone forms" in recap.scenes[0].narration_text
    assert recap.scenes[1].page_number == 2
    assert "inorganic" in recap.scenes[1].narration_text
    assert recap.estimated_duration_seconds > 0


def test_parse_scenes_fallback() -> None:
    raw_script = "First paragraph overview.\n\nSecond paragraph details."
    scenes = parse_scenes_from_script(raw_script, total_pages=2)
    assert len(scenes) == 2
    assert scenes[0].page_number == 1
    assert scenes[1].page_number == 2


def test_parse_scenes_deduplicates_pages() -> None:
    """If the LLM outputs two [Page 1] blocks, only the longer one should be kept."""
    raw_script = "[Page 1]: Short.\n[Page 1]: This is a much longer narration about page one content.\n[Page 2]: Page two content."
    scenes = parse_scenes_from_script(raw_script, total_pages=2)
    assert len(scenes) == 2
    assert scenes[0].page_number == 1
    assert "much longer" in scenes[0].narration_text
    assert scenes[1].page_number == 2


def test_parse_scenes_sorted_by_page() -> None:
    """Scenes should be ordered by page number even if the LLM outputs them out of order."""
    raw_script = "[Page 3]: Third page content.\n[Page 1]: First page content.\n[Page 2]: Second page content."
    scenes = parse_scenes_from_script(raw_script, total_pages=3)
    assert [s.page_number for s in scenes] == [1, 2, 3]


def test_clean_narration_strips_meta_phrases() -> None:
    """Meta-narrator phrases should be stripped from narration text."""
    assert (
        _clean_narration_text("On this page, bone structure is discussed.")
        == "Bone structure is discussed."
    )
    assert _clean_narration_text("Here we see the diagram of a cell.") == "The diagram of a cell."
    assert _clean_narration_text("Let's look at the next concept.") == "The next concept."
    assert _clean_narration_text("Moving on to page 3, the data shows...") == "The data shows..."
    # Clean text should be left unchanged
    assert _clean_narration_text("Bone is a composite tissue.") == "Bone is a composite tissue."


def test_recap_generator_fallback_on_empty_llm_response() -> None:
    mock_llm = MockLLMProvider(response_text="   ")
    generator = RecapGenerator(llm_provider=mock_llm)

    doc = Document(
        id="doc-2",
        source_path=Path("empty.pdf"),
        title="Blank Doc",
        pages=[],
    )
    analysis = DocumentAnalysis(
        title="Blank Doc",
        document_type=DocumentType.GENERAL,
        summary="Empty",
        key_topics=["Nothing"],
    )

    recap = generator.generate(document=doc, analysis=analysis)
    assert len(recap.scenes) >= 1
    assert "Blank Doc" in recap.scenes[0].narration_text
