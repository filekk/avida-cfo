"""Avida CFO – FastAPI entrypoint. Serves the API under /api and the built Vue app under /.

All demo state lives in memory (state.py, contract_library.py). Every route that reads or changes it is `async def`,
so it runs on the event loop – never in Starlette's thread pool – and two requests (e.g. a double-clicked
Approve, or a reset during a sync) can never interleave inside a check-then-act.
"""
from __future__ import annotations

import json
import logging
import re
from contextlib import aclosing
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import ask as ask_cfo
from . import contract_library, decision, tracing
from .config import settings
from .llm import llm
from .orchestrator import SyncAlreadyRunning, after_decision, current_dashboard, initial_dashboard, run_pipeline
from .state import POLICY, store
from .texts import localize

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# MLflow tracing of the agents – only if MLFLOW_TRACKING_URI is set; connects in the background, never blocks.
tracing.init()

app = FastAPI(title="Avida CFO", version="0.1.0")
# Same origin in production and behind the Vite proxy in dev – CORS only for the origins listed in CORS_ORIGINS.
# Never "*": the API changes state without a login, so any website could otherwise drive it from a visitor's browser.
if settings.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"],
                       allow_headers=["*"])


class Decision(BaseModel):
    edited_body: str | None = Field(default=None, max_length=5000)


Lang = Literal["en", "de"]


class Turn(BaseModel):
    role: Literal["owner", "agent"]
    text: str

    @field_validator("text", mode="before")
    @classmethod
    def _clip(cls, v):
        # the UI sends the agent's own answers back – a long answer must never make the next question fail (422)
        return str(v or "")[:2000]


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    lang: Lang = "en"
    # Problem chat: talk about ONE action card / finding (facts + suggestions limited to it)
    action_id: str | None = None
    finding_id: str | None = None
    # last turns of this conversation (oldest first) – for follow-ups like "and why?". Only the last 6 are used.
    history: list[Turn] = Field(default_factory=list)

    @field_validator("history", mode="before")
    @classmethod
    def _last_turns(cls, v):
        return list(v or [])[-6:]


