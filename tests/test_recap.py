"""Tests for recap generation and LLM interactions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

from app.analysis.models import DocumentAnalysis
from app.ingest.models import Document, DocumentPage, DocumentType
from app.llm.base import LLMProvider
from app.recap.recap_generator import RecapGenerator

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
    mock_llm = MockLLMProvider(response_text="Custom mock story narration with 10 words total here.")
    generator = RecapGenerator(llm_provider=mock_llm, words_per_minute=100)

    doc = Document(
        id="doc-1",
        source_path=Path("sample.pdf"),
        title="Test Document",
        pages=[DocumentPage(page_number=1, text="Sample text content for recap.")],
    )
    analysis = DocumentAnalysis(
        title="Test Document",
        document_type=DocumentType.GENERAL,
        summary="A test document summary.",
        key_topics=["Topic A", "Topic B"],
    )

    recap = generator.generate(document=doc, analysis=analysis)

    assert recap.title == "Recap: Test Document"
    assert "Custom mock story narration" in recap.raw_script
    assert len(recap.sections) == 1
    assert recap.estimated_duration_seconds > 0
    assert mock_llm.last_prompt is not None
    assert "Test Document" in mock_llm.last_prompt


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
    assert "recap of Blank Doc" in recap.raw_script
