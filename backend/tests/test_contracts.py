"""Contract upload + shared extraction code (offline: LLM disabled, demo files fall back to the index)."""
import json
import os

os.environ["LLM_ENABLED"] = "false"
os.environ["TRACE_DELAY_S"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from app import data, extraction  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
CLOUDHOST = (settings.data_dir / "contracts" / "cloudhost_msa.md").read_bytes()


def test_pages_from_markdown():
    pages = extraction.pages_from_markdown(CLOUDHOST.decode())
    assert pages[0].startswith("# Master Services Agreement")
    assert any(p.startswith("## §5 Fees") for p in pages)


def test_clean_drops_invented_clauses_and_fee():
    pages = extraction.pages_from_markdown(CLOUDHOST.decode())
    raw = {
        "counterparty": "CloudHost GmbH", "role": "supplier", "title": "MSA", "start_date": "2025-09-01",
        "monthly_fee": 12345, "fixed_price_until": "31.08.2027", "price_change_notice_days": "90",
        "max_annual_increase_pct": None, "payment_terms_days": None, "changes_require_written_agreement": False,
        "clauses": [
            {"id": "§5.2", "page": 6, "title": "Price guarantee",
             "text": "**§5.2 Price guarantee.** The fees under §5.1 are fixed for a period of 24 months from the commencement date"},
            {"id": "§99", "page": 1, "title": "Invented", "text": "The Provider may raise prices at any time without notice."},
        ],
    }
    ex = extraction.clean(raw, pages, "Müller Feinmechanik GmbH")
    assert ex["monthly_fee"] is None  # 12345 is not in the document
    assert ex["fixed_price_until"] is None  # not ISO
    assert ex["price_change_notice_days"] == 90
    assert [c["id"] for c in ex["clauses"]] == ["§5.2"]
    assert ex["clauses"][0]["text"].startswith("The fees under")
    assert len(ex["warnings"]) == 3


def test_benchmark_compare_on_truth_is_perfect():
    for t in data.index_contracts():
        role = "customer" if "customer" in t else "supplier"
        ex = {**{k: t.get(k) for k in extraction.SCHEMA["properties"]}, "role": role}
        assert all(r["ok"] for r in extraction.compare(ex, t)), t["id"]


def test_upload_used_by_legal_agent():
    client.post("/api/reset")
    r = client.post("/api/contracts/upload", files={"file": ("cloudhost_msa.md", CLOUDHOST, "text/markdown")})
    assert r.status_code == 200, r.text
    c = r.json()["contract"]
    assert c["origin"] == "uploaded" and c["supplier"] == "CloudHost GmbH"
    assert c["fixed_price_until"] == "2027-08-31"

    listed = client.get("/api/contracts").json()
    assert listed[0]["id"] == c["id"] and len(listed) == len(data.index_contracts()) + 1

    result = None
    with client.stream("GET", "/api/sync") as s:
        for line in s.iter_lines():
            if line.startswith("data:"):
                ev = json.loads(line[5:])
                if ev["type"] == "result":
                    result = ev["dashboard"]
    f = next(f for f in result["findings"] if f["extraction"]["party"] == "CloudHost GmbH")
    assert f["contract"]["verdict"] == "violates"
    assert f["contract"]["contract"]["origin"] == "uploaded"

    # uploading the same party again replaces the earlier upload
    r2 = client.post("/api/contracts/upload", files={"file": ("cloudhost_msa.md", CLOUDHOST, "text/markdown")})
    assert r2.json()["contract"]["id"] == c["id"]
    assert len(data.uploaded) == 1

    assert client.delete(f"/api/contracts/{c['id']}").status_code == 200
    assert data.uploaded == []
    assert client.delete("/api/contracts/C-001").status_code == 404
    client.post("/api/reset")


def test_reset_removes_uploaded_contracts():
    client.post("/api/reset")
    client.post("/api/contracts/upload", files={"file": ("cloudhost_msa.md", CLOUDHOST, "text/markdown")})
    assert len(data.uploaded) == 1
    client.post("/api/reset")
    assert data.uploaded == []
    assert all(c["origin"] == "index" for c in client.get("/api/contracts").json())


def test_upload_unknown_contract_without_model_is_rejected():
    r = client.post("/api/contracts/upload", files={"file": ("other.txt", b"Some contract text " * 10, "text/plain")})
    assert r.status_code == 422
    assert data.uploaded == []


def test_upload_empty_file():
    assert client.post("/api/contracts/upload", files={"file": ("x.pdf", b"", "application/pdf")}).status_code == 422


def test_clean_drops_implausible_values():
    pages = extraction.pages_from_markdown(CLOUDHOST.decode())
    raw = {
        "counterparty": "CloudHost GmbH", "role": "supplier", "title": "MSA", "start_date": "2025-09-01",
        "monthly_fee": None, "fixed_price_until": "2024-08-31", "price_change_notice_days": -5,
        "max_annual_increase_pct": 250, "payment_terms_days": 30, "changes_require_written_agreement": False,
        "clauses": [],
    }
    ex = extraction.clean(raw, pages)
    assert ex["fixed_price_until"] is None  # ends before the start
    assert ex["max_annual_increase_pct"] is None  # 250 % is not plausible
    assert ex["price_change_notice_days"] is None  # negative
    assert ex["payment_terms_days"] == 30  # plausible -> kept
    assert any("250" in w for w in ex["warnings"])
