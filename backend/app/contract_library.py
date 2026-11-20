"""Contract library: the owner uploads a contract, Granite extracts the terms live, the Legal Agent uses them.

The extraction itself lives in `extraction.py` and is shared with the Jupyter notebook that benchmarks it.
"""
from __future__ import annotations

import time
from pathlib import Path

from . import data, extraction
from .config import settings
from .llm import llm

MAX_BYTES = 5 * 1024 * 1024
MAX_CHARS = 30_000  # the model runs with max-model-len 16384 tokens


class ExtractionError(ValueError):
    pass


def _origin(c: dict) -> str:
    return c.get("origin", "index")


def listing() -> list[dict]:
    keys = ("id", "supplier", "customer", "title", "file", "start_date", "origin", "warnings", "extracted_by")
    return [{**{k: c[k] for k in keys if k in c}, "origin": _origin(c), "clauses": len(c.get("clauses", []))}
            for c in data.contracts()]


def _canned(filename: str) -> dict | None:
    """Offline fallback: a known demo contract gets its hand-labelled index entry (as raw model output)."""
    stem = Path(filename or "").stem.lower()
    for c in data.index_contracts():
        if Path(c.get("file", "")).stem.lower() == stem:
            role = "customer" if "customer" in c else "supplier"
            return {"counterparty": c[role], "role": role, **{k: c.get(k) for k in extraction.SCHEMA["properties"]
                                                                 if k not in ("counterparty", "role")}}
    return None


def _next_id() -> str:
    used = {c["id"] for c in data.contracts()}
    n = 1
    while f"U-{n:03d}" in used:
        n += 1
    return f"U-{n:03d}"


async def upload(filename: str, content: bytes) -> dict:
    if not content:
        raise ExtractionError("The file is empty.")
    if len(content) > MAX_BYTES:
        raise ExtractionError("The file is larger than 5 MB.")
    try:
        pages = extraction.pages_from_upload(filename, content)
    except Exception as e:  # noqa: BLE001 – broken PDF etc.
        raise ExtractionError(f"Could not read the document: {e}") from e
    if not pages:
        raise ExtractionError("No text found in the document (scanned PDFs are not supported yet).")
    if sum(map(len, pages)) > MAX_CHARS:
        raise ExtractionError(f"The document is too long for the model ({MAX_CHARS:,} characters max).")

    own = data.company()["name"]
    req = extraction.request_kwargs(settings.llm_model, pages, own)
    started = time.perf_counter()
    try:
        raw, source = await llm.json(req["messages"][0]["content"], req["messages"][1]["content"],
                                     extraction.SCHEMA, _canned(filename), max_tokens=req["max_tokens"])
    except Exception as e:  # noqa: BLE001
        raise ExtractionError(f"The model could not read the contract right now ({e}).") from e
    seconds = round(time.perf_counter() - started, 1)

    ex = extraction.clean(raw, pages, own)
    if not ex["counterparty"]:
        raise ExtractionError("The model could not find the other party of the contract.")

    # Same party uploaded again -> replace the earlier upload (index entries stay, uploads take precedence).
    prev = next((c for c in data.uploaded if extraction.party_of(c).lower() == ex["counterparty"].lower()), None)
    cid = prev["id"] if prev else _next_id()
    entry = extraction.to_index_entry(ex, cid, f"uploads/{Path(filename or 'contract').name}")
    entry.update({
        "origin": "uploaded",
        "extracted_by": f"{settings.llm_model} (live)" if source == "llm" else "cached answer",
        "warnings": ex["warnings"],
    })
    if prev:
        data.uploaded.remove(prev)
    data.uploaded.insert(0, entry)
    return {"contract": entry, "source": source, "seconds": seconds, "pages": len(pages)}


def delete(contract_id: str) -> bool:
    c = next((c for c in data.uploaded if c["id"] == contract_id), None)
    if c:
        data.uploaded.remove(c)
    return c is not None
