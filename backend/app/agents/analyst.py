"""Analyst Agent – the numbers person.

1. Reads the inbox: classifies each email (price change / late customer payment / other) and extracts
   the figures as structured data (LLM) – then checks every figure against the email text.
2. Forecasts cash 90 days ahead in three scenarios, quantifies each change, sizes a credit line
   (deterministic – the LLM never does arithmetic).
3. Writes an analytical briefing for the owner from those numbers (LLM).
"""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta

from .. import data, fallback, texts, tracing
from ..config import settings
from ..forecast import Adjustment, Delay, expand_items, pay_date, run_forecast, size_credit_line
from ..llm import llm

log = logging.getLogger("avida.analyst")

NAME = "Analyst Agent"

# --- 1) Inbox -------------------------------------------------------------------

EXTRACT_SYSTEM = (
    "You are the Analyst Agent of a CFO assistant for a small German company. Emails may be in English or German. "
    "Classify one email:\n"
    "- price_change: a supplier changes a recurring price. Fill old_monthly, new_monthly (monthly net EUR) and effective_date.\n"
    "- payment_delay: a customer will pay an invoice later than agreed. Fill invoice, amount, due_date and new_payment_date.\n"
    "- other: anything else.\n"
    "counterparty is the company name only (e.g. 'CloudHost GmbH', not a department). "
    "Copy numbers exactly as written in the email; if a number is not in the email, use 0 – never guess. "
    "Dates in ISO format YYYY-MM-DD, empty string if unknown. Leave fields of the other kinds empty or 0. "
    "The summary is at most 15 words, in English. Answer with JSON only."
)

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["price_change", "payment_delay", "other"]},
        "counterparty": {"type": "string"},
        "old_monthly": {"type": "number"},
        "new_monthly": {"type": "number"},
        "effective_date": {"type": "string"},
        "invoice": {"type": "string"},
        "amount": {"type": "number"},
        "due_date": {"type": "string"},
        "new_payment_date": {"type": "string"},
        "summary": {"type": "string", "description": "Max 15 words, plain English, e.g. 'CloudHost raises hosting by 15% from 1 Jan 2027.'"},
    },
    "required": ["kind", "counterparty", "old_monthly", "new_monthly", "effective_date",
                 "invoice", "amount", "due_date", "new_payment_date", "summary"],
}


@tracing.traced("analyst.read_email")
async def read_email(email: dict) -> tuple[dict, str]:
    user = f"From: {email['from_name']} <{email['from']}>\nSubject: {email['subject']}\nDate: {email['received']}\n\n{email['body']}"
    fb = fallback.EXTRACTIONS.get(email["id"], fallback.NOT_RELEVANT)
    raw, source = await llm.json(EXTRACT_SYSTEM, user, EXTRACT_SCHEMA, fb)
    out = sanitize(raw, email)
    # Demo guard: for the prepared inbox we know what each email is. If the model reads a key email differently
    # (wrong kind, or misses figures that are in the text), the whole story breaks – use the checked reading
    # instead and say so honestly (source "fallback" → "cached answer" in the UI).
    if source == "llm" and email["id"] in fallback.EXTRACTIONS:
        ref = sanitize(fb, email)
        if out["kind"] != ref["kind"] or (ref["figures_stated"] and not out["figures_stated"]):
            log.warning("read_email %s: model said %s/%s, expected %s/%s – using the checked reading",
                        email["id"], out["kind"], out["figures_stated"], ref["kind"], ref["figures_stated"])
            return ref, "fallback"
    return out, source


