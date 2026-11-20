"""Loads the mock data sources (bank, inbox, contract index). Swap these for real connectors later."""
import json
from functools import lru_cache

from .config import settings


def _load(name: str):
    with open(settings.data_dir / name, encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def company() -> dict:
    return _load("company.json")


@lru_cache
def cashflows() -> dict:
    return _load("cashflows.json")


@lru_cache
def inbox() -> list[dict]:
    return _load("inbox_mock.json")


@lru_cache
def contracts() -> list[dict]:
    return _load("contracts_index.json")["contracts"]


def start_balance() -> float:
    return float(sum(a["balance"] for a in company()["accounts"]))
