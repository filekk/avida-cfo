"""MLflow tracing is optional: without MLFLOW_TRACKING_URI (or with MLflow down) everything must work unchanged."""
import asyncio

from app import tracing


def test_tracing_off_without_tracking_uri(monkeypatch):
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    tracing.init(blocking=True)
    assert tracing.enabled() is False
    assert "not set" in tracing.status()["reason"]


def test_span_and_decorator_are_noops_when_off():
    with tracing.span("x", tracing.AGENT, inputs={"a": 1}) as s:
        s.outputs({"b": 2})
        s.attr("k", "v")

    @tracing.traced("agent.step")
    async def step(x: int) -> tuple[int, str]:
        return x + 1, "llm"

    assert asyncio.run(step(1)) == (2, "llm")


def test_unreachable_mlflow_turns_tracing_off(monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:9")  # nothing listens there
    tracing.init(blocking=True)
    assert tracing.enabled() is False
    assert "unreachable" in tracing.status()["reason"]
    monkeypatch.delenv("MLFLOW_TRACKING_URI")
    tracing.init(blocking=True)  # back to "off, not configured"


def test_tracing_health_endpoint():
    from fastapi.testclient import TestClient

    from app.main import app

    r = TestClient(app).get("/api/tracing/health")
    assert r.status_code == 200 and "enabled" in r.json()