def sanitize(r: dict, email: dict) -> dict:
    """Never trust the model's figures: every amount must appear in the email, every date must parse,
    and percentages / deltas are recomputed here. `figures_stated=False` means: don't calculate, ask."""
    kind = r.get("kind") if r.get("kind") in ("price_change", "payment_delay") else "other"
    # "Stahlhandel Nord GmbH – Vertrieb" → "Stahlhandel Nord GmbH" (department suffixes confuse contract matching)
    party = re.split(r"\s+[–-]\s+", str(r.get("counterparty") or email.get("from_name") or "").strip())[0]
    summary = str(r.get("summary") or "").strip() or email["subject"]
    stated = amounts_in(email["body"])

    if kind == "price_change":
        old, new = _num(r.get("old_monthly")), _num(r.get("new_monthly"))
        eff = _iso(r.get("effective_date"))
        ok = old > 0 and new > 0 and round(old, 2) in stated and round(new, 2) in stated and eff is not None
        return {
            "kind": kind, "party": party, "supplier": party, "summary": summary, "figures_stated": ok,
            "old_monthly": old if ok else 0.0, "new_monthly": new if ok else 0.0,
            "increase_pct": round((new - old) / old * 100, 2) if ok else 0.0,
            "monthly_delta": round(new - old, 2) if ok else 0.0,
            "effective_date": eff or "",
        }

    if kind == "payment_delay":
        amount = _num(r.get("amount"))
        due, new = _iso(r.get("due_date")), _iso(r.get("new_payment_date"))
        days = (date.fromisoformat(new) - date.fromisoformat(due)).days if due and new else 0
        ok = amount > 0 and round(amount, 2) in stated and days > 0
        return {
            "kind": kind, "party": party, "customer": party, "summary": summary, "figures_stated": ok,
            "invoice": str(r.get("invoice") or "").strip(), "amount": amount if ok else 0.0,
            "due_date": due or "", "new_payment_date": new or "", "days_late": days if ok else 0,
        }

    return {"kind": "other", "party": party, "summary": summary, "figures_stated": False}


NUM_TOKEN = re.compile(r"\d[\d.,]*\d|\d")


def readings(tok: str) -> set[float]:
    """One number token read both ways: '9,800.00' (English) and '14.000,00' (German)."""
    out: set[float] = set()
    for candidate in (tok.replace(",", ""), tok.replace(".", "").replace(",", ".")):
        try:
            out.add(round(float(candidate), 2))
        except ValueError:
            pass
    return out


def amounts_in(text: str) -> set[float]:
    """All amounts in a text, in both readings."""
    return set().union(*(readings(t) for t in NUM_TOKEN.findall(text)))


def _num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _iso(v) -> str | None:
    try:
        return date.fromisoformat(str(v or "")[:10]).isoformat()
    except ValueError:
        return None


# --- 2) Numbers (deterministic) -----------------------------------------------------


def forecast(adjustments: list[Adjustment], delays: list[Delay] | None = None) -> dict:
    today = settings.today()
    co = data.company()
    items = expand_items(data.cashflows(), today, settings.forecast_days, adjustments, delays)
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


def to_delay(extraction: dict) -> Delay:
    return Delay(
        counterparty=extraction["customer"],
        due=date.fromisoformat(extraction["due_date"]),
        new_date=date.fromisoformat(extraction["new_payment_date"]),
        label=f"paid {extraction['days_late']} days late",
    )


def impact(extraction: dict) -> dict:
    """Price change: how much it costs within the forecast horizon and over the next 12 months."""
    if not extraction["figures_stated"]:
        return {"monthly": 0.0, "in_horizon": 0.0, "next_12_months": 0.0,
                "calculation": texts.calc_no_figures("en"), "i18n": texts.de(calculation=texts.calc_no_figures("de"))}
    today = settings.today()
    eff = date.fromisoformat(extraction["effective_date"])
    horizon_end = today + timedelta(days=settings.forecast_days - 1)
    pay_day = _payment_day(extraction["supplier"])
    payments_in_horizon = sum(
        1 for i in range(settings.forecast_days)
        if (d := today + timedelta(days=i)) == pay_date(d.year, d.month, pay_day) and d >= eff
    )
    delta = extraction["monthly_delta"]
    return {
        "monthly": delta,
        "in_horizon": round(delta * payments_in_horizon, 2),
        "payments_in_horizon": payments_in_horizon,
        "next_12_months": round(delta * 12, 2),
        "horizon_end": horizon_end.isoformat(),
        "calculation": texts.calc_price(extraction["old_monthly"], extraction["new_monthly"], delta, "en"),
        "i18n": texts.de(calculation=texts.calc_price(extraction["old_monthly"], extraction["new_monthly"], delta, "de")),
    }


