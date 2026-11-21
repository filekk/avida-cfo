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

Events (docs/API.md → "SSE /api/sync"):
- `phase`  – a stage starts / ends (progress bar): inbox → legal → forecast → negotiation → approval → briefing
- `trace`  – one agent step; `to` + `kind: "handoff"` = a message from one agent to another
- `result` – the new dashboard
Every `phase` / `trace` event gets `id`, `ts`, `elapsed_ms` and `phase`; steps about one email also get
`finding_id` and `partner`, so the UI can group the parallel negotiations into threads.
Trace texts are written in the `lang` of the sync; the dashboard holds both languages (see texts.py).
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import AsyncIterator, Awaitable, Callable

from . import data, decision, texts, tracing
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
for _a in AGENTS:
    _a["i18n"] = {"de": texts.AGENT_DE[_a["name"]]}

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


def _handoff(frm: str, to: str, message: str, **extra) -> dict:
    """One agent passes its result to another – shown as an arrow in the UI."""
    return _trace(frm, ANALYZED, message, to=to, kind="handoff", **extra)


def _phase(name: str, status: str, lang: str) -> dict:
    return {"type": "phase", "phase": name, "status": status, "index": texts.PHASES.index(name) + 1,
            "total": len(texts.PHASES), "label": texts.phase_label(name, lang)}


def _about(f_or_mail_id: str, party: str) -> dict:
    return {"finding_id": f_or_mail_id, "partner": party}


async def _pause():
    if settings.trace_delay_s:
        await asyncio.sleep(settings.trace_delay_s)


def initial_dashboard() -> dict:
    """What the owner sees before syncing: today's forecast, no findings."""
    f = analyst.forecast([])
    return _dashboard(scenarios={"current": f}, recommended=f, findings=[], analysis=None)


def _kpis(recommended: dict) -> dict:
    co = data.company()
    return {
        "balance_today": data.start_balance(),
        "days_safe": recommended["days_safe"],
        "min_balance": recommended["min_balance"],
        "min_date": recommended["min_date"],
        "safety_buffer": co["safety_buffer"],
        "saved_liquidity": store.saved_liquidity,
    }


def _dashboard(scenarios: dict, recommended: dict, findings: list, analysis: dict | None) -> dict:
    co = data.company()
    return {
        "company": {"name": co["name"], "owner": co["owner"], "currency": co["currency"]},
        "today": settings.today().isoformat(),
        "headline": analyst.headline(recommended, "en"),
        "kpis": _kpis(recommended),
        # KPIs of the start screen (before this sync) → animate numbers from → to. null before the first sync.
        "kpis_previous": store.kpis_before_sync if findings or analysis else None,
        "agents": AGENTS,
        "analysis": analysis,
        "scenarios": scenarios,
        "findings": findings,
        "actions": list(store.actions.values()),
        # language the model wrote its texts in during the last sync (the other language = rule-based texts)
        "sync_lang": store.sync_lang if (findings or analysis) else None,
        "i18n": texts.de(headline=analyst.headline(recommended, "de")),
    }


# --- trace texts (EN / DE) ----------------------------------------------------------

def _reading_line(n: int, lang: str) -> str:
    return f"Lese {n} neue E-Mails…" if lang == "de" else f"Reading {n} new emails…"


def _found_line(mail: dict, ex: dict, lang: str) -> str:
    de = lang == "de"
    if ex["kind"] == "price_change":
        if not ex["figures_stated"]:
            return (f"{ex['party']} kündigt eine Preisänderung an, nennt aber keine Zahlen – ich rate nicht." if de
                    else f"Price change announced by {ex['party']}, but the email gives no figures – I won't guess.")
        if de:
            return (f"Preisänderung gefunden: {ex['party']} erhöht um {texts.pct(ex['increase_pct'], lang)} ab dem "
                    f"{texts.day(ex['effective_date'], lang)}.")
        return f"Price change found: {ex['summary']}"
    if ex["kind"] == "payment_delay":
        if de and ex["figures_stated"]:
            return (f"Verspätete Kundenzahlung: {ex['party']} zahlt Rechnung {ex['invoice']} "
                    f"{ex['days_late']} Tage später.")
        if de:
            return f"Verspätete Kundenzahlung angekündigt: {ex['party']}."
        return f"Late customer payment: {ex['summary']}"
    return (f"Ignoriert: „{mail['subject']}“ – es geht nicht um Preise oder Zahlungen." if de
            else f"Ignored: \"{mail['subject']}\" – not about prices or payments.")


