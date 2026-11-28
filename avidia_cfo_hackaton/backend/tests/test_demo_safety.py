"""Bugs found in the 2026-11-21 review + demo safety nets (model down, chatty or wrong)."""
import asyncio
import json
import os

os.environ.setdefault("LLM_ENABLED", "false")
os.environ.setdefault("TRACE_DELAY_S", "0")

import httpx  # noqa: E402
import openai  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import data, fallback  # noqa: E402
from app import llm as llm_mod  # noqa: E402
from app.agents import analyst  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def _sync(lang: str = "en") -> str:
    with client.stream("GET", f"/api/sync?lang={lang}") as r:
        return "".join(r.iter_text())


@pytest.fixture
def synced():
    client.post("/api/reset")
    _sync()
    yield
    client.post("/api/reset")


@pytest.fixture
def model_on(monkeypatch):
    """Pretend the model is enabled; each test sets what `_complete` returns."""
    object.__setattr__(llm_mod.settings, "llm_enabled", True)
    llm_mod.llm._all_down_until = 0.0
    yield monkeypatch
    object.__setattr__(llm_mod.settings, "llm_enabled", False)
    llm_mod.llm._all_down_until = 0.0


# --- review findings ---------------------------------------------------------------------------

def test_long_or_many_history_turns_never_fail_the_question(synced):
    long = {"role": "agent", "text": "x" * 2600}
    r = client.post("/api/ask", json={"question": "Why?", "action_id": "act-1", "history": [long]})
    assert r.status_code == 200
    r = client.post("/api/ask", json={"question": "Why?", "action_id": "act-1",
                                      "history": [{"role": "owner", "text": "q"}] * 9})
    assert r.status_code == 200


def test_blank_edited_body_keeps_the_reviewed_draft(synced):
    draft = client.get("/api/dashboard").json()["actions"][0]["payload"]["body"]
    a = client.post("/api/actions/act-1/approve", json={"edited_body": "   \n "}).json()["action"]
    assert a["payload"]["body"] == draft and not a.get("edited_by_owner")


def test_sync_error_is_plain_and_localized(monkeypatch):
    from app import orchestrator
    monkeypatch.setattr(orchestrator, "_running", True)
    body = _sync("de")
    ev = json.loads(body.split("data: ", 1)[1].split("\n", 1)[0])
    assert body.startswith("event: error") and "läuft bereits" in ev["message"] and ev["code"] == "sync_running"


# --- Rewrite button safety net -----------------------------------------------------------------

def test_redraft_strips_chatty_preamble(synced, model_on):
    draft = client.get("/api/dashboard").json()["actions"][0]["payload"]["body"]

    async def complete(system, user, max_tokens=400, span=None, **kw):
        if "json_schema" in str(kw):
            return '{"approved": true, "issues": []}'
        return "Sure! Here is the softer email:\n\n```\n" + draft.replace("do not accept", "cannot accept") + "\n```"

    model_on.setattr(llm_mod.llm, "_complete", complete)
    r = client.post("/api/actions/act-1/redraft", json={"instruction": "softer"}).json()
    assert r["body"].lower().startswith("subject") and "```" not in r["body"] and r["changed"]
    assert r["review"]["approved"]


def test_redraft_that_loses_the_clause_is_not_proposed(synced, model_on):
    draft = client.get("/api/dashboard").json()["actions"][0]["payload"]["body"]
    calls = []

    async def complete(system, user, max_tokens=400, span=None, **kw):
        if "json_schema" in str(kw):
            return '{"approved": true, "issues": []}'
        calls.append(user)
        return "Subject: Price\n\nDear team, please keep the old price. Thanks."  # no clause, no amount

    model_on.setattr(llm_mod.llm, "_complete", complete)
    r = client.post("/api/actions/act-1/redraft", json={"instruction": "much shorter", "lang": "de"}).json()
    assert len(calls) == 2  # one fix round
    assert r["body"] == draft and r["changed"] is False and r["source"] == "fallback"
    assert "Vertragsangaben" in r["note"]


