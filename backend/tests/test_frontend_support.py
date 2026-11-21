"""Back-end support for the front-end redesign: languages, richer SSE, decision support, problem chat,
owner draft tools, contract files page, chart data. Offline (LLM disabled)."""
import json
import os

os.environ["LLM_ENABLED"] = "false"
os.environ["TRACE_DELAY_S"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import texts  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def _sync(lang: str = "en") -> list[dict]:
    events = []
    with client.stream("GET", f"/api/sync?lang={lang}") as r:
        for line in r.iter_lines():
            if line.startswith("data:"):
                events.append(json.loads(line[5:]))
    assert events[-1]["type"] == "result"
    return events


@pytest.fixture
def synced_de():
    client.post("/api/reset")
    return _sync("de")


@pytest.fixture
def synced():
    client.post("/api/reset")
    return _sync("en")


# --- languages -----------------------------------------------------------------------

def test_localize_overlays_and_strips():
    obj = {"a": "en", "n": 1, "i18n": {"de": {"a": "de"}}, "kids": [{"b": "x", "i18n": {"de": {"b": "y"}}}]}
    assert texts.localize(obj, "de") == {"a": "de", "n": 1, "kids": [{"b": "y"}]}
    assert texts.localize(obj, "en") == {"a": "en", "n": 1, "kids": [{"b": "x"}]}
    assert texts.eur(-27882, "de") == "-27.882 EUR" and texts.num(9800, "de", 2) == "9.800,00"


def test_no_i18n_key_ever_leaves_the_api(synced_de):
    for lang in ("en", "de"):
        assert '"i18n"' not in client.get(f"/api/dashboard?lang={lang}").text
        assert '"i18n"' not in client.get(f"/api/policy?lang={lang}").text
    assert '"i18n"' not in json.dumps(synced_de)


def test_dashboard_in_both_languages_after_one_sync(synced_de):
    de = synced_de[-1]["dashboard"]
    assert de["lang"] == "de" and de["sync_lang"] == "de"
    assert de["headline"].startswith("Sie sind die nächsten 61 Tage sicher")
    cloud = next(a for a in de["actions"] if a.get("finding_id") == "mail-001")
    assert cloud["title"] == "Preiserhöhung um 15 % von CloudHost GmbH ablehnen"
    f = next(f for f in de["findings"] if f["id"] == "mail-001")
    assert f["contract"]["checks"][0]["check"] == "Preisgarantie"
    assert f["impact"]["calculation"].startswith("11.270,00 − 9.800,00")
    assert f["email"]["body"] == next(x for x in client.get("/api/dashboard").json()["findings"]
                                      if x["id"] == "mail-001")["email"]["body"]  # originals untouched
    # the same state in English – nothing re-runs
    en = client.get("/api/dashboard?lang=en").json()
    assert en["headline"].startswith("You're safe for the next 61 days")
    assert next(a for a in en["actions"] if a.get("finding_id") == "mail-001")["title"].startswith("Reject the 15%")
    assert "Subject:" in cloud["payload"]["body"]  # drafts are not translated


def test_policy_and_decision_results_are_translated(synced):
    assert client.get("/api/policy?lang=de").json()[0]["action"].startswith("Posteingang lesen")
    r = client.post("/api/actions/act-1/approve?lang=de", json={}).json()
    assert r["action"]["result"].startswith("E-Mail an") and r["saved_liquidity_previous"] == 0
    assert client.get("/api/dashboard?lang=en").json()["actions"][0]["result"].startswith("Email to")


def test_invalid_lang_is_rejected():
    assert client.get("/api/dashboard?lang=pl").status_code == 422


# --- SSE --------------------------------------------------------------------------------

def test_sse_has_phases_and_stamped_events(synced):
    evs = synced[:-1]
    phases = [(e["phase"], e["status"]) for e in evs if e["type"] == "phase"]
    assert phases == [(p, s) for p in texts.PHASES for s in ("start", "done")]
    assert [e["id"] for e in evs] == list(range(1, len(evs) + 1))
    assert all(e["phase"] in texts.PHASES and e["elapsed_ms"] >= 0 and e["ts"] for e in evs)
    negotiation = [e for e in evs if e["type"] == "trace" and e["phase"] == "negotiation"]
    assert negotiation and all(e["finding_id"] and e["partner"] for e in negotiation)
    waiting = [e for e in evs if e["type"] == "trace" and e["autonomy"] == "approval"]
    assert all(e["action_id"] for e in waiting)


def test_trace_replay(synced):
    r = client.get("/api/sync/trace").json()
    assert r["lang"] == "en" and len(r["events"]) == len(synced) - 1
    client.post("/api/reset")
    assert client.get("/api/sync/trace").json() == {"lang": None, "events": []}


# --- numbers & chart --------------------------------------------------------------------

def test_kpis_previous_and_chart_data(synced):
    d = client.get("/api/dashboard").json()
    assert d["kpis_previous"]["min_balance"] == 9000 and d["kpis"]["min_balance"] == -29882
    rec = d["scenarios"]["recommended"]
    day = rec["series"][0]
    assert {"inflow", "outflow"} <= day.keys()
    assert round(sum(p["inflow"] + p["outflow"] for p in rec["series"]), 2) == round(rec["end_balance"] - rec["start_balance"], 2)
    assert rec["outflows_by_category"][0]["category"] == "payroll"
    assert sum(c["total"] for c in rec["outflows_by_category"]) == pytest.approx(sum(e["amount"] for e in rec["events"] if e["amount"] < 0))
    client.post("/api/reset")
    assert client.get("/api/dashboard").json()["kpis_previous"] is None


# --- decision support ---------------------------------------------------------------------

def test_every_action_has_a_decision(synced):
    d = synced[-1]["dashboard"]
    for a in d["actions"]:
        dec = a["decision"]
        assert [o["choice"] for o in dec["options"]] == ["approve", "not_now"] and a["why_short"]
    cloud = next(a for a in d["actions"] if a.get("finding_id") == "mail-001")["decision"]
    assert cloud["deadline"] == "2027-01-01"
    approve, not_now = cloud["options"]
    assert approve["effects"]["min_balance"] == -29882 and not_now["effects"]["min_balance"] == -31352
    assert not_now["effects"]["cost_12m"] == 17640
    bauer = next(a for a in d["actions"] if a.get("finding_id") == "mail-004")["decision"]
    assert bauer["certainty"] == "medium" and bauer["options"][0]["effects"]["min_balance"] == 8118


# --- problem chat -------------------------------------------------------------------------

def test_scoped_suggestions_and_prepared_answers(synced):
    s = client.get("/api/ask/suggestions?lang=en&action_id=act-1").json()
    assert s["finding_id"] == "mail-001" and [x["id"] for x in s["suggestions"]] == ["why", "cost", "not_now", "deadline"]
    q = next(x for x in s["suggestions"] if x["id"] == "deadline")["question"]
    r = client.post("/api/ask", json={"question": q, "lang": "en", "action_id": "act-1"}).json()
    assert r["source"] == "rules" and "1 Jan 2027" in r["answer"] and r["action_id"] == "act-1"
    paper = client.get("/api/findings/mail-002/context?lang=de").json()
    assert paper["action"] is None and paper["finding"]["id"] == "mail-002"
    assert "negotiate" in [x["id"] for x in paper["suggestions"]["suggestions"]]


def test_scoped_free_text_uses_problem_facts_and_history(synced, monkeypatch):
    from app import ask as ask_mod

    seen = {}

    async def fake_json(system, user, schema, fallback):
        seen["user"] = user
        return {"answer": "You keep paying 9,800 EUR per month.", "in_data": True}, "llm"

    monkeypatch.setattr(ask_mod.llm, "json", fake_json)
    r = client.post("/api/ask", json={"question": "And what do I pay then?", "lang": "en", "action_id": "act-1",
                                      "history": [{"role": "owner", "text": "Should I reject it?"},
                                                  {"role": "agent", "text": "Yes."}]}).json()
    assert r["source"] == "llm" and r["answer"].startswith("You keep paying")
    assert "Contract clause §5.2" in seen["user"] and "OWNER: Should I reject it?" in seen["user"]
    assert "Bauer" not in seen["user"]  # only this problem's facts


def test_unknown_scope_is_404(synced):
    assert client.get("/api/actions/act-99/context").status_code == 404
    assert client.post("/api/ask", json={"question": "Why?", "finding_id": "nope"}).status_code == 404


# --- owner draft tools ----------------------------------------------------------------------

def test_review_of_owner_edit(synced):
    good = client.get("/api/dashboard").json()["actions"][0]["payload"]["body"]
    assert client.post("/api/actions/act-1/review", json={"body": good}).json()["approved"] is True
    bad = client.post("/api/actions/act-1/review", json={"body": "Hi [Name], cash flow is tight.", "lang": "de"}).json()
    assert not bad["approved"] and bad["issues"][0].startswith("Die E-Mail")


def test_redraft_is_only_a_proposal(synced, monkeypatch):
    from app import decision

    original = client.get("/api/dashboard").json()["actions"][0]["payload"]["body"]
    softer = original.replace("We therefore do not accept", "We are therefore unfortunately unable to accept")

    async def fake_text(system, user, fallback, max_tokens=400):
        return softer, "llm"

    monkeypatch.setattr(decision.llm, "text", fake_text)
    r = client.post("/api/actions/act-1/redraft", json={"instruction": "Make it softer"}).json()
    assert r["changed"] and r["body"] == softer and r["review"]["approved"]
    assert client.get("/api/dashboard").json()["actions"][0]["payload"]["body"] == original  # untouched
    credit = next(a for a in client.get("/api/dashboard").json()["actions"] if a["type"] == "credit_application")
    assert client.post(f"/api/actions/{credit['id']}/redraft", json={"instruction": "x"}).status_code == 409


def test_rewrite_button_hint_optional_attempts_and_chips(synced, monkeypatch):
    from app import decision

    seen = []

    async def fake_text(system, user, fallback, max_tokens=400):
        seen.append(user)
        return fallback, "fallback"  # model down → draft unchanged + note

    monkeypatch.setattr(decision.llm, "text", fake_text)
    r1 = client.post("/api/actions/act-1/redraft", json={}).json()  # no hint = "write it again"
    assert decision.DEFAULT_REWRITE in seen[0] and r1["instruction"] == decision.DEFAULT_REWRITE
    assert r1["attempt"] == 1 and r1["changed"] is False and r1["note"]
    r2 = client.post("/api/actions/act-1/redraft",
                     json={"instruction": "Mention we are customers since 2019", "body": r1["body"], "lang": "de"}).json()
    assert r2["attempt"] == 2 and "since 2019" in seen[1] and "nicht erreichbar" in r2["note"]

    h = client.get("/api/actions/act-1/redraft/hints?lang=de").json()
    assert h["action_id"] == "act-1" and h["placeholder"]
    assert {x["id"] for x in h["hints"]} >= {"softer", "shorter", "german"}
    assert next(x for x in h["hints"] if x["id"] == "shorter")["label"] == "Kürzer"
    assert client.get("/api/actions/nope/redraft/hints").status_code == 404
    credit = next(a for a in client.get("/api/dashboard").json()["actions"] if a["type"] == "credit_application")
    assert client.get(f"/api/actions/{credit['id']}/redraft/hints").status_code == 409


def test_edited_body_is_flagged(synced):
    client.post("/api/actions/act-3/approve", json={"edited_body": "Subject: Hi\n\nPlease send prices."})
    a = next(a for a in client.get("/api/dashboard").json()["actions"] if a["id"] == "act-3")
    assert a["edited_by_owner"] is True


# --- contract files page ---------------------------------------------------------------------

def test_contract_listing_metadata_filters_sort():
    client.post("/api/reset")
    content = (settings.data_dir / "contracts" / "cloudhost_msa.md").read_bytes()
    up = client.post("/api/contracts/upload", files={"file": ("cloudhost_msa.md", content, "text/markdown")}).json()
    cid = up["contract"]["id"]
    rows = client.get("/api/contracts").json()
    u = rows[0]
    assert u["id"] == cid and u["uploaded_at"] and u["size_bytes"] == len(content) and u["pages"] >= 1
    assert u["file_type"] == "md" and u["party_type"] == "supplier" and u["party"] == "CloudHost GmbH"
    assert all(r["uploaded_at"] is None for r in rows[1:])
    assert [r["id"] for r in client.get("/api/contracts?party_type=customer").json()] == ["C-004"]
    assert [r["origin"] for r in client.get("/api/contracts?origin=uploaded").json()] == ["uploaded"]
    assert [r["party"] for r in client.get("/api/contracts?q=paper").json()] == ["PaperPro GmbH"]
    by_size = [r["size_bytes"] for r in client.get("/api/contracts?sort=-size_bytes").json()]
    assert by_size == sorted(by_size, reverse=True)
    assert client.get("/api/contracts?sort=nonsense").status_code == 422

    detail = client.get(f"/api/contracts/{cid}").json()
    assert isinstance(detail["clauses"], list) and detail["clause_count"] == len(detail["clauses"])
    f = client.get(f"/api/contracts/{cid}/file?download=true")
    assert f.status_code == 200 and f.content == content and f.headers["content-disposition"].startswith("attachment")
    assert client.get("/api/contracts/C-004/file").status_code == 200
    assert client.get("/api/contracts/X-1").status_code == 404

    _sync()
    used = {r["id"]: r for r in client.get("/api/contracts").json()}
    assert used[cid]["used_in_last_sync"] and used[cid]["used_by_findings"] == ["mail-001"]
    client.post("/api/reset")
    assert client.get(f"/api/contracts/{cid}/file").status_code == 404