def _ask_line(ex: dict, lang: str) -> str:
    de = lang == "de"
    if not ex["figures_stated"]:
        return f"{ex['party']} (keine Zahlen)" if de else f"{ex['party']} (no figures)"
    if ex["kind"] == "payment_delay":
        return f"{ex['party']} zahlt {ex['days_late']} Tage später" if de else f"{ex['party']} pays {ex['days_late']} days late"
    return f"{ex['party']} +{texts.pct(ex['increase_pct'], lang)}" if de else f"{ex['party']} +{ex['increase_pct']}%"


def _please_check(relevant: list, lang: str) -> str:
    items = ", ".join(_ask_line(ex, lang) for _, ex in relevant)
    if lang == "de":
        return f"Bitte prüfe {len(relevant)} Änderung(en) gegen die Verträge: {items}."
    return f"Please check {len(relevant)} change(s) against the contracts: {items}."


VERDICT_DE = {"violates": "verstößt", "allowed": "erlaubt", "unclear": "unklar"}


def _verdict_line(ex: dict, res: dict, lang: str) -> str:
    de = lang == "de"
    clause = f" ({res['clause_id']})" if res.get("clause_id") else ""
    uploaded_contract = (res.get("contract") or {}).get("origin") == "uploaded"
    if res["verdict"] == "unclear":
        if de:
            why = "keine Zahlen in der E-Mail" if not ex["figures_stated"] else "kein Vertrag hinterlegt"
            return f"{ex['party']}: Prüfung nicht möglich – {why}. Bitte selbst prüfen."
        why = "no figures in the email" if not ex["figures_stated"] else "no contract on file"
        return f"{ex['party']}: cannot check – {why}. Please review."
    if de:
        what = "die spätere Zahlung" if ex["kind"] == "payment_delay" else "die Erhöhung"
        ok = "erlaubt" if res["verdict"] == "allowed" else "NICHT erlaubt"
        uploaded = " (von Ihnen hochgeladener Vertrag, Bedingungen vom Modell ausgelesen)" if uploaded_contract else ""
        return f"{ex['party']}: {what} ist laut Vertrag {ok}{clause}{uploaded}."
    what = "paying later" if ex["kind"] == "payment_delay" else "the increase"
    ok = "allowed" if res["verdict"] == "allowed" else "NOT allowed"
    uploaded = " (contract you uploaded, terms extracted by the model)" if uploaded_contract else ""
    return f"{ex['party']}: {what} is {ok} by the contract{clause}{uploaded}."


def _verdicts_line(checked: list, lang: str) -> str:
    if lang == "de":
        return "Ergebnisse: " + "; ".join(f"{ex['party']} → {VERDICT_DE[res['verdict']]}" for _, ex, res in checked) + "."
    return "Verdicts: " + "; ".join(f"{ex['party']} → {res['verdict']}" for _, ex, res in checked) + "."


def _forecasting_line(lang: str) -> str:
    n = settings.forecast_days
    return (f"Prognose Ihres Kontostands für die nächsten {n} Tage in 3 Szenarien…" if lang == "de"
            else f"Forecasting your cash for the next {n} days in 3 scenarios…")


def _lowest_line(rec: dict, acc: dict, lang: str) -> str:
    if lang == "de":
        return (f"Niedrigster Kontostand: {texts.eur(rec['min_balance'], lang)} am {texts.day(rec['min_date'], lang)} "
                f"(wenn Sie alle Erhöhungen akzeptieren: {texts.eur(acc['min_balance'], lang)}).")
    return (f"Lowest balance: {rec['min_balance']:,.0f} EUR on {rec['min_date']} "
            f"(if you accept all increases: {acc['min_balance']:,.0f} EUR).")


def _waiting_line(title: str, lang: str) -> str:
    return f"Wartet auf Ihre Freigabe: {title}." if lang == "de" else f"Waiting for your approval: {title}."


def _briefing_line(summary: str, lang: str) -> str:
    return f"Briefing fertig: {summary}" if lang == "de" else f"Briefing ready: {summary}"


# --- one negotiation (runs concurrently with the others) ---------------------------

async def _negotiate(f: dict, emit: Callable[[dict], Awaitable[None]], lang: str) -> dict:
    with tracing.span(f"negotiation · {f['extraction']['party']}", tracing.CHAIN,
                      inputs={"task": f["task"], "finding_id": f["id"]}) as s:
        n = await _negotiate_steps(f, emit, lang)
        s.outputs({"approved": n["review"]["approved"], "rounds": n["rounds"], "source": n["source"],
                   "issues": n["review"]["issues"]})
        s.attrs({"avida.review_rounds": n["rounds"], "avida.approved": n["review"]["approved"]})
        return n


