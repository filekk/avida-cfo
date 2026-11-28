"""In-memory state: pending actions, audit log, saved-liquidity counter, autonomy policy.

Single replica is fine for the demo. For persistence swap for Redis/Postgres on OpenShift.
"""
from __future__ import annotations

import itertools
from datetime import datetime, timezone

from . import texts

# The four levels required by the challenge card.
ANALYZED = "analyzed"          # agent does it on its own
RECOMMENDATION = "recommendation"
APPROVAL = "approval"          # needs the owner's OK
SIMULATED = "simulated"        # execution is simulated, nothing leaves the system

POLICY = [
    {"action": "Read inbox, detect price changes and late customer payments", "agent": "Analyst Agent", "autonomy": ANALYZED, "execution": "-"},
    {"action": "Check supplier and customer contracts", "agent": "Legal Agent", "autonomy": ANALYZED, "execution": "-"},
    {"action": "Forecast cash flow 90 days ahead", "agent": "Analyst Agent", "autonomy": ANALYZED, "execution": "-"},
    {"action": "Draft a reply to a supplier or customer", "agent": "Negotiator Agent", "autonomy": ANALYZED, "execution": "-"},
    {"action": "Review outgoing emails (four-eyes principle)", "agent": "Legal Agent", "autonomy": ANALYZED, "execution": "-"},
    {"action": "Recommend reject / accept / remind / review", "agent": "Legal Agent", "autonomy": RECOMMENDATION, "execution": "-"},
    {"action": "Send email to a supplier or customer", "agent": "Negotiator Agent", "autonomy": APPROVAL, "execution": SIMULATED},
    {"action": "Apply for a credit facility", "agent": "Analyst Agent", "autonomy": APPROVAL, "execution": SIMULATED},
]
for _rule in POLICY:
    _rule["i18n"] = texts.de(action=texts.POLICY_DE[_rule["action"]])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.dashboard: dict | None = None
        self.actions: dict[str, dict] = {}
        self.audit: list[dict] = []
        self.saved_liquidity: float = 0.0
        self.kpis_before_sync: dict | None = None  # KPIs of the start screen → "previous" values for number animations
        self.trace: list[dict] = []  # every SSE event of the last sync (replay: GET /api/sync/trace)
        self.sync_lang: str = "en"
        # the plan of the last sync (price adjustments kept, late payments assumed, findings) → re-run the forecast
        # when an approved decision changes it (e.g. a customer confirms paying on time)
        self.plan: dict | None = None
        self._ids = itertools.count(1)

    def add_action(self, **kwargs) -> dict:
        action = {
            "id": f"act-{next(self._ids)}",
            "status": "pending",
            "autonomy": APPROVAL,
            "execution": SIMULATED,
            "created": _now(),
            **kwargs,
        }
        self.actions[action["id"]] = action
        return action

    def log(self, event: str, **details) -> None:
        self.audit.append({"time": _now(), "event": event, **details})

    def decide(self, action_id: str, approve: bool, edited_body: str | None = None) -> dict:
        a = self.actions[action_id]
        if a["status"] != "pending":
            return a
        if approve:
            # a blank editor (e.g. cleared by mistake) never replaces the reviewed draft
            if (edited_body and edited_body.strip() and a.get("payload", {}).get("body") is not None
                    and edited_body.strip() != a["payload"]["body"].strip()):
                a["payload"]["body"] = edited_body
                a["edited_by_owner"] = True
            a["status"] = "executed"
            a["result"] = _simulate(a, "en")
            a.setdefault("i18n", {}).setdefault("de", {})["result"] = _simulate(a, "de")
            self.saved_liquidity += a.get("savings_12m", 0.0)
            self.log("approved", action=a["id"], title=a["title"], result=a["result"])
        else:
            a["status"] = "rejected"
            self.log("rejected", action=a["id"], title=a["title"])
        a["decided"] = _now()
        return a


def _simulate(action: dict, lang: str) -> str:
    if action["type"] == "send_email":
        return texts.result_email(action["payload"]["to"], lang)
    if action["type"] == "credit_application":
        p = action["payload"]
        return texts.result_credit(p["amount"], p["product"], lang)
    return texts.result_other(lang)


store = Store()
