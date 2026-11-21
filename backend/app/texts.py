"""Every text the backend writes for the owner, in English and German – plus the `localize()` helper.

How languages work (see docs/API.md → "Languages"):
- Objects are stored with their **English** text in the normal fields, and the German text in an `i18n` overlay:
  `{"title": "Reject …", "i18n": {"de": {"title": "… ablehnen"}}}`.
- `localize(obj, lang)` applies the overlay for `lang` and strips every `i18n` key – the API never shows it.
- Texts written by the model exist in **one** language (the `lang` of the sync); the other language gets the
  rule-based text for that field (and `source: "rules"` where the object has a `source`).
- Draft emails, original emails and contract quotes are never translated (they go to / come from the partner).

Nothing in here computes a number – it only formats numbers the agents already computed.
"""
from __future__ import annotations

from datetime import date

LANGS = ("en", "de")
Lang = str  # "en" | "de"

MONTHS_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
             "November", "Dezember"]


# --- localize ------------------------------------------------------------------------

def localize(obj, lang: Lang):
    """Deep copy of `obj` with every `i18n[lang]` overlay applied and every `i18n` key removed."""
    if isinstance(obj, list):
        return [localize(x, lang) for x in obj]
    if isinstance(obj, dict):
        out = {k: localize(v, lang) for k, v in obj.items() if k != "i18n"}
        over = (obj.get("i18n") or {}).get(lang)
        if over:
            out.update(localize(over, lang))
        return out
    return obj


def de(**fields) -> dict:
    """Shorthand for the German overlay: `{"de": {...}}`."""
    return {"de": fields}


# --- formatting ------------------------------------------------------------------------

def num(x: float, lang: Lang, decimals: int = 0) -> str:
    s = f"{x:,.{decimals}f}"
    if lang == "de":
        s = s.replace(",", "_").replace(".", ",").replace("_", ".")
    return s


def eur(x: float, lang: Lang, decimals: int = 0) -> str:
    """'17,640 EUR' / '17.640 EUR'."""
    return f"{num(x, lang, decimals)} EUR"


def pct(x: float, lang: Lang, decimals: int = 1) -> str:
    """'15.0%' / '15,0 %'."""
    return f"{num(x, lang, decimals)} %" if lang == "de" else f"{num(x, lang, decimals)}%"


def _d(v) -> date:
    return v if isinstance(v, date) else date.fromisoformat(str(v)[:10])


def day(v, lang: Lang) -> str:
    """'31 Aug 2027' / '31.08.2027'."""
    x = _d(v)
    return f"{x:%d.%m.%Y}" if lang == "de" else f"{x:%d %b %Y}"


def day_long(v, lang: Lang) -> str:
    """'22 January' / '22. Januar' (no year – used in the headline)."""
    x = _d(v)
    return f"{x.day}. {MONTHS_DE[x.month - 1]}" if lang == "de" else f"{x:%d %B}"


# --- phases of a sync (SSE `phase` events) ---------------------------------------------

PHASES = ["inbox", "legal", "forecast", "negotiation", "approval", "briefing"]
PHASE_LABEL = {
    "inbox": ("Reading the inbox", "Posteingang lesen"),
    "legal": ("Checking contracts", "Verträge prüfen"),
    "forecast": ("Forecasting cash", "Kontostand prognostizieren"),
    "negotiation": ("Drafting and reviewing replies", "Antworten entwerfen und prüfen"),
    "approval": ("Preparing your decisions", "Entscheidungen vorbereiten"),
    "briefing": ("Writing the briefing", "Briefing schreiben"),
}


def phase_label(phase: str, lang: Lang) -> str:
    en, de_ = PHASE_LABEL[phase]
    return de_ if lang == "de" else en


# --- agents & policy ---------------------------------------------------------------------

AGENT_DE = {
    "Analyst Agent": {"role": "Analyst", "does": "Liest den Posteingang, prognostiziert Ihren Kontostand und erklärt die Zahlen."},
    "Legal Agent": {"role": "Jurist", "does": "Prüft jede Änderung gegen Ihre Verträge und kontrolliert ausgehende E-Mails."},
    "Negotiator Agent": {"role": "Verhandler", "does": "Schreibt die Antworten an Lieferanten und Kunden – auf Basis der "
                                                       "Prüfung des Juristen und der Zahlen des Analysten."},
}

POLICY_DE = {
    "Read inbox, detect price changes and late customer payments": "Posteingang lesen, Preisänderungen und verspätete Kundenzahlungen erkennen",
    "Check supplier and customer contracts": "Lieferanten- und Kundenverträge prüfen",
    "Forecast cash flow 90 days ahead": "Kontostand 90 Tage im Voraus prognostizieren",
    "Draft a reply to a supplier or customer": "Antwort an Lieferanten oder Kunden entwerfen",
    "Review outgoing emails (four-eyes principle)": "Ausgehende E-Mails prüfen (Vier-Augen-Prinzip)",
    "Recommend reject / accept / remind / review": "Ablehnen / Akzeptieren / Erinnern / Prüfen empfehlen",
    "Send email to a supplier or customer": "E-Mail an Lieferanten oder Kunden senden",
    "Apply for a credit facility": "Kontokorrentkredit beantragen",
}


