"""Negotiator Agent – the writer.

Drafts the reply to the supplier from what the other two agents hand over:
- Legal Agent: verdict, the clause (verbatim) and the concrete violations,
- Analyst Agent: the exact prices and the yearly impact (only to set the tone – never disclosed).
After the Legal Agent's review it revises the draft once if issues were found.
"""
from __future__ import annotations

from .. import data, fallback
from ..llm import llm

NAME = "Negotiator Agent"

DRAFT_SYSTEM = (
    "You are the Negotiator Agent of a small German company. Write a short (max 150 words), polite but firm email "
    "in English rejecting a supplier's price increase that contradicts the contract. Quote the clause word for word "
    "and mention its number. State the agreed price. Never mention the company's own cash flow, liquidity or credit. "
    "Start with a 'Subject:' line. Sign with the owner's name and company. No placeholders, no markdown."
)

REVISE_SYSTEM = (
    "You are the Negotiator Agent. The Legal Agent reviewed your draft email and found issues. "
    "Rewrite the email so that every issue is fixed. Keep it short (max 150 words), polite and firm. "
    "Return only the full corrected email, starting with 'Subject:'. No placeholders, no markdown."
)


def _brief(extraction: dict, legal_result: dict, impact: dict) -> str:
    co = data.company()
    clause = legal_result.get("clause") or {}
    return (
        f"Company: {co['name']}, owner: {co['owner']}\n"
        f"Supplier: {extraction['supplier']}\n"
        f"[from Analyst Agent] Agreed price EUR {extraction['old_monthly']:,.2f}/month; announced "
        f"EUR {extraction['new_monthly']:,.2f}/month (+{extraction['increase_pct']}%) from {extraction['effective_date']}. "
        f"Impact {impact['next_12_months']:,.0f} EUR/year (internal, do not mention).\n"
        f"[from Legal Agent] Clause {clause.get('id', '')} {clause.get('title', '')}: \"{clause.get('text', '')}\"\n"
        "[from Legal Agent] Problems: " + "; ".join(c["detail"] for c in legal_result.get("checks", []) if not c["passed"])
    )


async def draft(extraction: dict, legal_result: dict, impact: dict) -> tuple[str, str]:
    fb = fallback.rejection_email(data.company(), extraction["supplier"], extraction, legal_result.get("clause"))
    return await llm.text(DRAFT_SYSTEM, _brief(extraction, legal_result, impact), fb, max_tokens=450)


async def revise(previous: str, issues: list[str], extraction: dict, legal_result: dict, impact: dict) -> tuple[str, str]:
    user = (
        _brief(extraction, legal_result, impact)
        + "\n\nIssues found by the Legal Agent:\n" + "\n".join(f"- {i}" for i in issues)
        + f"\n\nYOUR PREVIOUS DRAFT:\n{previous}"
    )
    # If revising fails, the template is guaranteed to pass the Legal Agent's rule checks.
    fb = fallback.rejection_email(data.company(), extraction["supplier"], extraction, legal_result.get("clause"))
    return await llm.text(REVISE_SYSTEM, user, fb, max_tokens=450)
