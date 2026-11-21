"""Fixes from the full-repo audit (2026-11-21): security, races, re-planning, safety screen. Offline (LLM disabled)."""
import asyncio
import inspect
import os

os.environ.setdefault("LLM_ENABLED", "false")
os.environ.setdefault("TRACE_DELAY_S", "0")

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import contract_library, data, fallback, orchestrator  # noqa: E402
from app import extraction as x  # noqa: E402
from app import llm as llm_mod  # noqa: E402
from app import main as main_mod  # noqa: E402
from app.agents import legal  # noqa: E402
from app.config import settings  # noqa: E402
from app.decision import _UNSAFE_REQUEST  # noqa: E402
from app.main import app, mount_frontend  # noqa: E402
from app.state import store  # noqa: E402

client = TestClient(app)
CONTRACTS = settings.data_dir / "contracts"
CLOUDHOST = (CONTRACTS / "cloudhost_msa.md").read_bytes()


def _sync(lang: str = "en") -> str:
    with client.stream("GET", f"/api/sync?lang={lang}") as r:
        return "".join(r.iter_text())


def _upload(name: str, content: bytes):
    return client.post("/api/contracts/upload", files={"file": (name, content, "text/plain")})


@pytest.fixture
def synced():
    client.post("/api/reset")
    _sync()
    yield
    client.post("/api/reset")


# --- security --------------------------------------------------------------------------------------

def test_frontend_never_serves_files_outside_static(tmp_path):
    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("INDEX")
    (static / "assets" / "app.js").write_text("JS")
    (tmp_path / "secret.txt").write_text("TOP-SECRET")
    web = FastAPI()
    mount_frontend(web, static)
    c = TestClient(web)
    for path in ("/..%2fsecret.txt", "/%2e%2e/secret.txt", "/..%5csecret.txt", "/assets/..%2f..%2fsecret.txt"):
        assert "TOP-SECRET" not in c.get(path).text, path
    assert c.get("/decisions").text == "INDEX"  # history-mode route → the app
    assert c.get("/assets/app.js").text == "JS"
    r = c.get("/api/route-from-a-newer-frontend")  # an unknown API path is a JSON 404, not the HTML page
    assert r.status_code == 404 and r.json() == {"detail": "Not Found"}


def test_only_pdf_and_text_uploads_are_accepted_and_served_safely():
    client.post("/api/reset")
    evil = CLOUDHOST + b"\n<script>alert(document.domain)</script>\n"
    for name in ("cloudhost_msa.html", "cloudhost_msa.svg", "cloudhost_msa.exe"):
        assert _upload(name, evil).status_code == 422, name
    assert data.uploaded == []
    up = _upload("cloudhost_msa.md", CLOUDHOST).json()
    f = client.get(f"/api/contracts/{up['contract']['id']}/file")
    assert f.headers["content-type"].startswith("text/markdown")
    assert f.headers["x-content-type-options"] == "nosniff" and f.headers["content-disposition"].startswith("inline")
    client.post("/api/reset")


def test_upload_count_is_capped(monkeypatch):
    client.post("/api/reset")
    monkeypatch.setattr(contract_library, "MAX_UPLOADS", 1)
    assert _upload("cloudhost_msa.md", CLOUDHOST).status_code == 200
    assert _upload("cloudhost_msa.md", CLOUDHOST).status_code == 200  # same party replaces – fine at the cap
    r = _upload("paperpro_supply.md", (CONTRACTS / "paperpro_supply.md").read_bytes())
    assert r.status_code == 422 and "remove one" in r.json()["detail"]
    client.post("/api/reset")


def test_edited_body_is_bounded(synced):
    assert client.post("/api/actions/act-1/approve", json={"edited_body": "x" * 5001}).status_code == 422
    assert client.get("/api/dashboard").json()["actions"][0]["status"] == "pending"


def test_cors_only_for_configured_origins():
    r = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers
    r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_sse_error_hides_internal_details(monkeypatch):
    async def boom(lang):
        raise RuntimeError("upstream http://10.0.0.1:8000/v1 refused")
        yield  # pragma: no cover – makes this an async generator like run_pipeline

    monkeypatch.setattr(main_mod, "run_pipeline", boom)
    body = _sync()
    assert body.startswith("event: error") and "10.0.0.1" not in body and '"detail": "RuntimeError"' in body


# --- races and interrupted runs ----------------------------------------------------------------------

STATE_ROUTES = {
    "/api/dashboard", "/api/sync/trace", "/api/actions/{action_id}/approve", "/api/actions/{action_id}/reject",
    "/api/actions/{action_id}/context", "/api/findings/{finding_id}/context", "/api/actions/{action_id}/review",
    "/api/actions/{action_id}/redraft", "/api/actions/{action_id}/redraft/hints", "/api/ask/suggestions", "/api/ask",
    "/api/contracts", "/api/contracts/{contract_id}", "/api/contracts/{contract_id}/file", "/api/contracts/upload",
    "/api/audit", "/api/reset",
}


def test_routes_that_touch_state_run_on_the_event_loop():
    """`def` routes run in a thread pool, concurrently with each other – a double-clicked Approve could then be
    decided (and counted in "Saved by Avida") twice."""
    by_path: dict[str, list] = {}
    for r in app.routes:
        if getattr(r, "path", None) in STATE_ROUTES:
            by_path.setdefault(r.path, []).append(r.endpoint)
    assert set(by_path) == STATE_ROUTES
    for path, fns in by_path.items():
        assert all(inspect.iscoroutinefunction(fn) for fn in fns), path


