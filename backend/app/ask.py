"""Ask your CFO – the owner asks in plain language, the right agent answers from numbers already computed.

    question ──► route() ──► facts of that agent only ──► LLM {answer, in_data} ──► answer_ok() guard
                                                              │ in_data=false → polite refusal + suggestions
                                                              └ guard fails  → canned answer of a suggestion

Nothing is computed here by the LLM: every fact comes from the dashboard (forecast, verdicts, drafted emails).
Suggestions are generated deterministically from the current situation, in English or German, each with a
canned answer that is used when the model is unavailable or its answer fails the guard.

Problem chat: with `action_id` / `finding_id` the conversation is about ONE problem (one action card / finding):
the facts are limited to that problem (all three agents' view of it + the decision options) and the suggestions
are decision helpers for it ("What if I do nothing?", "By when must I decide?"). `history` carries the last turns
so the owner can ask follow-ups ("and why?").
"""
from __future__ import annotations

import re
from datetime import date

from .agents import analyst, legal, negotiator
from .agents.analyst import NUM_TOKEN, amounts_in, readings
from .llm import llm
from .state import store
from .texts import localize

A, L, N = analyst.NAME, legal.NAME, negotiator.NAME
LANGS = ("en", "de")


def current_dashboard() -> dict:
    from .orchestrator import initial_dashboard  # late import: orchestrator imports the agents too

    return store.dashboard or initial_dashboard()


# --- 1) Facts per agent (English, exact numbers) ------------------------------------

def _eur(x: float) -> str:
    return f"{x:,.0f} EUR"


def _plan(d: dict) -> dict:
    return d["scenarios"].get("recommended") or d["scenarios"]["current"]


def analyst_facts(d: dict) -> list[str]:
    k, rec = d["kpis"], _plan(d)
    f = [
        f"Today ({d['today']}) the bank balance is {_eur(k['balance_today'])}.",
        f"The safety cushion is {_eur(k['safety_buffer'])}.",
        f"Lowest balance in the next {rec['horizon_days']} days: {_eur(k['min_balance'])} on {k['min_date']}.",
    ]
    if rec["first_breach_date"]:
        f.append(f"The balance is below the safety cushion from {rec['first_breach_date']} to {rec['last_breach_date']}; "
                 f"until then the company is safe for {k['days_safe']} days.")
    else:
        f.append("The balance stays above the safety cushion for the whole forecast.")
    f += [f"Large payment: {o['label']}, {_eur(-o['amount'])} on {o['date']}." for o in rec["largest_outflows"][:3]]
    if d.get("analysis"):
        f += d["analysis"]["key_points"]
    for fd in d["findings"]:
        ex, imp = fd["extraction"], fd["impact"]
        if fd["kind"] == "payment_delay" and ex["figures_stated"]:
            f.append(f"If {ex['party']} pays invoice {ex['invoice']} on time ({ex['due_date']}), the lowest balance is "
                     f"{_eur(imp['min_balance_on_time'])} on {imp['min_date_on_time']} instead of "
                     f"{_eur(imp['min_balance_late'])} on {imp['min_date_late']}.")
    if credit := _credit(d):
        p = credit["payload"]
        f.append(f"Proposed overdraft: {_eur(p['amount'])} from {p['from']} to {p['until']} ({p['days_needed']} days), "
                 f"rate {p['indicative_rate_pct']}%, max. interest {_eur(p['max_interest_cost'])}. Status: {credit['status']}.")
    if k["saved_liquidity"]:
        f.append(f"Saved by Avida so far: {_eur(k['saved_liquidity'])} over 12 months.")
    return f


def legal_facts(d: dict) -> list[str]:
    if not d["findings"]:
        return ["No emails have been checked yet, so no contract has been reviewed."]
    f = []
    for fd in d["findings"]:
        ex, c = fd["extraction"], fd["contract"]
        what = "late customer payment" if fd["kind"] == "payment_delay" else "price change"
        f.append(f"{ex['party']} ({what}): verdict '{c['verdict']}', recommendation '{fd['recommendation']}'. {c['explanation_simple']}")
        if c.get("clause_id") and c.get("quote"):
            f.append(f"{ex['party']} contract clause {c['clause_id']}: \"{c['quote']}\"")
        f += [f"{ex['party']} – {ch['check']}: {'OK' if ch['passed'] else 'VIOLATED'} – {ch['detail']}" for ch in c["checks"]]
    return f


