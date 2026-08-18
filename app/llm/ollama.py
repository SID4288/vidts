"""Ollama local LLM provider implementation."""

from __future__ import annotations

import json
import logging
from typing import Any, TypeVar
import urllib.error
import urllib.request

from app import LLMError
from app.llm.base import LLMProvider

LOGGER = logging.getLogger(__name__)
T = TypeVar("T")


class OllamaProvider(LLMProvider):
    """Local-first LLM provider using Ollama HTTP API."""

    def __init__(
        self,
        model: str = "gemma3",
        base_url: str = "http://localhost:11434",
        timeout_seconds: int = 120,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Sends a text completion request to Ollama."""
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, **kwargs.get("options", {})},
        }
        if system_prompt:
            payload["system"] = system_prompt

        response_data = self._post_json(f"{self.base_url}/api/generate", payload)
        content = response_data.get("response", "")
        if not content:
            LOGGER.warning("Ollama returned empty response for prompt")
        return content

    def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> T:
        """Requests JSON output from Ollama and instantiates response_model."""
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature, **kwargs.get("options", {})},
        }
        if system_prompt:
            payload["system"] = system_prompt

        response_data = self._post_json(f"{self.base_url}/api/generate", payload)
        content = response_data.get("response", "{}")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Failed to parse JSON response from Ollama: {content}") from exc

        if hasattr(response_model, "from_dict") and callable(getattr(response_model, "from_dict")):
            return response_model.from_dict(parsed)  # type: ignore[no-any-return]
        if hasattr(response_model, "model_validate") and callable(getattr(response_model, "model_validate")):
            return response_model.model_validate(parsed)  # type: ignore[no-any-return]
        if isinstance(parsed, dict):
            try:
                return response_model(**parsed)
            except Exception as exc:
                raise LLMError(f"Could not instantiate {response_model.__name__} from data: {parsed}") from exc
        raise LLMError(f"Unsupported structured model conversion for {response_model.__name__}")

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                status = resp.status
                body = resp.read().decode("utf-8")
                if status != 200:
                    raise LLMError(f"Ollama API returned HTTP {status}: {body}")
                return json.loads(body)  # type: ignore[no-any-return]
        except urllib.error.URLError as exc:
            raise LLMError(f"Failed to connect to Ollama at {url}: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Error communicating with Ollama: {exc}") from exc
