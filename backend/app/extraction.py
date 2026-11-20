"""Contract extraction – one piece of code for two places.

* **Backend (runtime):** the owner uploads a contract (PDF / Markdown / text), Granite on vLLM extracts the
  commercial terms live (JSON schema, guided decoding), and the Legal Agent uses them from then on.
* **Jupyter notebook on OpenShift AI (evaluation):** `notebooks/contract_extraction.ipynb` imports THIS module,
  runs it over the demo contracts and benchmarks it against the hand-labelled `contracts_index.json`.

So the accuracy number shown in the notebook is the accuracy of exactly the code the app runs.

Pure Python on purpose: no FastAPI, no app settings – only `pypdf` (for PDFs) and an OpenAI-compatible client.
"""
from __future__ import annotations

import io
import re
from datetime import date

# --- 1) Document -> pages -------------------------------------------------------------


def pages_from_markdown(text: str) -> list[str]:
    """Markdown/text contract -> 'pages' (one per '## ' section, the header block is page 1)."""
    text = text.replace("\r\n", "\n").strip()
    parts = text.split("\n## ")
    return [("## " + p if i else p).strip() for i, p in enumerate(parts) if p.strip()]


def pages_from_pdf(content: bytes) -> list[str]:
    from pypdf import PdfReader  # imported lazily: only needed for PDFs

    reader = PdfReader(io.BytesIO(content))
    return [t for t in ((p.extract_text() or "").strip() for p in reader.pages) if t]


def pages_from_upload(filename: str, content: bytes) -> list[str]:
    name = (filename or "").lower()
    if name.endswith(".pdf") or content[:5] == b"%PDF-":
        return pages_from_pdf(content)
    return pages_from_markdown(content.decode("utf-8", errors="replace"))


def document_text(pages: list[str]) -> str:
    return "\n\n".join(f"[page {i + 1}]\n{t}" for i, t in enumerate(pages))


# --- 2) What the model must return -------------------------------------------------

SCHEMA = {
    "type": "object",
    "properties": {
        "counterparty": {"type": "string"},
        "role": {"type": "string", "enum": ["supplier", "customer"]},
        "title": {"type": "string"},
        "start_date": {"type": "string"},
        "monthly_fee": {"type": ["number", "null"]},
        "fixed_price_until": {"type": ["string", "null"]},
        "price_change_notice_days": {"type": ["integer", "null"]},
        "max_annual_increase_pct": {"type": ["number", "null"]},
        "payment_terms_days": {"type": ["integer", "null"]},
        "changes_require_written_agreement": {"type": "boolean"},
        "clauses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "page": {"type": "integer"},
                    "title": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["id", "page", "title", "text"],
            },
        },
    },
    "required": [
        "counterparty", "role", "title", "start_date", "monthly_fee", "fixed_price_until",
        "price_change_notice_days", "max_annual_increase_pct", "payment_terms_days",
        "changes_require_written_agreement", "clauses",
    ],
}

# Fields the Legal Agent's rules read – these are what the benchmark scores.
SUPPLIER_FIELDS = ["start_date", "monthly_fee", "fixed_price_until", "price_change_notice_days", "max_annual_increase_pct"]
CUSTOMER_FIELDS = ["start_date", "payment_terms_days", "changes_require_written_agreement"]


def system_prompt(own_company: str) -> str:
    return (
        f"You extract key commercial terms from a contract of the small company '{own_company}'. "
        "counterparty = the OTHER party's company name (never our company). "
        "role = 'supplier' if the other party delivers goods/services to us, 'customer' if we deliver to them. "
        "Dates as YYYY-MM-DD. monthly_fee = recurring monthly net amount in EUR, else null. "
        "fixed_price_until = last day of any price guarantee (e.g. 24 months from 1 September 2025 -> 2027-08-31), else null. "
        "Notice periods in days (3 months = 90, 6 weeks = 42). max_annual_increase_pct = yearly cap on price increases, else null. "
        "payment_terms_days = days until invoices must be paid, else null. "
        "changes_require_written_agreement = true only if payment dates may only be changed by written agreement. "
        "Only include clauses about fees, prices, indexation, notice, payment or term; copy their text verbatim "
        "(without the bold heading) and give the page number and the clause number like §5.2. JSON only."
    )