# --- headline (Analyst) --------------------------------------------------------------------

def headline(f: dict, lang: Lang) -> str:
    if not f["first_breach_date"]:
        if lang == "de":
            return (f"Sie sind die nächsten {f['horizon_days']} Tage sicher. Ihr Kontostand bleibt über Ihrem "
                    "Sicherheitspolster.")
        return f"You're safe for the next {f['horizon_days']} days. Your balance stays above your safety cushion."
    if f["min_balance"] < 0:
        if lang == "de":
            return (f"Sie sind die nächsten {f['days_safe']} Tage sicher. Ab dem {day_long(f['first_breach_date'], lang)} "
                    f"fällt Ihr Kontostand unter Ihr Sicherheitspolster, und am {day_long(f['min_date'], lang)} wäre Ihr "
                    f"Konto mit {eur(-f['min_balance'], lang)} überzogen.")
        return (f"You're safe for the next {f['days_safe']} days. From {day_long(f['first_breach_date'], lang)} your "
                f"balance falls below your safety cushion, and on {day_long(f['min_date'], lang)} your account would be "
                f"{-f['min_balance']:,.0f} EUR overdrawn.")
    if lang == "de":
        return (f"Sie sind die nächsten {f['days_safe']} Tage sicher. Um den {day_long(f['first_breach_date'], lang)} sinkt "
                f"Ihr Kontostand auf {eur(f['min_balance'], lang)} – unter Ihr Sicherheitspolster von "
                f"{eur(f['buffer'], lang)}.")
    return (f"You're safe for the next {f['days_safe']} days. Around {day_long(f['first_breach_date'], lang)} your "
            f"balance drops to {f['min_balance']:,.0f} EUR – below your safety cushion of {f['buffer']:,.0f} EUR.")


# --- contract checks (Legal) -----------------------------------------------------------

CHECK_DE = {
    "Price guarantee period": "Preisgarantie",
    "Notice period": "Ankündigungsfrist",
    "Maximum yearly increase": "Maximale jährliche Erhöhung",
    "Agreed payment date": "Vereinbartes Zahlungsdatum",
    "Change of payment date": "Änderung des Zahlungsdatums",
}


def check_guarantee(until, eff, ok: bool, lang: Lang) -> str:
    if lang == "de":
        return (f"Die Preisgarantie endete am {day(until, lang)}." if ok
                else f"Die Preise sind bis {day(until, lang)} fest, die Erhöhung beginnt aber am {day(eff, lang)}.")
    return (f"The price guarantee ended on {day(until, lang)}." if ok
            else f"Prices are fixed until {day(until, lang)}, but the increase starts on {day(eff, lang)}.")


def check_notice(given: int, need: int, ok: bool, lang: Lang) -> str:
    if lang == "de":
        return (f"{given} Tage Ankündigung gegeben ({need} erforderlich)." if ok
                else f"{given} Tage Ankündigung gegeben, {need} Tage erforderlich.")
    return f"{given} days' notice given ({need} required)." if ok else f"{given} days' notice given, {need} days required."


def check_cap(increase: float, cap: float, lang: Lang) -> str:
    if lang == "de":
        return f"Erhöhung um {pct(increase, lang)} bei erlaubten maximal {pct(cap, lang)}."
    return f"Increase of {increase}% vs. allowed maximum of {cap}%."


def check_payment(inv: str | None, due, new, late: int, lang: Lang) -> str:
    if lang == "de":
        who = f"Rechnung {inv}" if inv else "Die Rechnung"
        return f"{who} ist am {day(due, lang)} fällig; die Zahlung ist für den {day(new, lang)} angekündigt ({late} Tage zu spät)."
    return f"{inv or 'the invoice'} is due on {day(due, lang)}; payment is announced for {day(new, lang)} ({late} days late)."


def check_written(lang: Lang) -> str:
    if lang == "de":
        return ("Zahlungstermine können nur durch schriftliche Vereinbarung beider Parteien geändert werden – "
                "eine solche Vereinbarung gibt es nicht.")
    return "Payment dates can only be changed by written agreement of both parties – no such agreement exists."


def violations(checks: list[dict], lang: Lang) -> str:
    return " ".join(localize(c, lang)["detail"] for c in checks if not c["passed"])


# --- plain-language contract explanation (rule-based; the model may write its own) ------