class DraftCheck(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    lang: Lang = "en"


class Redraft(BaseModel):
    # the owner's hint; empty = "write it again" (a fresh version with the same facts)
    instruction: str = Field(default="", max_length=300)
    body: str | None = Field(default=None, max_length=5000)  # the text currently in the editor (default: the draft)
    lang: Lang = "en"


def _dash(d: dict, lang: str) -> dict:
    out = localize(d, lang)
    out["lang"] = lang
    return out


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/llm/health")
async def llm_health():
    return await llm.health()


@app.get("/api/tracing/health")
def tracing_health():
    """Is MLflow tracing of the agents on? (diagnostics only, not used by the UI)"""
    return tracing.status()


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
async def dashboard(lang: Lang = "en"):
    return _dash(current_dashboard(), lang)


@app.get("/api/sync")
async def sync(lang: Lang = "en"):
    """Server-Sent Events stream: `phase` events (progress), one `trace` event per agent step, then `result`.
    Trace texts are written in `lang`; the model writes its texts (explanations, briefing) in `lang` too."""

    async def events():
        try:
            # aclosing: if the browser disconnects, the pipeline is closed right away (and cancels its LLM calls).
            async with aclosing(run_pipeline(lang)) as pipeline:
                async for ev in pipeline:
                    if ev["type"] == "result":
                        ev = {"type": "result", "dashboard": _dash(ev["dashboard"], lang)}
                    yield _sse(ev["type"], ev)
        except SyncAlreadyRunning:
            msg = ("Die Prüfung läuft bereits (vielleicht in einem anderen Fenster) – bitte kurz warten." if lang == "de"
                   else "A check is already running (maybe in another window) – please wait a moment.")
            yield _sse("error", {"type": "error", "message": msg, "code": "sync_running"})
        except Exception as e:  # noqa: BLE001
            logging.exception("pipeline failed")
            # plain words for the owner; only the error type goes to the browser – the details stay in the log
            msg = ("Bei der Prüfung ist ein Fehler aufgetreten. Bitte versuchen Sie es erneut." if lang == "de"
                   else "Something went wrong during the check. Please try again.")
            yield _sse("error", {"type": "error", "message": msg, "detail": type(e).__name__})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/sync/trace")
async def sync_trace():
    """Replay of the last inbox check: every `phase` / `trace` event, in the language of that sync."""
    return {"lang": store.sync_lang if store.trace else None, "events": store.trace}


@app.post("/api/actions/{action_id}/approve")
async def approve(action_id: str, body: Decision | None = None, lang: Lang = "en"):
    return _decide(action_id, True, body, lang)


@app.post("/api/actions/{action_id}/reject")
async def reject(action_id: str, lang: Lang = "en"):
    return _decide(action_id, False, None, lang)


def _gone(lang: str) -> HTTPException:
    """404 for an action / finding the backend no longer knows (the demo was reset or restarted while the page
    still shows the old decisions). A plain, localized message the UI shows as delivered."""
    if lang == "de":
        msg = ("Diese Entscheidung gibt es nicht mehr – die Demo wurde zurückgesetzt. "
               "Bitte laden Sie die Seite neu und klicken Sie auf „Posteingang prüfen“.")
    else:
        msg = ("This decision no longer exists – the demo was reset. "
               "Please reload the page and click \"Check my inbox\" again.")
    return HTTPException(404, msg)


def _decide(action_id: str, approve: bool, body: Decision | None, lang: str):
    """Synchronous on purpose (called from async routes): check-then-act on the action status with no await in
    between, so a double-clicked Approve is decided – and counted in "Saved by Avida" – exactly once."""
    if action_id not in store.actions:
        raise _gone(lang)
    before = store.saved_liquidity
    was_pending = store.actions[action_id]["status"] == "pending"
    action = store.decide(action_id, approve, body.edited_body if body else None)
    if was_pending:
        after_decision(action, approve)  # simulated partner reply / re-run plan (GET /api/dashboard shows it)
    return {"action": localize(action, lang), "saved_liquidity": store.saved_liquidity,
            "saved_liquidity_previous": before}


def _workspace(f: dict | None, a: dict | None, lang: str) -> dict:
    d = current_dashboard()
    return {"lang": lang, "action": localize(a, lang) if a else None, "finding": localize(f, lang) if f else None,
            "suggestions": ask_cfo.public_scoped(d, f, a, lang)}


@app.get("/api/actions/{action_id}/context")
async def action_context(action_id: str, lang: Lang = "en"):
    """Everything for one problem view: the action (with `decision`), its finding and the chat suggestions."""
    try:
        f, a = ask_cfo.resolve_scope(current_dashboard(), action_id, None)
    except ask_cfo.UnknownScope:
        raise _gone(lang) from None
    return _workspace(f, a, lang)


@app.get("/api/findings/{finding_id}/context")
async def finding_context(finding_id: str, lang: Lang = "en"):
    """Same as the action context, for a finding (also findings without an action, e.g. an allowed increase)."""
    try:
        f, a = ask_cfo.resolve_scope(current_dashboard(), None, finding_id)
    except ask_cfo.UnknownScope:
        raise _gone(lang) from None
    return _workspace(f, a, lang)


@app.post("/api/actions/{action_id}/review")
async def review_draft(action_id: str, req: DraftCheck):
    """Instant rule check of the owner's edited draft (no model) – same rules as the Legal Agent's review."""
    try:
        return decision.review_body(action_id, req.body, req.lang)
    except KeyError:
        raise _gone(req.lang) from None
    except decision.NotEditable as e:
        raise HTTPException(409, str(e)) from e


@app.post("/api/actions/{action_id}/redraft")
async def redraft(action_id: str, req: Redraft):
    """Owner asks for a change in plain words → Negotiator rewrites, Legal reviews → a PROPOSAL (nothing is sent,
    the action is not changed; the owner approves with `edited_body` as usual). 3–8 s with the model."""
    try:
        return await decision.redraft(action_id, req.instruction, req.body, req.lang)
    except KeyError:
        raise _gone(req.lang) from None
    except decision.UnsafeInstruction as e:
        raise HTTPException(422, str(e)) from e
    except decision.NotEditable as e:
        raise HTTPException(409, str(e)) from e


@app.get("/api/actions/{action_id}/redraft/hints")
async def redraft_hints(action_id: str, lang: Lang = "en"):
    """Quick hints (chips) and a placeholder for the Rewrite button's hint field."""
    try:
        return decision.rewrite_hints(action_id, lang)
    except KeyError:
        raise _gone(lang) from None
    except decision.NotEditable as e:
        raise HTTPException(409, str(e)) from e


@app.get("/api/ask/suggestions")
async def ask_suggestions(lang: Lang = "en", action_id: str | None = None, finding_id: str | None = None):
    """Questions that fit the current situation (change after a sync), in the site's language.
    With action_id / finding_id: decision helpers for that one problem."""
    d = current_dashboard()
    if not (action_id or finding_id):
        return ask_cfo.public_suggestions(d, lang)
    try:
        f, a = ask_cfo.resolve_scope(d, action_id, finding_id)
    except ask_cfo.UnknownScope as e:
        raise HTTPException(404, str(e)) from None
    return ask_cfo.public_scoped(d, f, a, lang)


@app.post("/api/ask")
async def ask(q: Question):
    """'Ask your CFO': the right agent answers from the numbers already computed (guarded, with fallback).
    With action_id / finding_id the conversation is about that one problem."""
    try:
        return await ask_cfo.ask(q.question.strip(), q.lang, q.action_id, q.finding_id,
                                 [t.model_dump() for t in q.history])
    except ask_cfo.UnknownScope as e:
        raise HTTPException(404, str(e)) from None


@app.get("/api/contracts")
async def contracts(
    q: str | None = Query(None, max_length=100, description="text in party, title or file name"),
    origin: Literal["index", "uploaded"] | None = None,
    party_type: Literal["supplier", "customer"] | None = None,
    sort: Literal["uploaded_at", "-uploaded_at", "party", "-party", "title", "-title", "start_date", "-start_date",
                  "size_bytes", "-size_bytes", "pages", "-pages"] | None = None,
):
    """The Legal Agent's knowledge base: notebook-prepared index + contracts uploaded at runtime."""
    return contract_library.listing(q, origin, party_type, sort)


@app.get("/api/contracts/{contract_id}")
async def contract_detail(contract_id: str):
    c = contract_library.detail(contract_id)
    if not c:
        raise HTTPException(404, "unknown contract")
    return c


_UNSAFE_HEADER_CHARS = re.compile(r'[\x00-\x1f\x7f"\\]')


@app.get("/api/contracts/{contract_id}/file")
async def contract_file(contract_id: str, download: bool = False):
    """The original document (preview inline, or `?download=true`). Only PDF / Markdown / text are ever served,
    with `nosniff`, so the browser can't be talked into rendering an upload as HTML."""
    f = contract_library.original_file(contract_id)
    if not f:
        raise HTTPException(404, "no file for this contract")
    name, content, media = f
    inline = not download and media != "application/octet-stream"
    # RFC 6266/5987: ASCII fallback + UTF-8 name (uploads may be called "Rahmenvertrag – Müller.pdf")
    ascii_name = _UNSAFE_HEADER_CHARS.sub("_", name.encode("ascii", "replace").decode().replace("?", "_"))
    header = f"{'inline' if inline else 'attachment'}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name, safe='')}"
    return Response(content, media_type=media,
                    headers={"Content-Disposition": header, "X-Content-Type-Options": "nosniff"})


@app.post("/api/contracts/upload")
async def upload_contract(file: UploadFile = File(...)):
    """Owner uploads a contract (PDF / .md / .txt) -> Granite extracts the terms live (guided JSON)
    -> the Legal Agent uses them on the next inbox check."""
    content = await file.read(contract_library.MAX_BYTES + 1)
    try:
        result = await contract_library.upload(file.filename or "contract", content)
    except contract_library.ExtractionError as e:
        raise HTTPException(422, str(e)) from e
    c = result["contract"]
    store.log("contract_uploaded", contract_id=c["id"], party=c.get("supplier") or c.get("customer"),
              file=file.filename, extracted_by=c["extracted_by"], warnings=len(c["warnings"]))
    return result


@app.delete("/api/contracts/{contract_id}")
async def delete_contract(contract_id: str):
    if not contract_library.delete(contract_id):
        raise HTTPException(404, "only uploaded contracts can be removed")
    return contract_library.listing()


@app.get("/api/policy")
def policy(lang: Lang = "en"):
    return localize(POLICY, lang)


@app.get("/api/audit")
async def audit():
    return store.audit


@app.post("/api/reset")
async def reset(lang: Lang = "en"):
    """Clean demo start: findings, actions, audit AND contracts uploaded at runtime."""
    store.reset()
    contract_library.clear_uploads()
    return _dash(initial_dashboard(), lang)


# --- Frontend (built by Vite into STATIC_DIR) ---------------------------------

def static_file(root: Path, path: str) -> Path | None:
    """The file under `root` a URL path points to, or None. Never leaves `root`: the path arrives URL-decoded,
    so `/..%2f..%2fetc/passwd` must not resolve to a file outside the built front-end."""
    if not path:
        return None
    base = root.resolve()
    f = (base / path).resolve()
    return f if f.is_relative_to(base) and f.is_file() else None


def mount_frontend(target: FastAPI, root: Path) -> None:
    """Serve the built Vue app: real files as they are, every other path → index.html (history-mode routing).
    Unknown /api/* paths get a JSON 404 instead of the HTML page, so the UI never parses HTML as data."""
    if (root / "assets").is_dir():
        target.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

    @target.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        return FileResponse(static_file(root, path) or root / "index.html")


if settings.static_dir.is_dir():
    mount_frontend(app, settings.static_dir)