async def _negotiate_steps(f: dict, emit: Callable[[dict], Awaitable[None]], lang: str) -> dict:
    task, ex, res, imp = f["task"], f["extraction"], f["contract"], f["impact"]
    name = ex["party"]
    de = lang == "de"
    about = _about(f["id"], name)
    violations = texts.violations(res["checks"], lang)

    if task == "reject_price":
        await emit(_handoff(A, N, (
            f"{name}: vereinbart {texts.eur(ex['old_monthly'], lang)} pro Monat, angekündigt "
            f"{texts.eur(ex['new_monthly'], lang)}. Es geht um {texts.eur(imp['next_12_months'], lang)} pro Jahr." if de else
            f"{name}: agreed EUR {ex['old_monthly']:,.0f}/month, announced EUR {ex['new_monthly']:,.0f}. "
            f"Worth {imp['next_12_months']:,.0f} EUR/year."), **about))
        await emit(_handoff(L, N, f"{name}: {'nutze' if de else 'use'} {res['clause_id']} – {violations}", **about))
    elif task == "payment_reminder":
        await emit(_handoff(A, N, (
            f"{name}: Rechnung {ex['invoice']} ({texts.eur(ex['amount'], lang)}) kommt {ex['days_late']} Tage später "
            f"und senkt Ihren niedrigsten Kontostand um {texts.eur(imp['lowest_balance_effect'], lang)}." if de else
            f"{name}: invoice {ex['invoice']} (EUR {ex['amount']:,.0f}) arriving {ex['days_late']} days late lowers "
            f"your lowest balance by {imp['lowest_balance_effect']:,.0f} EUR."), **about))
        await emit(_handoff(L, N, f"{name}: {'nutze' if de else 'use'} {res['clause_id']} – {violations}", **about))
    else:
        await emit(_handoff(L, N, (
            f"{name}: keine Zahlen und kein Vertrag hinterlegt – bitte nach den genauen Preisen fragen." if de else
            f"{name}: no figures and no contract on file – please ask for the exact prices."), **about))

    body, src = await negotiator.draft(task, ex, res, imp)
    await emit(_trace(N, ANALYZED, f"Entwurf an {name} geschrieben." if de else f"Draft to {name} written.",
                      source=src, **about))
    await emit(_handoff(N, L, (f"Bitte prüfe meinen Entwurf an {name}, bevor er zur Freigabe geht." if de
                               else f"Please review my draft to {name} before the owner sees it."), **about))

    review, rsrc = await legal.review_draft(body, task, ex, res)
    rounds = 1
    if review["approved"]:
        if de:
            ok_txt = "der Ton passt" if task == "ask_details" else "Klausel, Zahlen und Ton stimmen"
            msg = f"Entwurf an {name} freigegeben – {ok_txt}."
        else:
            ok_txt = "tone is right" if task == "ask_details" else "clause, figures and tone are right"
            msg = f"Draft to {name} approved – {ok_txt}."
        await emit(_trace(L, ANALYZED, msg, source=rsrc, **about))
    else:
        issues = " ".join(review["issues"])
        await emit(_trace(L, ANALYZED, (f"Entwurf an {name}: Probleme gefunden. {issues}" if de
                                        else f"Draft to {name}: found issues. {issues}"),
                          source=rsrc, to=N, kind="handoff", **about))
        body, src = await negotiator.revise(task, body, review["issues"], ex, res, imp)
        await emit(_trace(N, ANALYZED, f"Entwurf an {name} überarbeitet." if de else f"Draft to {name} revised.",
                          source=src, **about))
        review, rsrc = await legal.review_draft(body, task, ex, res)
        rounds = 2
        if review["approved"]:
            msg = f"Überarbeiteter Entwurf an {name} freigegeben." if de else f"Revised draft to {name} approved."
        elif review.get("rule_issues"):
            # Demo safety net: after two rounds the draft still breaks a hard rule (clause, amount, placeholder,
            # internal finance) → the owner gets the checked template instead of a wrong email.
            body, src = negotiator._template(task, ex, res), "fallback"
            review = {"approved": True, "issues": [], "rule_issues": []}
            rsrc = "rules"
            msg = (f"Entwurf an {name} verletzt weiter Regeln – geprüfte Vorlage verwendet." if de
                   else f"Draft to {name} still breaks the rules – using the checked template instead.")
        else:
            issues = " ".join(review["issues"])
            msg = (f"Entwurf an {name} noch nicht perfekt – bitte vor dem Senden prüfen: {issues}" if de
                   else f"Draft to {name} still not perfect – please check it before sending: {issues}")
        await emit(_trace(L, ANALYZED, msg, source=rsrc, **about))
    return {"body": body, "source": src, "review": review, "rounds": rounds}


