"""Thin client for the vLLM OpenAI-compatible endpoint running on OpenShift AI.

Every call takes a `fallback`. If the model is down, slow or returns invalid JSON and
DEMO_FALLBACK=true, the fallback is used and the result is marked source="fallback",
so the UI can be honest about it.

Two endpoints are supported: LLM_BASE_URL (primary, e.g. the llm-d inference gateway) and the optional
LLM_FALLBACK_BASE_URL (e.g. the plain vLLM InferenceService). When the primary endpoint is unreachable or
answers 404/5xx, the same request goes to the fallback endpoint, and the primary is skipped for
LLM_FAILOVER_COOLDOWN_S seconds. Only when both fail do the canned answers kick in.
"""
from __future__ import annotations

import copy
import json
import logging
import os
import re
import ssl
import time
from dataclasses import dataclass

import httpx
import openai
from openai import AsyncOpenAI

from . import tracing
from .config import settings

log = logging.getLogger("avida.llm")


@dataclass
class Endpoint:
    name: str  # "primary" / "fallback"
    base_url: str
    model: str
    client: AsyncOpenAI


def _endpoint(name: str, base_url: str, model: str, ca_file: str = "") -> Endpoint:
    """`ca_file`: extra CA to trust for an in-cluster HTTPS endpoint (e.g. the vLLM pod behind llm-d, whose certificate
    is signed by the OpenShift service CA). Verification stays on – it just trusts that CA."""
    http_client = None
    if ca_file and base_url.startswith("https://"):
        if os.path.exists(ca_file):
            http_client = httpx.AsyncClient(verify=ssl.create_default_context(cafile=ca_file),
                                            timeout=settings.llm_timeout_s)
        else:
            log.warning("LLM %s endpoint: CA file %s not found – using the default trust store", name, ca_file)
    client = AsyncOpenAI(base_url=base_url, api_key=settings.llm_api_key,
                         timeout=settings.llm_timeout_s, max_retries=0, http_client=http_client)
    return Endpoint(name, base_url, model, client)


def _is_endpoint_failure(err: Exception) -> bool:
    """Endpoint down / not routable (worth trying the other one) vs. a bad answer from a healthy model."""
    if isinstance(err, openai.APIConnectionError):  # includes timeouts
        return True
    if isinstance(err, openai.APIStatusError):
        return err.status_code == 404 or err.status_code >= 500
    return False


def _configured_endpoints() -> list[Endpoint]:
    endpoints = [_endpoint("primary", settings.llm_base_url, settings.llm_model)]
    if settings.llm_fallback_base_url:
        endpoints.append(_endpoint("fallback", settings.llm_fallback_base_url,
                                   settings.llm_fallback_model or settings.llm_model,
                                   settings.llm_fallback_ca_file))
    return endpoints


class LLM:
    def __init__(self) -> None:
        self.model = settings.llm_model
        self.reconnect()

    def reconnect(self) -> None:
        """Fresh HTTP clients and a closed breaker. The async clients are bound to the event loop they first ran
        in – a script that runs each request in its own `asyncio.run()` (the MLflow eval) must call this per run,
        otherwise every call after the first fails on a closed loop and silently uses the canned answer."""
        self.endpoints = _configured_endpoints()
        self._primary_down_until = 0.0
        # Circuit breaker: when every endpoint is down / timing out, skip the model for LLM_BREAKER_S seconds
        # and answer from the fallback right away – otherwise each call of a sync waits for its own timeout and
        # the SSE stream can outlive the route timeout in the middle of a demo.
        self._all_down_until = 0.0

    def _broken(self) -> bool:
        return time.monotonic() < self._all_down_until

    def _note_failure(self, err: Exception) -> None:
        if _is_endpoint_failure(err) and settings.llm_breaker_s > 0:
            self._all_down_until = time.monotonic() + settings.llm_breaker_s
            log.warning("all LLM endpoints failed – using canned answers for %.0f s", settings.llm_breaker_s)

    def _order(self) -> list[Endpoint]:
        if len(self.endpoints) > 1 and time.monotonic() < self._primary_down_until:
            return self.endpoints[::-1]
        return self.endpoints

    async def health(self) -> dict:
        if not settings.llm_enabled:
            return {"ok": False, "reason": "LLM_ENABLED=false", "base_url": settings.llm_base_url}
        checks = []
        for ep in self.endpoints:
            try:
                models = await ep.client.models.list()
                checks.append({"name": ep.name, "ok": True, "base_url": ep.base_url, "model": ep.model,
                               "models": [m.id for m in models.data]})
            except Exception as e:  # noqa: BLE001
                checks.append({"name": ep.name, "ok": False, "base_url": ep.base_url, "model": ep.model,
                               "reason": str(e)})
        active = next((c for c in checks if c["ok"]), None)
        out = {"ok": active is not None, "base_url": (active or checks[0])["base_url"],
               "active": active["name"] if active else None, "endpoints": checks}
        if active:
            out["models"] = active["models"]
        else:
            out["reason"] = checks[0]["reason"]
        return out

    async def _complete(self, system: str, user: str, max_tokens: int = 400, span=None, **kwargs) -> str:
        order = self._order()
        for i, ep in enumerate(order):
            try:
                resp = await ep.client.chat.completions.create(
                    model=ep.model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    temperature=0.1,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            except Exception as e:  # noqa: BLE001
                if i + 1 < len(order) and _is_endpoint_failure(e):
                    log.warning("LLM endpoint %s (%s) failed, trying %s: %s",
                                ep.name, ep.base_url, order[i + 1].name, e)
                    if ep.name == "primary":
                        self._primary_down_until = time.monotonic() + settings.llm_failover_cooldown_s
                    if span is not None:
                        span.attr(f"failover.{ep.name}", repr(e))
                    continue
                raise
            if ep.name == "primary":
                self._primary_down_until = 0.0
            self._all_down_until = 0.0
            if span is not None:
                span.attr("avida.endpoint", ep.name)
                span.attr("avida.base_url", ep.base_url)
                if resp.usage:
                    span.attr(tracing.TOKEN_USAGE, {"input_tokens": resp.usage.prompt_tokens,
                                                    "output_tokens": resp.usage.completion_tokens,
                                                    "total_tokens": resp.usage.total_tokens})
            return resp.choices[0].message.content or ""
        raise RuntimeError("no LLM endpoint configured")

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
        if self._broken() and fallback is not None:
            span.attr("avida.breaker_open", True)
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
            self._note_failure(e)
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
        if self._broken():
            span.attr("avida.breaker_open", True)
            return fallback, "fallback"
        try:
            out = (await self._complete(system, user, max_tokens=max_tokens, span=span)).strip()
            if not out:
                raise ValueError("empty completion")
            return out, "llm"
        except Exception as e:  # noqa: BLE001
            span.attr("error", repr(e))
            self._note_failure(e)
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
