"""Runs the full pipeline with the LLM disabled (fallback answers) – must work offline."""
import json
import os

os.environ["LLM_ENABLED"] = "false"
os.environ["TRACE_DELAY_S"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _sync() -> dict:
    result = None
    with client.stream("GET", "/api/sync") as r:
        for line in r.iter_lines():
            if line.startswith("data:"):
                ev = json.loads(line[5:])
                if ev["type"] == "result":
                    result = ev["dashboard"]
    assert result is not None
    return result


def test_forecast_before_sync():
    d = client.get("/api/dashboard").json()
    assert d["kpis"]["min_balance"] == 11000
    assert d["findings"] == []


def test_full_happy_path():
    d = _sync()
    verdicts = {f["extraction"]["supplier"]: f["contract"]["verdict"] for f in d["findings"]}
    assert verdicts == {"CloudHost GmbH": "violates", "PaperPro GmbH": "allowed"}

    cloud = next(f for f in d["findings"] if f["extraction"]["supplier"] == "CloudHost GmbH")
    assert cloud["contract"]["clause_id"] == "§5.2"
    assert cloud["impact"]["next_12_months"] == 17640

    types = sorted(a["type"] for a in d["actions"])
    assert types == ["credit_application", "send_email"]
    credit = next(a for a in d["actions"] if a["type"] == "credit_application")
    assert credit["payload"]["amount"] == 5000

    # Nothing is executed without approval.
    assert all(a["status"] == "pending" for a in d["actions"])
    email = next(a for a in d["actions"] if a["type"] == "send_email")
    r = client.post(f"/api/actions/{email['id']}/approve", json={}).json()
    assert r["action"]["status"] == "executed"
    assert r["saved_liquidity"] == 17640


def test_supplier_name_is_normalised_to_contract(monkeypatch):
    """Real models return e.g. 'CloudHost GmbH – Billing'; the forecast must still hit the CloudHost line."""
    from app import fallback

    noisy = dict(fallback.EXTRACTIONS["mail-001"], supplier="CloudHost GmbH – Billing")
    monkeypatch.setitem(fallback.EXTRACTIONS, "mail-001", noisy)
    d = _sync()
    assert d["scenarios"]["if_accepted"]["min_balance"] == 9488
    assert d["scenarios"]["recommended"]["min_balance"] == 10958


def test_three_agents_collaborate():
    d = _sync()
    assert [a["name"] for a in d["agents"]] == ["Analyst Agent", "Legal Agent", "Negotiator Agent"]
    email = next(a for a in d["actions"] if a["type"] == "send_email")
    assert email["agent"] == "Negotiator Agent" and email["reviewed_by"] == "Legal Agent"
    assert email["review"]["approved"]  # the template draft passes the lawyer's checks
    assert d["analysis"]["key_points"] and d["analysis"]["risk_level"] in {"low", "medium", "high"}


def test_legal_review_catches_bad_drafts():
    from app.agents.legal import rule_review

    ex = {"old_monthly": 9800.0}
    res = {"clause": {"id": "§5.2"}}
    good = "Under §5.2 the agreed price of EUR 9,800.00 applies."
    assert rule_review(good, ex, res) == []
    bad = "Dear [Name], we cannot pay more because of our tight cash flow."
    assert len(rule_review(bad, ex, res)) == 4


def test_briefing_guard_drops_invented_numbers():
    from app.agents.analyst import _numbers

    facts = "Balance today: 93,000 EUR. Safety cushion: 15,000 EUR. Lowest 10,958 EUR on 2027-02-03, +15.0%."
    assert _numbers("Lowest balance 10,958 EUR (+15%) on 2027-02-03") <= _numbers(facts)
    assert not _numbers("leaving 78,000 EUR for operations") <= _numbers(facts)
