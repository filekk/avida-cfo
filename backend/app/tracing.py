"""Optional MLflow tracing for the agents.

Every sync becomes one MLflow trace:  sync → Analyst / Legal / Negotiator spans → LLM call spans
(prompt, answer, tokens, latency, and whether the answer came from the model or the fallback).

Tracing is strictly optional and can never break the app:
- MLFLOW_TRACKING_URI not set, or the `mlflow-tracing` package missing → every helper is a no-op.
- MLflow server unreachable at startup → tracing switches itself off (one warning in the log).
- Any error inside MLflow while recording a span is swallowed and logged.
"""
from __future__ import annotations

import functools
import inspect
import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Iterator

log = logging.getLogger("avida.tracing")

try:  # the app must start even without the package
    import mlflow
except Exception:  # noqa: BLE001
    mlflow = None

_enabled = False
_status: dict[str, Any] = {"enabled": False, "reason": "not initialised"}

# MLflow span types (strings, so this module imports fine without mlflow)
CHAIN, AGENT, LLM, TOOL, RETRIEVER = "CHAIN", "AGENT", "CHAT_MODEL", "TOOL", "RETRIEVER"
TOKEN_USAGE = "mlflow.chat.tokenUsage"  # MLflow shows this attribute as token counts in the UI


def enabled() -> bool:
    return _enabled


def status() -> dict:
    return dict(_status)


def init(blocking: bool = False) -> None:
    """Connect to MLflow if configured. Runs in a background thread by default so startup is never delayed."""
    uri = os.getenv("MLFLOW_TRACKING_URI", "").strip()
    if not uri:
        _status.update(enabled=False, reason="MLFLOW_TRACKING_URI not set")
        return
    if mlflow is None:
        _status.update(enabled=False, reason="mlflow-tracing package not installed")
        log.warning("MLFLOW_TRACKING_URI is set but mlflow is not installed – tracing off")
        return
    # Set here (not at import), so a script that only imports the agents – e.g. the eval – keeps MLflow's defaults.
    # Keep MLflow's HTTP client from retrying for minutes when the server is down.
    os.environ.setdefault("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "5")
    # Traces are sent from a background thread, so the agents never wait for MLflow.
    os.environ.setdefault("MLFLOW_ENABLE_ASYNC_TRACE_LOGGING", "true")
    if blocking:
        _connect(uri, attempts=1)
    else:
        threading.Thread(target=_connect, args=(uri,), name="mlflow-init", daemon=True).start()


def _connect(uri: str, attempts: int = 10, wait_s: float = 30) -> None:
    """Tries a few times (the MLflow pod may start after the app), then gives up quietly."""
    global _enabled
    experiment = os.getenv("MLFLOW_EXPERIMENT_NAME", "avida-cfo-agents")
    for attempt in range(1, attempts + 1):
        try:
            mlflow.set_tracking_uri(uri)
            exp = mlflow.set_experiment(experiment)  # also checks that the server answers
            _enabled = True
            _status.update(enabled=True, reason="ok", tracking_uri=uri, experiment=experiment,
                           experiment_id=exp.experiment_id)
            log.info("MLflow tracing on: %s (experiment %s)", uri, experiment)
            return
        except Exception as e:  # noqa: BLE001
            _status.update(enabled=False, reason=f"MLflow unreachable (attempt {attempt}/{attempts}): {e}",
                           tracking_uri=uri)
            log.warning("MLflow at %s unreachable (attempt %d/%d) – tracing off: %s", uri, attempt, attempts, e)
            if attempt < attempts:
                time.sleep(wait_s)


class _Span:
    """Wraps an MLflow span (or nothing). Every call is safe."""

    def __init__(self, span=None) -> None:
        self._span = span

    def _call(self, method: str, *args) -> None:
        if self._span is None:
            return
        try:
            getattr(self._span, method)(*args)
        except Exception as e:  # noqa: BLE001
            log.debug("span.%s failed: %s", method, e)

    def inputs(self, value: Any) -> None:
        self._call("set_inputs", value)

    def outputs(self, value: Any) -> None:
        self._call("set_outputs", value)

    def attr(self, key: str, value: Any) -> None:
        self._call("set_attribute", key, value)

    def attrs(self, values: dict) -> None:
        self._call("set_attributes", values)


@contextmanager
def span(name: str, span_type: str = CHAIN, inputs: Any = None, **attributes) -> Iterator[_Span]:
    """`with tracing.span("legal.check", tracing.AGENT, inputs={...}) as s: ... s.outputs(...)`"""
    if not _enabled:
        yield _Span()
        return
    try:
        cm = mlflow.start_span(name=name, span_type=span_type)
        raw = cm.__enter__()
    except Exception as e:  # noqa: BLE001
        log.debug("start_span %s failed: %s", name, e)
        cm = None
    if cm is None:
        # yielded outside the `except`, so an error in the caller's block is not chained to the MLflow error
        yield _Span()
        return
    s = _Span(raw)
    if inputs is not None:
        s.inputs(inputs)
    if attributes:
        s.attrs(attributes)
    exc: tuple = (None, None, None)
    try:
        yield s
    except BaseException as e:
        exc = (type(e), e, e.__traceback__)
        raise
    finally:
        try:
            cm.__exit__(*exc)
        except Exception as e:  # noqa: BLE001
            log.debug("end span %s failed: %s", name, e)


def traced(name: str, span_type: str = AGENT, skip: tuple[str, ...] = ()):
    """Decorator for async agent functions: records arguments, result and the answer source (llm/fallback).

    Agent functions return (result, source); the source is also stored as a span attribute,
    so fallbacks can be filtered in the MLflow UI. `skip` leaves big arguments (e.g. file bytes) out of the trace.
    """

    def deco(fn):
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            if not _enabled:
                return await fn(*args, **kwargs)
            try:
                bound = sig.bind_partial(*args, **kwargs)
                inputs = {k: v for k, v in bound.arguments.items() if k not in skip}
            except Exception:  # noqa: BLE001
                inputs = None
            with span(name, span_type, inputs=inputs) as s:
                out = await fn(*args, **kwargs)
                if isinstance(out, tuple) and len(out) == 2 and isinstance(out[1], str):
                    s.outputs({"result": out[0], "source": out[1]})
                    s.attr("avida.source", out[1])
                else:
                    s.outputs(out)
                return out

        return wrapper

    return deco


def tag_trace(**tags: str) -> None:
    """Tags on the current trace (searchable in the MLflow UI)."""
    if not _enabled:
        return
    try:
        mlflow.update_current_trace(tags={k: str(v) for k, v in tags.items()})
    except Exception as e:  # noqa: BLE001
        log.debug("update_current_trace failed: %s", e)
