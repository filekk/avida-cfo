"""Failover between the primary endpoint (llm-d gateway) and the fallback endpoint (plain vLLM)."""
import asyncio
from types import SimpleNamespace

import httpx
import openai

from app import llm as llm_mod


def _resp(text: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))], usage=None)


def _client(fn):
    calls = []

    async def create(**kw):
        calls.append(kw["model"])
        return fn()

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), calls


def _down():
    raise openai.APIConnectionError(request=httpx.Request("POST", "http://x"))


def _make(primary_fn, fallback_fn):
    m = llm_mod.LLM()
    p, pc = _client(primary_fn)
    f, fc = _client(fallback_fn)
    m.endpoints = [llm_mod.Endpoint("primary", "http://llmd/v1", "granite-llmd", p),
                   llm_mod.Endpoint("fallback", "http://vllm/v1", "granite-8b", f)]
    return m, pc, fc


def test_primary_used_when_up():
    m, pc, fc = _make(lambda: _resp("from llm-d"), lambda: _resp("from vllm"))
    assert asyncio.run(m._complete("s", "u")) == "from llm-d"
    assert pc == ["granite-llmd"] and fc == []


def test_failover_to_fallback_and_cooldown():
    m, pc, fc = _make(_down, lambda: _resp("from vllm"))
    assert asyncio.run(m._complete("s", "u")) == "from vllm"
    assert fc == ["granite-8b"]
    # primary is skipped during the cooldown
    asyncio.run(m._complete("s", "u"))
    assert len(pc) == 1 and len(fc) == 2


def test_both_down_uses_canned_answer():
    m, _, _ = _make(_down, _down)
    out, source = asyncio.run(m.text("s", "u", fallback="canned"))
    assert (out, source) == ("canned", "fallback")


def test_bad_request_is_not_failed_over():
    def bad():
        raise openai.BadRequestError("bad", response=httpx.Response(400, request=httpx.Request("POST", "http://x")),
                                     body=None)
    m, _, fc = _make(bad, lambda: _resp("from vllm"))
    out, source = asyncio.run(m.text("s", "u", fallback="canned"))
    assert source == "fallback" and fc == []



def test_https_fallback_trusts_the_given_ca(tmp_path, monkeypatch):
    """The fallback = vLLM pod behind llm-d (https, OpenShift service CA): verification stays on, with that CA."""
    seen = []
    real = llm_mod.ssl.create_default_context
    monkeypatch.setattr(llm_mod.ssl, "create_default_context", lambda cafile=None: seen.append(cafile) or real())
    ca = tmp_path / "service-ca.crt"
    ca.write_text("dummy")
    ep = llm_mod._endpoint("fallback", "https://vllm.svc:8000/v1", "granite-8b", str(ca))
    assert str(ca) in seen and ep.client is not None
    seen.clear()
    llm_mod._endpoint("fallback", "https://vllm.svc:8000/v1", "granite-8b", str(tmp_path / "missing.crt"))
    llm_mod._endpoint("primary", "http://gateway/v1", "granite-8b", str(ca))  # http: CA not needed
    assert str(ca) not in seen and str(tmp_path / "missing.crt") not in seen
