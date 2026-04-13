from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from openai import AsyncOpenAI, BadRequestError, RateLimitError

log = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_ANALYSIS_MAX_TOKENS = 1400
DEFAULT_ANALYSIS_RETRY_MAX_TOKENS = 900


class LlmIntegration:
    def __init__(
        self,
    ) -> None:
        self._base_url = (os.getenv("GROQ_BASE_URL") or DEFAULT_GROQ_BASE_URL)
        self._api_key = (os.getenv("GROQ_API_KEY"))
        self._model = (os.getenv("GROQ_MODEL") or DEFAULT_GROQ_MODEL)
        self._analysis_max_tokens = self._read_int_env(
            "GROQ_ANALYSIS_MAX_TOKENS",
            DEFAULT_ANALYSIS_MAX_TOKENS,
        )
        self._analysis_retry_max_tokens = self._read_int_env(
            "GROQ_ANALYSIS_RETRY_MAX_TOKENS",
            DEFAULT_ANALYSIS_RETRY_MAX_TOKENS,
        )
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
            response = await self._request_analysis(prompt)
        except RateLimitError as exc:
            log.warning("LLM analysis fallback model=%s reason=rate_limit", self._model)
            return None
        except BadRequestError as exc:
            if not self._is_json_validation_error(exc):
                log.exception("LLM analysis request failed model=%s", self._model)
                return None

            log.warning("LLM analysis retry model=%s reason=json_schema_validation", self._model)

            try:
                response = await self._request_analysis(
                    self._build_compact_retry_prompt(prompt),
                    response_format={"type": "json_object"},
                    max_tokens=self._analysis_retry_max_tokens,
                )
            except Exception:
                log.exception("LLM analysis retry failed model=%s", self._model)
                return None
        except Exception:
            log.exception("LLM analysis request failed model=%s", self._model)
            return None

        log.info(
            "LLM response received for model %s with %s choice(s)",
            self._model,
            len(getattr(response, "choices", []) or []),
        )
        output_text = self._extract_output_text(response)
        if not output_text:
            log.warning("LLM analysis fallback model=%s reason=no_output", self._model)
            return None

        try:
            return json.loads(output_text)
        except json.JSONDecodeError:
            cleaned_output = self._extract_json_text(output_text)
            if not cleaned_output:
                log.warning("LLM analysis fallback model=%s reason=invalid_json", self._model)
                return None

            try:
                return json.loads(cleaned_output)
            except json.JSONDecodeError:
                log.warning("LLM analysis fallback model=%s reason=invalid_json", self._model)
                return None

    async def _request_analysis(
        self,
        prompt: str,
        *,
        response_format: dict[str, Any] | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        return await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens or self._analysis_max_tokens,
            response_format=response_format or self._json_schema_response_format(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Voce e um analista de decks de Magic: The Gathering. "
                        "Responda em portugues do Brasil com observacoes uteis, objetivas e curtas. "
                        "Nao invente cartas, formatos ou interacoes que nao estejam evidentes no contexto. "
                        "Quando o contexto for insuficiente, admita a limitacao e seja conservador. "
                        "Retorne apenas JSON valido, sem markdown e sem texto extra."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

    @staticmethod
    def _json_schema_response_format() -> dict[str, Any]:
        return {
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
        }

    @staticmethod
    def _is_json_validation_error(exc: BadRequestError) -> bool:
        body = getattr(exc, "body", None)
        if not isinstance(body, dict):
            return False

        error = body.get("error")
        if not isinstance(error, dict):
            return False

        return str(error.get("code") or "") == "json_validate_failed"

    @staticmethod
    def _build_compact_retry_prompt(prompt: str) -> str:
        return (
            "Responda somente com um objeto JSON valido contendo as chaves "
            '"summary", "strengths", "weaknesses" e "suggestions". '
            "Summary com no maximo 3 frases curtas e cada lista com exatamente 3 frases curtas. "
            "Nao use markdown, comentarios ou texto fora do JSON.\n\n"
            f"{prompt}"
        )

    @staticmethod
    def _read_int_env(name: str, default: int) -> int:
        raw_value = os.getenv(name)
        if raw_value is None:
            return default

        try:
            value = int(raw_value)
        except ValueError:
            log.warning("Invalid integer for %s: %s. Using default %s", name, raw_value, default)
            return default

        return max(1, value)

    @staticmethod
    def _extract_output_text(response: Any) -> str | None:
        try:
            choice = (getattr(response, "choices", None) or [])[0]
            message = getattr(choice, "message", None)
            parsed = getattr(message, "parsed", None)
            if parsed is not None:
                if isinstance(parsed, str) and parsed.strip():
                    return parsed.strip()
                if isinstance(parsed, dict):
                    return json.dumps(parsed, ensure_ascii=False)
            text = getattr(message, "content", None)
            if isinstance(text, str) and text.strip():
                return text.strip()
            if isinstance(text, list):
                chunks: list[str] = []
                for item in text:
                    if isinstance(item, str) and item.strip():
                        chunks.append(item.strip())
                        continue
                    if not hasattr(item, "type"):
                        continue
                    if getattr(item, "type", None) == "text":
                        value = getattr(item, "text", None)
                        if isinstance(value, str) and value.strip():
                            chunks.append(value.strip())
                if chunks:
                    return "\n".join(chunks)
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
