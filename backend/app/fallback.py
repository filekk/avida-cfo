"""Canned answers used when the LLM is unavailable (DEMO_FALLBACK=true).

They mirror what the model is expected to return for the demo inbox, so the pitch
never depends on network luck. Results produced from here are labelled "fallback" in the UI.
"""

EXTRACTIONS = {
    "mail-001": {
        "is_price_change": True,
        "supplier": "CloudHost GmbH",
        "old_monthly": 9800.0,
        "new_monthly": 11270.0,
        "increase_pct": 15.0,
        "effective_date": "2027-01-01",
        "summary": "CloudHost raises the monthly hosting fee by 15% from 1 January 2027.",
    },
    "mail-002": {
        "is_price_change": True,
        "supplier": "PaperPro GmbH",
        "old_monthly": 1200.0,
        "new_monthly": 1242.0,
        "increase_pct": 3.5,
        "effective_date": "2027-01-01",
        "summary": "PaperPro applies its yearly 3.5% inflation adjustment from 1 January 2027.",
    },
}

NOT_PRICE_CHANGE = {
    "is_price_change": False,
    "supplier": "",
    "old_monthly": 0.0,
    "new_monthly": 0.0,
    "increase_pct": 0.0,
    "effective_date": "",
    "summary": "Not related to prices or payments.",
}


def contract_explanation(verdict: str, supplier: str, failed: list[dict], clause: dict | None) -> dict:
    if verdict == "violates":
        reasons = " ".join(c["detail"] for c in failed)
        simple = f"Your contract with {supplier} does not allow this increase. {reasons}"
    elif verdict == "allowed":
        simple = f"Your contract with {supplier} allows this increase. It is within the agreed limits."
    else:
        simple = f"I could not find a contract with {supplier}. Please check this one yourself."
    return {
        "explanation_simple": simple,
        "clause_id": clause["id"] if clause else "",
        "quote": clause["text"] if clause else "",
    }


def rejection_email(company: dict, supplier: str, extraction: dict, clause: dict | None) -> str:
    clause_ref = f"{clause['id']} ({clause['title']})" if clause else "our agreement"
    quote = f'\n\n  "{clause["text"]}"\n' if clause else ""
    return (
        f"Subject: Re: Price adjustment from {extraction.get('effective_date', '')}\n\n"
        f"Dear {supplier} team,\n\n"
        f"thank you for your message regarding the planned price increase of {extraction['increase_pct']:.0f}% "
        f"from EUR {extraction['old_monthly']:,.2f} to EUR {extraction['new_monthly']:,.2f} per month.\n\n"
        f"Under {clause_ref} of our agreement:{quote}\n"
        f"We therefore do not accept the increase and expect to continue to be invoiced at "
        f"EUR {extraction['old_monthly']:,.2f} per month for the remainder of the guaranteed period.\n\n"
        f"Please confirm in writing.\n\n"
        f"Kind regards,\n{company['owner']}\n{company['name']}"
    )
