"""Runs the three agents in sequence and streams every step as a trace event (SSE)."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from . import data
from .agents import contract, inbox, liquidity
from .config import settings
from .state import ANALYZED, APPROVAL, RECOMMENDATION, store


def _trace(agent: str, autonomy: str, message: str, **extra) -> dict:
    return {"type": "trace", "agent": agent, "autonomy": autonomy, "message": message, **extra}


async def _pause():
    if settings.trace_delay_s:
        await asyncio.sleep(settings.trace_delay_s)


def initial_dashboard() -> dict:
    """What the owner sees before syncing: today's forecast, no findings."""
    f = liquidity.forecast([])
    return _dashboard(scenarios={"current": f}, recommended=f, findings=[])


def _dashboard(scenarios: dict, recommended: dict, findings: list) -> dict:
    co = data.company()
    return {
        "company": {"name": co["name"], "owner": co["owner"], "currency": co["currency"]},
        "today": settings.today().isoformat(),
        "headline": liquidity.headline(recommended),
        "kpis": {
            "balance_today": data.start_balance(),
            "days_safe": recommended["days_safe"],
            "min_balance": recommended["min_balance"],
            "min_date": recommended["min_date"],
            "safety_buffer": co["safety_buffer"],
            "saved_liquidity": store.saved_liquidity,
        },
        "scenarios": scenarios,
        "findings": findings,
        "actions": list(store.actions.values()),
    }


async def run_pipeline() -> AsyncIterator[dict]:
    store.reset()
    store.log("sync_started")

    # 1) Inbox Agent ---------------------------------------------------------
    mails = data.inbox()
    yield _trace("Inbox Agent", ANALYZED, f"Reading {len(mails)} new emails…")
    await _pause()
    price_changes = []
    for mail in mails:
        ex, src = await inbox.analyze_email(mail)
        if ex["is_price_change"]:
            price_changes.append((mail, ex))
            yield _trace("Inbox Agent", ANALYZED, f"Price change found: {ex['summary']}", source=src, email_id=mail["id"])
        else:
            yield _trace("Inbox Agent", ANALYZED, f"Ignored: \"{mail['subject']}\" – not about prices.", source=src)
        await _pause()

    # 2) Contract Agent ------------------------------------------------------
    checked = []
    for mail, ex in price_changes:
        yield _trace("Contract Agent", ANALYZED, f"Looking up the contract with {ex['supplier']}…")
        await _pause()
        res, src = await contract.check_price_change(ex, mail["received"])
        checked.append((mail, ex, res))
        verdict_txt = {"violates": "NOT allowed by the contract", "allowed": "allowed by the contract", "unclear": "no contract found"}
        yield _trace(
            "Contract Agent", RECOMMENDATION,
            f"{ex['supplier']}: increase is {verdict_txt[res['verdict']]}"
            + (f" ({res['clause_id']})." if res.get("clause_id") else "."),
            source=src,
        )
        await _pause()

    # 3) Liquidity Agent -----------------------------------------------------
    yield _trace("Liquidity Agent", ANALYZED, f"Forecasting your cash flow for the next {settings.forecast_days} days…")
    await _pause()
    all_adj = [liquidity.to_adjustment(ex) for _, ex, _ in checked]
    legit_adj = [liquidity.to_adjustment(ex) for _, ex, r in checked if r["verdict"] == "allowed"]
    scenarios = {
        "current": liquidity.forecast([]),
        "if_accepted": liquidity.forecast(all_adj),
        "recommended": liquidity.forecast(legit_adj),
    }
    rec = scenarios["recommended"]
    yield _trace(
        "Liquidity Agent", ANALYZED,
        f"Lowest balance: {rec['min_balance']:,.0f} EUR on {rec['min_date']} "
        f"(if you accept all increases: {scenarios['if_accepted']['min_balance']:,.0f} EUR).",
    )
    await _pause()

    findings = []
    for mail, ex, res in checked:
        imp = liquidity.impact(ex)
        finding = {"id": mail["id"], "email": mail, "extraction": ex, "contract": res, "impact": imp}
        if res["verdict"] == "violates":
            yield _trace("Liquidity Agent", ANALYZED, f"Drafting a reply to {ex['supplier']}…")
            body, src = await liquidity.draft_rejection(ex, res)
            action = store.add_action(
                type="send_email",
                agent="Liquidity Agent",
                title=f"Reject the {ex['increase_pct']:.0f}% price increase from {ex['supplier']}",
                why=f"{res['explanation_simple']} Saves {imp['next_12_months']:,.0f} EUR over 12 months.",
                savings_12m=imp["next_12_months"],
                payload={"to": mail["from"], "body": body},
                source=src,
            )
            finding["action_id"] = action["id"]
            finding["recommendation"] = "reject"
            yield _trace("Liquidity Agent", APPROVAL, f"Waiting for your approval: {action['title']}.", source=src)
        else:
            finding["recommendation"] = "accept" if res["verdict"] == "allowed" else "review"
        findings.append(finding)
        await _pause()

    credit = liquidity.credit_proposal(rec)
    if credit:
        credit_if_accepted = liquidity.credit_proposal(scenarios["if_accepted"])
        compare = (
            f" If you accepted all price increases you would need {credit_if_accepted['amount']:,.0f} EUR."
            if credit_if_accepted and credit_if_accepted["amount"] != credit["amount"] else ""
        )
        action = store.add_action(
            type="credit_application",
            agent="Liquidity Agent",
            title=f"Arrange a {credit['amount']:,.0f} EUR overdraft facility as a safety net",
            why=(
                f"Between {credit['from']} and {credit['until']} your balance falls below your safety cushion "
                f"by up to {credit['gap']:,.0f} EUR. A short overdraft bridges the gap until customer payments arrive. "
                f"Maximum interest cost: {credit['max_interest_cost']:,.0f} EUR.{compare}"
            ),
            savings_12m=0.0,
            payload=credit,
            source="rules",
        )
        yield _trace("Liquidity Agent", APPROVAL, f"Waiting for your approval: {action['title']}.")

    dash = _dashboard(scenarios, rec, findings)
    store.dashboard = dash
    store.log("sync_finished", findings=len(findings), actions=len(store.actions))
    yield {"type": "result", "dashboard": dash}