def delay_impact(extraction: dict, adjustments: list[Adjustment], delays: list[Delay]) -> dict:
    """Late customer payment: costs nothing, but moves cash – how much lower does the lowest balance get?"""
    this = to_delay(extraction)
    late_f = forecast(adjustments, delays)
    on_time_f = forecast(adjustments, [d for d in delays if d != this])
    late, on_time = late_f["min_balance"], on_time_f["min_balance"]
    effect = round(on_time - late, 2)
    return {
        "monthly": 0.0, "in_horizon": 0.0, "next_12_months": 0.0,
        "amount": extraction["amount"], "days_late": extraction["days_late"],
        "due_date": extraction["due_date"], "new_payment_date": extraction["new_payment_date"],
        "min_balance_on_time": on_time, "min_date_on_time": on_time_f["min_date"],
        "min_balance_late": late, "min_date_late": late_f["min_date"], "lowest_balance_effect": effect,
        "calculation": texts.calc_delay(extraction["amount"], extraction["days_late"], this.due, this.new_date,
                                        on_time, late, effect, "en"),
        "i18n": texts.de(calculation=texts.calc_delay(extraction["amount"], extraction["days_late"], this.due,
                                                      this.new_date, on_time, late, effect, "de")),
    }


def saving_events(monthly: float, effective: date, pay_day: int) -> list[dict]:
    """Dated savings inside the forecast horizon: `monthly` EUR on every pay day from `effective`
    (e.g. a rejected increase = the difference not paid each month). The UI sums them per period."""
    today = settings.today()
    out = []
    for i in range(settings.forecast_days):
        d = today + timedelta(days=i)
        if d >= effective and d == pay_date(d.year, d.month, pay_day):
            out.append({"date": d.isoformat(), "amount": round(monthly, 2)})
    return out


def price_saving_events(extraction: dict) -> list[dict]:
    return saving_events(extraction["monthly_delta"], date.fromisoformat(extraction["effective_date"]),
                         _payment_day(extraction["supplier"]))


def _payment_day(counterparty: str) -> int:
    for r in data.cashflows()["recurring_monthly"]:
        if r["counterparty"] == counterparty:
            return r["day"]
    return 1


def credit_proposal(f: dict) -> dict | None:
    return size_credit_line(f, data.company()["credit_offer"])


def headline(f: dict, lang: str = "en") -> str:
    """Plain-language status for the top of the dashboard (deterministic, no LLM)."""
    return texts.headline(f, lang)


# --- 3) Analytical briefing (LLM explains the numbers it was given) ---------------

BRIEFING_SYSTEM = (
    "You are the Analyst Agent of a CFO assistant. You get exact facts from a cash-flow forecast. "
    "Explain to a small business owner who is not a finance expert, in at most 2 short sentences, "
    "what the situation is and what following the advice changes. "
    "Copy numbers exactly as given. NEVER compute a new number. {language} Answer with JSON only."
)

LANGUAGE = {
    "en": "Write in English.",
    "de": "Write in German (formal 'Sie'); keep numbers and dates exactly as written in the facts.",
}
CREDIT_SENTENCE = {"en": " A short overdraft bridges the gap.", "de": " Ein kurzer Kontokorrentkredit überbrückt die Lücke."}

BRIEFING_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string", "description": "Max 2 short sentences."}},
    "required": ["summary"],
}


def _uncovered_outflow(f: dict) -> dict | None:
    """The biggest payment that falls on a day when the account would be overdrawn (e.g. payroll)."""
    balance = {p["date"]: p["balance"] for p in f["series"]}
    return next((o for o in f["largest_outflows"] if balance.get(o["date"], 0) < 0), None)


