"""Relevance gate: keep a walked candidate iff it is on-topic (cosine vs the
front's anchor set, computed by openbrain) AND within the depth cap. Per-run
budget is enforced by the walk loop."""

from __future__ import annotations


def keep(cosine: float, hop: int, *, radius: float, max_hops: int) -> bool:
    return cosine >= radius and hop <= max_hops