def negotiator_facts(d: dict) -> list[str]:
    emails = [a for a in d["actions"] if a["type"] == "send_email"]
    if not emails:
        return ["No emails have been drafted yet."]
    f = []
    for a in emails:
        r = a.get("review") or {}
        checked = ("approved by the Legal Agent" if r.get("approved") else "the Legal Agent still has remarks: "
                   + " ".join(r.get("issues", [])))
        f.append(f"Email to {a['payload']['to']} – \"{a['title']}\". Status: {a['status']} (needs the owner's approval to "
                 f"be sent; sending is simulated). {checked} after {r.get('rounds', 1)} round(s).")
        f.append(f"Text of that email: {a['payload']['body'][:700]}")
    return f


FACTS = {A: analyst_facts, L: legal_facts, N: negotiator_facts}


def _credit(d: dict) -> dict | None:
    return next((a for a in d["actions"] if a["type"] == "credit_application"), None)


# --- 2) Router (deterministic, EN + DE) ----------------------------------------------

LEGAL_WORDS = {"contract", "contracts", "clause", "clauses", "legal", "legally", "allowed", "allow", "law", "rights",
               "vertrag", "verträge", "vertrags", "klausel", "erlaubt", "rechtlich", "zulässig", "darf", "dürfen"}
NEGOTIATOR_WORDS = {"email", "e-mail", "emails", "e-mails", "mail", "mails", "reply", "letter", "write", "wrote",
                    "written", "draft", "drafts", "send", "sent", "antwort", "antworten", "schreiben", "geschrieben",
                    "entwurf", "senden", "gesendet", "brief"}


def route(question: str) -> str:
    words = set(re.findall(r"[\wäöüß-]+", question.lower()))
    legal_score = len(words & LEGAL_WORDS) + ("§" in question)
    writer_score = len(words & NEGOTIATOR_WORDS)
    if writer_score > legal_score:
        return N
    if legal_score:
        return L
    return A


# --- 3) Suggestions (deterministic, EN / DE, each with a canned answer) ---------------

def _d(iso: str, lang: str) -> str:
    x = date.fromisoformat(iso)
    return f"{x:%d.%m.%Y}" if lang == "de" else f"{x.day} {x:%b %Y}"


def _m(x: float, lang: str) -> str:
    s = f"{x:,.0f}"
    return (s.replace(",", ".") if lang == "de" else s) + " EUR"


NOTE_BEFORE_SYNC = {
    "en": "More precise questions will appear after you check your inbox.",
    "de": "Nach dem Abgleich Ihres Posteingangs erscheinen genauere Fragen.",
}