def _facts(scenarios: dict, findings: list[dict], credit: dict | None, lang: str = "en") -> list[str]:
    """Short, unambiguous facts – also shown to the owner as the analyst's key points."""
    if lang == "de":
        return _facts_de(scenarios, findings, credit)
    rec, acc = scenarios["recommended"], scenarios["if_accepted"]
    facts = []
    for f in findings:
        ex = f["extraction"]
        if ex["kind"] == "payment_delay" and ex["figures_stated"] and f.get("confirmed_on_time"):
            facts.append(f"{ex['customer']} confirmed paying {ex['amount']:,.0f} EUR on time, on {ex['due_date']}.")
        elif ex["kind"] == "payment_delay" and ex["figures_stated"]:
            facts.append(
                f"{ex['customer']} wants to pay {ex['amount']:,.0f} EUR {ex['days_late']} days late "
                f"({ex['new_payment_date']} instead of {ex['due_date']}). The forecast plans with the later date."
            )
    overdrawn = " – your account would be overdrawn" if rec["min_balance"] < 0 else ""
    facts.append(
        f"If you follow the advice, your lowest balance is {rec['min_balance']:,.0f} EUR on {rec['min_date']}{overdrawn} "
        f"(safety cushion: {rec['buffer']:,.0f} EUR)."
    )
    if (o := _uncovered_outflow(rec)) is not None:
        facts.append(f"{o['label']}: {-o['amount']:,.0f} EUR on {o['date']} would not be covered without an overdraft.")
    if acc["min_balance"] != rec["min_balance"]:
        facts.append(f"If you accept every price increase, it drops to {acc['min_balance']:,.0f} EUR.")
    for f in findings:
        ex, imp = f["extraction"], f["impact"]
        if ex["kind"] != "price_change":
            continue
        if not ex["figures_stated"]:
            facts.append(f"{ex['supplier']} announced higher prices without figures – ask for the exact prices first.")
        elif f["recommendation"] == "reject":
            facts.append(f"Rejecting the {ex['supplier']} increase keeps {imp['next_12_months']:,.0f} EUR per year in your company.")
        elif f["recommendation"] == "accept":
            facts.append(f"The {ex['supplier']} increase is allowed and costs {imp['next_12_months']:,.0f} EUR per year.")
    if credit:
        facts.append(
            f"A {credit['amount']:,.0f} EUR overdraft for {credit['days_needed']} days covers the gap "
            f"(max. {credit['max_interest_cost']:,.0f} EUR interest)."
        )
    return facts


def _facts_de(scenarios: dict, findings: list[dict], credit: dict | None) -> list[str]:
    """German key points – the same facts as `_facts`, same order."""
    L = "de"
    rec, acc = scenarios["recommended"], scenarios["if_accepted"]
    facts = []
    for f in findings:
        ex = f["extraction"]
        if ex["kind"] == "payment_delay" and ex["figures_stated"] and f.get("confirmed_on_time"):
            facts.append(f"{ex['customer']} hat bestätigt, {texts.eur(ex['amount'], L)} pünktlich am "
                         f"{texts.day(ex['due_date'], L)} zu zahlen.")
        elif ex["kind"] == "payment_delay" and ex["figures_stated"]:
            facts.append(
                f"{ex['customer']} möchte {texts.eur(ex['amount'], L)} {ex['days_late']} Tage später zahlen "
                f"({texts.day(ex['new_payment_date'], L)} statt {texts.day(ex['due_date'], L)}). "
                "Die Prognose rechnet mit dem späteren Datum."
            )
    overdrawn = " – Ihr Konto wäre überzogen" if rec["min_balance"] < 0 else ""
    facts.append(
        f"Wenn Sie der Empfehlung folgen, liegt Ihr niedrigster Kontostand bei {texts.eur(rec['min_balance'], L)} am "
        f"{texts.day(rec['min_date'], L)}{overdrawn} (Sicherheitspolster: {texts.eur(rec['buffer'], L)})."
    )
    if (o := _uncovered_outflow(rec)) is not None:
        facts.append(f"{o['label']}: {texts.eur(-o['amount'], L)} am {texts.day(o['date'], L)} wären ohne "
                     "Kontokorrentkredit nicht gedeckt.")
    if acc["min_balance"] != rec["min_balance"]:
        facts.append(f"Wenn Sie alle Preiserhöhungen akzeptieren, sinkt er auf {texts.eur(acc['min_balance'], L)}.")
    for f in findings:
        ex, imp = f["extraction"], f["impact"]
        if ex["kind"] != "price_change":
            continue
        if not ex["figures_stated"]:
            facts.append(f"{ex['supplier']} hat höhere Preise ohne Zahlen angekündigt – fragen Sie zuerst nach den genauen Preisen.")
        elif f["recommendation"] == "reject":
            facts.append(f"Wenn Sie die Erhöhung von {ex['supplier']} ablehnen, bleiben {texts.eur(imp['next_12_months'], L)} "
                         "pro Jahr in Ihrer Firma.")
        elif f["recommendation"] == "accept":
            facts.append(f"Die Erhöhung von {ex['supplier']} ist erlaubt und kostet {texts.eur(imp['next_12_months'], L)} pro Jahr.")
    if credit:
        facts.append(
            f"Ein Kontokorrentkredit über {texts.eur(credit['amount'], L)} für {credit['days_needed']} Tage deckt die Lücke "
            f"(max. {texts.eur(credit['max_interest_cost'], L)} Zinsen)."
        )
    return facts


