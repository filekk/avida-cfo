"""Coordinates the three collaborating agents and streams every step as a trace event (SSE).

    Analyst ──changes──► Legal ──verdicts──► Analyst (forecast, impact, credit)
       │                   │                     │
       └──figures──► Negotiator ◄──clause────────┘        (one negotiation per finding, all in parallel)
                         │  draft
                         ▼
                       Legal (review) ──issues──► Negotiator (revise once)
                         │
                         ▼
                       Owner (approve / reject)
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, Awaitable, Callable

from . import data
from .agents import analyst, legal, negotiator
from .config import settings
from .state import ANALYZED, APPROVAL, RECOMMENDATION, store

AGENTS = [
    {"name": analyst.NAME, "role": "Analyst", "icon": "📊",
     "does": "Reads the inbox, forecasts your cash and explains the numbers."},
    {"name": legal.NAME, "role": "Lawyer", "icon": "⚖️",
     "does": "Checks every change against your contracts and reviews outgoing emails."},
    {"name": negotiator.NAME, "role": "Negotiator", "icon": "✉️",
     "does": "Writes the replies to suppliers and customers, based on the lawyer's findings and the analyst's numbers."},
]

A, L, N = analyst.NAME, legal.NAME, negotiator.NAME

# recommendation per (kind, verdict); anything missing → "review"
RECOMMEND = {
    ("price_change", "violates"): "reject",
    ("price_change", "allowed"): "accept",
    ("payment_delay", "violates"): "remind",
    ("payment_delay", "allowed"): "accept",
}

# which email the Negotiator writes for a finding (None = nothing to write)
def _task(f: dict) -> str | None:
    if f["recommendation"] == "reject":
        return "reject_price"
    if f["recommendation"] == "remind":
        return "payment_reminder"
    if f["recommendation"] == "review" and f["kind"] == "price_change":
        return "ask_details"
    return None


class SyncAlreadyRunning(RuntimeError):
    pass


_running = False  # one sync at a time – a second click must not wipe the first run's actions


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


# --- trace texts ------------------------------------------------------------------

def _found_line(mail: dict, ex: dict) -> str:
    if ex["kind"] == "price_change":
        return (f"Price change found: {ex['summary']}" if ex["figures_stated"]
                else f"Price change announced by {ex['party']}, but the email gives no figures – I won't guess.")
    if ex["kind"] == "payment_delay":
        return f"Late customer payment: {ex['summary']}"
    return f"Ignored: \"{mail['subject']}\" – not about prices or payments."


def _ask_line(ex: dict) -> str:
    if not ex["figures_stated"]:
        return f"{ex['party']} (no figures)"
    if ex["kind"] == "payment_delay":
        return f"{ex['party']} pays {ex['days_late']} days late"
    return f"{ex['party']} +{ex['increase_pct']}%"


def _verdict_line(ex: dict, res: dict) -> str:
    clause = f" ({res['clause_id']})" if res.get("clause_id") else ""
    if res["verdict"] == "unclear":
        why = "no figures in the email" if not ex["figures_stated"] else "no contract on file"
        return f"{ex['party']}: cannot check – {why}. Please review."
    what = "paying later" if ex["kind"] == "payment_delay" else "the increase"
    ok = "allowed" if res["verdict"] == "allowed" else "NOT allowed"
    uploaded = " (contract you uploaded, terms extracted by the model)" if (res.get("contract") or {}).get("origin") == "uploaded" else ""
    return f"{ex['party']}: {what} is {ok} by the contract{clause}{uploaded}."


# --- one negotiation (runs concurrently with the others) ---------------------------

async def _negotiate(f: dict, emit: Callable[[dict], Awaitable[None]]) -> dict:
    task, ex, res, imp = f["task"], f["extraction"], f["contract"], f["impact"]
    name = ex["party"]
    violations = " ".join(c["detail"] for c in res["checks"] if not c["passed"])

    if task == "reject_price":
        await emit(_handoff(A, N, f"{name}: agreed EUR {ex['old_monthly']:,.0f}/month, announced "
                                  f"EUR {ex['new_monthly']:,.0f}. Worth {imp['next_12_months']:,.0f} EUR/year."))
        await emit(_handoff(L, N, f"{name}: use {res['clause_id']} – {violations}"))
    elif task == "payment_reminder":
        await emit(_handoff(A, N, f"{name}: invoice {ex['invoice']} (EUR {ex['amount']:,.0f}) arriving "
                                  f"{ex['days_late']} days late lowers your lowest balance by "
                                  f"{imp['lowest_balance_effect']:,.0f} EUR."))
        await emit(_handoff(L, N, f"{name}: use {res['clause_id']} – {violations}"))
    else:
        await emit(_handoff(L, N, f"{name}: no figures and no contract on file – please ask for the exact prices."))

    body, src = await negotiator.draft(task, ex, res, imp)
    await emit(_trace(N, ANALYZED, f"Draft to {name} written.", source=src))
    await emit(_handoff(N, L, f"Please review my draft to {name} before the owner sees it."))

    review, rsrc = await legal.review_draft(body, task, ex, res)
    rounds = 1
    if review["approved"]:
        ok_txt = "tone is right" if task == "ask_details" else "clause, figures and tone are right"
        await emit(_trace(L, ANALYZED, f"Draft to {name} approved – {ok_txt}.", source=rsrc))
    else:
        await emit(_trace(L, ANALYZED, f"Draft to {name}: found issues. " + " ".join(review["issues"]),
                          source=rsrc, to=N, kind="handoff"))
        body, src = await negotiator.revise(task, body, review["issues"], ex, res, imp)
        await emit(_trace(N, ANALYZED, f"Draft to {name} revised.", source=src))
        review, rsrc = await legal.review_draft(body, task, ex, res)
        rounds = 2
        await emit(_trace(L, ANALYZED, f"Revised draft to {name} approved." if review["approved"]
                          else f"Draft to {name} still not perfect – please check it before sending: "
                               + " ".join(review["issues"]), source=rsrc))
    return {"body": body, "source": src, "review": review, "rounds": rounds}


def _email_action(f: dict, n: dict) -> dict:
    ex, res, imp, mail = f["extraction"], f["contract"], f["impact"], f["email"]
    name = ex["party"]
    if f["task"] == "reject_price":
        title = f"Reject the {ex['increase_pct']:.0f}% price increase from {name}"
        why = f"{res['explanation_simple']} Saves {imp['next_12_months']:,.0f} EUR over 12 months."
        savings = imp["next_12_months"]
    elif f["task"] == "payment_reminder":
        title = f"Ask {name} to pay invoice {ex['invoice']} on time"
        why = (f"{res['explanation_simple']} If they pay on the agreed date, your lowest balance is "
               f"{imp['lowest_balance_effect']:,.0f} EUR higher.")
        savings = 0.0
    else:
        title = f"Ask {name} for the exact new prices"
        why = res["explanation_simple"]
        savings = 0.0
    return store.add_action(
        type="send_email",
        agent=N,
        reviewed_by=L,
        finding_id=f["id"],
        title=title,
        why=why,
        savings_12m=savings,
        payload={"to": mail["from"], "body": n["body"]},
        review={"approved": n["review"]["approved"], "issues": n["review"]["issues"], "rounds": n["rounds"]},
        source=n["source"],
    )


# --- the pipeline -------------------------------------------------------------------

async def run_pipeline() -> AsyncIterator[dict]:
    global _running
    if _running:
        raise SyncAlreadyRunning("A check is already running – please wait for it to finish.")
    _running = True
    background: list[asyncio.Task] = []
    try:
        async for ev in _pipeline(background):
            yield ev
    finally:
        # Client disconnected or error: don't leave LLM calls running in the background.
        for t in background:
            t.cancel()
        _running = False


async def _pipeline(background: list[asyncio.Task]) -> AsyncIterator[dict]:
    store.reset()
    store.log("sync_started")

    # 1) Analyst reads the inbox ---------------------------------------------------
    mails = data.inbox()
    yield _trace(A, ANALYZED, f"Reading {len(mails)} new emails…")
    await _pause()
    # All emails go to vLLM at once – it batches them.
    read = await asyncio.gather(*(analyst.read_email(m) for m in mails))
    relevant = []
    for mail, (ex, src) in zip(mails, read):
        if ex["kind"] != "other":
            relevant.append((mail, ex))
        yield _trace(A, ANALYZED, _found_line(mail, ex), source=src, email_id=mail["id"])
        await _pause()

    if relevant:
        yield _handoff(A, L, f"Please check {len(relevant)} change(s) against the contracts: "
                             + ", ".join(_ask_line(ex) for _, ex in relevant) + ".")
        await _pause()

    # 2) Legal checks the contracts -----------------------------------------------
    results = await asyncio.gather(*(legal.check(ex, mail["received"]) for mail, ex in relevant))
    checked = []
    for (mail, ex), (res, src) in zip(relevant, results):
        checked.append((mail, ex, res))
        yield _trace(L, RECOMMENDATION, _verdict_line(ex, res), source=src)
        await _pause()

    if checked:
        yield _handoff(L, A, "Verdicts: " + "; ".join(f"{ex['party']} → {res['verdict']}" for _, ex, res in checked) + ".")
        await _pause()

    # 3) Analyst: forecast, impact, credit (deterministic) ---------------------------
    yield _trace(A, ANALYZED, f"Forecasting your cash for the next {settings.forecast_days} days in 3 scenarios…")
    prices = [(ex, res) for _, ex, res in checked if ex["kind"] == "price_change" and ex["figures_stated"]]
    delays = [analyst.to_delay(ex) for _, ex, _ in checked if ex["kind"] == "payment_delay" and ex["figures_stated"]]
    all_adj = [analyst.to_adjustment(ex) for ex, _ in prices]
    # Prudent planning: only increases that break the contract are left out; late payments are assumed to happen.
    plan_adj = [analyst.to_adjustment(ex) for ex, res in prices if res["verdict"] != "violates"]
    scenarios = {
        "current": analyst.forecast([]),
        "if_accepted": analyst.forecast(all_adj, delays),
        "recommended": analyst.forecast(plan_adj, delays),
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
        imp = (analyst.delay_impact(ex, plan_adj, delays) if ex["kind"] == "payment_delay" and ex["figures_stated"]
               else analyst.impact(ex) if ex["kind"] == "price_change"
               else {"monthly": 0.0, "in_horizon": 0.0, "next_12_months": 0.0, "calculation": "No figures in the email."})
        f = {"id": mail["id"], "kind": ex["kind"], "email": mail, "extraction": ex, "contract": res, "impact": imp,
             "recommendation": RECOMMEND.get((ex["kind"], res["verdict"]), "review")}
        f["task"] = _task(f)
        findings.append(f)
    credit = analyst.credit_proposal(rec)

    # The briefing (LLM) runs in the background while the Negotiator works.
    briefing_task = asyncio.create_task(analyst.briefing(scenarios, findings, credit))
    background.append(briefing_task)

    # 4) Negotiator drafts, Legal reviews – one negotiation per finding, all in parallel ----
    to_write = [f for f in findings if f["task"]]
    queue: asyncio.Queue = asyncio.Queue()

    async def run(f: dict) -> dict:
        try:
            return await _negotiate(f, queue.put)
        finally:
            await queue.put(None)  # "this negotiation is done"

    tasks = [asyncio.create_task(run(f)) for f in to_write]
    background.extend(tasks)
    remaining = len(tasks)
    while remaining:
        ev = await queue.get()
        if ev is None:
            remaining -= 1
            continue
        yield ev
        await _pause()

    # Actions are created in inbox order, so ids are stable between runs.
    for f, t in zip(to_write, tasks):
        action = _email_action(f, t.result())
        f["action_id"] = action["id"]
        yield _trace(N, APPROVAL, f"Waiting for your approval: {action['title']}.", source=action["source"])

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