def suggestions(d: dict, lang: str) -> list[dict]:
    """Up to 4 questions that fit the current situation. Internal: includes the canned answer."""
    k, rec, out = d["kpis"], _plan(d), []
    de = lang == "de"

    def add(sid: str, agent: str, q: tuple[str, str], a: tuple[str, str]):
        out.append({"id": sid, "agent": agent, "question": q[1] if de else q[0], "answer": a[1] if de else a[0]})

    if credit := _credit(d):
        p = credit["payload"]
        add("overdraft", A, ("Why do I need an overdraft?", "Warum brauche ich einen Kontokorrentkredit?"), (
            f"Between {_d(p['from'], lang)} and {_d(p['until'], lang)} your balance would fall up to {_m(p['gap'], lang)} "
            f"below your safety cushion of {_m(k['safety_buffer'], lang)}. An overdraft of {_m(p['amount'], lang)} for "
            f"{p['days_needed']} days bridges this gap and costs at most {_m(p['max_interest_cost'], lang)} in interest.",
            f"Zwischen dem {_d(p['from'], lang)} und dem {_d(p['until'], lang)} läge Ihr Kontostand bis zu {_m(p['gap'], lang)} "
            f"unter Ihrem Sicherheitspolster von {_m(k['safety_buffer'], lang)}. Ein Kontokorrentkredit über "
            f"{_m(p['amount'], lang)} für {p['days_needed']} Tage überbrückt die Lücke und kostet höchstens "
            f"{_m(p['max_interest_cost'], lang)} Zinsen.",
        ))

    for fd in d["findings"]:
        ex, c, imp = fd["extraction"], fd["contract"], fd["impact"]
        if fd["kind"] == "payment_delay" and ex["figures_stated"] and not any(s["id"] == "on_time" for s in out):
            add("on_time", A, (f"What if {ex['party']} pays on time?", f"Was passiert, wenn {ex['party']} pünktlich zahlt?"), (
                f"If {ex['party']} pays invoice {ex['invoice']} on {_d(ex['due_date'], lang)}, your lowest balance is "
                f"{_m(imp['min_balance_on_time'], lang)} instead of {_m(imp['min_balance_late'], lang)}. "
                "Avida has drafted a friendly reminder for you to approve.",
                f"Wenn {ex['party']} die Rechnung {ex['invoice']} am {_d(ex['due_date'], lang)} bezahlt, liegt Ihr "
                f"niedrigster Kontostand bei {_m(imp['min_balance_on_time'], lang)} statt {_m(imp['min_balance_late'], lang)}. "
                "Avida hat eine freundliche Erinnerung zur Freigabe vorbereitet.",
            ))
        if fd["recommendation"] == "reject" and not any(s["id"] == "reject" for s in out):
            add("reject", L, (f"Why can I reject the {ex['party']} price increase?",
                              f"Warum kann ich die Preiserhöhung von {ex['party']} ablehnen?"), (
                f"Your contract says in {c['clause_id']}: \"{c['quote']}\" The increase therefore does not apply, "
                f"which keeps {_m(imp['next_12_months'], lang)} per year in your company.",
                f"Ihr Vertrag regelt in {c['clause_id']}: „{c['quote']}“ Die Erhöhung gilt daher nicht – das sind "
                f"{_m(imp['next_12_months'], lang)} pro Jahr, die in Ihrer Firma bleiben.",
            ))
        if fd["kind"] == "price_change" and not ex["figures_stated"] and not any(s["id"] == "no_figures" for s in out):
            add("no_figures", N, (f"What should I do about {ex['party']}?", f"Was soll ich wegen {ex['party']} tun?"), (
                f"{ex['party']} announced higher prices but gave no figures, so nothing can be checked yet. "
                "Avida drafted an email asking for the exact prices – please read and approve it.",
                f"{ex['party']} hat höhere Preise angekündigt, aber keine Zahlen genannt – daher lässt sich noch nichts "
                "prüfen. Avida hat eine E-Mail mit der Bitte um die genauen Preise vorbereitet – bitte prüfen und freigeben.",
            ))

    if rec["first_breach_date"]:
        safe = (f"For the next {k['days_safe']} days your balance stays above your safety cushion of "
                f"{_m(k['safety_buffer'], lang)}. From {_d(rec['first_breach_date'], lang)} it falls below it, the lowest point "
                f"is {_m(k['min_balance'], lang)} on {_d(k['min_date'], lang)}.",
                f"In den nächsten {k['days_safe']} Tagen bleibt Ihr Kontostand über Ihrem Sicherheitspolster von "
                f"{_m(k['safety_buffer'], lang)}. Ab dem {_d(rec['first_breach_date'], lang)} fällt er darunter, der "
                f"Tiefstand liegt bei {_m(k['min_balance'], lang)} am {_d(k['min_date'], lang)}.")
    else:
        safe = (f"Yes. Your balance stays above your safety cushion of {_m(k['safety_buffer'], lang)} for the next "
                f"{rec['horizon_days']} days.",
                f"Ja. Ihr Kontostand bleibt in den nächsten {rec['horizon_days']} Tagen über Ihrem Sicherheitspolster "
                f"von {_m(k['safety_buffer'], lang)}.")
    add("safe", A, (f"Am I safe for the next {rec['horizon_days']} days?",
                    f"Bin ich in den nächsten {rec['horizon_days']} Tagen sicher?"), safe)

    top = rec["largest_outflows"][:3]
    add("big_payments", A, ("What are my biggest payments coming up?", "Welche großen Zahlungen stehen an?"), (
        "Your biggest upcoming payments: " + "; ".join(f"{o['label']} – {_m(-o['amount'], lang)} on {_d(o['date'], lang)}" for o in top) + ".",
        "Ihre größten anstehenden Zahlungen: " + "; ".join(f"{o['label']} – {_m(-o['amount'], lang)} am {_d(o['date'], lang)}" for o in top) + ".",
    ))
    # Fixed priority (liquidity first, then legal, then emails) – a predictable list for the UI.
    order = ["overdraft", "on_time", "reject", "no_figures", "safe", "big_payments"]
    return sorted(out, key=lambda s: order.index(s["id"]))[:4]


