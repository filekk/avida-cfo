"""Liquidity Agent – forecasts cash X days ahead, quantifies the impact of each finding,
drafts the supplier reply and sizes a credit facility if the safety buffer is breached."""
from __future__ import annotations

from datetime import date, timedelta

from .. import data, fallback
from ..config import settings
from ..forecast import Adjustment, expand_items, run_forecast, size_credit_line
from ..llm import llm

DRAFT_SYSTEM = (
    "You are the Negotiation assistant of a small German company. Write a short (max 150 words), polite but firm email in English "
    "rejecting a supplier's price increase that contradicts the contract. Quote the clause word for word. "
    "Start with a 'Subject:' line. Sign with the owner's name and company. No placeholders, no markdown."
)


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
    contract_day = _payment_day(extraction["supplier"])
    payments_in_horizon = sum(
        1 for i in range(settings.forecast_days)
        if (d := today + timedelta(days=i)).day == contract_day and d >= eff
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


async def draft_rejection(extraction: dict, contract_result: dict) -> tuple[str, str]:
    co = data.company()
    clause = contract_result.get("clause")
    fb = fallback.rejection_email(co, extraction["supplier"], extraction, clause)
    user = (
        f"Company: {co['name']}, owner: {co['owner']}\n"
        f"Supplier: {extraction['supplier']}\n"
        f"Announced: {extraction['summary']} ({extraction['old_monthly']} -> {extraction['new_monthly']} EUR/month from {extraction['effective_date']})\n"
        f"Clause {clause['id']} {clause['title']}: \"{clause['text']}\"\n"
        "Problems found: " + "; ".join(c["detail"] for c in contract_result["checks"] if not c["passed"])
    )
    return await llm.text(DRAFT_SYSTEM, user, fb, max_tokens=450)


def headline(f: dict) -> str:
    """Plain-language status for the top of the dashboard (deterministic, no LLM)."""
    if not f["first_breach_date"]:
        return f"You're safe for the next {f['horizon_days']} days. Your balance stays above your safety cushion."
    d = date.fromisoformat(f["first_breach_date"])
    return (
        f"You're safe for the next {f['days_safe']} days. Around {d:%d %B} your balance drops to "
        f"{f['min_balance']:,.0f} EUR – below your safety cushion of {f['buffer']:,.0f} EUR."
    )
