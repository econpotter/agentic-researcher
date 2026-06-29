"""Relevance check for citation expansion: keep a candidate paper iff it is on-topic
(its similarity to the topic's core papers, computed by openbrain, clears the radius)
AND within the citation-distance cap. The per-run paper budget is enforced by the
expansion loop, not here."""

from __future__ import annotations


def is_relevant(
    similarity: float,
    citation_distance: int,
    *,
    radius: float,
    max_distance: int,
) -> bool:
    return similarity >= radius and citation_distance <= max_distance