def public_suggestions(d: dict, lang: str) -> dict:
    return {
        "lang": lang,
        "note": None if d["findings"] else NOTE_BEFORE_SYNC[lang],
        "suggestions": [{k: s[k] for k in ("id", "question", "agent")} for s in suggestions(d, lang)],
    }


# --- 4) Answer -----------------------------------------------------------------------

ROLE = {
    A: "You are the Analyst Agent of Avida, a CFO assistant for a small company. You explain cash, forecast and credit.",
    L: "You are the Legal Agent of Avida, a CFO assistant for a small company. You explain what the company's contracts "
       "say about each change. You give no legal advice beyond the contract text.",
    N: "You are the Negotiator Agent of Avida, a CFO assistant for a small company. You explain the emails you drafted "
       "for the owner and their status.",
}

ASK_RULES = (
    " Answer the owner's question using ONLY the facts below. The owner is not a finance expert: at most 3 short, "
    "friendly sentences in plain words. Copy numbers exactly from the facts, never compute new ones. "
    "If the facts do not contain the answer, set in_data to false. Answer in {language}. Answer with JSON only."
)

ASK_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}, "in_data": {"type": "boolean"}},
    "required": ["answer", "in_data"],
}

REFUSAL = {
    "en": "I can't tell that from your company's data. I can answer questions about your cash, your contracts and "
          "the emails I prepared – for example one of these:",
    "de": "Das kann ich aus den Daten Ihrer Firma nicht beantworten. Ich beantworte Fragen zu Ihrem Geld, Ihren "
          "Verträgen und den vorbereiteten E-Mails – zum Beispiel diese:",
}
UNSURE = {
    "en": "I'm not completely sure I understood your question. This is what I can tell you: ",
    "de": "Ich bin nicht ganz sicher, ob ich Ihre Frage richtig verstanden habe. Das kann ich Ihnen sagen: ",
}

_DATE_DE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b")


def answer_ok(answer, facts: list[str]) -> bool:
    """Guard: short, and every number in the answer (EN or DE format) appears in the facts."""
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 500:
        return False
    if len([s for s in re.split(r"(?<=[.!?])\s+", answer.strip()) if s]) > 4:
        return False
    known = amounts_in(" ".join(facts))
    text = _DATE_DE.sub(lambda m: f"{m[1]} {m[2]} {m[3]}", answer)  # 03.02.2027 → 03 02 2027
    return all(readings(tok) & known for tok in NUM_TOKEN.findall(text))


def _norm(q: str) -> str:
    return q.strip().lower().rstrip("?!. ")


# --- 5) Problem chat (one action card / finding) ---------------------------------------

class UnknownScope(LookupError):
    pass


def resolve_scope(d: dict, action_id: str | None, finding_id: str | None) -> tuple[dict | None, dict | None]:
    """(finding, action) of the problem the owner is looking at. Raises UnknownScope for unknown ids."""
    a = next((x for x in d["actions"] if x["id"] == action_id), None) if action_id else None
    if action_id and not a:
        raise UnknownScope(f"unknown action {action_id}")
    fid = finding_id or (a or {}).get("finding_id")
    f = next((x for x in d["findings"] if x["id"] == fid), None) if fid else None
    if finding_id and not f:
        raise UnknownScope(f"unknown finding {finding_id}")
    if f and not a and f.get("action_id"):
        a = next((x for x in d["actions"] if x["id"] == f["action_id"]), None)
    return f, a


def _option(a: dict | None, choice: str, lang: str) -> dict | None:
    if not a or not a.get("decision"):
        return None
    return next((o for o in localize(a["decision"], lang)["options"] if o["choice"] == choice), None)


