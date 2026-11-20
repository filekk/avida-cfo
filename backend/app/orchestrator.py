"""Coordinates the three collaborating agents and streams every step as a trace event (SSE).

    Analyst ──price changes──► Legal ──verdicts──► Analyst (forecast, impact, credit)
       │                         │                     │
       └──prices, impact──► Negotiator ◄──clause───────┘
                               │  draft
                               ▼
                             Legal (review) ──issues──► Negotiator (revise once)
                               │
                               ▼
                             Owner (approve / reject)
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from . import data
from .agents import analyst, legal, negotiator
from .config import settings
from .state import ANALYZED, APPROVAL, RECOMMENDATION, store

AGENTS = [
    {"name": analyst.NAME, "role": "Analyst", "icon": "📊",
     "does": "Reads the inbox, forecasts your cash and explains the numbers."},
    {"name": legal.NAME, "role": "Lawyer", "icon": "⚖️",
     "does": "Checks every price change against your contracts and reviews outgoing emails."},
    {"name": negotiator.NAME, "role": "Negotiator", "icon": "✉️",
     "does": "Writes the reply to the supplier, based on the lawyer's findings and the analyst's numbers."},
]

VERDICT_TXT = {"violates": "NOT allowed by the contract", "allowed": "allowed by the contract", "unclear": "no contract found"}


def _trace(agent: str, autonomy: str, message: str, **extra) -> dict:
    return {"type": "trace", "agent": agent, "autonomy": autonomy, "message": message, **extra}


def _handoff(frm: str, to: str, message: str) -> dict:
    """One agent passes its result to another – shown as an arrow in the UI."""
    return _trace(frm, ANALYZED, message, to=to, kind="handoff")


async def _pause():
    if settings.trace_delay_s:
        await asyncio.sleep(settings.trace_delay_s)


def initial_dashboard() -> dict:
    """What the owner sees before syncing: today's forecast, no findings."""
    f = analyst.forecast([])
    return _dashboard(scenarios={"current": f}, recommended=f, findings=[], analysis=None)


def _dashboard(scenarios: dict, recommended: dict, findings: list, analysis: dict | None) -> dict:
    co = data.company()
    return {
        "company": {"name": co["name"], "owner": co["owner"], "currency": co["currency"]},
        "today": settings.today().isoformat(),
        "headline": analyst.headline(recommended),
        "kpis": {
            "balance_today": data.start_balance(),
            "days_safe": recommended["days_safe"],
            "min_balance": recommended["min_balance"],
            "min_date": recommended["min_date"],
            "safety_buffer": co["safety_buffer"],
            "saved_liquidity": store.saved_liquidity,
        },
        "agents": AGENTS,
        "analysis": analysis,
        "scenarios": scenarios,
        "findings": findings,
        "actions": list(store.actions.values()),
    }


