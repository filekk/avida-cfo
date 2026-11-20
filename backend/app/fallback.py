"""Canned answers used when the LLM is unavailable (DEMO_FALLBACK=true).

They mirror what the model is expected to return for the demo inbox, so the pitch
never depends on network luck. Results produced from here are labelled "fallback" in the UI.
The extractions are in the RAW model format (same JSON schema as the LLM answer) – the
Analyst Agent validates both the same way.
"""
from datetime import date

_EMPTY = {
    "kind": "other", "counterparty": "", "summary": "",
    "old_monthly": 0.0, "new_monthly": 0.0, "effective_date": "",
    "invoice": "", "amount": 0.0, "due_date": "", "new_payment_date": "",
}

EXTRACTIONS = {
    "mail-001": {**_EMPTY, "kind": "price_change", "counterparty": "CloudHost GmbH",
                 "old_monthly": 9800.0, "new_monthly": 11270.0, "effective_date": "2027-01-01",
                 "summary": "CloudHost raises the monthly hosting fee by 15% from 1 January 2027."},
    "mail-002": {**_EMPTY, "kind": "price_change", "counterparty": "PaperPro GmbH",
                 "old_monthly": 1200.0, "new_monthly": 1242.0, "effective_date": "2027-01-01",
                 "summary": "PaperPro applies its yearly 3.5% inflation adjustment from 1 January 2027."},
    "mail-004": {**_EMPTY, "kind": "payment_delay", "counterparty": "Bauer Maschinenbau AG",
                 "invoice": "RE-2026-1187", "amount": 38000.0, "due_date": "2027-01-05", "new_payment_date": "2027-02-04",
                 "summary": "Bauer will pay invoice RE-2026-1187 a month late because of an SAP migration."},
    "mail-005": {**_EMPTY, "kind": "price_change", "counterparty": "Stahlhandel Nord GmbH",
                 "old_monthly": 14000.0, "new_monthly": 14840.0, "effective_date": "2027-01-01",
                 "summary": "Stahlhandel Nord raises material prices by 6% from 1 January 2027."},
    "mail-006": {**_EMPTY, "kind": "price_change", "counterparty": "IT-Service Kraus e.K.",
                 "effective_date": "2027-01-01",
                 "summary": "IT-Service Kraus announces higher prices from 2027 without giving figures."},
}

NOT_RELEVANT = {**_EMPTY, "summary": "Not related to prices or payments."}


def contract_explanation(verdict: str, party: str, failed: list[dict], clause: dict | None, kind: str = "price_change",
                         figures: bool = True) -> dict:
    if not figures:
        simple = (f"{party} announces a change but gives no figures, so I cannot check it. "
                  "Ask for the exact new price before it takes effect.")
    elif verdict == "violates":
        reasons = " ".join(c["detail"] for c in failed)
        what = "paying later" if kind == "payment_delay" else "this increase"
        simple = f"Your contract with {party} does not allow {what}. {reasons}"
    elif verdict == "allowed":
        simple = f"Your contract with {party} allows this change. It is within the agreed limits."
    else:
        simple = f"I could not find a contract with {party}. Please check this one yourself."
    return {
        "explanation_simple": simple,
        "clause_id": clause["id"] if clause else "",
        "quote": clause["text"] if clause else "",
    }


def _clause_block(clause: dict | None) -> tuple[str, str]:
    ref = f"{clause['id']} ({clause['title']})" if clause else "our agreement"
    quote = f'\n\n  "{clause["text"]}"\n' if clause else ""
    return ref, quote


def _sign(company: dict) -> str:
    return f"Kind regards,\n{company['owner']}\n{company['name']}"


def _long_date(iso: str) -> str:
    try:
        return f"{date.fromisoformat(iso):%d %B %Y}"
    except ValueError:
        return iso


def rejection_email(company: dict, supplier: str, extraction: dict, clause: dict | None) -> str:
    ref, quote = _clause_block(clause)
    return (
        f"Subject: Re: Price adjustment from {_long_date(extraction.get('effective_date', ''))}\n\n"
        f"Dear {supplier} team,\n\n"
        f"thank you for your message regarding the planned price increase of {extraction['increase_pct']:.0f}% "
        f"from EUR {extraction['old_monthly']:,.2f} to EUR {extraction['new_monthly']:,.2f} per month.\n\n"
        f"Under {ref} of our agreement:{quote}\n"
        f"We therefore do not accept the increase and expect to continue to be invoiced at "
        f"EUR {extraction['old_monthly']:,.2f} per month for the remainder of the guaranteed period.\n\n"
        f"Please confirm in writing.\n\n{_sign(company)}"
    )


def payment_reminder_email(company: dict, customer: str, extraction: dict, clause: dict | None) -> str:
    ref, quote = _clause_block(clause)
    return (
        f"Subject: Re: Payment run postponed – invoice {extraction['invoice']}\n\n"
        f"Dear {customer} team,\n\n"
        f"thank you for letting us know about your system migration in good time.\n\n"
        f"Our invoice {extraction['invoice']} over EUR {extraction['amount']:,.2f} is due on "
        f"{_long_date(extraction['due_date'])}. Under {ref} of our framework agreement:{quote}\n"
        f"We would therefore kindly ask you to pay this invoice on the agreed due date, for example with a "
        f"manual payment before the migration starts.\n\n"
        f"Please let us know how you would like to proceed. We value our cooperation very much.\n\n{_sign(company)}"
    )


def ask_details_email(company: dict, supplier: str, extraction: dict) -> str:
    when = f" from {_long_date(extraction['effective_date'])}" if extraction.get("effective_date") else ""
    return (
        f"Subject: Re: Your price change{when}\n\n"
        f"Dear {supplier} team,\n\n"
        f"thank you for informing us about the planned price change{when}.\n\n"
        f"To review it, please send us the current and the new monthly amount for our contract, the date from which "
        f"the new amount applies and the contractual basis for the change.\n\n"
        f"Until we have received and checked these details, we assume that the current prices continue to apply.\n\n"
        f"{_sign(company)}"
    )
