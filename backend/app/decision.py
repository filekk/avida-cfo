"""Decision support for every action card – what changes if the owner approves vs. says "Not now".

Everything here is deterministic (the forecast is re-run with / without the change); the LLM is used only by
`redraft()`, where the owner asks the Negotiator to rewrite a draft in plain words ("make it softer").
Nothing here executes anything: `redraft()` returns a proposal, the owner still has to approve.

    Action.decision = {
      "recommended": "approve" | "not_now",
      "certainty":   "high" | "medium",      # medium = the outcome depends on the partner (e.g. a customer may still pay late)
      "deadline":    "2027-01-01" | null,    # decide before this date …
      "deadline_reason": "…",                # … because of this
      "options": [ {"choice": "approve", "label", "summary", "effects": {...}},
                   {"choice": "not_now", "label", "summary", "effects": {...}} ]
    }
`effects` holds numbers only (EUR / ISO dates) so the UI can show a compact comparison:
`min_balance`, `min_date`, `cost_12m`, `cost_in_horizon`, `max_interest`, `credit_line`.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import texts, tracing
from .agents import analyst, legal, negotiator
from .llm import llm
from .state import store


@dataclass
class Context:
    scenarios: dict
    plan_adj: list
    delays: list
    credit: dict | None


def _opt(choice: str, label: tuple[str, str], summary: tuple[str, str], **effects) -> dict:
    return {"choice": choice, "label": label[0], "summary": summary[0],
            "effects": {k: v for k, v in effects.items() if v is not None},
            "i18n": texts.de(label=label[1], summary=summary[1])}


def _decision(recommended: str, certainty: str, deadline: str | None, reason: tuple[str, str], options: list) -> dict:
    return {"recommended": recommended, "certainty": certainty, "deadline": deadline or None,
            "deadline_reason": reason[0] if deadline else None, "options": options,
            "i18n": texts.de(deadline_reason=reason[1] if deadline else None)}


def _e(x, lg):
    return texts.eur(x, lg)


def _d(x, lg):
    return texts.day(x, lg)


def for_email(f: dict, ctx: Context) -> dict:
    ex, imp, res = f["extraction"], f["impact"], f["contract"]
    rec = ctx.scenarios["recommended"]
    party = ex["party"]

    if f["task"] == "reject_price":
        accepted = analyst.forecast(ctx.plan_adj + [analyst.to_adjustment(ex)], ctx.delays)
        clause = res.get("clause_id") or ""
        return _decision("approve", "high", ex["effective_date"], (
            "The new price would be invoiced from this date.", "Ab diesem Datum würde der neue Preis berechnet."), [
            _opt("approve", ("Send the rejection", "Ablehnung senden"), (
                f"{party} is told that {clause} excludes the increase. You keep paying {_e(ex['old_monthly'], 'en')} "
                f"per month; lowest balance {_e(rec['min_balance'], 'en')} on {_d(rec['min_date'], 'en')}.",
                f"{party} erfährt, dass {clause} die Erhöhung ausschließt. Sie zahlen weiter {_e(ex['old_monthly'], 'de')} "
                f"pro Monat; niedrigster Kontostand {_e(rec['min_balance'], 'de')} am {_d(rec['min_date'], 'de')}."),
                min_balance=rec["min_balance"], min_date=rec["min_date"], cost_12m=0.0, cost_in_horizon=0.0),
            _opt("not_now", ("Not now", "Jetzt nicht"), (
                f"Without an objection {party} will likely invoice {_e(ex['new_monthly'], 'en')} from "
                f"{_d(ex['effective_date'], 'en')}: {_e(imp['next_12_months'], 'en')} more per year, lowest balance "
                f"{_e(accepted['min_balance'], 'en')}.",
                f"Ohne Widerspruch berechnet {party} voraussichtlich ab dem {_d(ex['effective_date'], 'de')} "
                f"{_e(ex['new_monthly'], 'de')}: {_e(imp['next_12_months'], 'de')} mehr pro Jahr, niedrigster Kontostand "
                f"{_e(accepted['min_balance'], 'de')}."),
                min_balance=accepted["min_balance"], min_date=accepted["min_date"],
                cost_12m=imp["next_12_months"], cost_in_horizon=imp["in_horizon"]),
        ])

    if f["task"] == "payment_reminder":
        return _decision("approve", "medium", ex["due_date"], (
            "The invoice is due on this date – ask before it.", "Die Rechnung ist an diesem Tag fällig – vorher fragen."), [
            _opt("approve", ("Send the reminder", "Erinnerung senden"), (
                f"If {party} pays on {_d(ex['due_date'], 'en')} as agreed, your lowest balance is "
                f"{_e(imp['min_balance_on_time'], 'en')}. They may still pay late – the plan keeps the later date until "
                "they confirm.",
                f"Zahlt {party} wie vereinbart am {_d(ex['due_date'], 'de')}, liegt Ihr niedrigster Kontostand bei "
                f"{_e(imp['min_balance_on_time'], 'de')}. Der Kunde kann trotzdem später zahlen – der Plan rechnet bis "
                "zur Bestätigung mit dem späteren Datum."),
                min_balance=imp["min_balance_on_time"], min_date=imp["min_date_on_time"]),
            _opt("not_now", ("Not now", "Jetzt nicht"), (
                f"{_e(ex['amount'], 'en')} arrives on {_d(ex['new_payment_date'], 'en')}, {ex['days_late']} days late; "
                f"lowest balance {_e(imp['min_balance_late'], 'en')} on {_d(imp['min_date_late'], 'en')}.",
                f"{_e(ex['amount'], 'de')} kommen am {_d(ex['new_payment_date'], 'de')}, {ex['days_late']} Tage zu spät; "
                f"niedrigster Kontostand {_e(imp['min_balance_late'], 'de')} am {_d(imp['min_date_late'], 'de')}."),
                min_balance=imp["min_balance_late"], min_date=imp["min_date_late"]),
        ])

    # ask_details – no figures, nothing to compute
    eff = ex.get("effective_date") or None
    when_en = f" from {_d(eff, 'en')}" if eff else ""
    when_de = f" ab dem {_d(eff, 'de')}" if eff else ""
    return _decision("approve", "medium", eff, (
        "The supplier announced the change from this date.", "Der Lieferant hat die Änderung ab diesem Datum angekündigt."), [
        _opt("approve", ("Ask for the exact prices", "Nach den genauen Preisen fragen"), (
            f"{party} is asked for the current and new amounts. The current prices apply until you have checked them.",
            f"{party} wird nach den aktuellen und neuen Beträgen gefragt. Bis zur Prüfung gelten die aktuellen Preise.")),
        _opt("not_now", ("Not now", "Jetzt nicht"), (
            f"{party} may start invoicing higher prices{when_en} that nobody has checked against a contract.",
            f"{party} könnte{when_de} höhere Preise berechnen, die niemand gegen einen Vertrag geprüft hat.")),
    ])


def for_credit(ctx: Context, credit_if_accepted: dict | None) -> dict:
    c, rec = ctx.credit, ctx.scenarios["recommended"]
    uncovered = analyst._uncovered_outflow(rec)

    def not_now(lg: str) -> str:
        de = lg == "de"
        if rec["min_balance"] < 0:
            s = (f"Am {_d(rec['min_date'], lg)} wäre Ihr Konto mit {_e(-rec['min_balance'], lg)} überzogen" if de
                 else f"On {_d(rec['min_date'], lg)} your account would be {_e(-rec['min_balance'], lg)} overdrawn")
        else:
            s = (f"Ihr Kontostand fällt auf {_e(rec['min_balance'], lg)} – unter Ihr Sicherheitspolster" if de
                 else f"Your balance falls to {_e(rec['min_balance'], lg)} – below your safety cushion")
        if uncovered:
            s += (f"; {uncovered['label']} ({_e(-uncovered['amount'], lg)}) am {_d(uncovered['date'], lg)} wäre nicht gedeckt"
                  if de else f"; {uncovered['label']} ({_e(-uncovered['amount'], lg)}) on {_d(uncovered['date'], lg)} "
                             "would not be covered")
        return s + "."

    return _decision("approve", "high", c["from"], (
        "First day below your safety cushion.", "Erster Tag unter Ihrem Sicherheitspolster."), [
        _opt("approve", ("Arrange the overdraft", "Kontokorrentkredit einrichten"), (
            f"{_e(c['amount'], 'en')} is available from {_d(c['from'], 'en')} to {_d(c['until'], 'en')} and covers the "
            f"gap of {_e(c['gap'], 'en')}. At most {_e(c['max_interest_cost'], 'en')} interest – only if you use it.",
            f"{_e(c['amount'], 'de')} stehen vom {_d(c['from'], 'de')} bis {_d(c['until'], 'de')} bereit und decken die "
            f"Lücke von {_e(c['gap'], 'de')}. Höchstens {_e(c['max_interest_cost'], 'de')} Zinsen – nur bei Nutzung."),
            min_balance=rec["min_balance"], min_date=rec["min_date"], credit_line=c["amount"],
            max_interest=c["max_interest_cost"]),
        _opt("not_now", ("Not now", "Jetzt nicht"), (not_now("en"), not_now("de")),
             min_balance=rec["min_balance"], min_date=rec["min_date"], credit_line=0.0),
    ])


# --- owner tools on a draft email ------------------------------------------------------

class NotEditable(ValueError):
    pass


def _context(action_id: str) -> tuple[dict, dict]:
    """The pending email action and the finding it answers."""
    a = store.actions.get(action_id)
    if not a:
        raise KeyError(action_id)
    if a["type"] != "send_email":
        raise NotEditable("Only email drafts can be reviewed or rewritten.")
    f = next((f for f in (store.dashboard or {}).get("findings", []) if f["id"] == a.get("finding_id")), None)
    if not f:
        raise KeyError(action_id)
    return a, f


def review_body(action_id: str, body: str, lang: str) -> dict:
    """Instant rule check of a draft the owner edited (no LLM): clause cited, amounts right, no placeholders,
    no internal finance leaked. Same rules the Legal Agent applies to the Negotiator."""
    a, f = _context(action_id)
    issues = legal.rule_review(body, f["task"], f["extraction"], f["contract"], lang)
    return {"action_id": a["id"], "approved": not issues, "issues": issues, "source": "rules"}


REDRAFT_SYSTEM = (
    "You are the Negotiator Agent. The company owner asks you to change a draft email to a business partner. "
    "Apply the owner's request, but keep the contract clause (with its number), all amounts, invoice numbers and dates "
    "exactly as in the draft. Never mention the company's own cash flow, liquidity, overdraft or credit. "
    "Keep the language of the draft unless the owner explicitly asks for another language. "
    "Max 170 words, no placeholders, no markdown. Return only the full email, starting with 'Subject:'."
)


# Quick hints for the "Rewrite" button (chips next to the hint field). `instruction` goes to the model unchanged.
REWRITE_HINTS = [
    ("softer", "Friendlier", "Freundlicher",
     "Make the tone friendlier and warmer; we want to keep a good relationship."),
    ("firmer", "Firmer", "Bestimmter",
     "Make the tone firmer and more direct, still polite."),
    ("shorter", "Shorter", "Kürzer",
     "Make the email noticeably shorter: three to five sentences."),
    ("formal", "More formal", "Förmlicher",
     "Use a more formal business tone."),
    ("german", "In German", "Auf Deutsch",
     "Write the email in German (formal 'Sie')."),
    ("english", "In English", "Auf Englisch",
     "Write the email in English."),
]
DEFAULT_REWRITE = "Write a different version of this email with the same content and the same facts."


def rewrite_hints(action_id: str, lang: str) -> dict:
    """Chips for the Rewrite button. 404/409 like the other draft tools."""
    a, f = _context(action_id)
    de = lang == "de"
    return {
        "action_id": a["id"],
        "placeholder": ("z. B. „Erwähne, dass wir seit 5 Jahren Kunde sind“" if de
                        else "e.g. \"Mention that we have been customers for 5 years\""),
        "hints": [{"id": i, "label": l_de if de else l_en, "instruction": instr}
                  for i, l_en, l_de, instr in REWRITE_HINTS],
    }


def _attempts(action_id: str) -> int:
    return sum(1 for e in store.audit if e.get("event") == "redraft_proposed" and e.get("action") == action_id)


@tracing.traced("negotiator.redraft", tracing.AGENT)
async def redraft(action_id: str, instruction: str, body: str | None, lang: str) -> dict:
    """The owner asks for a change in plain words → Negotiator rewrites → Legal reviews. Returns a PROPOSAL:
    the action is not changed; the UI puts the text into the editor and the owner approves as usual.
    Empty `instruction` = "write it again" (a fresh version with the same facts)."""
    a, f = _context(action_id)
    if a["status"] != "pending":
        raise NotEditable("This action has already been decided.")
    instruction = instruction.strip() or DEFAULT_REWRITE
    current = body or a["payload"]["body"]
    user = f"OWNER'S REQUEST: {instruction}\n\nCURRENT DRAFT:\n{current}"
    new, source = await llm.text(REDRAFT_SYSTEM, user, current, max_tokens=500)
    review, rsrc = await legal.review_draft(new, f["task"], f["extraction"], f["contract"])
    rules_now = legal.rule_review(new, f["task"], f["extraction"], f["contract"], lang)
    store.log("redraft_proposed", action=a["id"], instruction=instruction, source=source, approved=review["approved"])
    note = None
    if source == "fallback":
        note = ("Das Modell ist gerade nicht erreichbar – der Entwurf ist unverändert." if lang == "de"
                else "The model is not available right now – the draft is unchanged.")
    return {
        "action_id": a["id"],
        "attempt": _attempts(a["id"]),  # 1, 2, 3 … – "Version 2" in the UI
        "instruction": instruction,
        "body": new,
        "changed": new.strip() != current.strip(),
        "source": source,
        "note": note,
        # Legal Agent's review of the proposal: rule issues in the UI language, model remarks in English
        "review": {"approved": review["approved"],
                   "issues": rules_now + [i for i in review["issues"] if i not in review["rule_issues"]],
                   "source": rsrc},
    }