# --- action texts (EN in the fields, DE in the overlay) -------------------------------

def _email_texts(f: dict, lang: str) -> dict:
    ex, imp = f["extraction"], f["impact"]
    expl = texts.localize(f["contract"], lang)["explanation_simple"]
    name, de = ex["party"], lang == "de"
    if f["task"] == "reject_price":
        if de:
            return {"title": f"Preiserhöhung um {texts.num(ex['increase_pct'], lang)} % von {name} ablehnen",
                    "why": f"{expl} Spart {texts.eur(imp['next_12_months'], lang)} in 12 Monaten.",
                    "why_short": f"Der Vertrag erlaubt das nicht. Spart {texts.eur(imp['next_12_months'], lang)} in 12 Monaten."}
        return {"title": f"Reject the {ex['increase_pct']:.0f}% price increase from {name}",
                "why": f"{expl} Saves {imp['next_12_months']:,.0f} EUR over 12 months.",
                "why_short": f"The contract does not allow it. Saves {imp['next_12_months']:,.0f} EUR over 12 months."}
    if f["task"] == "payment_reminder":
        eff = imp["lowest_balance_effect"]
        if de:
            return {"title": f"{name} bitten, Rechnung {ex['invoice']} pünktlich zu zahlen",
                    "why": f"{expl} Zahlt der Kunde zum vereinbarten Termin, liegt Ihr niedrigster Kontostand um "
                           f"{texts.eur(eff, lang)} höher.",
                    "why_short": f"Der Vertrag erlaubt keine spätere Zahlung. Pünktlich liegt Ihr niedrigster Kontostand "
                                 f"um {texts.eur(eff, lang)} höher."}
        return {"title": f"Ask {name} to pay invoice {ex['invoice']} on time",
                "why": f"{expl} If they pay on the agreed date, your lowest balance is {eff:,.0f} EUR higher.",
                "why_short": f"The contract does not allow paying late. On time, your lowest balance is {eff:,.0f} EUR higher."}
    if de:
        return {"title": f"{name} nach den genauen neuen Preisen fragen", "why": expl,
                "why_short": "Keine Zahlen genannt – nachfragen, bevor neue Preise gelten."}
    return {"title": f"Ask {name} for the exact new prices", "why": expl,
            "why_short": "No figures given – ask before the new prices apply."}


def _email_action(f: dict, n: dict) -> dict:
    en, de_ = _email_texts(f, "en"), _email_texts(f, "de")
    return store.add_action(
        type="send_email",
        agent=N,
        reviewed_by=L,
        finding_id=f["id"],
        partner=f["extraction"]["party"],
        **en,
        savings_12m=f["impact"]["next_12_months"] if f["task"] == "reject_price" else 0.0,
        payload={"to": f["email"]["from"], "body": n["body"]},
        review={"approved": n["review"]["approved"], "issues": n["review"]["issues"], "rounds": n["rounds"]},
        source=n["source"],
        i18n={"de": de_},
    )


