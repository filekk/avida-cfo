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
