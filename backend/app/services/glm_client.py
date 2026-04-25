"""Reusable GLM-5.1 client backed by the ilmu console (OpenAI-compatible).

This wraps the `openai` SDK and adds:
  - Lazy singleton so endpoints don't re-create clients per request.
  - Optional web-search activation (GLM-5.1's built-in tool). We attempt to pass
    `tools=[{"type": "web_search"}]` and, if the API rejects the shape, transparently
    retry without tools. The caller's prompt is expected to already instruct the
    model to search for today's data, so prompt-only is a safe fallback.
  - Strict JSON-mode helper that parses the response and raises a clear error on
    malformed output.

Pipeline parts 2-5 should use `chat_json(...)` for structured responses.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

from openai import APIStatusError, BadRequestError, OpenAI, OpenAIError

from app.core.config import settings

logger = logging.getLogger(__name__)

_WEB_SEARCH_TOOL: list[dict[str, Any]] = [{"type": "web_search"}]


class GLMClientError(RuntimeError):
    """Raised when GLM cannot be reached or returns an unusable response."""


class GLMNotConfiguredError(GLMClientError):
    """Raised when ILMU_API_KEY is not set. Distinct from runtime/API errors."""


@dataclass(slots=True)
class _ClientBundle:
    """Caches the underlying OpenAI SDK client and tracks web-search support."""

    client: OpenAI
    model: str
    supports_web_search: bool = True


_bundle: Optional[_ClientBundle] = None


def _get_bundle() -> _ClientBundle:
    global _bundle
    if _bundle is not None:
        return _bundle

    if not settings.ILMU_API_KEY:
        raise GLMNotConfiguredError(
            "ILMU_API_KEY is not set. Add it to backend/.env to enable GLM calls."
        )

    client = OpenAI(
        api_key=settings.ILMU_API_KEY,
        base_url=settings.ILMU_BASE_URL,
        timeout=settings.ILMU_TIMEOUT_SECONDS,
    )
    _bundle = _ClientBundle(
        client=client,
        model=settings.ILMU_MODEL,
        supports_web_search=settings.ILMU_WEB_SEARCH_ENABLED,
    )
    return _bundle


def reset_client_cache() -> None:
    """Reset the cached client. Primarily useful for tests."""
    global _bundle
    _bundle = None


def chat_json(
    messages: list[dict[str, str]],
    *,
    enable_web_search: bool = False,
    temperature: float = 0.3,
    max_retries_on_bad_json: int = 1,
) -> dict[str, Any]:
    """Call GLM-5.1 and parse the response as JSON.

    Args:
        messages: OpenAI-style chat messages. The last user turn should instruct
            the model to respond with a strict JSON object.
        enable_web_search: If True AND the underlying API supports it, the request
            is made with web search enabled so the model can pull today's data.
        temperature: Sampling temperature. Defaults low so JSON structure is stable.
        max_retries_on_bad_json: How many times to retry if the model's output
            can't be parsed as JSON (with a nudge message appended).

    Returns:
        The parsed JSON response as a dict.

    Raises:
        GLMNotConfiguredError: if ILMU_API_KEY is missing.
        GLMClientError: for transport errors or unparsable output after retries.
    """
    bundle = _get_bundle()

    effective_messages = list(messages)
    attempts_left = max_retries_on_bad_json + 1
    last_raw_content: Optional[str] = None
    last_error: Optional[Exception] = None

    while attempts_left > 0:
        attempts_left -= 1
        try:
            content = _raw_chat(
                bundle=bundle,
                messages=effective_messages,
                enable_web_search=enable_web_search,
                temperature=temperature,
            )
        except GLMClientError:
            raise
        except OpenAIError as exc:
            raise GLMClientError(f"ilmu API error: {exc}") from exc

        last_raw_content = content
        parsed = _try_parse_json(content)
        if parsed is not None:
            return parsed

        last_error = ValueError("Model response was not valid JSON.")
        if attempts_left > 0:
            effective_messages = [
                *messages,
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": (
                        "Your previous response was not valid JSON. "
                        "Return only a single JSON object with no markdown fences, "
                        "no prose, no trailing commentary."
                    ),
                },
            ]

    raise GLMClientError(
        "GLM did not return valid JSON after retries. "
        f"Last response: {last_raw_content!r}"
    ) from last_error


def _raw_chat(
    *,
    bundle: _ClientBundle,
    messages: list[dict[str, str]],
    enable_web_search: bool,
    temperature: float,
) -> str:
    """Make one chat completion call; retry without tools if the API rejects them."""
    should_try_tools = enable_web_search and bundle.supports_web_search

    def _call(with_tools: bool) -> str:
        kwargs: dict[str, Any] = {
            "model": bundle.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        if with_tools:
            kwargs["tools"] = _WEB_SEARCH_TOOL
        response = bundle.client.chat.completions.create(**kwargs)
        choice = response.choices[0].message.content or ""
        return choice

    if not should_try_tools:
        return _call(with_tools=False)

    try:
        return _call(with_tools=True)
    except (BadRequestError, APIStatusError) as exc:
        logger.warning(
            "GLM rejected web-search tool (%s). Falling back to prompt-only for this "
            "client lifetime.",
            exc,
        )
        bundle.supports_web_search = False
        return _call(with_tools=False)


def _try_parse_json(raw: str) -> Optional[dict[str, Any]]:
    """Best-effort JSON parsing. Strips common fencing the model may add."""
    if not raw:
        return None
    text = raw.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
