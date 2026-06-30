"""Collect papers for a topic: for each search term, discover candidates from
openbrain (external sources, nothing stored yet), keep those on-topic by the
driver's own relevance gate (similarity to the topic's core papers, within the
radius), and store only the keepers. Deterministic; no LLM. Mutates the topic in
place.

The gate runs driver-side: discovery returns candidate metadata + abstracts,
`score_relevance` scores each against the core centroid, and only papers clearing
the radius are handed to `store_papers`. A topic therefore needs at least one core
paper before it can collect — without a centroid there is nothing to gate against.
"""

from __future__ import annotations

from .openbrain import Openbrain
from .topics import Topic


def collect_for_topic(topic: Topic, openbrain: Openbrain, *, radius: float) -> dict:
    if not topic.core_paper_ids:
        raise ValueError("collect's relevance gate needs at least one core paper")

    seen = set(topic.collected_paper_ids)
    per_term: dict[str, int] = {}
    new_ids: list[str] = []
    for term in topic.search_terms:
        candidates = openbrain.fetch_candidates(term)
        texts = [f"{c.get('title', '')} {c.get('abstract', '')}".strip() for c in candidates]
        scores = openbrain.score_relevance(topic.core_paper_ids, texts)
        kept = [c for c, score in zip(candidates, scores) if score >= radius]
        per_term[term] = len(kept)
        if not kept:
            continue
        stored = openbrain.store_papers(kept)
        for record in stored.get("results", []):
            paper_id = record["id"]
            if paper_id not in seen:
                seen.add(paper_id)
                topic.collected_paper_ids.append(paper_id)
                new_ids.append(paper_id)
    return {"per_term": per_term, "new_ids": new_ids}
