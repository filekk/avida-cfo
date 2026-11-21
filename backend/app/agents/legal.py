"""Legal Agent – the lawyer.

1. Finds the contract with the supplier / customer, retrieves relevant clauses and checks the announced change
   (price increase or later payment). The verdict comes from explicit rules (auditable); the LLM explains it
   and picks the clause to quote.
2. Reviews the Negotiator's draft email before the owner sees it (four-eyes principle).
"""
from __future__ import annotations

import re
from datetime import date

from .. import data, fallback, texts, tracing
from ..llm import llm

NAME = "Legal Agent"

PRICE_TERMS = ("price", "fee", "increase", "adjust", "index", "notice", "fixed", "guarantee")
PAYMENT_TERMS = ("payment", "payable", "invoice", "late", "interest", "agreement")

SYSTEM = (
    "You are the Legal Agent of a CFO assistant for a small company owner who is not a lawyer. "
    "You get contract clauses, a change announced by a supplier or customer (a price increase or a later payment) "
    "and the results of automatic rule checks. Explain in at most 2 short, friendly sentences whether the change is "
    "allowed, and pick the single clause that matters most. Quote it word for word. "
    "Do not give legal advice beyond the contract text. {language} Answer with JSON only."
)

LANGUAGE = {
    "en": "Write explanation_simple in English.",
    "de": "Write explanation_simple in German (formal 'Sie'). The quote stays word for word in the contract's language.",
}

SCHEMA = {
    "type": "object",
    "properties": {
        "explanation_simple": {"type": "string"},
        "clause_id": {"type": "string"},
        "quote": {"type": "string"},
    },
    "required": ["explanation_simple", "clause_id", "quote"],
}


def _party(contract: dict) -> str:
    return contract.get("supplier") or contract.get("customer") or ""


def find_contract(name: str) -> dict | None:
    s = name.lower().strip()
    if not s:  # "" is a substring of every name – never match on an empty name
        return None
    for c in data.contracts():
        p = _party(c).lower()
        if p in s or s in p or any(a in s for a in c.get("aliases", [])):
            return c
    return None


def retrieve_clauses(contract: dict, terms: tuple[str, ...] = PRICE_TERMS, k: int = 3) -> list[dict]:
    """Keyword retrieval – enough for a handful of contracts. Swap for ChromaDB/embeddings if it grows."""
    scored = [(sum(t in cl["text"].lower() or t in cl["title"].lower() for t in terms), cl) for cl in contract["clauses"]]
    scored.sort(key=lambda x: -x[0])
    return [cl for score, cl in scored[:k] if score > 0]


def rule_checks(contract: dict, extraction: dict, received: date) -> list[dict]:
    """Price change: guarantee period, notice period, yearly cap."""
    checks = []
    eff = date.fromisoformat(extraction["effective_date"])

    if contract.get("fixed_price_until"):
        until = date.fromisoformat(contract["fixed_price_until"])
        ok = eff > until
        checks.append(_check("Price guarantee period", ok, _clause_with(contract, "guarantee"),
                             lambda lg: texts.check_guarantee(until, eff, ok, lg)))

    if contract.get("price_change_notice_days"):
        need = contract["price_change_notice_days"]
        given = (eff - received).days
        ok = given >= need
        checks.append(_check("Notice period", ok, _clause_with(contract, "notice"),
                             lambda lg: texts.check_notice(given, need, ok, lg)))

    if contract.get("max_annual_increase_pct") is not None:
        cap = contract["max_annual_increase_pct"]
        ok = extraction["increase_pct"] <= cap
        checks.append(_check("Maximum yearly increase", ok, _clause_with(contract, "index"),
                             lambda lg: texts.check_cap(extraction["increase_pct"], cap, lg)))
    return checks


def payment_checks(contract: dict, extraction: dict) -> list[dict]:
    """Late customer payment: agreed due date, and whether payment dates may be changed one-sidedly."""
    due, new = date.fromisoformat(extraction["due_date"]), date.fromisoformat(extraction["new_payment_date"])
    late = (new - due).days
    inv = extraction.get("invoice") or None
    checks = [_check("Agreed payment date", late <= 0, _clause_with(contract, "payable"),
                     lambda lg: texts.check_payment(inv, due, new, late, lg))]
    if contract.get("changes_require_written_agreement"):
        checks.append(_check("Change of payment date", late <= 0, _clause_with(contract, "written agreement"),
                             texts.check_written))
    return checks


def _check(name: str, passed: bool, clause_id: str, detail) -> dict:
    """One rule check; `detail(lang)` writes the sentence (English in the fields, German in the overlay)."""
    return {"check": name, "passed": passed, "clause_id": clause_id, "detail": detail("en"),
            "i18n": texts.de(check=texts.CHECK_DE.get(name, name), detail=detail("de"))}


def _clause_with(contract: dict, word: str) -> str:
    for cl in contract["clauses"]:
        if word in cl["text"].lower() or word in cl["title"].lower():
            return cl["id"]
    return ""


