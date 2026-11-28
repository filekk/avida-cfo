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

import re
from dataclasses import dataclass

from . import texts, tracing
from .agents import analyst, legal
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
    uncovered = analyst.uncovered_outflow(rec)

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


class UnsafeInstruction(ValueError):
    """The owner asked the Rewrite button for something illegal or deceptive → 422, the draft stays as it is."""


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
    "Max 170 words, no placeholders, no markdown. Return only the full email, starting with 'Subject:'. "
    "If the owner's request asks for anything illegal, deceptive or unethical (fraud, scams, made-up claims or amounts, "
    "threats, blackmail, bribery, insults), do not write an email: reply with exactly the word REFUSED."
)

# Rules screen for the owner's Rewrite request (EN + DE). Runs before the model, so a clear
# "scam them for 1 million dollars" is refused instantly and never reaches the Negotiator. The model's own
# REFUSED answer catches the wordings this list misses.
# Stems may take any ending ("fraud" → "fraudulent"). Short words must match as WHOLE words: as stems, "lie" would
# refuse "Liebe Frau Bauer", "Lieferung" and "liegt bei", "forge" would refuse "forget", "fälsch" "fälschlicherweise".
_UNSAFE_STEMS = (
    r"scam|fraud|defraud|swindl|cheat|deceiv|decept|mislead|misled|fabricat|falsif|blackmail|extort|brib|kickback|"
    r"launder|intimidat|harass|insult|"
    r"betrug|betrüg|(?:ab)?zock|täusch|erpress|bestechung|bestechen|bestoch|schmiergeld|geldwäsch|beleidig|"
    r"einschüchter|gefälscht|fälschen|fälschung"
)
_UNSAFE_WORDS = (
    r"lie|lies|lied|lying|liar|liars|fake|faked|fakes|forge|forged|forgery|forging|"
    r"steal|steals|stealing|stole|stolen|rip\s*(?:them|him|her)?\s*off|trick\s+(?:them|him|her)|"
    r"lüge|lügen|lügt|lügner|gelogen|belügen|erfinde|erfinden|erfindet|erfunden|stehlen|gestohlen|klauen|"
    r"über\s+den\s+tisch"
)
_UNSAFE_REQUEST = re.compile(rf"\b(?:{_UNSAFE_STEMS}|(?:{_UNSAFE_WORDS})\b)", re.I)
_REFUSED = re.compile(r"^\W*refused\W*$", re.I)


def _refusal(lang: str) -> str:
    return ("Dabei kann die KI nicht helfen: Die Bitte wäre unrechtmäßig oder irreführend. "
            "Der Entwurf bleibt unverändert." if lang == "de" else
            "The AI can't help with that: the request would be illegal or misleading. The draft is unchanged.")


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


_PREAMBLE = re.compile(r"^.*?(?=^(subject|betreff)\s*:)", re.I | re.S | re.M)


def _clean_email(text: str) -> str:
    """Models like to add "Sure! Here is the email:" or ``` fences – keep only the email itself."""
    t = re.sub(r"```[a-z]*", "", text).replace("**", "").strip()
    return _PREAMBLE.sub("", t, count=1).strip() or t


def _issues(text: str, f: dict) -> list[str]:
    return legal.rule_review(text, f["task"], f["extraction"], f["contract"])


@tracing.traced("negotiator.redraft", tracing.AGENT)
async def redraft(action_id: str, instruction: str, body: str | None, lang: str) -> dict:
    """The owner asks for a change in plain words → Negotiator rewrites → Legal reviews. Returns a PROPOSAL:
    the action is not changed; the UI puts the text into the editor and the owner approves as usual.
    Empty `instruction` = "write it again" (a fresh version with the same facts).

    Safety net (demo): a rewrite that breaks a hard rule the current text kept (clause, amount, placeholder,
    internal finance) gets one fix round; if it is still broken, the current text is returned unchanged with a note,
    so the editor never receives a worse email than it had."""
    instruction = instruction.strip() or DEFAULT_REWRITE
    # first: an illegal request gets the clear refusal whatever state the action is in
    if _UNSAFE_REQUEST.search(instruction):
        store.log("redraft_refused", action=action_id, instruction=instruction, source="rules")
        raise UnsafeInstruction(_refusal(lang))
    a, f = _context(action_id)
    if a["status"] != "pending":
        raise NotEditable("This action has already been decided.")
    current = body if body and body.strip() else a["payload"]["body"]
    user = f"OWNER'S REQUEST: {instruction}\n\nCURRENT DRAFT:\n{current}"
    new, source = await llm.text(REDRAFT_SYSTEM, user, current, max_tokens=500)
    if source == "llm" and _REFUSED.match(new.strip()):
        store.log("redraft_refused", action=a["id"], instruction=instruction, source="llm")
        raise UnsafeInstruction(_refusal(lang))
    new = _clean_email(new) if source == "llm" else current
    de = lang == "de"
    note = None

    if source == "llm":
        before = set(_issues(current, f))
        broken = [i for i in _issues(new, f) if i not in before]
        if broken:
            fix = (f"{user}\n\nYOUR VERSION:\n{new}\n\nIt breaks these rules – fix them and keep the owner's request:\n- "
                   + "\n- ".join(broken))
            new2, s2 = await llm.text(REDRAFT_SYSTEM, fix, new, max_tokens=500)
            new2 = _clean_email(new2)
            if s2 == "llm" and not [i for i in _issues(new2, f) if i not in before]:
                new = new2
            else:
                new, source = current, "fallback"
                note = ("Die neue Fassung hat Vertragsangaben verloren – der Entwurf bleibt unverändert. "
                        "Bitte formulieren Sie die Bitte anders." if de else
                        "The new version lost contract details – the draft is unchanged. Please try another wording.")
    else:
        note = ("Das Modell ist gerade nicht erreichbar – der Entwurf ist unverändert." if de
                else "The model is not available right now – the draft is unchanged.")

    changed = new.strip() != current.strip()
    rules_now = legal.rule_review(new, f["task"], f["extraction"], f["contract"], lang)
    if changed:
        review, rsrc = await legal.review_draft(new, f["task"], f["extraction"], f["contract"])
        model_remarks = [i for i in review["issues"] if i not in review["rule_issues"]]
    else:  # nothing new to review – the instant rule check is enough
        rsrc, model_remarks = "rules", []
    store.log("redraft_proposed", action=a["id"], instruction=instruction, source=source, changed=changed,
              approved=not (rules_now or model_remarks))
    return {
        "action_id": a["id"],
        "attempt": _attempts(a["id"]),  # 1, 2, 3 … – "Version 2" in the UI
        "instruction": instruction,
        "body": new,
        "changed": changed,
        "source": source,
        "note": note,
        # Legal Agent's review of the proposal: rule issues in the UI language, model remarks in English
        "review": {"approved": not (rules_now or model_remarks), "issues": rules_now + model_remarks, "source": rsrc},
    }