@tracing.traced("analyst.briefing")
async def briefing(scenarios: dict, findings: list[dict], credit: dict | None, lang: str = "en") -> tuple[dict, str]:
    """Key points are deterministic (both languages); the model writes the 2-sentence summary in `lang` only –
    the other language gets the rule-based summary."""
    facts = {lg: _facts(scenarios, findings, credit, lg) for lg in texts.LANGS}
    rec = scenarios["recommended"]
    risk = "high" if rec["min_balance"] < 0 else "medium" if rec["first_breach_date"] else "low"
    fb = {lg: texts.headline(rec, lg) + (CREDIT_SENTENCE[lg] if credit else "") for lg in texts.LANGS}
    # Only the 3 most important facts: with all of them an 8B model writes too much and mixes them up.
    top = facts[lang][:3]
    system = BRIEFING_SYSTEM.format(language=LANGUAGE[lang])
    out, source = await llm.json(system, "\n".join(top), BRIEFING_SCHEMA, {"summary": fb[lang]})

    summary = out.get("summary")
    if not summary_ok(summary, top):
        summary, source = fb[lang], "fallback"
    summaries, sources = dict(fb), {lg: "rules" for lg in texts.LANGS}
    summaries[lang], sources[lang] = summary, source
    return {
        "summary": summaries["en"], "key_points": facts["en"], "risk_level": risk, "source": sources["en"],
        "i18n": texts.de(summary=summaries["de"], key_points=facts["de"], source=sources["de"]),
    }, source


def briefing_rules(scenarios: dict, findings: list[dict], credit: dict | None) -> dict:
    """Same briefing without the model – after an approved decision changed the plan (instant, both languages)."""
    rec = scenarios["recommended"]
    risk = "high" if rec["min_balance"] < 0 else "medium" if rec["first_breach_date"] else "low"
    facts = {lg: _facts(scenarios, findings, credit, lg) for lg in texts.LANGS}
    summary = {lg: texts.headline(rec, lg) + (CREDIT_SENTENCE[lg] if credit else "") for lg in texts.LANGS}
    return {"summary": summary["en"], "key_points": facts["en"], "risk_level": risk, "source": "rules",
            "i18n": texts.de(summary=summary["de"], key_points=facts["de"], source="rules")}


def summary_ok(summary, facts: list[str]) -> bool:
    """Anti-hallucination guard: short (the longer the text, the more room to mix facts up) and every number
    the model writes must come from the facts."""
    if not isinstance(summary, str) or not summary.strip():
        return False
    sentences = [x for x in re.split(r"(?<=[.!?])\s+", summary.strip()) if x]
    return len(sentences) <= 3 and len(summary) <= 320 and _numbers(summary) <= _numbers(" ".join(facts))


def _numbers(text: str) -> set[float]:
    """All numbers in a text, normalised ('10,958' -> 10958.0, '15.0%' -> 15.0)."""
    out = set()
    for raw in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        try:
            out.add(float(raw.replace(",", "")))
        except ValueError:
            pass
    return out
