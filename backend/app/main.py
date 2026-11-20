"""Avida CFO – FastAPI entrypoint. Serves the API under /api and the built Vue app under /."""
from __future__ import annotations

import json
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import settings
from .llm import llm
from .orchestrator import initial_dashboard, run_pipeline
from .state import POLICY, store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Avida CFO", version="0.1.0")
# Only needed for local dev when Vite runs on :5173 without the proxy.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class Decision(BaseModel):
    edited_body: str | None = None


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/llm/health")
async def llm_health():
    return await llm.health()


@app.get("/api/config")
def config():
    return {
        "model": settings.llm_model,
        "llm_enabled": settings.llm_enabled,
        "demo_fallback": settings.demo_fallback,
        "forecast_days": settings.forecast_days,
        "today": settings.today().isoformat(),
    }


@app.get("/api/dashboard")
def dashboard():
    if store.dashboard:
        d = store.dashboard
        # refresh live parts (counter, action statuses)
        d["kpis"]["saved_liquidity"] = store.saved_liquidity
        d["actions"] = list(store.actions.values())
        return d
    return initial_dashboard()


@app.get("/api/sync")
async def sync():
    """Server-Sent Events stream: one `trace` event per agent step, then a final `result`."""

    async def events():
        try:
            async for ev in run_pipeline():
                yield f"event: {ev['type']}\ndata: {json.dumps(ev, default=str)}\n\n"
        except Exception as e:  # noqa: BLE001
            logging.exception("pipeline failed")
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/actions/{action_id}/approve")
def approve(action_id: str, decision: Decision | None = None):
    return _decide(action_id, True, decision)


@app.post("/api/actions/{action_id}/reject")
def reject(action_id: str):
    return _decide(action_id, False, None)


def _decide(action_id: str, approve: bool, decision: Decision | None):
    if action_id not in store.actions:
        raise HTTPException(404, "unknown action")
    action = store.decide(action_id, approve, decision.edited_body if decision else None)
    return {"action": action, "saved_liquidity": store.saved_liquidity}


@app.get("/api/policy")
def policy():
    return POLICY


@app.get("/api/audit")
def audit():
    return store.audit


@app.post("/api/reset")
def reset():
    store.reset()
    return initial_dashboard()


# --- Frontend (built by Vite into STATIC_DIR) ---------------------------------
if settings.static_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=settings.static_dir / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = settings.static_dir / path
        if path and f.is_file():
            return FileResponse(f)
        return FileResponse(settings.static_dir / "index.html")
