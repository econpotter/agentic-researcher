"""C — harvest: run `openbrain acquire` for each of a front's terms and record
which papers landed. Deterministic; no LLM. Mutates the front in place.

Until openbrain reports stored_ids (Task 4), `report.get("stored_ids", [])`
yields []: harvest still runs (papers are stored in openbrain) but records no
membership into the front — no rework needed once stored_ids arrives.
"""

from __future__ import annotations

from .fronts import Front
from .openbrain_client import OpenbrainClient


def harvest_front(
    front: Front,
    client: OpenbrainClient,
    *,
    since: int | None = None,
    limit: int = 50,
) -> dict:
    seen = set(front.acquired_paper_ids)
    per_term: dict[str, int] = {}
    new_ids: list[str] = []
    for term in front.terms:
        report = client.acquire(term, since=since, limit=limit)
        ids = list(report.get("stored_ids", []))
        per_term[term] = len(ids)
        for pid in ids:
            if pid not in seen:
                seen.add(pid)
                front.acquired_paper_ids.append(pid)
                new_ids.append(pid)
    return {"per_term": per_term, "new_ids": new_ids}
