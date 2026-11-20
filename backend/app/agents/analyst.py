"""Analyst Agent – the numbers person.

1. Reads the inbox and extracts price changes as structured data (LLM).
2. Forecasts cash 90 days ahead in three scenarios, quantifies each change, sizes a credit line
   (deterministic – the LLM never does arithmetic).
3. Writes an analytical briefing for the owner from those numbers (LLM).
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from .. import data, fallback
from ..config import settings
from ..forecast import Adjustment, expand_items, run_forecast, size_credit_line
from ..llm import llm

NAME = "Analyst Agent"

# --- 1) Inbox -------------------------------------------------------------------

EXTRACT_SYSTEM = (
    "You are the Analyst Agent of a CFO assistant for a small German company. "
    "Read one email and decide whether a supplier announces a change of a recurring price. "
    "Extract the numbers exactly as written in the email. Amounts are monthly net EUR. "
    "The supplier is the company name only (e.g. 'CloudHost GmbH', not a department). "
    "Dates in ISO format YYYY-MM-DD. If the email is not about a price change, set is_price_change to false "
    "and leave the other fields empty or 0. The summary is at most 15 words. Answer with JSON only."
)

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "is_price_change": {"type": "boolean"},
        "supplier": {"type": "string"},
        "old_monthly": {"type": "number"},
        "new_monthly": {"type": "number"},
        "increase_pct": {"type": "number"},
        "effective_date": {"type": "string"},
        "summary": {"type": "string", "description": "Max 15 words, plain language, e.g. 'CloudHost raises hosting by 15% from 1 Jan 2027.'"},
    },
    "required": ["is_price_change", "supplier", "old_monthly", "new_monthly", "increase_pct", "effective_date", "summary"],
}


async def read_email(email: dict) -> tuple[dict, str]:
    user = f"From: {email['from_name']} <{email['from']}>\nSubject: {email['subject']}\nDate: {email['received']}\n\n{email['body']}"
    fb = fallback.EXTRACTIONS.get(email["id"], fallback.NOT_PRICE_CHANGE)
    result, source = await llm.json(EXTRACT_SYSTEM, user, EXTRACT_SCHEMA, fb)
    return _sanitize(result), source


def _sanitize(r: dict) -> dict:
    """Never trust model arithmetic: recompute the percentage from the two prices."""
    old, new = float(r.get("old_monthly") or 0), float(r.get("new_monthly") or 0)
    if r.get("is_price_change") and old > 0 and new > 0:
        r["increase_pct"] = round((new - old) / old * 100, 2)
        r["monthly_delta"] = round(new - old, 2)
    else:
        r["is_price_change"] = bool(r.get("is_price_change")) and old > 0 and new > 0
        r["monthly_delta"] = 0.0
    return r


# --- 2) Numbers (deterministic) -----------------------------------------------------


def forecast(adjustments: list[Adjustment]) -> dict:
    today = settings.today()
    co = data.company()
    items = expand_items(data.cashflows(), today, settings.forecast_days, adjustments)
    f = run_forecast(data.start_balance(), items, today, settings.forecast_days, co["safety_buffer"])
    f["largest_outflows"] = [i.to_dict() for i in sorted(items, key=lambda i: i.amount)[:5]]
    return f


def to_adjustment(extraction: dict) -> Adjustment:
    return Adjustment(
        counterparty=extraction["supplier"],
        monthly_delta=extraction["monthly_delta"],
        effective=date.fromisoformat(extraction["effective_date"]),
        label=f"+{extraction['increase_pct']:.1f}%",
    )


def impact(extraction: dict) -> dict:
    """How much the change costs: within the forecast horizon and over the next 12 months."""
    today = settings.today()
    eff = date.fromisoformat(extraction["effective_date"])
    horizon_end = today + timedelta(days=settings.forecast_days - 1)
    pay_day = _payment_day(extraction["supplier"])
    payments_in_horizon = sum(
        1 for i in range(settings.forecast_days)
        if (d := today + timedelta(days=i)).day == pay_day and d >= eff
    )
    delta = extraction["monthly_delta"]
    return {
        "monthly": delta,
        "in_horizon": round(delta * payments_in_horizon, 2),
        "payments_in_horizon": payments_in_horizon,
        "next_12_months": round(delta * 12, 2),
        "horizon_end": horizon_end.isoformat(),
        "calculation": f"{extraction['new_monthly']:,.2f} − {extraction['old_monthly']:,.2f} = {delta:,.2f} EUR/month × 12 = {delta * 12:,.2f} EUR/year",
    }


def _payment_day(counterparty: str) -> int:
    for r in data.cashflows()["recurring_monthly"]:
        if r["counterparty"] == counterparty:
            return r["day"]
    return 1


def credit_proposal(f: dict) -> dict | None:
    return size_credit_line(f, data.company()["credit_offer"])


def headline(f: dict) -> str:
    """Plain-language status for the top of the dashboard (deterministic, no LLM)."""
    if not f["first_breach_date"]:
        return f"You're safe for the next {f['horizon_days']} days. Your balance stays above your safety cushion."
    d = date.fromisoformat(f["first_breach_date"])
    return (
        f"You're safe for the next {f['days_safe']} days. Around {d:%d %B} your balance drops to "
        f"{f['min_balance']:,.0f} EUR – below your safety cushion of {f['buffer']:,.0f} EUR."
    )


# --- 3) Analytical briefing (LLM explains the numbers it was given) ---------------

BRIEFING_SYSTEM = (
    "You are the Analyst Agent of a CFO assistant. You get exact facts from a cash-flow forecast. "
    "Explain to a small business owner who is not a finance expert, in at most 2 short sentences, "
    "what the situation is and what following the advice changes. "
    "Copy numbers exactly as given. NEVER compute a new number. Answer with JSON only."
)

BRIEFING_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string", "description": "Max 2 short sentences."}},
    "required": ["summary"],
}


def _facts(scenarios: dict, findings: list[dict], credit: dict | None) -> list[str]:
    """Short, unambiguous facts – also shown to the owner as the analyst's key points."""
    rec, acc = scenarios["recommended"], scenarios["if_accepted"]
    facts = [
        f"If you follow the advice, your lowest balance is {rec['min_balance']:,.0f} EUR on {rec['min_date']} "
        f"(safety cushion: {rec['buffer']:,.0f} EUR).",
    ]
    if acc["min_balance"] != rec["min_balance"]:
        facts.append(f"If you accept every price increase, it drops to {acc['min_balance']:,.0f} EUR.")
    for f in findings:
        ex, imp = f["extraction"], f["impact"]
        if f["recommendation"] == "reject":
            facts.append(f"Rejecting the {ex['supplier']} increase keeps {imp['next_12_months']:,.0f} EUR per year in your company.")
        elif f["recommendation"] == "accept":
            facts.append(f"The {ex['supplier']} increase is allowed and costs {imp['next_12_months']:,.0f} EUR per year.")
    if credit:
        facts.append(
            f"A {credit['amount']:,.0f} EUR overdraft for {credit['days_needed']} days covers the gap "
            f"(max. {credit['max_interest_cost']:,.0f} EUR interest)."
        )
    return facts


async def briefing(scenarios: dict, findings: list[dict], credit: dict | None) -> tuple[dict, str]:
    """Key points are deterministic; the model only writes the 2-sentence summary."""
    facts = _facts(scenarios, findings, credit)
    rec = scenarios["recommended"]
    risk = "high" if rec["min_balance"] < 0 else "medium" if rec["first_breach_date"] else "low"
    fb = {"summary": headline(rec) + (" A short overdraft bridges the gap." if credit else "")}
    out, source = await llm.json(BRIEFING_SYSTEM, "\n".join(facts), BRIEFING_SCHEMA, fb)

    # Anti-hallucination guard: every number the model writes must come from the facts.
    summary = out.get("summary")
    if not isinstance(summary, str) or not summary.strip() or not _numbers(summary) <= _numbers(" ".join(facts)):
        summary, source = fb["summary"], "fallback"
    return {"summary": summary, "key_points": facts, "risk_level": risk}, source


def _numbers(text: str) -> set[float]:
    """All numbers in a text, normalised ('10,958' -> 10958.0, '15.0%' -> 15.0)."""
    out = set()
    for raw in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        try:
            out.add(float(raw.replace(",", "")))
        except ValueError:
            pass
    return out
