"""Groq Cloud LLM provider implementation."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, TypeVar

from app import LLMError
from app.llm.base import LLMProvider

LOGGER = logging.getLogger(__name__)
T = TypeVar("T")


class GroqProvider(LLMProvider):
    """Cloud LLM provider using Groq API."""

    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        api_key: str | None = None,
        base_url: str = "https://api.groq.com/openai/v1",
        timeout_seconds: int = 60,
    ) -> None:
        self.model = model
        self.api_key = (api_key if api_key is not None else os.getenv("GROQ_API_KEY", "")).strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _get_headers(self) -> dict[str, str]:
        if not self.api_key:
            raise LLMError(
                "GROQ_API_KEY is not set. Please enter your API key in the UI sidebar "
                "or set the GROQ_API_KEY environment variable. Get a free key at https://console.groq.com"
            )
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "vidts/1.0",
        }

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Sends a chat completion request to Groq."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            **kwargs,
        }

        response_data = self._post_json(f"{self.base_url}/chat/completions", payload)
        choices = response_data.get("choices", [])
        if not choices:
            LOGGER.warning("Groq returned empty choices for prompt")
            return ""

        content: str = str(choices[0].get("message", {}).get("content", ""))
        return content

    def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> T:
        """Requests JSON output from Groq and instantiates response_model."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            **kwargs,
        }

        response_data = self._post_json(f"{self.base_url}/chat/completions", payload)
        choices = response_data.get("choices", [])
        if not choices:
            raise LLMError("Groq returned empty response for structured request")

        content = choices[0].get("message", {}).get("content", "{}")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Failed to parse JSON response from Groq: {content}") from exc

        model_any: Any = response_model
        if hasattr(model_any, "from_dict") and callable(model_any.from_dict):
            return model_any.from_dict(parsed)  # type: ignore[no-any-return]
        if hasattr(model_any, "model_validate") and callable(model_any.model_validate):
            return model_any.model_validate(parsed)  # type: ignore[no-any-return]
        if isinstance(parsed, dict):
            try:
                return response_model(**parsed)
            except Exception as exc:
                raise LLMError(
                    f"Could not instantiate {response_model.__name__} from data: {parsed}"
                ) from exc
        raise LLMError(f"Unsupported structured model conversion for {response_model.__name__}")

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = self._get_headers()
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                status = resp.status
                body = resp.read().decode("utf-8")
                if status != 200:
                    raise LLMError(f"Groq API returned HTTP {status}: {body}")
                return json.loads(body)  # type: ignore[no-any-return]
        except urllib.error.HTTPError as exc:
            try:
                err_body = exc.read().decode("utf-8")
                err_json = json.loads(err_body)
                err_msg = err_json.get("error", {}).get("message", err_body)
            except Exception:
                err_msg = str(exc)
            raise LLMError(f"Groq API error ({exc.code}): {err_msg}") from exc
        except urllib.error.URLError as exc:
            raise LLMError(f"Failed to connect to Groq at {url}: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Error communicating with Groq: {exc}") from exc