def scope_facts(d: dict, f: dict | None, a: dict | None) -> list[str]:
    """Everything the three agents know about ONE problem (English, exact numbers)."""
    k = d["kpis"]
    facts = [f"Today ({d['today']}) the bank balance is {_eur(k['balance_today'])}; safety cushion {_eur(k['safety_buffer'])}.",
             f"Lowest balance in the plan: {_eur(k['min_balance'])} on {k['min_date']}."]
    if f:
        ex, c, imp = f["extraction"], f["contract"], f["impact"]
        facts.append(f"Email from {f['email']['from_name']} received {f['email']['received']}: \"{f['email']['subject']}\". "
                     f"Summary: {ex['summary']}")
        if f["kind"] == "price_change" and ex["figures_stated"]:
            facts.append(f"{ex['party']} wants EUR {ex['new_monthly']:,.2f} instead of EUR {ex['old_monthly']:,.2f} per month "
                         f"(+{ex['increase_pct']}%, +{_eur(ex['monthly_delta'])} per month) from {ex['effective_date']}.")
            facts.append(f"Cost: {_eur(imp['next_12_months'])} over 12 months, {_eur(imp['in_horizon'])} within the forecast. "
                         f"Calculation: {imp['calculation']}")
        elif f["kind"] == "payment_delay" and ex["figures_stated"]:
            facts.append(f"{ex['party']} wants to pay invoice {ex['invoice']} over {_eur(ex['amount'])} on "
                         f"{ex['new_payment_date']} instead of {ex['due_date']} ({ex['days_late']} days late).")
            facts.append(f"Lowest balance: {_eur(imp['min_balance_on_time'])} if paid on time, {_eur(imp['min_balance_late'])} "
                         f"if paid late. Calculation: {imp['calculation']}")
        else:
            facts.append(f"{ex['party']} gave no figures, so nothing can be calculated or checked yet.")
        facts.append(f"Legal Agent verdict: '{c['verdict']}', recommendation '{f['recommendation']}'. {c['explanation_simple']}")
        if c.get("clause_id") and c.get("quote"):
            facts.append(f"Contract clause {c['clause_id']}: \"{c['quote']}\"")
        facts += [f"Check – {ch['check']}: {'OK' if ch['passed'] else 'VIOLATED'} – {ch['detail']}" for ch in c["checks"]]
        if (c.get("contract") or {}).get("title"):
            facts.append(f"Contract on file: {c['contract']['title']}.")
    if a:
        facts.append(f"Proposed action (needs the owner's click, execution is simulated): \"{a['title']}\". Status: {a['status']}. "
                     f"{a['why']}")
        if a["type"] == "send_email":
            r = a.get("review") or {}
            facts.append(f"The Legal Agent {'approved' if r.get('approved') else 'has remarks on'} the draft after "
                         f"{r.get('rounds', 1)} round(s). Draft text: {a['payload']['body'][:700]}")
        else:
            p = a["payload"]
            facts.append(f"Overdraft: {_eur(p['amount'])} from {p['from']} to {p['until']} ({p['days_needed']} days), rate "
                         f"{p['indicative_rate_pct']}%, max. interest {_eur(p['max_interest_cost'])}. {p['calculation']}")
        dec = a.get("decision") or {}
        for o in dec.get("options", []):
            facts.append(f"If the owner chooses '{o['choice']}': {o['summary']}")
        if dec.get("deadline"):
            facts.append(f"Decide before {dec['deadline']}: {dec['deadline_reason']}")
    return facts


