"""Collect papers for a topic: run an openbrain search for each of the topic's
search terms and record which papers landed. Deterministic; no LLM. Mutates the
topic in place.

If openbrain's acquire result omits collected ids (older server), `.get(..., [])`
yields []: collection still runs (papers are stored in openbrain) but records no
membership — no rework needed once the server reports ids.
"""

from __future__ import annotations

from .openbrain import Openbrain
from .topics import Topic


def collect_for_topic(
    topic: Topic,
    openbrain: Openbrain,
    *,
    since: int | None = None,
    limit: int = 50,
) -> dict:
    seen = set(topic.collected_paper_ids)
    per_term: dict[str, int] = {}
    new_ids: list[str] = []
    for term in topic.search_terms:
        report = openbrain.acquire(term, since=since, limit=limit)
        ids = list(report.get("stored_ids", []))
        per_term[term] = len(ids)
        for paper_id in ids:
            if paper_id not in seen:
                seen.add(paper_id)
                topic.collected_paper_ids.append(paper_id)
                new_ids.append(paper_id)
    return {"per_term": per_term, "new_ids": new_ids}