def _unclear(extraction: dict, contract: dict | None, figures: bool) -> tuple[dict, str]:
    party = extraction["party"]

    def text(lg: str) -> str:
        t = texts.explanation("unclear", party, [], extraction["kind"], figures, lg)
        return t + (texts.no_contract_either(party, lg) if not contract and not figures else "")

    return {"verdict": "unclear", "contract": _contract_info(contract), "clause": None, "checks": [], "clauses": [],
            "explanation_simple": text("en"), "clause_id": "", "quote": "", "source": "rules",
            "i18n": texts.de(explanation_simple=text("de"))}, "rules"


def _contract_info(contract: dict | None) -> dict | None:
    if not contract:
        return None
    keys = ("id", "supplier", "customer", "title", "file", "start_date", "fixed_price_until", "payment_terms_days",
            "origin", "extracted_by")
    return {k: contract[k] for k in keys if k in contract}


def _normalise(extraction: dict, contract: dict) -> None:
    """The model may return 'CloudHost GmbH – Billing' etc. Use the contract's canonical name from here on,
    so the forecast matches the right cash-flow line."""
    name = _party(contract)
    extraction["party"] = name
    extraction["customer" if extraction["kind"] == "payment_delay" else "supplier"] = name


@tracing.traced("legal.check")
async def check(extraction: dict, received: str, lang: str = "en") -> tuple[dict, str]:
    """Entry point for every finding (price change or late payment). The model explains in `lang`; the other
    language gets the rule-based explanation."""
    contract = find_contract(extraction["party"])
    if contract:
        _normalise(extraction, contract)
    if not contract or not extraction["figures_stated"]:
        return _unclear(extraction, contract, extraction["figures_stated"])

    if extraction["kind"] == "payment_delay":
        checks = payment_checks(contract, extraction)
        clauses = retrieve_clauses(contract, PAYMENT_TERMS)
        change = (f"{extraction['summary']} (invoice {extraction['invoice']} over EUR {extraction['amount']:,.2f}, "
                  f"due {extraction['due_date']}, customer will pay on {extraction['new_payment_date']})")
    else:
        checks = rule_checks(contract, extraction, date.fromisoformat(received))
        clauses = retrieve_clauses(contract, PRICE_TERMS)
        change = (f"{extraction['summary']} (from {extraction['old_monthly']} to {extraction['new_monthly']} EUR/month, "
                  f"effective {extraction['effective_date']}, announced {received})")

    failed = [c for c in checks if not c["passed"]]
    verdict = "violates" if failed else "allowed"
    key_id = failed[0]["clause_id"] if failed else (checks[-1]["clause_id"] if checks else "")
    key_clause = next((c for c in contract["clauses"] if c["id"] == key_id), clauses[0] if clauses else None)

    user = (
        f"Contract: {contract['title']} with {_party(contract)}\n"
        "Clauses:\n" + "\n".join(f"- {c['id']} {c['title']}: {c['text']}" for c in clauses) + "\n\n"
        f"Announced change: {change}\n"
        "Rule checks:\n" + "\n".join(f"- {c['check']}: {'OK' if c['passed'] else 'VIOLATED'} – {c['detail']}" for c in checks) + "\n"
        f"Overall verdict (fixed, do not change it): {verdict.upper()}\n"
        + (f"Main clause (fixed – cite this clause_id and quote from it): {key_clause['id']} {key_clause['title']}"
           if key_clause else "")
    )
    fb = fallback.contract_explanation(verdict, _party(contract), failed, key_clause, extraction["kind"])
    rule_text = {lg: texts.explanation(verdict, _party(contract), failed, extraction["kind"], True, lg)
                 for lg in texts.LANGS}
    fb["explanation_simple"] = rule_text[lang]
    expl, source = await llm.json(SYSTEM.format(language=LANGUAGE[lang]), user, SCHEMA, fb)

    # The main clause is decided by the rules (first failed check: price guarantee before notice period), never by
    # the model – it may pick another clause that is also relevant but weaker. Its quote is kept only if it really
    # comes from that clause (guard against hallucinated quotes), else the clause's own text is quoted.
    real = key_clause
    quote = str(expl.get("quote", "")).strip().strip('"“”„')
    if not real or expl.get("clause_id") != real["id"] or not quote or quote[:40] not in real["text"]:
        expl["clause_id"], expl["quote"] = fb["clause_id"], fb["quote"]
    if not str(expl.get("explanation_simple", "")).strip():
        expl["explanation_simple"] = fb["explanation_simple"]

    explained = dict(rule_text)
    explained[lang] = str(expl["explanation_simple"]).strip()
    sources = {lg: "rules" for lg in texts.LANGS}
    sources[lang] = source
    return {
        "verdict": verdict,
        "contract": _contract_info(contract),
        "clause": real,
        "checks": checks,
        "clauses": clauses,
        "clause_id": expl["clause_id"],
        "quote": expl["quote"],
        "explanation_simple": explained["en"],
        "source": sources["en"],
        "i18n": texts.de(explanation_simple=explained["de"], source=sources["de"]),
    }, source


