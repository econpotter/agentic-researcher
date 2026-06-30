"""Collect papers for a topic: for each search term, fetch candidates from openbrain
(without storing), keep only those that clear the driver-side relevance gate, then
store the keepers. Deterministic; no LLM. Mutates the topic in place.

The relevance gate is a lexical recall check — how many distinct term tokens appear
in a candidate's title/abstract. This is the `min_overlap` filter openbrain's old
combined search-and-store tool applied internally; the fetch/store split moved it
here, where the driver owns acquisition policy.

If openbrain's store_papers result omits stored ids (older server), `.get(..., [])`
yields []: collection still runs (papers are stored in openbrain) but records no
membership — no rework needed once the server reports ids.
"""

from __future__ import annotations

import re

from .openbrain import Openbrain
from .topics import Topic

_WORD = re.compile(r"\w+")


def _overlap(term: str, paper: dict) -> int:
    """Count distinct `term` tokens that also appear in the paper's title/abstract
    (case-insensitive) — the lexical recall gate (openbrain's old server-side
    min_overlap) used before the fetch/store split moved it driver-side."""
    wanted = set(_WORD.findall(term.lower()))
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    return len(wanted & set(_WORD.findall(text)))


def collect_for_topic(
    topic: Topic,
    openbrain: Openbrain,
    *,
    since: int | None = None,
    limit: int = 50,
    min_overlap: int = 2,
) -> dict:
    seen = set(topic.collected_paper_ids)
    per_term: dict[str, int] = {}
    new_ids: list[str] = []
    for term in topic.search_terms:
        candidates = openbrain.fetch_papers(term, since=since, limit=limit, store=False)
        keepers = [c for c in candidates if _overlap(term, c) >= min_overlap]
        result = openbrain.store_papers(keepers) if keepers else {"stored_ids": []}
        ids = list(result.get("stored_ids", []))
        per_term[term] = len(ids)
        for paper_id in ids:
            if paper_id not in seen:
                seen.add(paper_id)
                topic.collected_paper_ids.append(paper_id)
                new_ids.append(paper_id)
    return {"per_term": per_term, "new_ids": new_ids}
