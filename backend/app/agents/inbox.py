"""Inbox Agent – reads incoming mail and extracts price changes as structured data."""
from .. import fallback
from ..llm import llm

SYSTEM = (
    "You are the Inbox Agent of a CFO assistant for a small German company. "
    "Read one email and decide whether a supplier announces a change of a recurring price. "
    "Extract the numbers exactly as written in the email. Amounts are monthly net EUR. "
    "Dates in ISO format YYYY-MM-DD. If the email is not about a price change, set is_price_change to false "
    "and leave the other fields empty or 0. Answer with JSON only."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "is_price_change": {"type": "boolean"},
        "supplier": {"type": "string"},
        "old_monthly": {"type": "number"},
        "new_monthly": {"type": "number"},
        "increase_pct": {"type": "number"},
        "effective_date": {"type": "string"},
        "summary": {"type": "string", "description": "One plain-language sentence for a non-expert."},
    },
    "required": ["is_price_change", "supplier", "old_monthly", "new_monthly", "increase_pct", "effective_date", "summary"],
}


async def analyze_email(email: dict) -> tuple[dict, str]:
    user = f"From: {email['from_name']} <{email['from']}>\nSubject: {email['subject']}\nDate: {email['received']}\n\n{email['body']}"
    fb = fallback.EXTRACTIONS.get(email["id"], fallback.NOT_PRICE_CHANGE)
    result, source = await llm.json(SYSTEM, user, SCHEMA, fb)
    return _sanitize(result), source


def _sanitize(r: dict) -> dict:
    """Never trust model arithmetic: recompute the percentage from the two prices."""
    old, new = float(r.get("old_monthly") or 0), float(r.get("new_monthly") or 0)
    if r.get("is_price_change") and old > 0 and new > 0:
        r["increase_pct"] = round((new - old) / old * 100, 2)
        r["monthly_delta"] = round(new - old, 2)
    else:
        r["is_price_change"] = bool(r.get("is_price_change")) and old > 0 and new > 0
        r["monthly_delta"] = 0.0
    return r
