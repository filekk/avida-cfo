"""Negotiator Agent – the writer.

Drafts the reply to a business partner from what the other two agents hand over:
- Legal Agent: verdict, the clause (verbatim) and the concrete violations,
- Analyst Agent: the exact figures and their effect (only to set the tone – never disclosed).
After the Legal Agent's review it revises the draft once if issues were found.

Tasks:
- reject_price       supplier increase that breaks the contract → polite but firm rejection
- payment_reminder   important customer wants to pay late → friendly request to pay on the agreed date
- ask_details        price change announced without figures → ask for the exact numbers before it applies
"""
from __future__ import annotations

from .. import data, fallback
from ..llm import llm

NAME = "Negotiator Agent"

_COMMON = (
    "Never mention the company's own cash flow, liquidity, overdraft or credit. "
    "Start with a 'Subject:' line. Sign with the owner's name and company. No placeholders, no markdown. Max 150 words. "
    "Write in English."
)

DRAFT_SYSTEM = {
    "reject_price": (
        "You are the Negotiator Agent of a small German company. Write a polite but firm email rejecting a supplier's "
        "price increase that contradicts the contract. Quote the clause word for word and mention its number. "
        "State the agreed price. " + _COMMON
    ),
    "payment_reminder": (
        "You are the Negotiator Agent of a small German company. An important customer announced that it will pay an "
        "invoice late. Write a friendly but clear email: thank them for the early notice, state the invoice number, "
        "amount and agreed due date, quote the contract clause word for word with its number, and kindly ask them to "
        "pay on the agreed date (for example with a manual payment). Keep the relationship warm, no threats. " + _COMMON
    ),
    "ask_details": (
        "You are the Negotiator Agent of a small German company. A supplier announced a price change without giving "
        "any figures. Write a short, polite email asking for the current and new monthly amount, the start date and "
        "the contractual basis, and state that the current prices apply until then. " + _COMMON
    ),
}

REVISE_SYSTEM = (
    "You are the Negotiator Agent. The Legal Agent reviewed your draft email and found issues. "
    "Rewrite the email so that every issue is fixed. Keep it short (max 150 words), polite and clear. "
    "Return only the full corrected email, starting with 'Subject:'. No placeholders, no markdown."
)


def _brief(task: str, extraction: dict, legal_result: dict, impact: dict) -> str:
    co = data.company()
    clause = legal_result.get("clause") or {}
    problems = "; ".join(c["detail"] for c in legal_result.get("checks", []) if not c["passed"])
    head = f"Sender (sign with this): {co['owner']}, {co['name']}\n"
    clause_line = f"[from Legal Agent] Clause {clause.get('id', '')} {clause.get('title', '')}: \"{clause.get('text', '')}\"\n"
    if task == "reject_price":
        return (
            head + f"Supplier: {extraction['supplier']}\n"
            f"[from Analyst Agent] Agreed price EUR {extraction['old_monthly']:,.2f}/month; announced "
            f"EUR {extraction['new_monthly']:,.2f}/month (+{extraction['increase_pct']}%) from {extraction['effective_date']}. "
            f"Impact {impact['next_12_months']:,.0f} EUR/year (internal, do not mention).\n"
            + clause_line + f"[from Legal Agent] Problems: {problems}"
        )
    if task == "payment_reminder":
        return (
            head + f"Customer: {extraction['customer']} (important long-term customer)\n"
            f"[from Analyst Agent] Invoice {extraction['invoice']} over EUR {extraction['amount']:,.2f}, due "
            f"{extraction['due_date']}; they announced payment on {extraction['new_payment_date']} "
            f"({extraction['days_late']} days late). Reason given in their email: {extraction['summary']}\n"
            + clause_line + f"[from Legal Agent] Problems: {problems}"
        )
    return (
        head + f"Supplier: {extraction['party']}\n"
        f"[from Analyst Agent] Their email: {extraction['summary']} Planned start: {extraction.get('effective_date') or 'not stated'}.\n"
        "[from Legal Agent] The email contains no figures and there is no contract on file – ask for details."
    )


def _template(task: str, extraction: dict, legal_result: dict) -> str:
    """Guaranteed to pass the Legal Agent's rule checks – used if the model is unavailable."""
    co, clause = data.company(), legal_result.get("clause")
    if task == "reject_price":
        return fallback.rejection_email(co, extraction["supplier"], extraction, clause)
    if task == "payment_reminder":
        return fallback.payment_reminder_email(co, extraction["customer"], extraction, clause)
    return fallback.ask_details_email(co, extraction["party"], extraction)


async def draft(task: str, extraction: dict, legal_result: dict, impact: dict) -> tuple[str, str]:
    fb = _template(task, extraction, legal_result)
    return await llm.text(DRAFT_SYSTEM[task], _brief(task, extraction, legal_result, impact), fb, max_tokens=450)


async def revise(task: str, previous: str, issues: list[str], extraction: dict, legal_result: dict, impact: dict) -> tuple[str, str]:
    user = (
        _brief(task, extraction, legal_result, impact)
        + "\n\nIssues found by the Legal Agent:\n" + "\n".join(f"- {i}" for i in issues)
        + f"\n\nYOUR PREVIOUS DRAFT:\n{previous}"
    )
    return await llm.text(REVISE_SYSTEM, user, _template(task, extraction, legal_result), max_tokens=450)