# --- Review of the Negotiator's draft ----------------------------------------------

REVIEW_SYSTEM = (
    "You are the Legal Agent reviewing an email that a colleague drafted to a business partner. "
    "Approve it unless there is a real problem: the contract clause is misquoted, amounts or dates are wrong, "
    "it claims rights the contract does not give, it reveals the company's own cash-flow problems, "
    "it is rude or threatening, or it contains placeholders like [Name]. Report at most 2 concrete issues. "
    "Answer with JSON only."
)

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["approved", "issues"],
}

INTERNAL_FINANCE = re.compile(
    r"liquidity|cash[- ]?flow|overdraft|credit line|financial difficult|bottleneck|"
    r"liquidität|engpass|überziehung|kontokorrent|zahlungsschwierig",
    re.I,
)


def _digits(s: str) -> str:
    return re.sub(r"[^0-9]", "", s)


def rule_review(draft: str, task: str, extraction: dict, legal_result: dict, lang: str = "en") -> list[str]:
    """Deterministic checks the draft must pass regardless of what the model thinks.

    task: reject_price | payment_reminder | ask_details
    lang: language of the issue texts (the Negotiator always gets English).
    """
    de = lang == "de"
    issues = []
    clause = legal_result.get("clause") or {}
    if task in ("reject_price", "payment_reminder") and clause.get("id") and clause["id"] not in draft:
        issues.append(f"Die E-Mail verweist nicht auf {clause['id']} des Vertrags." if de
                      else f"The email does not refer to {clause['id']} of the contract.")
    if task == "reject_price" and _digits(f"{extraction['old_monthly']:.0f}") not in _digits(draft):
        issues.append(f"Die E-Mail nennt den vereinbarten Preis von {texts.eur(extraction['old_monthly'], lang, 2)} nicht."
                      if de else f"The email does not state the agreed price of EUR {extraction['old_monthly']:,.2f}.")
    if task == "payment_reminder" and _digits(f"{extraction['amount']:.0f}") not in _digits(draft):
        issues.append(f"Die E-Mail nennt den Rechnungsbetrag von {texts.eur(extraction['amount'], lang, 2)} nicht."
                      if de else f"The email does not state the invoice amount of EUR {extraction['amount']:,.2f}.")
    if re.search(r"\[[^\]]{2,40}\]", draft):
        issues.append("Die E-Mail enthält noch einen Platzhalter in eckigen Klammern." if de
                      else "The email still contains a placeholder in square brackets.")
    if INTERNAL_FINANCE.search(draft):
        issues.append("Die E-Mail verrät interne Finanzinformationen." if de
                      else "The email reveals internal financial information.")
    return issues


def _review_context(task: str, extraction: dict, legal_result: dict) -> str:
    clause = legal_result.get("clause") or {}
    clause_txt = f"Contract clause {clause.get('id', '')}: \"{clause.get('text', '')}\"\n" if clause else ""
    problems = "; ".join(c["detail"] for c in legal_result.get("checks", []) if not c["passed"])
    if task == "reject_price":
        return (f"Supplier: {extraction['supplier']}. Agreed price EUR {extraction['old_monthly']:,.2f}/month, "
                f"announced EUR {extraction['new_monthly']:,.2f}/month from {extraction['effective_date']}.\n"
                f"{clause_txt}Problems with the increase: {problems}\n"
                "The email should reject the increase politely but firmly.")
    if task == "payment_reminder":
        return (f"Customer (an important one): {extraction['customer']}. Invoice {extraction['invoice']} over "
                f"EUR {extraction['amount']:,.2f}, due {extraction['due_date']}; the customer announced payment on "
                f"{extraction['new_payment_date']}.\n{clause_txt}Problems: {problems}\n"
                "The email should ask friendly but clearly for payment on the agreed date and keep the relationship warm.")
    return (f"Supplier: {extraction['party']} announced a price change without figures; there is no contract on file.\n"
            "The email should ask for the exact current and new amounts, the start date and the contractual basis.")


@tracing.traced("legal.review_draft")
async def review_draft(draft: str, task: str, extraction: dict, legal_result: dict) -> tuple[dict, str]:
    rules = rule_review(draft, task, extraction, legal_result)
    user = _review_context(task, extraction, legal_result) + f"\n\nDRAFT EMAIL:\n{draft}"
    fb = {"approved": not rules, "issues": []}
    out, source = await llm.json(REVIEW_SYSTEM, user, REVIEW_SCHEMA, fb)
    llm_issues = [i for i in out.get("issues", []) if isinstance(i, str) and i.strip()][:2] if not out.get("approved", True) else []
    issues = rules + llm_issues
    return {"approved": not issues, "issues": issues, "rule_issues": rules}, source
