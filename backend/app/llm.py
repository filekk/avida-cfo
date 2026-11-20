"""Thin client for the vLLM OpenAI-compatible endpoint running on OpenShift AI.

Every call takes a `fallback`. If the model is down, slow or returns invalid JSON and
DEMO_FALLBACK=true, the fallback is used and the result is marked source="fallback",
so the UI can be honest about it.
"""
from __future__ import annotations

import json
import logging
import re

from openai import AsyncOpenAI

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

    async def _complete(self, system: str, user: str, max_tokens: int = 400, **kwargs) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.1,
            max_tokens=max_tokens,
            **kwargs,
        )
        return resp.choices[0].message.content or ""

    def _fail(self, what: str, err: Exception, fallback):
        log.warning("LLM %s failed: %s", what, err)
        if not settings.demo_fallback:
            raise err
        return fallback, "fallback"

    async def json(self, system: str, user: str, schema: dict, fallback: dict) -> tuple[dict, str]:
        """Structured output. vLLM enforces the JSON schema via guided decoding."""
        if not settings.llm_enabled:
            return fallback, "fallback"
        try:
            raw = await self._complete(
                system,
                user,
                response_format={"type": "json_schema", "json_schema": {"name": "result", "schema": schema}},
            )
            return _parse_json(raw), "llm"
        except Exception as e:  # noqa: BLE001
            return self._fail("json", e, fallback)

    async def text(self, system: str, user: str, fallback: str, max_tokens: int = 400) -> tuple[str, str]:
        if not settings.llm_enabled:
            return fallback, "fallback"
        try:
            out = (await self._complete(system, user, max_tokens=max_tokens)).strip()
            if not out:
                raise ValueError("empty completion")
            return out, "llm"
        except Exception as e:  # noqa: BLE001
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