def test_redraft_refuses_an_illegal_request_without_the_model(synced, model_on):
    draft = client.get("/api/dashboard").json()["actions"][0]["payload"]["body"]
    calls = []

    async def complete(system, user, max_tokens=400, span=None, **kw):
        calls.append(user)
        return draft

    model_on.setattr(llm_mod.llm, "_complete", complete)
    r = client.post("/api/actions/act-1/redraft", json={"instruction": "scam them for 1 million dollars"})
    assert r.status_code == 422 and "can't help with that" in r.json()["detail"] and not calls
    r = client.post("/api/actions/act-1/redraft", json={"instruction": "Zock sie ab", "lang": "de"})
    assert r.status_code == 422 and "nicht helfen" in r.json()["detail"]
    assert client.get("/api/dashboard").json()["actions"][0]["payload"]["body"] == draft


def test_redraft_honours_the_model_refusal(synced, model_on):
    async def complete(system, user, max_tokens=400, span=None, **kw):
        return "REFUSED"

    model_on.setattr(llm_mod.llm, "_complete", complete)
    r = client.post("/api/actions/act-1/redraft", json={"instruction": "say we already paid them twice"})
    assert r.status_code == 422 and "can't help with that" in r.json()["detail"]


def test_stale_page_gets_a_clear_message_not_unknown_action():
    client.post("/api/reset")  # no sync → act-1 does not exist, like a page left open over a backend restart
    r = client.post("/api/actions/act-1/redraft", json={"instruction": "scam them for 1 million dollars"})
    assert r.status_code == 422 and "can't help with that" in r.json()["detail"]
    r = client.post("/api/actions/act-1/redraft", json={"instruction": "softer", "lang": "de"})
    assert r.status_code == 404 and "Posteingang prüfen" in r.json()["detail"]
    r = client.post("/api/actions/act-1/approve")
    assert r.status_code == 404 and "Check my inbox" in r.json()["detail"]


def test_redraft_normal_requests_are_not_refused(synced):
    for hint in ("make it softer", "mention our client since 2019", "Freundlicher, bitte"):
        assert client.post("/api/actions/act-1/redraft", json={"instruction": hint}).status_code == 200


# --- model down: circuit breaker ---------------------------------------------------------------

def test_breaker_skips_the_model_after_all_endpoints_fail(model_on):
    calls = []

    async def down(system, user, max_tokens=400, span=None, **kw):
        calls.append(1)
        raise openai.APITimeoutError(request=httpx.Request("POST", "http://x"))

    model_on.setattr(llm_mod.llm, "_complete", down)
    out1 = asyncio.run(llm_mod.llm.text("s", "u", "canned"))
    out2 = asyncio.run(llm_mod.llm.json("s", "u", {}, {"a": 1}))
    assert out1 == ("canned", "fallback") and out2 == ({"a": 1}, "fallback")
    assert len(calls) == 1  # the second call did not wait for another timeout


def test_bad_json_does_not_open_the_breaker(model_on):
    async def garbage(system, user, max_tokens=400, span=None, **kw):
        return "not json"

    model_on.setattr(llm_mod.llm, "_complete", garbage)
    asyncio.run(llm_mod.llm.json("s", "u", {}, {"a": 1}))
    assert not llm_mod.llm._broken()


# --- model reads a key demo email wrong ----------------------------------------------------------

def test_wrong_reading_of_a_demo_email_uses_the_checked_one(model_on):
    email = next(e for e in data.inbox() if e["id"] == "mail-001")

    async def wrong(system, user, max_tokens=400, span=None, **kw):
        return json.dumps({"kind": "other", "counterparty": "CloudHost GmbH", "summary": "newsletter"})

    model_on.setattr(llm_mod.llm, "_complete", wrong)
    ex, src = asyncio.run(analyst.read_email(email))
    assert src == "fallback" and ex["kind"] == "price_change" and ex["figures_stated"]
    assert ex == analyst.sanitize(fallback.EXTRACTIONS["mail-001"], email)