# --- 3) Cleaning: never trust the model blindly ------------------------------------


def _iso(v) -> str | None:
    try:
        return date.fromisoformat(str(v or "")[:10]).isoformat()
    except ValueError:
        return None


def _num(v) -> float | None:
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def _int(v) -> int | None:
    n = _num(v)
    return None if n is None else int(round(n))


def _squash(s: str) -> str:
    return re.sub(r"[\s*_]+", " ", s).strip().lower()


def _fee_in_text(fee: float, text: str) -> bool:
    """The monthly fee must literally appear in the contract (9,800.00 / 9.800,00 / 9800)."""
    digits = re.sub(r"[^0-9]", "", text)
    whole = f"{fee:.0f}"
    return whole in digits


def sanity_check(out: dict) -> list[str]:
    """
    A function to perform sanity checks on the input dictionary (out)
    and adjust implausible values, returning a list of warning messages.
    """
    warnings = []

    # Warning 1: Price guarantee
    if out.get('start_date') and out.get('fixed_price_until') \
            and out['fixed_price_until'] < out['start_date']:
        warnings.append("Price guarantee ends before the contract starts – ignored.")
        out['fixed_price_until'] = None

    # Warning 2: Max annual increase percentage
    value = out.get('max_annual_increase_pct')
    if value is not None and not (0 <= value <= 100):
        warnings.append(f"Yearly price increase cap of {value}% is not plausible – ignored.")
        out['max_annual_increase_pct'] = None

    # Warning 3: Days for price change notice and payment terms
    for days_name in ('price_change_notice_days', 'payment_terms_days'):
        value = out.get(days_name)
        if value is not None and not (0 <= value <= 730):
            warnings.append(f"'{days_name}' of {value} days is not plausible – ignored.")
            out[days_name] = None

    return warnings


def clean(raw: dict, pages: list[str], own_company: str = "") -> dict:
    """Normalise the model output and attach `warnings` the owner should look at before trusting it.

    * dates must parse, numbers must be numbers
    * the monthly fee must appear in the document
    * every clause quote must exist verbatim in the document (else it is dropped)
    * our own company is never the counterparty
    """
    full = _squash("\n".join(pages))
    warnings: list[str] = []

    party = str(raw.get("counterparty") or "").split(",")[0].strip()  # "Bauer AG, Darmstadt" -> "Bauer AG"
    if own_company and party and _squash(own_company) in _squash(party):
        warnings.append("The model named our own company as the other party – please check.")
    role = raw.get("role") if raw.get("role") in ("supplier", "customer") else "supplier"

    out: dict = {
        "counterparty": party,
        "role": role,
        "title": str(raw.get("title") or "").strip(),
        "start_date": _iso(raw.get("start_date")),
        "monthly_fee": _num(raw.get("monthly_fee")),
        "fixed_price_until": _iso(raw.get("fixed_price_until")),
        "price_change_notice_days": _int(raw.get("price_change_notice_days")),
        "max_annual_increase_pct": _num(raw.get("max_annual_increase_pct")),
        "payment_terms_days": _int(raw.get("payment_terms_days")),
        "changes_require_written_agreement": bool(raw.get("changes_require_written_agreement")),
    }
    for f in ("start_date", "fixed_price_until"):
        if raw.get(f) and not out[f]:
            warnings.append(f"Could not read the date in '{f}' ({raw.get(f)!r}).")
    if out["monthly_fee"] is not None and not _fee_in_text(out["monthly_fee"], "\n".join(pages)):
        warnings.append(f"Monthly fee EUR {out['monthly_fee']:,.2f} does not appear in the document – ignored.")
        out["monthly_fee"] = None
    warnings.extend(sanity_check(out))

    clauses, dropped = [], 0
    for cl in raw.get("clauses") or []:
        text = str(cl.get("text") or "").strip().strip('"“”„')
        text = re.sub(r"^\*\*.*?\*\*\s*", "", text)  # model sometimes keeps the bold heading
        if len(text) < 15 or _squash(text)[:60] not in full:
            dropped += 1
            continue
        page = _int(cl.get("page")) or 1
        clauses.append({
            "id": str(cl.get("id") or f"§{len(clauses) + 1}").strip(),
            "page": min(max(page, 1), max(len(pages), 1)),
            "title": str(cl.get("title") or "").strip().rstrip("."),
            "text": text,
        })
    if dropped:
        warnings.append(f"{dropped} clause quote(s) were not found word for word in the document and were dropped.")
    if not clauses:
        warnings.append("No relevant clauses found – the Legal Agent will not be able to quote this contract.")
    out["clauses"] = clauses
    out["warnings"] = warnings
    return out


