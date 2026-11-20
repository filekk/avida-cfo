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


def _finding(d: dict, party: str) -> dict:
    return next(f for f in d["findings"] if f["extraction"]["party"] == party)


def test_forecast_before_sync():
    client.post("/api/reset")  # the store is global – other test files may have synced already
    d = client.get("/api/dashboard").json()
    assert d["kpis"]["min_balance"] == 11000
    assert d["findings"] == []


def test_full_happy_path():
    d = _sync()
    verdicts = {f["extraction"]["party"]: (f["contract"]["verdict"], f["recommendation"]) for f in d["findings"]}
    assert verdicts == {
        "CloudHost GmbH": ("violates", "reject"),
        "PaperPro GmbH": ("allowed", "accept"),
        "Bauer Maschinenbau AG": ("violates", "remind"),
        "Stahlhandel Nord GmbH": ("allowed", "accept"),
        "IT-Service Kraus e.K.": ("unclear", "review"),
    }

    cloud = _finding(d, "CloudHost GmbH")
    assert cloud["contract"]["clause_id"] == "§5.2"
    assert cloud["impact"]["next_12_months"] == 17640

    assert sorted(a["type"] for a in d["actions"]) == ["credit_application"] + ["send_email"] * 3
    credit = next(a for a in d["actions"] if a["type"] == "credit_application")
    assert credit["payload"]["amount"] == 45000

    # Nothing is executed without approval.
    assert all(a["status"] == "pending" for a in d["actions"])
    email = next(a for a in d["actions"] if a.get("finding_id") == "mail-001")
    r = client.post(f"/api/actions/{email['id']}/approve", json={}).json()
    assert r["action"]["status"] == "executed"
    assert r["saved_liquidity"] == 17640


def test_supplier_name_is_normalised_to_contract(monkeypatch):
    """Real models return e.g. 'CloudHost GmbH – Billing'; the forecast must still hit the CloudHost line."""
    from app import fallback

    noisy = dict(fallback.EXTRACTIONS["mail-001"], counterparty="CloudHost GmbH – Billing")
    monkeypatch.setitem(fallback.EXTRACTIONS, "mail-001", noisy)
    d = _sync()
    assert d["scenarios"]["if_accepted"]["min_balance"] == -29352
    assert d["scenarios"]["recommended"]["min_balance"] == -27882


def test_late_customer_payment_moves_cash():
    d = _sync()
    bauer = _finding(d, "Bauer Maschinenbau AG")
    assert bauer["kind"] == "payment_delay" and bauer["contract"]["clause_id"] == "§7.1"
    assert bauer["impact"]["days_late"] == 30 and bauer["impact"]["lowest_balance_effect"] == 38000
    # Payment left 5 Jan and arrives 4 Feb in the plan.
    cur = {p["date"]: p["balance"] for p in d["scenarios"]["current"]["series"]}
    rec = {p["date"]: p["balance"] for p in d["scenarios"]["recommended"]["series"]}
    assert cur["2027-01-05"] - rec["2027-01-05"] > 37000
    assert d["analysis"]["risk_level"] == "high"
    assert any("Payroll" in p for p in d["analysis"]["key_points"])
    reminder = next(a for a in d["actions"] if a.get("finding_id") == "mail-004")
    assert "RE-2026-1187" in reminder["payload"]["body"] and reminder["review"]["approved"]


def test_vague_email_is_not_guessed():
    d = _sync()
    kraus = _finding(d, "IT-Service Kraus e.K.")
    assert kraus["extraction"]["figures_stated"] is False and kraus["impact"]["next_12_months"] == 0
    ask = next(a for a in d["actions"] if a.get("finding_id") == "mail-006")
    assert ask["title"].startswith("Ask IT-Service Kraus") and ask["review"]["approved"]


def test_german_email_is_understood():
    d = _sync()
    steel = _finding(d, "Stahlhandel Nord GmbH")
    assert steel["extraction"]["increase_pct"] == 6.0 and steel["contract"]["verdict"] == "allowed"


def test_extraction_guard_drops_invented_amounts():
    from app.agents.analyst import amounts_in, sanitize

    email = {"from_name": "X", "subject": "s", "body": "Der Betrag steigt von 14.000,00 EUR auf 14.840,00 EUR. Old: EUR 9,800.00"}
    assert {14000.0, 14840.0, 9800.0} <= amounts_in(email["body"])
    ok = sanitize({"kind": "price_change", "counterparty": "X", "old_monthly": 14000, "new_monthly": 14840,
                   "effective_date": "2027-01-01"}, email)
    assert ok["figures_stated"] and ok["increase_pct"] == 6.0
    invented = sanitize({"kind": "price_change", "counterparty": "X", "old_monthly": 500, "new_monthly": 600,
                         "effective_date": "2027-01-01"}, email)
    assert not invented["figures_stated"] and invented["monthly_delta"] == 0
    bad_date = sanitize({"kind": "price_change", "counterparty": "X", "old_monthly": 14000, "new_monthly": 14840,
                         "effective_date": "January"}, email)
    assert not bad_date["figures_stated"]


def test_empty_party_matches_no_contract():
    from app.agents.legal import find_contract

    assert find_contract("") is None
    assert find_contract("CloudHost GmbH – Billing")["id"] == "C-001"


def test_fallback_answers_are_not_mutated():
    from app import fallback

    _sync()
    assert "monthly_delta" not in fallback.EXTRACTIONS["mail-001"]
    assert fallback.EXTRACTIONS["mail-001"]["counterparty"] == "CloudHost GmbH"


def test_second_sync_is_refused_while_running(monkeypatch):
    from app import orchestrator

    monkeypatch.setattr(orchestrator, "_running", True)
    with client.stream("GET", "/api/sync") as r:
        body = "".join(r.iter_lines())
    assert "event: error" in body and "already running" in body


def test_legal_review_catches_bad_drafts():
    from app.agents.legal import rule_review

    ex = {"old_monthly": 9800.0}
    res = {"clause": {"id": "§5.2"}}
    good = "Under §5.2 the agreed price of EUR 9,800.00 applies."
    assert rule_review(good, "reject_price", ex, res) == []
    bad = "Dear [Name], we cannot pay more because of our tight cash flow."
    assert len(rule_review(bad, "reject_price", ex, res)) == 4
    assert rule_review("Wegen unserer Liquidität …", "ask_details", ex, res)  # German leak is caught too


def test_briefing_guard_drops_invented_numbers():
    from app.agents.analyst import _numbers

    facts = "Balance today: 93,000 EUR. Safety cushion: 15,000 EUR. Lowest 10,958 EUR on 2027-02-03, +15.0%."
    assert _numbers("Lowest balance 10,958 EUR (+15%) on 2027-02-03") <= _numbers(facts)
    assert not _numbers("leaving 78,000 EUR for operations") <= _numbers(facts)


def test_briefing_guard_drops_long_summaries():
    from app.agents.analyst import summary_ok

    facts = ["Lowest balance 10,958 EUR on 2027-02-03.", "Rejecting CloudHost keeps 17,640 EUR per year."]
    assert summary_ok("Your balance dips to 10,958 EUR in February. Rejecting CloudHost keeps 17,640 EUR.", facts)
    assert not summary_ok("One. Two. Three. Four sentences are too many.", facts)


def test_department_suffix_is_stripped():
    from app.agents.analyst import sanitize

    ex = sanitize({"kind": "other", "counterparty": "Stahlhandel Nord GmbH – Vertrieb"}, {"subject": "s", "body": ""})
    assert ex["party"] == "Stahlhandel Nord GmbH"