def explanation(verdict: str, party: str, failed: list[dict], kind: str, figures: bool, lang: Lang) -> str:
    if lang == "de":
        if not figures:
            return (f"{party} kündigt eine Änderung an, nennt aber keine Zahlen – daher kann ich sie nicht prüfen. "
                    "Fragen Sie nach dem genauen neuen Preis, bevor er gilt.")
        if verdict == "violates":
            what = "die spätere Zahlung" if kind == "payment_delay" else "diese Erhöhung"
            return f"Ihr Vertrag mit {party} erlaubt {what} nicht. {violations(failed, lang)}"
        if verdict == "allowed":
            return f"Ihr Vertrag mit {party} erlaubt diese Änderung. Sie liegt innerhalb der vereinbarten Grenzen."
        return f"Ich konnte keinen Vertrag mit {party} finden. Bitte prüfen Sie diesen Fall selbst."
    if not figures:
        return (f"{party} announces a change but gives no figures, so I cannot check it. "
                "Ask for the exact new price before it takes effect.")
    if verdict == "violates":
        what = "paying later" if kind == "payment_delay" else "this increase"
        return f"Your contract with {party} does not allow {what}. {violations(failed, lang)}"
    if verdict == "allowed":
        return f"Your contract with {party} allows this change. It is within the agreed limits."
    return f"I could not find a contract with {party}. Please check this one yourself."


def no_contract_either(party: str, lang: Lang) -> str:
    return (f" Außerdem ist kein Vertrag mit {party} hinterlegt." if lang == "de"
            else f" There is also no contract with {party} on file.")


# --- calculations ("Show calculation") -----------------------------------------------------

def calc_price(old: float, new: float, delta: float, lang: Lang) -> str:
    if lang == "de":
        return (f"{num(new, lang, 2)} − {num(old, lang, 2)} = {num(delta, lang, 2)} EUR/Monat × 12 = "
                f"{num(delta * 12, lang, 2)} EUR/Jahr")
    return f"{new:,.2f} − {old:,.2f} = {delta:,.2f} EUR/month × 12 = {delta * 12:,.2f} EUR/year"


def calc_no_figures(lang: Lang) -> str:
    return ("Die E-Mail nennt keine Zahlen – noch nichts zu berechnen." if lang == "de"
            else "The email gives no figures – nothing to calculate yet.")


def calc_delay(amount: float, days_late: int, due, new, on_time: float, late: float, effect: float, lang: Lang) -> str:
    if lang == "de":
        return (f"{eur(amount, lang, 2)} kommen {days_late} Tage später ({day(due, lang)} → {day(new, lang)}). "
                f"Niedrigster Kontostand: {eur(on_time, lang)} bei pünktlicher Zahlung, {eur(late, lang)} bei später "
                f"Zahlung → {eur(effect, lang)} weniger.")
    return (f"EUR {amount:,.2f} arrives {days_late} days later ({day(due, lang)} → {day(new, lang)}). Lowest balance: "
            f"{on_time:,.0f} EUR if paid on time, {late:,.0f} EUR if paid late → {effect:,.0f} EUR less.")


def calc_credit(min_balance: float, min_date, buffer: float, gap: float, amount: float, rate: float, days: int,
                interest: float, lang: Lang) -> str:
    if lang == "de":
        return (f"Niedrigster Kontostand {eur(min_balance, lang)} am {day(min_date, lang)} vs. Sicherheitspolster "
                f"{eur(buffer, lang)} → Lücke {eur(gap, lang)}, aufgerundet auf {eur(amount, lang)}. "
                f"Max. Zinsen: {num(amount, lang)} × {num(rate, lang, 1)} % × {days}/365 = {eur(interest, lang)}.")
    return (f"Lowest balance {min_balance:,.0f} EUR on {str(min_date)[:10]} vs. safety buffer {buffer:,.0f} EUR → gap "
            f"{gap:,.0f} EUR, rounded up to {amount:,.0f} EUR. Max. interest: {amount:,.0f} × {rate}% × {days}/365 = "
            f"{interest:,.0f} EUR.")


CREDIT_NOTE_DE = "Unverbindliche, simulierte Konditionen – nur für die Demo."


# --- simulated execution (Store.decide) --------------------------------------------------

def result_email(to: str, lang: Lang) -> str:
    return (f"E-Mail an {to} gesendet (simuliert – nichts hat das System verlassen)." if lang == "de"
            else f"Email to {to} sent (simulated – nothing left the system).")


def result_credit(amount: float, product: str, lang: Lang) -> str:
    return (f"Antrag über {eur(amount, lang)} ({product}) vorbereitet und eingereicht (simuliert)." if lang == "de"
            else f"Application for {amount:,.0f} EUR {product} prepared and submitted (simulated).")


def result_other(lang: Lang) -> str:
    return "Erledigt (simuliert)." if lang == "de" else "Done (simulated)."
