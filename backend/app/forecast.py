"""Deterministic cash-flow forecast. No LLM here – numbers must be exact and explainable."""
from __future__ import annotations

import calendar
import math
from dataclasses import asdict, dataclass
from datetime import date, timedelta

from . import texts


@dataclass
class CashItem:
    date: date
    amount: float
    label: str
    category: str
    counterparty: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        return d


@dataclass
class Adjustment:
    """A change to a recurring item, e.g. a supplier price increase."""

    counterparty: str
    monthly_delta: float  # positive = costs more each month
    effective: date
    label: str


@dataclass
class Delay:
    """A customer pays an expected inflow later than agreed."""

    counterparty: str
    due: date
    new_date: date
    label: str


def pay_date(year: int, month: int, day: int) -> date:
    """Recurring item on day 30/31 falls on the last day of shorter months."""
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _month_iter(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def expand_items(
    cashflows: dict,
    start: date,
    days: int,
    adjustments: list[Adjustment] | None = None,
    delays: list[Delay] | None = None,
) -> list[CashItem]:
    """Turn recurring + one-off definitions into dated items within [start, start+days)."""
    end = start + timedelta(days=days - 1)
    adjustments = adjustments or []
    items: list[CashItem] = []

    for rec in cashflows.get("recurring_monthly", []):
        for y, m in _month_iter(start, end):
            d = pay_date(y, m, rec["day"])
            if not (start <= d <= end):
                continue
            amount = float(rec["amount"])
            label = rec["label"]
            for adj in adjustments:
                if adj.counterparty == rec["counterparty"] and d >= adj.effective:
                    # Outflows are negative: a price increase makes them more negative.
                    amount -= adj.monthly_delta
                    label = f"{label} ({adj.label})"
            items.append(CashItem(d, amount, label, rec["category"], rec["counterparty"]))

    for one in cashflows.get("one_off", []):
        d = date.fromisoformat(one["date"])
        if start <= d <= end:
            items.append(CashItem(d, float(one["amount"]), one["label"], one["category"], one["counterparty"]))

    for dl in delays or []:
        # Move the customer's inflow closest to the agreed due date (±3 days); drop it if it now falls after the horizon.
        candidates = [i for i in items if i.counterparty == dl.counterparty and i.amount > 0 and abs((i.date - dl.due).days) <= 3]
        if not candidates:
            continue
        it = min(candidates, key=lambda i: abs((i.date - dl.due).days))
        items.remove(it)
        if dl.new_date <= end:
            items.append(CashItem(dl.new_date, it.amount, f"{it.label} ({dl.label})", it.category, it.counterparty))

    items.sort(key=lambda i: (i.date, -i.amount))
    return items


def _by_category(items: list[CashItem], outflows: bool) -> list[dict]:
    """Totals per category over the whole horizon (outflows negative), biggest first."""
    acc: dict[str, dict] = {}
    for it in items:
        if (it.amount < 0) != outflows or it.amount == 0:
            continue
        c = acc.setdefault(it.category, {"category": it.category, "total": 0.0, "count": 0})
        c["total"] += it.amount
        c["count"] += 1
    out = [{**c, "total": round(c["total"], 2)} for c in acc.values()]
    return sorted(out, key=lambda c: abs(c["total"]), reverse=True)


def run_forecast(start_balance: float, items: list[CashItem], start: date, days: int, buffer: float) -> dict:
    by_day: dict[date, float] = {}
    ins: dict[date, float] = {}
    outs: dict[date, float] = {}
    for it in items:
        by_day[it.date] = by_day.get(it.date, 0.0) + it.amount
        bucket = ins if it.amount > 0 else outs
        bucket[it.date] = bucket.get(it.date, 0.0) + it.amount

    balance = start_balance
    series = []
    min_balance, min_date = start_balance, start
    first_breach: date | None = None
    last_breach: date | None = None
    for i in range(days):
        d = start + timedelta(days=i)
        balance += by_day.get(d, 0.0)
        series.append({"date": d.isoformat(), "balance": round(balance, 2),
                       "inflow": round(ins.get(d, 0.0), 2), "outflow": round(outs.get(d, 0.0), 2)})
        if balance < min_balance:
            min_balance, min_date = balance, d
        if balance < buffer:
            first_breach = first_breach or d
            last_breach = d

    return {
        "start_balance": start_balance,
        "end_balance": round(balance, 2),
        "min_balance": round(min_balance, 2),
        "min_date": min_date.isoformat(),
        "buffer": buffer,
        "first_breach_date": first_breach.isoformat() if first_breach else None,
        "last_breach_date": last_breach.isoformat() if last_breach else None,
        "days_safe": (first_breach - start).days if first_breach else days,
        "horizon_days": days,
        "series": series,
        # every dated payment in the horizon → chart annotations ("why does it drop here?") and own aggregations
        "events": [it.to_dict() for it in items],
        "outflows_by_category": _by_category(items, outflows=True),
        "inflows_by_category": _by_category(items, outflows=False),
    }


def size_credit_line(forecast: dict, offer: dict) -> dict | None:
    """Propose an overdraft that keeps the balance above the safety buffer."""
    gap = forecast["buffer"] - forecast["min_balance"]
    if gap <= 0:
        return None
    step = offer.get("step", 5000)
    amount = math.ceil(gap / step) * step
    start = date.fromisoformat(forecast["first_breach_date"])
    end = date.fromisoformat(forecast["last_breach_date"])
    days_needed = (end - start).days + 1
    rate = offer["indicative_rate_pct"] / 100
    # Upper bound: assumes the full amount is drawn for the whole period.
    max_interest = amount * rate * days_needed / 365
    return {
        "product": offer["product"],
        "bank": offer["bank"],
        "amount": amount,
        "gap": round(gap, 2),
        "from": start.isoformat(),
        "until": end.isoformat(),
        "days_needed": days_needed,
        "indicative_rate_pct": offer["indicative_rate_pct"],
        "max_interest_cost": round(max_interest, 2),
        "calculation": texts.calc_credit(forecast["min_balance"], forecast["min_date"], forecast["buffer"], gap, amount,
                                         offer["indicative_rate_pct"], days_needed, max_interest, "en"),
        "note": offer.get("note", ""),
        "i18n": texts.de(
            calculation=texts.calc_credit(forecast["min_balance"], forecast["min_date"], forecast["buffer"], gap, amount,
                                          offer["indicative_rate_pct"], days_needed, max_interest, "de"),
            note=texts.CREDIT_NOTE_DE,
        ),
    }