def scoped_suggestions(d: dict, f: dict | None, a: dict | None, lang: str) -> list[dict]:
    """Up to 4 decision helpers for one problem, each with a prepared (always correct) answer."""
    de, out = lang == "de", []

    def add(sid: str, agent: str, q: tuple[str, str], ans: tuple[str, str]):
        out.append({"id": sid, "agent": agent, "question": q[1] if de else q[0], "answer": ans[1] if de else ans[0]})

    if f:
        ex, c, imp = f["extraction"], f["contract"], f["impact"]
        party = ex["party"]
        quote_en = f" Your contract says in {c['clause_id']}: \"{c['quote']}\"" if c.get("quote") else ""
        quote_de = f" Ihr Vertrag regelt in {c['clause_id']}: „{c['quote']}“" if c.get("quote") else ""
        expl_de = localize(c, "de")["explanation_simple"]
        if f["recommendation"] == "reject":
            add("why", L, (f"Why can I reject the {party} increase?", f"Warum kann ich die Erhöhung von {party} ablehnen?"),
                (c["explanation_simple"] + quote_en, expl_de + quote_de))
            add("cost", A, ("What does it cost me if I accept?", "Was kostet es mich, wenn ich zustimme?"), (
                f"{_m(ex['monthly_delta'], lang)} more per month, {_m(imp['next_12_months'], lang)} over 12 months "
                f"({_m(imp['in_horizon'], lang)} within the next {d['scenarios']['current']['horizon_days']} days).",
                f"{_m(ex['monthly_delta'], lang)} mehr pro Monat, {_m(imp['next_12_months'], lang)} in 12 Monaten "
                f"({_m(imp['in_horizon'], lang)} in den nächsten {d['scenarios']['current']['horizon_days']} Tagen)."))
        elif f["recommendation"] == "remind":
            add("why", L, ("Is paying late allowed?", "Ist die spätere Zahlung erlaubt?"),
                (c["explanation_simple"] + quote_en, expl_de + quote_de))
            add("on_time", A, (f"What if {party} pays on time?", f"Was passiert, wenn {party} pünktlich zahlt?"), (
                f"If {party} pays invoice {ex['invoice']} on {_d(ex['due_date'], lang)}, your lowest balance is "
                f"{_m(imp['min_balance_on_time'], lang)} instead of {_m(imp['min_balance_late'], lang)}.",
                f"Wenn {party} die Rechnung {ex['invoice']} am {_d(ex['due_date'], lang)} bezahlt, liegt Ihr niedrigster "
                f"Kontostand bei {_m(imp['min_balance_on_time'], lang)} statt {_m(imp['min_balance_late'], lang)}."))
            add("tone", N, ("Will the email upset the customer?", "Verärgert die E-Mail den Kunden?"), (
                "No – it thanks them for the early notice and only asks to keep the agreed date, for example with a manual "
                "payment. No threats and no interest claims.",
                "Nein – sie bedankt sich für die frühe Information und bittet nur darum, den vereinbarten Termin zu halten, "
                "zum Beispiel mit einer manuellen Zahlung. Keine Drohungen, keine Zinsforderungen."))
        elif f["recommendation"] == "accept":
            add("why", L, (f"Why is the {party} increase allowed?", f"Warum ist die Erhöhung von {party} erlaubt?"),
                (c["explanation_simple"] + quote_en, expl_de + quote_de))
            if ex["figures_stated"] and f["kind"] == "price_change":
                add("cost", A, ("How much does it cost me?", "Wie viel kostet mich das?"), (
                    f"{_m(ex['monthly_delta'], lang)} more per month, {_m(imp['next_12_months'], lang)} over 12 months.",
                    f"{_m(ex['monthly_delta'], lang)} mehr pro Monat, {_m(imp['next_12_months'], lang)} in 12 Monaten."))
            add("negotiate", N, ("Can I still negotiate?", "Kann ich trotzdem verhandeln?"), (
                f"You can ask {party} for a better price, but the contract allows this increase, so they do not have to "
                "agree. That is why Avida did not draft an objection.",
                f"Sie können {party} um einen besseren Preis bitten, aber der Vertrag erlaubt diese Erhöhung – {party} muss "
                "nicht zustimmen. Deshalb hat Avida keinen Widerspruch entworfen."))
        else:  # review – no figures / no contract
            add("why", L, ("Why can't Avida check this?", "Warum kann Avida das nicht prüfen?"),
                (c["explanation_simple"], expl_de))
            add("email", N, ("What will the email ask for?", "Wonach fragt die E-Mail?"), (
                f"It asks {party} for the current and the new monthly amount, the start date and the contractual basis. "
                "Until then the current prices apply.",
                f"Sie fragt {party} nach dem aktuellen und dem neuen Monatsbetrag, dem Startdatum und der vertraglichen "
                "Grundlage. Bis dahin gelten die aktuellen Preise."))
    elif a and a["type"] == "credit_application":
        p = a["payload"]
        add("why", A, ("Why do I need an overdraft?", "Warum brauche ich einen Kontokorrentkredit?"), (
            f"Between {_d(p['from'], lang)} and {_d(p['until'], lang)} your balance would fall up to {_m(p['gap'], lang)} "
            f"below your safety cushion. An overdraft of {_m(p['amount'], lang)} bridges this gap.",
            f"Zwischen dem {_d(p['from'], lang)} und dem {_d(p['until'], lang)} läge Ihr Kontostand bis zu "
            f"{_m(p['gap'], lang)} unter Ihrem Sicherheitspolster. Ein Kontokorrentkredit über {_m(p['amount'], lang)} "
            "überbrückt die Lücke."))
        add("cost", A, ("What does it cost?", "Was kostet das?"), (
            f"At most {_m(p['max_interest_cost'], lang)} in interest ({p['indicative_rate_pct']}% for {p['days_needed']} days, "
            "if the full amount is used the whole time). If you don't use it, you pay no interest.",
            f"Höchstens {_m(p['max_interest_cost'], lang)} Zinsen ({str(p['indicative_rate_pct']).replace('.', ',')} % für "
            f"{p['days_needed']} Tage, wenn der volle Betrag die ganze Zeit genutzt wird). Ohne Nutzung zahlen Sie keine Zinsen."))

    if (o := _option(a, "not_now", lang)) and a["status"] == "pending":
        add("not_now", A, ("What happens if I do nothing?", "Was passiert, wenn ich nichts tue?"), (o["summary"], o["summary"]))
    dec = a.get("decision") if a else None
    if dec and dec.get("deadline") and a["status"] == "pending":
        reason = localize(dec, lang)["deadline_reason"]
        add("deadline", A, ("By when should I decide?", "Bis wann sollte ich entscheiden?"), (
            f"Before {_d(dec['deadline'], lang)}. {reason}", f"Vor dem {_d(dec['deadline'], lang)}. {reason}"))
    return out[:4]


