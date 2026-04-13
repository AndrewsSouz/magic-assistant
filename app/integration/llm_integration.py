from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from openai import AsyncOpenAI, RateLimitError

log = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class LlmIntegration:
    def __init__(
        self,
    ) -> None:
        self._base_url = (os.getenv("GROQ_BASE_URL"))
        self._api_key = (os.getenv("GROQ_API_KEY"))
        self._model = (os.getenv("GROQ_MODEL"))
        self._client = (
            AsyncOpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
            )
            if self._api_key
            else None
        )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def generate_deck_analysis(self, prompt: str) -> dict[str, Any] | None:
        if not self._client:
            return None

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=800,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "deck_analysis",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "summary": {"type": "string"},
                                "strengths": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "weaknesses": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "suggestions": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["summary", "strengths", "weaknesses", "suggestions"],
                        },
                    },
                },
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Voce e um analista de decks de Magic: The Gathering. "
                            "Responda em portugues do Brasil com observacoes uteis, objetivas e curtas. "
                            "Nao invente cartas, formatos ou interacoes que nao estejam evidentes no contexto. "
                            "Quando o contexto for insuficiente, admita a limitacao e seja conservador."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )
        except RateLimitError as exc:
            log.warning("LLM provider rate-limited model %s: %s",
                        self._model, exc)
            return None
        except Exception:
            log.exception(
                "LLM deck analysis request failed for model %s", self._model)
            return None

        log.info(
            "LLM response received for model %s with %s choice(s)",
            self._model,
            len(getattr(response, "choices", []) or []),
        )
        output_text = self._extract_output_text(response)
        if not output_text:
            log.info(
                "LLM response returned no output text for model %s", self._model)
            return None

        try:
            return json.loads(output_text)
        except json.JSONDecodeError:
            cleaned_output = self._extract_json_text(output_text)
            if not cleaned_output:
                log.warning(
                    "LLM response was not valid JSON for model %s", self._model)
                return None

            try:
                return json.loads(cleaned_output)
            except json.JSONDecodeError:
                log.warning(
                    "LLM response was not valid JSON for model %s", self._model)
                return None

    @staticmethod
    def _extract_output_text(response: Any) -> str | None:
        try:
            choice = (getattr(response, "choices", None) or [])[0]
            message = getattr(choice, "message", None)
            text = getattr(message, "content", None)
            if isinstance(text, str) and text.strip():
                return text.strip()
        except (AttributeError, IndexError, TypeError):
            return None
        return None

    @staticmethod
    def _extract_json_text(text: str) -> str | None:
        fenced_match = re.search(
            r"```json\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        if fenced_match:
            return fenced_match.group(1)

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]

        return None