# --- 4) Shape used by the Legal Agent (contracts_index.json entry) -----------------


def aliases_for(name: str) -> list[str]:
    base = re.sub(r"\b(gmbh|ag|kg|ug|se|ltd|inc|co|llc|e\.k\.|ohg)\b\.?", "", name, flags=re.I)
    base = re.sub(r"[^\w\s-]", " ", base).strip().lower()
    base = re.sub(r"\s+", " ", base)
    out = [a for a in {base, base.split(" ")[0] if base else ""} if len(a) >= 4]
    return sorted(out, key=len, reverse=True)


def to_index_entry(ex: dict, contract_id: str, file: str, aliases: list[str] | None = None) -> dict:
    """Turn a cleaned extraction into the structure `contracts_index.json` uses."""
    entry: dict = {"id": contract_id, ex["role"]: ex["counterparty"],
                   "aliases": aliases or aliases_for(ex["counterparty"]),
                   "title": ex["title"], "file": file, "start_date": ex["start_date"]}
    if ex["role"] == "supplier":
        for f in ("monthly_fee", "fixed_price_until", "price_change_notice_days", "max_annual_increase_pct"):
            entry[f] = ex[f]
    else:
        entry["payment_terms_days"] = ex["payment_terms_days"]
        entry["changes_require_written_agreement"] = ex["changes_require_written_agreement"]
    entry["clauses"] = ex["clauses"]
    return entry


# --- 5) Calling the model (sync client for the notebook; the backend uses app.llm) ---


def request_kwargs(model: str, pages: list[str], own_company: str) -> dict:
    return {
        "model": model,
        "temperature": 0,
        "max_tokens": 1500,
        "messages": [
            {"role": "system", "content": system_prompt(own_company)},
            {"role": "user", "content": document_text(pages)},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "contract", "schema": SCHEMA}},
    }


def extract_sync(client, model: str, pages: list[str], own_company: str) -> dict:
    """For the notebook: `client` is an `openai.OpenAI` pointed at vLLM."""
    import json

    r = client.chat.completions.create(**request_kwargs(model, pages, own_company))
    return clean(json.loads(r.choices[0].message.content), pages, own_company)


# --- 6) Benchmark (notebook) -------------------------------------------------------


def party_of(entry: dict) -> str:
    return entry.get("supplier") or entry.get("customer") or entry.get("counterparty") or ""


def match_truth(name: str, truth: list[dict]) -> dict | None:
    s = name.lower()
    for t in truth:
        if party_of(t).lower() in s or s in party_of(t).lower() or any(a in s for a in t.get("aliases", [])):
            return t
    return None


def compare(ex: dict, truth_entry: dict) -> list[dict]:
    role = "customer" if "customer" in truth_entry else "supplier"
    fields = CUSTOMER_FIELDS if role == "customer" else SUPPLIER_FIELDS
    rows = [{"party": party_of(truth_entry), "field": "role", "expected": role, "got": ex.get("role"),
             "ok": ex.get("role") == role}]
    for f in fields:
        exp, got = truth_entry.get(f), ex.get(f)
        ok = (exp == got) if not isinstance(exp, float) or got is None else abs(exp - got) < 1e-6
        rows.append({"party": party_of(truth_entry), "field": f, "expected": exp, "got": got, "ok": bool(ok)})
    want = {c["id"] for c in truth_entry.get("clauses", [])}
    got_ids = {c["id"] for c in ex.get("clauses", [])}
    rows.append({"party": party_of(truth_entry), "field": "clauses found", "expected": len(want),
                 "got": len(want & got_ids), "ok": want <= got_ids})
    return rows