def public_scoped(d: dict, f: dict | None, a: dict | None, lang: str) -> dict:
    return {"lang": lang, "note": None, "action_id": (a or {}).get("id"), "finding_id": (f or {}).get("id"),
            "suggestions": [{k: s[k] for k in ("id", "question", "agent")} for s in scoped_suggestions(d, f, a, lang)]}


def _history_block(history: list[dict] | None) -> str:
    if not history:
        return ""
    lines = [f"{'OWNER' if h.get('role') == 'owner' else 'AVIDA'}: {str(h.get('text', ''))[:600]}" for h in history[-4:]]
    return "EARLIER IN THIS CONVERSATION:\n" + "\n".join(lines) + "\n\n"


async def ask(question: str, lang: str, action_id: str | None = None, finding_id: str | None = None,
              history: list[dict] | None = None) -> dict:
    d = current_dashboard()
    scoped = bool(action_id or finding_id)
    if scoped:
        f, a = resolve_scope(d, action_id, finding_id)
        sugg = scoped_suggestions(d, f, a, lang)
        public = public_scoped(d, f, a, lang)
    else:
        sugg = suggestions(d, lang)
        public = public_suggestions(d, lang)
    picked = next((s for s in sugg if _norm(s["question"]) == _norm(question)), None)
    agent = picked["agent"] if picked else route(question)
    facts = scope_facts(d, f, a) if scoped else FACTS[agent](d)
    extra = {k: v for k, v in public.items() if k != "lang"}

    if picked:
        # Clicked suggestion → the prepared answer, instantly and always correct (the 8B model can twist the
        # meaning, especially in German). The LLM answers free-text questions only.
        store.log("question", question=question, lang=lang, agent=agent, source="rules", in_data=True,
                  action_id=action_id, finding_id=finding_id)
        return {"question": question, "lang": lang, "agent": agent, "answer": picked["answer"], "source": "rules",
                "in_data": True, **extra}

    # Fallback for free text: the routed agent's first suggestion, introduced honestly.
    pool = sugg or suggestions(d, lang)
    canned = next((s for s in pool if s["agent"] == agent), pool[0])
    fb_answer = UNSURE[lang] + canned["answer"]

    language = ("German, formal 'Sie' (write amounts like 27.882 EUR and dates like 03.02.2027)" if lang == "de"
                else "English (write dates like 3 Feb 2027)")
    system = ROLE[agent] + ASK_RULES.format(language=language)
    user = ("FACTS:\n" + "\n".join(f"- {x}" for x in facts) + "\n\n" + _history_block(history)
            + f"QUESTION: {question}")
    out, source = await llm.json(system, user, ASK_SCHEMA, {"answer": fb_answer, "in_data": True})

    in_data = bool(out.get("in_data", True))
    if source == "llm" and not in_data:
        answer = REFUSAL[lang]
    elif source == "llm" and answer_ok(out.get("answer"), facts):
        answer = out["answer"].strip()
    else:
        answer, source, in_data = fb_answer, "fallback", True

    store.log("question", question=question, lang=lang, agent=agent, source=source, in_data=in_data,
              action_id=action_id, finding_id=finding_id)
    return {
        "question": question,
        "lang": lang,
        "agent": agent,
        "answer": answer,
        "source": source,
        "in_data": in_data,
        **extra,
    }
