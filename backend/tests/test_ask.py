"""'Ask your CFO' – offline (LLM disabled) plus guard / router unit tests."""
import json
import os

os.environ["LLM_ENABLED"] = "false"
os.environ["TRACE_DELAY_S"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import ask as ask_mod  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def _sync():
    with client.stream("GET", "/api/sync") as r:
        for line in r.iter_lines():
            if line.startswith("data:") and json.loads(line[5:])["type"] == "result":
                return
    raise AssertionError("no result")


@pytest.fixture
def before_sync():
    client.post("/api/reset")


@pytest.fixture
def after_sync():
    client.post("/api/reset")
    _sync()


def test_suggestions_before_sync_have_note(before_sync):
    for lang in ("en", "de"):
        s = client.get(f"/api/ask/suggestions?lang={lang}").json()
        assert s["note"] and s["suggestions"]
        assert all("answer" not in x for x in s["suggestions"])  # canned answers stay internal
    de = client.get("/api/ask/suggestions?lang=de").json()
    assert de["suggestions"][0]["question"].startswith("Bin ich")


def test_suggestions_after_sync_fit_the_situation(after_sync):
    s = client.get("/api/ask/suggestions?lang=en").json()
    assert s["note"] is None
    ids = [x["id"] for x in s["suggestions"]]
    assert ids == ["overdraft", "on_time", "reject", "no_figures"]
    agents = {x["id"]: x["agent"] for x in s["suggestions"]}
    assert agents["reject"] == "Legal Agent" and agents["no_figures"] == "Negotiator Agent"


def test_clicked_suggestion_gets_prepared_answer(after_sync):
    q = next(x for x in client.get("/api/ask/suggestions?lang=de").json()["suggestions"] if x["id"] == "on_time")
    r = client.post("/api/ask", json={"question": q["question"], "lang": "de"}).json()
    assert r["agent"] == "Analyst Agent" and r["source"] == "rules"  # prepared answer, no LLM
    assert "10.118 EUR" in r["answer"] and "-27.882 EUR" in r["answer"]  # German number format


def test_free_text_falls_back_honestly(after_sync):
    r = client.post("/api/ask", json={"question": "Is the CloudHost increase allowed by the contract?"}).json()
    assert r["agent"] == "Legal Agent"
    assert r["answer"].startswith("I'm not completely sure") and "§5.2" in r["answer"]


def test_off_topic_is_refused(after_sync, monkeypatch):
    async def fake_json(system, user, schema, fallback):
        return {"answer": "EUR/USD will be 1.12.", "in_data": False}, "llm"

    monkeypatch.setattr(ask_mod.llm, "json", fake_json)
    r = client.post("/api/ask", json={"question": "What will EUR/USD be next year?", "lang": "en"}).json()
    assert r["in_data"] is False and r["answer"].startswith("I can't tell") and r["suggestions"]


def test_invented_number_from_model_is_replaced(after_sync, monkeypatch):
    async def fake_json(system, user, schema, fallback):
        return {"answer": "You need 60,000 EUR.", "in_data": True}, "llm"

    monkeypatch.setattr(ask_mod.llm, "json", fake_json)
    r = client.post("/api/ask", json={"question": "How big is the overdraft you propose?"}).json()
    assert r["source"] == "fallback" and r["answer"].startswith("I'm not completely sure") and "45,000 EUR" in r["answer"]


def test_answer_guard_accepts_german_formats():
    facts = ["Lowest balance: -27,882 EUR on 2027-02-03.", "Proposed overdraft: 45,000 EUR, rate 9.5%."]
    assert ask_mod.answer_ok("Am 03.02.2027 läge Ihr Konto bei -27.882 EUR; Zinssatz 9,5 %.", facts)
    assert ask_mod.answer_ok("On 3 Feb 2027 your balance is -27,882 EUR.", facts)
    assert not ask_mod.answer_ok("Sie brauchen 50.000 EUR.", facts)
    assert not ask_mod.answer_ok("One. Two. Three. Four. Five.", facts)


def test_router():
    assert ask_mod.route("Is this allowed by my contract?") == "Legal Agent"
    assert ask_mod.route("Was steht in der E-Mail an Bauer?") == "Negotiator Agent"
    assert ask_mod.route("Was sagt das Briefing?") == "Analyst Agent"  # 'Briefing' is not 'Brief'
    assert ask_mod.route("When is my balance lowest?") == "Analyst Agent"


def test_invalid_input_is_rejected():
    assert client.post("/api/ask", json={"question": "Hi", "lang": "pl"}).status_code == 422
    assert client.post("/api/ask", json={"question": ""}).status_code == 422
