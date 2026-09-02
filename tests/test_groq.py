"""Tests for Groq LLM provider."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app import LLMError
from app.llm.groq import GroqProvider


def test_groq_missing_api_key_raises_error() -> None:
    provider = GroqProvider(api_key="")
    with pytest.raises(LLMError, match="GROQ_API_KEY is not set"):
        provider.generate("Hello")


def test_groq_generate_success() -> None:
    provider = GroqProvider(api_key="gsk_test123")
    mock_response_data = {
        "choices": [{"message": {"content": "This is a test generation from Groq."}}]
    }

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        result = provider.generate("Test prompt", system_prompt="You are an expert.")
        assert result == "This is a test generation from Groq."
        mock_urlopen.assert_called_once()


def test_groq_generate_structured_success() -> None:
    from dataclasses import dataclass

    @dataclass
    class SimpleResponse:
        title: str
        count: int

    provider = GroqProvider(api_key="gsk_test123")
    mock_response_data = {
        "choices": [{"message": {"content": json.dumps({"title": "Sample Title", "count": 42})}}]
    }

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = provider.generate_structured("Extract info", response_model=SimpleResponse)
        assert result.title == "Sample Title"
        assert result.count == 42