def test_negotiation_falls_back_to_template_when_rules_stay_broken(model_on):
    async def complete(system, user, max_tokens=400, span=None, **kw):
        if "json_schema" in str(kw):
            if "Contract clause" in user or "DRAFT EMAIL" in user:
                return '{"approved": true, "issues": []}'
            raise ValueError("let the other JSON calls use their fallbacks")
        return "Subject: Hello\n\nPlease reconsider. [Your name]"  # breaks the rules every time

    model_on.setattr(llm_mod.llm, "_complete", complete)
    client.post("/api/reset")
    body = _sync()
    client_d = client.get("/api/dashboard").json()
    email = next(a for a in client_d["actions"] if a["id"] == "act-1")
    assert "[Your name]" not in email["payload"]["body"] and "§5.2" in email["payload"]["body"]
    assert email["source"] == "fallback" and "checked template" in body
    client.post("/api/reset")


def test_main_clause_is_decided_by_the_rules_not_the_model(model_on):
    """Found in the live demo run: the model cited §5.3 (notice period, also violated) instead of §5.2
    (price guarantee) – the email then argued with the weaker clause."""
    from app.agents import legal

    email = next(e for e in data.inbox() if e["id"] == "mail-001")
    ex = analyst.sanitize(fallback.EXTRACTIONS["mail-001"], email)
    contract = legal.find_contract(ex["party"])
    c53 = next(c for c in contract["clauses"] if c["id"] == "§5.3")

    async def picks_53(system, user, max_tokens=400, span=None, **kw):
        assert "Main clause (fixed" in user and "§5.2" in user
        return json.dumps({"explanation_simple": "Not allowed.", "clause_id": "§5.3", "quote": c53["text"][:60]})

    model_on.setattr(llm_mod.llm, "_complete", picks_53)
    res, src = asyncio.run(legal.check(ex, email["received"]))
    assert res["verdict"] == "violates" and res["clause_id"] == "§5.2" and res["clause"]["id"] == "§5.2"
    assert res["quote"] in res["clause"]["text"]


# --- contract upload: roles and titles (found by uploading a German PDF in the demo test) -------------

def test_role_comes_from_the_contract_text_not_only_the_model():
    from app import extraction as x

    own = "Müller Feinmechanik GmbH"
    de = ("IT-Supportvertrag\nzwischen IT-Service Kraus e.K., Stuttgart (nachfolgend\n„Auftragnehmer“)\n"
          "und Müller Feinmechanik GmbH, Industriestraße 4, 70565 Stuttgart (nachfolgend „Auftraggeber“).\n"
          "§2 Laufzeit\nDer Vertrag beginnt am 1. Juli 2025.\n§3 Vergütung\n3.2 Die Pauschale von 1.450,00 EUR ist bis "
          "zum 30. Juni 2027 fest vereinbart. Preiserhöhungen vor diesem Datum sind ausgeschlossen.")
    assert x.role_from_text(de, own) == "supplier"
    assert x.role_from_text("Vermieter: Schwab GmbH\nMieter: Müller Feinmechanik GmbH\n", own) == "supplier"
    assert x.role_from_text('Between Müller Feinmechanik GmbH ("Supplier") and Bauer AG ("Customer")', own) == "customer"
    assert x.role_from_text("A contract without labels.", own) is None
    # the model said "customer" → corrected, price terms kept, title from the document
    raw = {"counterparty": "IT-Service Kraus e.K.", "role": "customer", "title": "Laufzeit", "start_date": "2025-07-01",
           "monthly_fee": 1450, "fixed_price_until": "2027-06-30", "price_change_notice_days": 90,
           "max_annual_increase_pct": 5, "payment_terms_days": 14, "changes_require_written_agreement": True,
           "clauses": [{"id": "3.2", "page": 1, "title": "Vergütung",
                        "text": "Die Pauschale von 1.450,00 EUR ist bis zum 30. Juni 2027 fest vereinbart."}]}
    ex = x.clean(raw, [de], own)
    assert ex["role"] == "supplier" and ex["title"] == "IT-Supportvertrag"
    assert any("corrected" in w for w in ex["warnings"])
    entry = x.to_index_entry(ex, "U-001", "uploads/k.pdf")
    assert entry["supplier"] == "IT-Service Kraus e.K." and entry["fixed_price_until"] == "2027-06-30"