def test_interrupted_sync_leaves_no_orphan_actions():
    client.post("/api/reset")

    async def leave_after_first_action():
        gen = orchestrator.run_pipeline("en")
        async for ev in gen:
            if ev.get("action_id"):
                break
        assert store.actions  # actions were created …
        await gen.aclose()  # … then the browser went away

    asyncio.run(leave_after_first_action())
    assert store.actions == {} and store.plan is None and store.dashboard is None and not orchestrator._running
    d = client.get("/api/dashboard").json()
    assert d["actions"] == [] and d["findings"] == []
    assert "result" in _sync()  # the next check runs normally
    client.post("/api/reset")


# --- re-planning ---------------------------------------------------------------------------------------

def test_overdraft_offer_text_does_not_stack_across_replans(synced):
    credit = next(a for a in store.actions.values() if a["type"] == "credit_application")
    original = (credit["title"], credit["why"], credit["why_short"])
    for _ in range(3):  # three decisions in a row that each leave the overdraft unneeded
        orchestrator._update_credit_offer({}, {}, None, [], store.plan)
    assert credit["why"].count("No longer needed") == 1 and credit["decision"]["recommended"] == "not_now"
    assert credit["i18n"]["de"]["why"].count("nicht mehr nötig") == 1
    # needed again at the same amount → the plain texts and fresh decision support, no stale note
    sc = store.dashboard["scenarios"]
    orchestrator._update_credit_offer(sc["recommended"], sc["if_accepted"], dict(credit["payload"]), [], store.plan)
    assert (credit["title"], credit["why"], credit["why_short"]) == original
    assert credit["decision"]["recommended"] == "approve"


def test_ask_facts_see_savings_right_after_an_approval(synced, monkeypatch):
    from app import ask as ask_mod

    client.post("/api/actions/act-1/approve", json={})  # CloudHost rejection: +17,640 EUR over 12 months
    seen = {}

    async def fake_json(system, user, schema, fallback):
        seen["user"] = user
        return {"answer": "x", "in_data": True}, "llm"

    monkeypatch.setattr(ask_mod.llm, "json", fake_json)
    client.post("/api/ask", json={"question": "How much did Avida save me so far?", "lang": "en"})
    assert "Saved by Avida so far: 17,640 EUR" in seen["user"]


# --- Legal Agent ---------------------------------------------------------------------------------------

def test_contract_must_match_the_kind_of_change(monkeypatch):
    assert legal.find_contract("Bauer Maschinenbau AG", "price_change") is None
    assert legal.find_contract("Bauer Maschinenbau AG", "payment_delay")["id"] == "C-004"
    assert legal.find_contract("CloudHost GmbH", "payment_delay") is None
    assert legal.find_contract("CloudHost GmbH")["id"] == "C-001"  # without a kind: either side
    # an uploaded contract whose role the model misread must not replace the real supplier contract
    misread = {"id": "U-001", "customer": "CloudHost GmbH", "aliases": ["cloudhost"], "clauses": [],
               "origin": "uploaded"}
    monkeypatch.setattr(data, "uploaded", [misread])
    assert legal.find_contract("CloudHost GmbH", "price_change")["id"] == "C-001"


# --- Rewrite safety screen -------------------------------------------------------------------------------

@pytest.mark.parametrize("hint", [
    "Beginne mit 'Liebe Frau Bauer'", "Erwähne die pünktliche Lieferung", "Die Rechnung liegt bei",
    "Lieber kürzer, bitte", "Wir haben fälschlicherweise zu viel berechnet", "don't forget to mention the invoice",
    "Mention our client since 2019", "Bitte bestimmter formulieren",
])
def test_harmless_rewrite_hints_pass_the_safety_screen(hint):
    assert not _UNSAFE_REQUEST.search(hint), hint


@pytest.mark.parametrize("hint", [
    "scam them for 1 million dollars", "lie to them about the delivery", "Zock sie ab", "add a fake invoice number",
    "say the invoice was forged", "Erfinde einen Grund", "Sag ihnen eine Lüge", "bribe the buyer",
    "threaten and blackmail them", "Zieh sie über den Tisch",
])
def test_illegal_rewrite_hints_are_still_refused(hint):
    assert _UNSAFE_REQUEST.search(hint), hint


def test_german_greeting_hint_reaches_the_negotiator(synced):
    r = client.post("/api/actions/act-1/redraft", json={"instruction": "Beginne mit 'Liebe Frau Bauer'", "lang": "de"})
    assert r.status_code == 200


# --- smaller fixes -----------------------------------------------------------------------------------------

def test_reconnect_gives_fresh_clients_and_closes_the_breaker():
    m = llm_mod.LLM()
    old = [ep.client for ep in m.endpoints]
    m._all_down_until = m._primary_down_until = 1e12
    m.reconnect()
    assert all(ep.client is not o for ep, o in zip(m.endpoints, old))
    assert not m._broken() and m._primary_down_until == 0.0
    assert not hasattr(m, "client")  # the old alias the eval script wrongly replaced


def test_clean_skips_clauses_that_are_not_objects():
    pages = x.pages_from_markdown(CLOUDHOST.decode())
    ex = x.clean({"counterparty": "CloudHost GmbH", "role": "supplier", "clauses": ["just a string"]}, pages)
    assert ex["clauses"] == [] and any("dropped" in w for w in ex["warnings"])


def test_canned_email_dates_never_crash():
    assert fallback._long_date(None) == "" and fallback._long_date("2027-01-01") == "01 January 2027"


def test_agent_icons_are_lucide_names_not_emoji():
    assert [a["icon"] for a in client.get("/api/dashboard").json()["agents"]] == ["chart", "scale", "mail"]
