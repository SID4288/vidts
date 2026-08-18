"""Data models for LLM interactions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class LLMRequest:
    """Represents a request sent to an LLM provider."""

    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMResponse:
    """Standardized response received from an LLM provider."""

    content: str
    model: str
    total_tokens: int | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)
