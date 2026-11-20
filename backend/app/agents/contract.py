"""Contract Agent – finds the supplier contract, retrieves relevant clauses and checks the price change.

The verdict comes from explicit rules (auditable). The LLM only explains it in plain language
and picks the clause to quote.
"""
from __future__ import annotations

from datetime import date

from .. import data, fallback
from ..llm import llm

PRICE_TERMS = ("price", "fee", "increase", "adjust", "index", "notice", "fixed", "guarantee")

SYSTEM = (
    "You are the Contract Agent of a CFO assistant for a small company owner who is not a lawyer. "
    "You get contract clauses, a supplier's price change and the results of automatic rule checks. "
    "Explain in 2-3 short, friendly sentences whether the increase is allowed, and pick the single clause "
    "that matters most. Quote it word for word. Do not give legal advice beyond the contract text. Answer with JSON only."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "explanation_simple": {"type": "string"},
        "clause_id": {"type": "string"},
        "quote": {"type": "string"},
    },
    "required": ["explanation_simple", "clause_id", "quote"],
}


def find_contract(supplier: str) -> dict | None:
    s = supplier.lower()
    for c in data.contracts():
        if c["supplier"].lower() in s or s in c["supplier"].lower() or any(a in s for a in c["aliases"]):
            return c
    return None


def retrieve_clauses(contract: dict, k: int = 3) -> list[dict]:
    """Keyword retrieval – enough for a handful of contracts. Swap for ChromaDB/embeddings if it grows."""
    scored = [(sum(t in cl["text"].lower() or t in cl["title"].lower() for t in PRICE_TERMS), cl) for cl in contract["clauses"]]
    scored.sort(key=lambda x: -x[0])
    return [cl for score, cl in scored[:k] if score > 0]


def rule_checks(contract: dict, extraction: dict, received: date) -> list[dict]:
    checks = []
    eff = date.fromisoformat(extraction["effective_date"])

    if contract.get("fixed_price_until"):
        until = date.fromisoformat(contract["fixed_price_until"])
        ok = eff > until
        checks.append({
            "check": "Price guarantee period",
            "passed": ok,
            "clause_id": _clause_with(contract, "guarantee"),
            "detail": (
                f"Prices are fixed until {until:%d %b %Y}, but the increase starts on {eff:%d %b %Y}."
                if not ok else f"The price guarantee ended on {until:%d %b %Y}."
            ),
        })

    if contract.get("price_change_notice_days"):
        need = contract["price_change_notice_days"]
        given = (eff - received).days
        ok = given >= need
        checks.append({
            "check": "Notice period",
            "passed": ok,
            "clause_id": _clause_with(contract, "notice"),
            "detail": f"{given} days' notice given, {need} days required." if not ok else f"{given} days' notice given ({need} required).",
        })

    if contract.get("max_annual_increase_pct") is not None:
        cap = contract["max_annual_increase_pct"]
        ok = extraction["increase_pct"] <= cap
        checks.append({
            "check": "Maximum yearly increase",
            "passed": ok,
            "clause_id": _clause_with(contract, "index"),
            "detail": f"Increase of {extraction['increase_pct']}% vs. allowed maximum of {cap}%.",
        })
    return checks


def _clause_with(contract: dict, word: str) -> str:
    for cl in contract["clauses"]:
        if word in cl["text"].lower() or word in cl["title"].lower():
            return cl["id"]
    return ""


async def check_price_change(extraction: dict, received: str) -> tuple[dict, str]:
    contract = find_contract(extraction["supplier"])
    if not contract:
        fb = fallback.contract_explanation("unclear", extraction["supplier"], [], None)
        return {"verdict": "unclear", "contract": None, "checks": [], "clauses": [], **fb}, "rules"

    clauses = retrieve_clauses(contract)
    checks = rule_checks(contract, extraction, date.fromisoformat(received))
    failed = [c for c in checks if not c["passed"]]
    verdict = "violates" if failed else "allowed"

    key_id = failed[0]["clause_id"] if failed else (checks[-1]["clause_id"] if checks else "")
    key_clause = next((c for c in contract["clauses"] if c["id"] == key_id), clauses[0] if clauses else None)

    user = (
        f"Contract: {contract['title']} with {contract['supplier']}\n"
        "Clauses:\n" + "\n".join(f"- {c['id']} {c['title']}: {c['text']}" for c in clauses) + "\n\n"
        f"Announced change: {extraction['summary']} (from {extraction['old_monthly']} to {extraction['new_monthly']} EUR/month, "
        f"effective {extraction['effective_date']}, announced {received})\n"
        "Rule checks:\n" + "\n".join(f"- {c['check']}: {'OK' if c['passed'] else 'VIOLATED'} – {c['detail']}" for c in checks) + "\n"
        f"Overall verdict (fixed, do not change it): {verdict.upper()}"
    )
    fb = fallback.contract_explanation(verdict, contract["supplier"], failed, key_clause)
    expl, source = await llm.json(SYSTEM, user, SCHEMA, fb)

    # Guard against hallucinated quotes: the quote must exist in the contract, else use the real clause.
    real = next((c for c in contract["clauses"] if c["id"] == expl.get("clause_id")), None)
    quote = expl.get("quote", "").strip().strip('"“”„')
    if not real or not quote or quote[:40] not in real["text"]:
        expl["clause_id"], expl["quote"] = fb["clause_id"], fb["quote"]
        real = key_clause

    return {
        "verdict": verdict,
        "contract": {k: contract[k] for k in ("id", "supplier", "title", "file", "start_date", "fixed_price_until")},
        "clause": real,
        "checks": checks,
        "clauses": clauses,
        **expl,
    }, source