def _credit_texts(credit: dict, credit_if_accepted: dict | None, lang: str) -> dict:
    differs = credit_if_accepted and credit_if_accepted["amount"] != credit["amount"]
    if lang == "de":
        compare = (f" Würden Sie alle Preiserhöhungen akzeptieren, bräuchten Sie {texts.eur(credit_if_accepted['amount'], lang)}."
                   if differs else "")
        return {
            "title": f"Kontokorrentkredit über {texts.eur(credit['amount'], lang)} als Sicherheitsnetz einrichten",
            "why": (f"Zwischen dem {texts.day(credit['from'], lang)} und dem {texts.day(credit['until'], lang)} fällt Ihr "
                    f"Kontostand um bis zu {texts.eur(credit['gap'], lang)} unter Ihr Sicherheitspolster. Ein kurzer "
                    "Kontokorrentkredit überbrückt die Lücke, bis Kundenzahlungen eingehen. Maximale Zinskosten: "
                    f"{texts.eur(credit['max_interest_cost'], lang)}.{compare}"),
            "why_short": (f"Deckt eine Lücke von bis zu {texts.eur(credit['gap'], lang)} vom {texts.day(credit['from'], lang)} "
                          f"bis {texts.day(credit['until'], lang)}; max. {texts.eur(credit['max_interest_cost'], lang)} Zinsen."),
        }
    compare = (f" If you accepted all price increases you would need {credit_if_accepted['amount']:,.0f} EUR."
               if differs else "")
    return {
        "title": f"Arrange a {credit['amount']:,.0f} EUR overdraft facility as a safety net",
        "why": (f"Between {credit['from']} and {credit['until']} your balance falls below your safety cushion "
                f"by up to {credit['gap']:,.0f} EUR. A short overdraft bridges the gap until customer payments arrive. "
                f"Maximum interest cost: {credit['max_interest_cost']:,.0f} EUR.{compare}"),
        "why_short": (f"Covers a gap of up to {credit['gap']:,.0f} EUR from {texts.day(credit['from'], lang)} to "
                      f"{texts.day(credit['until'], lang)}; max. {credit['max_interest_cost']:,.0f} EUR interest."),
    }


# --- the pipeline -------------------------------------------------------------------

