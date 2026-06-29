"""Expand a topic by following citations outward: from the papers a topic already
has, fetch each paper's references and citing works, keep only those still on-topic
(similarity to the topic's core papers, within the radius), and stop at the
citation-distance cap or the per-run paper budget. Deterministic; core papers are
read-only (the expansion never edits them)."""

from __future__ import annotations

from collections import deque

from .openbrain import Openbrain
from .relevance import is_relevant
from .topics import Topic


def expand_by_citations(
    topic: Topic,
    openbrain: Openbrain,
    *,
    radius: float,
    max_citation_distance: int,
    max_papers_per_run: int,
) -> dict:
    if not topic.core_paper_ids:
        raise ValueError("citation expansion needs at least one core paper")

    seeds = topic.collected_paper_ids or topic.core_paper_ids
    frontier: deque[tuple[str, int]] = deque((pid, 0) for pid in seeds)
    known = set(topic.collected_paper_ids) | set(topic.expanded_paper_ids)
    added = 0

    while frontier:
        paper_id, distance = frontier.popleft()
        if paper_id in topic.expanded_paper_ids:
            continue
        topic.expanded_paper_ids.append(paper_id)
        if distance >= max_citation_distance:
            continue
        citations = openbrain.get_citations(paper_id)
        fresh = [c for c in citations if c["id"] not in known]
        if not fresh:
            continue
        texts = [f"{c.get('title', '')} {c.get('abstract', '')}".strip() for c in fresh]
        scores = openbrain.score_relevance(topic.core_paper_ids, texts)
        for candidate, score in zip(fresh, scores):
            candidate_id = candidate["id"]
            if candidate_id in known:
                continue
            if not is_relevant(
                score, distance + 1, radius=radius, max_distance=max_citation_distance
            ):
                continue
            openbrain.store_paper(candidate)
            known.add(candidate_id)
            topic.collected_paper_ids.append(candidate_id)
            topic.citation_distance[candidate_id] = distance + 1
            frontier.append((candidate_id, distance + 1))
            added += 1
            if added >= max_papers_per_run:
                return {
                    "added": added,
                    "expanded": len(topic.expanded_paper_ids),
                    "stopped": "budget",
                }
    return {"added": added, "expanded": len(topic.expanded_paper_ids), "stopped": "frontier"}