async def run_pipeline() -> AsyncIterator[dict]:
    store.reset()
    store.log("sync_started")
    A, L, N = analyst.NAME, legal.NAME, negotiator.NAME

    # 1) Analyst reads the inbox ---------------------------------------------------
    mails = data.inbox()
    yield _trace(A, ANALYZED, f"Reading {len(mails)} new emails…")
    await _pause()
    # All emails go to vLLM at once – it batches them.
    read = await asyncio.gather(*(analyst.read_email(m) for m in mails))
    price_changes = []
    for mail, (ex, src) in zip(mails, read):
        if ex["is_price_change"]:
            price_changes.append((mail, ex))
            yield _trace(A, ANALYZED, f"Price change found: {ex['summary']}", source=src, email_id=mail["id"])
        else:
            yield _trace(A, ANALYZED, f"Ignored: \"{mail['subject']}\" – not about prices.", source=src)
        await _pause()

    if price_changes:
        yield _handoff(A, L, f"Please check {len(price_changes)} price change(s): "
                             + ", ".join(f"{ex['supplier']} +{ex['increase_pct']}%" for _, ex in price_changes) + ".")
        await _pause()

    # 2) Legal checks the contracts -----------------------------------------------
    results = await asyncio.gather(*(legal.check_price_change(ex, mail["received"]) for mail, ex in price_changes))
    checked = []
    for (mail, ex), (res, src) in zip(price_changes, results):
        checked.append((mail, ex, res))
        yield _trace(
            L, RECOMMENDATION,
            f"{ex['supplier']}: increase is {VERDICT_TXT[res['verdict']]}"
            + (f" ({res['clause_id']})." if res.get("clause_id") else "."),
            source=src,
        )
        await _pause()

    if checked:
        yield _handoff(L, A, "Verdicts: " + "; ".join(f"{ex['supplier']} → {res['verdict']}" for _, ex, res in checked) + ".")
        await _pause()

    # 3) Analyst: forecast, impact, credit (deterministic) ---------------------------
    yield _trace(A, ANALYZED, f"Forecasting your cash for the next {settings.forecast_days} days in 3 scenarios…")
    all_adj = [analyst.to_adjustment(ex) for _, ex, _ in checked]
    legit_adj = [analyst.to_adjustment(ex) for _, ex, r in checked if r["verdict"] == "allowed"]
    scenarios = {
        "current": analyst.forecast([]),
        "if_accepted": analyst.forecast(all_adj),
        "recommended": analyst.forecast(legit_adj),
    }
    rec = scenarios["recommended"]
    yield _trace(
        A, ANALYZED,
        f"Lowest balance: {rec['min_balance']:,.0f} EUR on {rec['min_date']} "
        f"(if you accept all increases: {scenarios['if_accepted']['min_balance']:,.0f} EUR).",
    )
    await _pause()

    findings = []
    for mail, ex, res in checked:
        rec_txt = {"violates": "reject", "allowed": "accept"}.get(res["verdict"], "review")
        findings.append({"id": mail["id"], "email": mail, "extraction": ex, "contract": res,
                         "impact": analyst.impact(ex), "recommendation": rec_txt})
    credit = analyst.credit_proposal(rec)

    # The briefing (LLM) runs in the background while the Negotiator works.
    briefing_task = asyncio.create_task(analyst.briefing(scenarios, findings, credit))

    # 4) Negotiator drafts, Legal reviews, Negotiator revises -------------------------
    for f in (f for f in findings if f["recommendation"] == "reject"):
        ex, res, imp, mail = f["extraction"], f["contract"], f["impact"], f["email"]
        yield _handoff(A, N, f"{ex['supplier']}: agreed EUR {ex['old_monthly']:,.0f}/month, "
                             f"announced EUR {ex['new_monthly']:,.0f}. Worth {imp['next_12_months']:,.0f} EUR/year.")
        yield _handoff(L, N, f"Use {res['clause_id']} – " + "; ".join(c["detail"] for c in res["checks"] if not c["passed"]))
        await _pause()

        body, src = await negotiator.draft(ex, res, imp)
        yield _trace(N, ANALYZED, f"Draft reply to {ex['supplier']} written.", source=src)
        yield _handoff(N, L, "Please review my draft before it goes to the owner.")

        review, rsrc = await legal.review_draft(body, ex, res)
        rounds = [{"draft": body, "review": review}]
        if review["approved"]:
            yield _trace(L, ANALYZED, "Draft approved – clause quoted correctly, figures match.", source=rsrc)
        else:
            yield _trace(L, ANALYZED, "Found issues: " + " ".join(review["issues"]), source=rsrc, to=N, kind="handoff")
            body, src = await negotiator.revise(body, review["issues"], ex, res, imp)
            review, rsrc = await legal.review_draft(body, ex, res)
            rounds.append({"draft": body, "review": review})
            yield _trace(N, ANALYZED, "Draft revised.", source=src)
            yield _trace(L, ANALYZED, "Revised draft approved." if review["approved"]
                         else "Still not perfect – please check the email before sending: " + " ".join(review["issues"]),
                         source=rsrc)
        await _pause()

        action = store.add_action(
            type="send_email",
            agent=N,
            reviewed_by=L,
            title=f"Reject the {ex['increase_pct']:.0f}% price increase from {ex['supplier']}",
            why=f"{res['explanation_simple']} Saves {imp['next_12_months']:,.0f} EUR over 12 months.",
            savings_12m=imp["next_12_months"],
            payload={"to": mail["from"], "body": body},
            review={"approved": review["approved"], "issues": review["issues"], "rounds": len(rounds)},
            source=src,
        )
        f["action_id"] = action["id"]
        yield _trace(N, APPROVAL, f"Waiting for your approval: {action['title']}.", source=src)

    if credit:
        credit_if_accepted = analyst.credit_proposal(scenarios["if_accepted"])
        compare = (
            f" If you accepted all price increases you would need {credit_if_accepted['amount']:,.0f} EUR."
            if credit_if_accepted and credit_if_accepted["amount"] != credit["amount"] else ""
        )
        action = store.add_action(
            type="credit_application",
            agent=A,
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
        yield _trace(A, APPROVAL, f"Waiting for your approval: {action['title']}.")

    analysis, bsrc = await briefing_task
    analysis["source"] = bsrc
    yield _trace(A, ANALYZED, f"Briefing ready: {analysis['summary']}", source=bsrc)

    dash = _dashboard(scenarios, rec, findings, analysis)
    store.dashboard = dash
    store.log("sync_finished", findings=len(findings), actions=len(store.actions))
    yield {"type": "result", "dashboard": dash}
