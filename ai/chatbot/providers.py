from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
import logging
import time
from typing import Any, Literal

import httpx

logger = logging.getLogger("terraqora.ai.providers")


@dataclass(frozen=True)
class ChatTurn:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model_name: str
    latency_ms: int


class LLMProviderError(RuntimeError):
    """Structured non-leaking exception raised by LLM provider adapters."""

    def __init__(
        self,
        code: Literal[
            "missing_key",
            "invalid_credentials",
            "rate_limited",
            "timeout",
            "bad_response",
            "upstream_error",
        ],
        message: str,
        status_code: int = 503,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class LLMProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    def generate(
        self,
        *,
        system_prompt: str,
        history: Sequence[ChatTurn],
        user_message: str,
        temperature: float = 0.35,
        max_output_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate an assistant completion from system instructions, history, and turn."""


def _redact_secret(text: str, secret: str | None) -> str:
    if secret and len(secret) >= 4:
        return text.replace(secret, "[REDACTED]")
    return text


def _classify_gemini_error(exc: Exception, api_key: str) -> LLMProviderError:
    if isinstance(exc, LLMProviderError):
        return exc

    status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    raw_msg = _redact_secret(str(exc), api_key)
    lower_msg = raw_msg.lower()

    if isinstance(exc, (TimeoutError, httpx.TimeoutException)) or "timeout" in lower_msg or "timed out" in lower_msg or status_code == 504:
        return LLMProviderError(
            "timeout",
            "The AI advisor timed out while waiting for Gemini. Please retry in a moment.",
            status_code=504,
        )

    if status_code == 429 or "resource_exhausted" in lower_msg or "rate limit" in lower_msg or "quota" in lower_msg:
        return LLMProviderError(
            "rate_limited",
            "Gemini API rate or quota limit reached temporarily. Please retry shortly.",
            status_code=429,
        )

    if (
        status_code in (401, 403)
        or "api_key_invalid" in lower_msg
        or "api key not valid" in lower_msg
        or "invalid api key" in lower_msg
        or "permission_denied" in lower_msg
    ):
        return LLMProviderError(
            "invalid_credentials",
            "Gemini API credentials could not be verified. Check server GEMINI_API_KEY configuration.",
            status_code=503,
        )

    return LLMProviderError(
        "upstream_error",
        "Unable to obtain a response from the Gemini AI service right now. Please try again later.",
        status_code=503,
    )


class GeminiProvider(LLMProvider):
    provider_name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        timeout_seconds: float = 20.0,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self.model_name = model_name.strip() or "gemini-2.5-flash"
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self._injected_client = client

    def _build_client(self) -> Any:
        if self._injected_client is not None:
            return self._injected_client
        if not self._api_key:
            raise LLMProviderError(
                "missing_key",
                "Gemini API key is not configured on the backend server. Configure GEMINI_API_KEY in environment settings.",
                status_code=503,
            )

        from google import genai
        from google.genai import types

        http_options = types.HttpOptions(timeout=int(self.timeout_seconds * 1000))
        return genai.Client(api_key=self._api_key, http_options=http_options)

    def generate(
        self,
        *,
        system_prompt: str,
        history: Sequence[ChatTurn],
        user_message: str,
        temperature: float = 0.35,
        max_output_tokens: int = 1024,
    ) -> LLMResponse:
        if not self._api_key and self._injected_client is None:
            raise LLMProviderError(
                "missing_key",
                "Gemini API key is not configured on the backend server. Configure GEMINI_API_KEY in environment settings.",
                status_code=503,
            )

        from google.genai import types

        contents: list[types.Content] = []
        for turn in history:
            role = "model" if turn.role == "assistant" else "user"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=turn.content)],
                )
            )
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_message)],
            )
        )

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        client = self._build_client()
        started = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            classified = _classify_gemini_error(exc, self._api_key)
            logger.warning(
                "Gemini request failed (code=%s, status=%s, model=%s)",
                classified.code,
                classified.status_code,
                self.model_name,
            )
            raise classified from exc

        elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise LLMProviderError(
                "bad_response",
                "Gemini returned an empty advisory response. Please rephrase and retry.",
                status_code=502,
            )

        return LLMResponse(
            text=text,
            provider=self.provider_name,
            model_name=self.model_name,
            latency_ms=elapsed_ms,
        )


class OpenAIProvider(LLMProvider):
    """Pluggable OpenAI Chat Completions adapter implementing LLMProvider."""

    provider_name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = "gpt-4o-mini",
        timeout_seconds: float = 20.0,
    ) -> None:
        self._api_key = api_key.strip()
        self.model_name = model_name.strip() or "gpt-4o-mini"
        self.timeout_seconds = max(1.0, float(timeout_seconds))

    def generate(
        self,
        *,
        system_prompt: str,
        history: Sequence[ChatTurn],
        user_message: str,
        temperature: float = 0.35,
        max_output_tokens: int = 1024,
    ) -> LLMResponse:
        if not self._api_key:
            raise LLMProviderError(
                "missing_key",
                "OpenAI API key is not configured on the backend server.",
                status_code=503,
            )

        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for turn in history:
            messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": user_message})

        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_output_tokens,
                    },
                )
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                "timeout",
                "OpenAI service timed out while generating advisory response.",
                status_code=504,
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                "upstream_error",
                "Unable to connect to the OpenAI advisory service.",
                status_code=503,
            ) from exc

        elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
        if resp.status_code in (401, 403):
            raise LLMProviderError(
                "invalid_credentials",
                "OpenAI API credentials could not be verified.",
                status_code=503,
            )
        if resp.status_code == 429:
            raise LLMProviderError(
                "rate_limited",
                "OpenAI rate limit reached temporarily. Please retry shortly.",
                status_code=429,
            )
        if resp.status_code >= 400:
            raise LLMProviderError(
                "upstream_error",
                "Upstream OpenAI provider returned an error.",
                status_code=502,
            )

        data = resp.json()
        choices = data.get("choices") or []
        content = (
            choices[0].get("message", {}).get("content", "").strip() if choices else ""
        )
        if not content:
            raise LLMProviderError(
                "bad_response",
                "OpenAI returned an empty advisory response.",
                status_code=502,
            )

        return LLMResponse(
            text=content,
            provider=self.provider_name,
            model_name=self.model_name,
            latency_ms=elapsed_ms,
        )


def build_llm_provider(settings: Any) -> LLMProvider:
    provider_name = getattr(settings, "LLM_PROVIDER", "gemini")
    timeout = float(getattr(settings, "GEMINI_TIMEOUT_SECONDS", 20.0))

    if provider_name == "openai":
        return OpenAIProvider(
            api_key=getattr(settings, "resolved_openai_api_key", ""),
            model_name=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            timeout_seconds=timeout,
        )

    return GeminiProvider(
        api_key=getattr(settings, "resolved_gemini_api_key", ""),
        model_name=getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash"),
        timeout_seconds=timeout,
    )
