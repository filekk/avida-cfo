"""Contract library: the owner uploads a contract, Granite extracts the terms live, the Legal Agent uses them.

The extraction itself lives in `extraction.py` and is shared with the Jupyter notebook that benchmarks it.
"""
from __future__ import annotations

import mimetypes
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from . import data, extraction
from .config import settings
from .llm import llm
from .state import store

MAX_BYTES = 5 * 1024 * 1024
MAX_CHARS = 30_000  # the model runs with max-model-len 16384 tokens


class ExtractionError(ValueError):
    pass


def _origin(c: dict) -> str:
    return c.get("origin", "index")


# Original bytes of uploaded files (in memory like everything else; cleared by reset) → GET /api/contracts/{id}/file
_files: dict[str, tuple[str, bytes]] = {}

SORT_KEYS = ("uploaded_at", "party", "title", "start_date", "size_bytes", "pages")


def _party_type(c: dict) -> str:
    return "customer" if "customer" in c else "supplier"


def _file_type(name: str) -> str:
    return (Path(name or "").suffix.lstrip(".") or "txt").lower()


@lru_cache
def _index_file_meta(file: str) -> dict:
    """Size and page count of a notebook-prepared contract file on disk (cached – the files never change)."""
    path = settings.data_dir / file
    if not path.is_file():
        return {"size_bytes": None, "pages": None}
    content = path.read_bytes()
    try:
        pages = len(extraction.pages_from_upload(path.name, content))
    except Exception:  # noqa: BLE001
        pages = None
    return {"size_bytes": len(content), "pages": pages}


def _used_by() -> dict[str, list[str]]:
    """contract id → finding ids of the last inbox check that relied on it."""
    out: dict[str, list[str]] = {}
    for f in (store.dashboard or {}).get("findings", []):
        cid = ((f.get("contract") or {}).get("contract") or {}).get("id")
        if cid:
            out.setdefault(cid, []).append(f["id"])
    return out


def _summary(c: dict, used: dict[str, list[str]]) -> dict:
    keys = ("id", "supplier", "customer", "title", "file", "start_date", "warnings", "extracted_by")
    meta = ({k: c.get(k) for k in ("size_bytes", "pages")} if _origin(c) == "uploaded"
            else _index_file_meta(c.get("file", "")))
    return {
        **{k: c[k] for k in keys if k in c},
        "origin": _origin(c),
        "party": extraction.party_of(c),
        "party_type": _party_type(c),
        "file_name": Path(c.get("file", "")).name,
        "file_type": _file_type(c.get("file", "")),
        **meta,
        "uploaded_at": c.get("uploaded_at"),        # null for the notebook-prepared index
        "extraction_seconds": c.get("extraction_seconds"),
        "source": c.get("source", "rules"),         # llm | fallback (uploads) · rules (prepared index)
        "warnings_count": len(c.get("warnings", [])),
        "clauses": len(c.get("clauses", [])),
        "used_in_last_sync": c["id"] in used,
        "used_by_findings": used.get(c["id"], []),
    }


def listing(q: str | None = None, origin: str | None = None, party_type: str | None = None,
            sort: str | None = None) -> list[dict]:
    """Contracts for the files page. Default order: uploads (newest first), then the index.
    Filters: origin (index|uploaded), party_type (supplier|customer), q (text in party / title / file name).
    sort: one of SORT_KEYS, '-' prefix = descending; empty values always go last."""
    used = _used_by()
    rows = [_summary(c, used) for c in data.contracts()]
    if origin:
        rows = [r for r in rows if r["origin"] == origin]
    if party_type:
        rows = [r for r in rows if r["party_type"] == party_type]
    if q and q.strip():
        needle = q.strip().lower()
        rows = [r for r in rows if needle in f"{r['party']} {r['title']} {r['file_name']}".lower()]
    if sort:
        key, desc = sort.lstrip("-"), sort.startswith("-")
        present = [r for r in rows if r.get(key) is not None]
        missing = [r for r in rows if r.get(key) is None]
        present.sort(key=lambda r: r[key].lower() if isinstance(r[key], str) else r[key], reverse=desc)
        rows = present + missing
    return rows


def detail(contract_id: str) -> dict | None:
    """Everything about one contract: extracted terms, all clauses, file metadata, where it was used."""
    c = next((c for c in data.contracts() if c["id"] == contract_id), None)
    if not c:
        return None
    return {**c, **_summary(c, _used_by()), "clauses": c.get("clauses", []), "clause_count": len(c.get("clauses", []))}


def original_file(contract_id: str) -> tuple[str, bytes, str] | None:
    """(file name, bytes, media type) of the original document – uploads from memory, the index from disk."""
    if contract_id in _files:
        name, content = _files[contract_id]
    else:
        c = next((c for c in data.index_contracts() if c["id"] == contract_id), None)
        path = settings.data_dir / c["file"] if c else None
        if not path or not path.is_file():
            return None
        name, content = path.name, path.read_bytes()
    media = {"md": "text/markdown", "txt": "text/plain", "pdf": "application/pdf"}.get(
        _file_type(name), mimetypes.guess_type(name)[0] or "application/octet-stream")
    return name, content, media


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
        "uploaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "size_bytes": len(content),
        "pages": len(pages),
        "extraction_seconds": seconds,
        "source": source,
    })
    if prev:
        data.uploaded.remove(prev)
    data.uploaded.insert(0, entry)
    _files[cid] = (Path(filename or "contract").name, content)
    return {"contract": entry, "source": source, "seconds": seconds, "pages": len(pages)}


def clear_uploads() -> None:
    """POST /api/reset: back to the notebook-prepared index only."""
    data.uploaded.clear()
    _files.clear()


def delete(contract_id: str) -> bool:
    c = next((c for c in data.uploaded if c["id"] == contract_id), None)
    if c:
        data.uploaded.remove(c)
        _files.pop(contract_id, None)
    return c is not None
