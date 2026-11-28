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
def replies() -> dict:
    """Simulated partner replies, keyed by the inbox email id the owner answered (see replies_mock.json)."""
    return {k: v for k, v in _load("replies_mock.json").items() if not k.startswith("_")}


@lru_cache
def index_contracts() -> list[dict]:
    """Contracts prepared offline (notebook / hand-labelled)."""
    return _load("contracts_index.json")["contracts"]


# Contracts the owner uploaded at runtime and Granite extracted live (in memory, like the rest of the state).
uploaded: list[dict] = []


def contracts() -> list[dict]:
    """Knowledge base of the Legal Agent. Uploaded contracts come first, so a newer upload of the same
    party's contract wins over the index entry."""
    return uploaded + index_contracts()


def start_balance() -> float:
    return float(sum(a["balance"] for a in company()["accounts"]))
