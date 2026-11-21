"""Thin client for the vLLM OpenAI-compatible endpoint running on OpenShift AI.

Every call takes a `fallback`. If the model is down, slow or returns invalid JSON and
DEMO_FALLBACK=true, the fallback is used and the result is marked source="fallback",
so the UI can be honest about it.
"""
from __future__ import annotations

import copy
import json
import logging
import re

from openai import AsyncOpenAI

from . import tracing
from .config import settings

log = logging.getLogger("avida.llm")


class LLM:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout_s,
            max_retries=0,
        )
        self.model = settings.llm_model

    async def health(self) -> dict:
        if not settings.llm_enabled:
            return {"ok": False, "reason": "LLM_ENABLED=false", "base_url": settings.llm_base_url}
        try:
            models = await self.client.models.list()
            return {"ok": True, "base_url": settings.llm_base_url, "models": [m.id for m in models.data]}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "base_url": settings.llm_base_url, "reason": str(e)}

    async def _complete(self, system: str, user: str, max_tokens: int = 400, span=None, **kwargs) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.1,
            max_tokens=max_tokens,
            **kwargs,
        )
        if span is not None and resp.usage:
            span.attr(tracing.TOKEN_USAGE, {"input_tokens": resp.usage.prompt_tokens,
                                            "output_tokens": resp.usage.completion_tokens,
                                            "total_tokens": resp.usage.total_tokens})
        return resp.choices[0].message.content or ""

    def _span(self, kind: str, system: str, user: str, max_tokens: int):
        """One MLflow span per model call (no-op when tracing is off)."""
        return tracing.span(
            f"llm.{kind}", tracing.LLM,
            inputs={"messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "max_tokens": max_tokens},
            model=self.model, base_url=settings.llm_base_url,
        )

    def _fail(self, what: str, err: Exception, fallback):
        log.warning("LLM %s failed: %s", what, err)
        if not settings.demo_fallback:
            raise err
        return copy.deepcopy(fallback), "fallback"

    async def json(self, system: str, user: str, schema: dict, fallback: dict | None,
                   max_tokens: int = 400) -> tuple[dict, str]:
        """Structured output. vLLM enforces the JSON schema via guided decoding.

        The fallback is deep-copied: callers mutate results, and canned answers must stay pristine across runs.
        fallback=None means "no canned answer exists": a model failure is raised to the caller.
        """
        with self._span("json", system, user, max_tokens) as span:
            out, source = await self._json(system, user, schema, fallback, max_tokens, span)
            span.outputs({"result": out, "source": source})
            span.attr("avida.source", source)
            return out, source

    async def _json(self, system, user, schema, fallback, max_tokens, span) -> tuple[dict, str]:
        if not settings.llm_enabled:
            if fallback is None:
                raise RuntimeError("LLM is disabled (LLM_ENABLED=false)")
            return copy.deepcopy(fallback), "fallback"
        try:
            raw = await self._complete(
                system,
                user,
                max_tokens=max_tokens,
                span=span,
                response_format={"type": "json_schema", "json_schema": {"name": "result", "schema": schema}},
            )
            span.attr("raw_completion", raw)
            return _parse_json(raw), "llm"
        except Exception as e:  # noqa: BLE001
            span.attr("error", repr(e))
            if fallback is None:
                log.warning("LLM json failed (no fallback): %s", e)
                raise
            return self._fail("json", e, fallback)

    async def text(self, system: str, user: str, fallback: str, max_tokens: int = 400) -> tuple[str, str]:
        with self._span("text", system, user, max_tokens) as span:
            out, source = await self._text(system, user, fallback, max_tokens, span)
            span.outputs({"result": out, "source": source})
            span.attr("avida.source", source)
            return out, source

    async def _text(self, system, user, fallback, max_tokens, span) -> tuple[str, str]:
        if not settings.llm_enabled:
            return fallback, "fallback"
        try:
            out = (await self._complete(system, user, max_tokens=max_tokens, span=span)).strip()
            if not out:
                raise ValueError("empty completion")
            return out, "llm"
        except Exception as e:  # noqa: BLE001
            span.attr("error", repr(e))
            return self._fail("text", e, fallback)


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    # Some models wrap JSON in ``` fences or add thinking blocks – strip them.
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip()
    m = re.search(r"\{.*\}", raw, flags=re.S)
    if not m:
        raise ValueError(f"no JSON object in completion: {raw[:200]}")
    return json.loads(m.group(0))


llm = LLM()