async def run_pipeline(lang: str = "en") -> AsyncIterator[dict]:
    """Wraps the pipeline: one sync at a time, stamps every event (id, ts, elapsed_ms, phase) and keeps a copy
    for the replay endpoint (GET /api/sync/trace)."""
    global _running
    if _running:
        raise SyncAlreadyRunning("A check is already running – please wait for it to finish.")
    _running = True
    background: list[asyncio.Task] = []
    started = time.perf_counter()
    seq, phase = 0, None
    try:
        # One MLflow trace per sync (no-op when tracing is off); agent and LLM spans nest under it.
        with tracing.span("sync_inbox", tracing.CHAIN,
                          inputs={"today": settings.today().isoformat(), "lang": lang}) as root:
            sources: dict[str, int] = {}
            async for ev in _pipeline(background, lang):
                if ev.get("source"):
                    sources[ev["source"]] = sources.get(ev["source"], 0) + 1
                if ev["type"] in ("trace", "phase"):
                    seq += 1
                    if ev["type"] == "phase" and ev["status"] == "start":
                        phase = ev["phase"]
                    ev = {"id": seq, "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                          "elapsed_ms": int((time.perf_counter() - started) * 1000), "phase": phase, **ev}
                    store.trace.append(ev)
                if ev["type"] == "result":
                    root.outputs(_trace_summary(ev["dashboard"], sources))
                    tracing.tag_trace(app="avida-cfo", flow="sync", lang=lang,
                                      fallback_used=str(sources.get("fallback", 0) > 0).lower())
                yield ev
    finally:
        # Client disconnected or error: don't leave LLM calls running in the background.
        for t in background:
            t.cancel()
        _running = False


def _trace_summary(dash: dict, sources: dict) -> dict:
    """Compact result for the MLflow trace: what the agents decided, not the whole dashboard."""
    return {
        "findings": {f["extraction"]["party"]: {"kind": f["kind"], "verdict": f["contract"]["verdict"],
                                                "recommendation": f.get("recommendation")} for f in dash["findings"]},
        "actions": [a["title"] for a in dash["actions"]],
        "min_balance": dash["kpis"]["min_balance"],
        "risk_level": (dash.get("analysis") or {}).get("risk_level"),
        "trace_sources": sources,
    }


async def _pipeline(background: list[asyncio.Task], lang: str) -> AsyncIterator[dict]:
    start_kpis = initial_dashboard()["kpis"]
    store.reset()
    store.kpis_before_sync = {**start_kpis, "saved_liquidity": 0.0}
    store.sync_lang = lang
    store.log("sync_started", lang=lang)

    # 1) Analyst reads the inbox ---------------------------------------------------
    yield _phase("inbox", "start", lang)
    mails = data.inbox()
    yield _trace(A, ANALYZED, _reading_line(len(mails), lang))
    await _pause()
    # All emails go to vLLM at once – it batches them.
    read = await asyncio.gather(*(analyst.read_email(m) for m in mails))
    relevant = []
    for mail, (ex, src) in zip(mails, read):
        if ex["kind"] != "other":
            relevant.append((mail, ex))
        yield _trace(A, ANALYZED, _found_line(mail, ex, lang), source=src, email_id=mail["id"],
                     **(_about(mail["id"], ex["party"]) if ex["kind"] != "other" else {}))
        await _pause()
    yield _phase("inbox", "done", lang)

    # 2) Legal checks the contracts -----------------------------------------------
    yield _phase("legal", "start", lang)
    if relevant:
        yield _handoff(A, L, _please_check(relevant, lang))
        await _pause()
    results = await asyncio.gather(*(legal.check(ex, mail["received"], lang) for mail, ex in relevant))
    checked = []
    for (mail, ex), (res, src) in zip(relevant, results):
        checked.append((mail, ex, res))
        yield _trace(L, RECOMMENDATION, _verdict_line(ex, res, lang), source=src, **_about(mail["id"], ex["party"]))
        await _pause()
    if checked:
        yield _handoff(L, A, _verdicts_line(checked, lang))
        await _pause()
    yield _phase("legal", "done", lang)

    # 3) Analyst: forecast, impact, credit (deterministic) ---------------------------
    yield _phase("forecast", "start", lang)
    yield _trace(A, ANALYZED, _forecasting_line(lang))
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
    yield _trace(A, ANALYZED, _lowest_line(rec, scenarios["if_accepted"], lang))
    await _pause()

    findings = []
    for mail, ex, res in checked:
        if ex["kind"] == "payment_delay" and ex["figures_stated"]:
            imp = analyst.delay_impact(ex, plan_adj, delays)
        elif ex["kind"] == "price_change":
            imp = analyst.impact(ex)
        else:
            imp = {"monthly": 0.0, "in_horizon": 0.0, "next_12_months": 0.0, "calculation": "No figures in the email.",
                   "i18n": texts.de(calculation="Keine Zahlen in der E-Mail.")}
        f = {"id": mail["id"], "kind": ex["kind"], "email": mail, "extraction": ex, "contract": res, "impact": imp,
             "recommendation": RECOMMEND.get((ex["kind"], res["verdict"]), "review")}
        f["task"] = _task(f)
        findings.append(f)
    credit = analyst.credit_proposal(rec)
    yield _phase("forecast", "done", lang)

    # The briefing (LLM) runs in the background while the Negotiator works.
    briefing_task = asyncio.create_task(analyst.briefing(scenarios, findings, credit, lang))
    background.append(briefing_task)

    # 4) Negotiator drafts, Legal reviews – one negotiation per finding, all in parallel ----
    yield _phase("negotiation", "start", lang)
    to_write = [f for f in findings if f["task"]]
    queue: asyncio.Queue = asyncio.Queue()

    async def run(f: dict) -> dict:
        try:
            return await _negotiate(f, queue.put, lang)
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
    yield _phase("negotiation", "done", lang)

    # 5) Actions for the owner, each with decision support ---------------------------------
    yield _phase("approval", "start", lang)
    ctx = decision.Context(scenarios=scenarios, plan_adj=plan_adj, delays=delays, credit=credit)
    # Actions are created in inbox order, so ids are stable between runs.
    for f, t in zip(to_write, tasks):
        action = _email_action(f, t.result())
        action["decision"] = decision.for_email(f, ctx)
        f["action_id"] = action["id"]
        yield _trace(N, APPROVAL, _waiting_line(texts.localize(action, lang)["title"], lang), source=action["source"],
                     action_id=action["id"], **_about(f["id"], f["extraction"]["party"]))

    if credit:
        credit_if_accepted = analyst.credit_proposal(scenarios["if_accepted"])
        en, de_ = _credit_texts(credit, credit_if_accepted, "en"), _credit_texts(credit, credit_if_accepted, "de")
        action = store.add_action(type="credit_application", agent=A, **en, savings_12m=0.0, payload=credit,
                                  source="rules", i18n={"de": de_})
        action["decision"] = decision.for_credit(ctx, credit_if_accepted)
        yield _trace(A, APPROVAL, _waiting_line(texts.localize(action, lang)["title"], lang), action_id=action["id"])
    yield _phase("approval", "done", lang)

    # 6) Briefing ---------------------------------------------------------------------
    yield _phase("briefing", "start", lang)
    analysis, bsrc = await briefing_task
    yield _trace(A, ANALYZED, _briefing_line(texts.localize(analysis, lang)["summary"], lang), source=bsrc)
    yield _phase("briefing", "done", lang)

    dash = _dashboard(scenarios, rec, findings, analysis)
    store.dashboard = dash
    store.log("sync_finished", findings=len(findings), actions=len(store.actions))
    yield {"type": "result", "dashboard": dash}
