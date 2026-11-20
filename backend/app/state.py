"""In-memory state: pending actions, audit log, saved-liquidity counter, autonomy policy.

Single replica is fine for the demo. For persistence swap for Redis/Postgres on OpenShift.
"""
from __future__ import annotations

import itertools
from datetime import datetime, timezone

# The four levels required by the challenge card.
ANALYZED = "analyzed"          # agent does it on its own
RECOMMENDATION = "recommendation"
APPROVAL = "approval"          # needs the owner's OK
SIMULATED = "simulated"        # execution is simulated, nothing leaves the system

POLICY = [
    {"action": "Read inbox and detect price changes", "agent": "Analyst Agent", "autonomy": ANALYZED, "execution": "-"},
    {"action": "Check supplier contracts", "agent": "Legal Agent", "autonomy": ANALYZED, "execution": "-"},
    {"action": "Forecast cash flow 90 days ahead", "agent": "Analyst Agent", "autonomy": ANALYZED, "execution": "-"},
    {"action": "Draft a reply to a supplier", "agent": "Negotiator Agent", "autonomy": ANALYZED, "execution": "-"},
    {"action": "Review outgoing emails (four-eyes principle)", "agent": "Legal Agent", "autonomy": ANALYZED, "execution": "-"},
    {"action": "Recommend rejecting / accepting a price change", "agent": "Legal Agent", "autonomy": RECOMMENDATION, "execution": "-"},
    {"action": "Send email to a supplier", "agent": "Negotiator Agent", "autonomy": APPROVAL, "execution": SIMULATED},
    {"action": "Apply for a credit facility", "agent": "Analyst Agent", "autonomy": APPROVAL, "execution": SIMULATED},
]


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
            if edited_body and a.get("payload", {}).get("body") is not None:
                a["payload"]["body"] = edited_body
            a["status"] = "executed"
            a["result"] = _simulate(a)
            self.saved_liquidity += a.get("savings_12m", 0.0)
            self.log("approved", action=a["id"], title=a["title"], result=a["result"])
        else:
            a["status"] = "rejected"
            self.log("rejected", action=a["id"], title=a["title"])
        a["decided"] = _now()
        return a


def _simulate(action: dict) -> str:
    if action["type"] == "send_email":
        return f"Email to {action['payload']['to']} sent (simulated – nothing left the system)."
    if action["type"] == "credit_application":
        p = action["payload"]
        return f"Application for {p['amount']:,.0f} EUR {p['product']} prepared and submitted (simulated)."
    return "Done (simulated)."


store = Store()
