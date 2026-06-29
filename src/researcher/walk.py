"""A — citation frontier walk. Expand a front outward along citation edges,
keeping only candidates within the anchor relevance radius, bounded by depth and
per-run budget. Deterministic; anchors are read-only."""

from __future__ import annotations

from collections import deque

from .fronts import Front
from .gate import keep
from .openbrain_client import OpenbrainClient


def walk_front(
    front: Front,
    client: OpenbrainClient,
    *,
    radius: float,
    max_hops: int,
    per_run_budget: int,
) -> dict:
    if not front.anchor_paper_ids:
        raise ValueError("citation walk requires a non-empty anchor set")

    seeds = front.acquired_paper_ids or front.anchor_paper_ids
    frontier: deque[tuple[str, int]] = deque((pid, 0) for pid in seeds)
    known = set(front.acquired_paper_ids) | set(front.visited)
    added = 0

    while frontier:
        pid, hop = frontier.popleft()
        if pid in front.visited:
            continue
        front.visited.append(pid)
        if hop >= max_hops:
            continue
        neighbors = client.citation_neighbors(pid)
        fresh = [n for n in neighbors if n["id"] not in known]
        if not fresh:
            continue
        texts = [f"{n.get('title', '')} {n.get('abstract', '')}".strip() for n in fresh]
        cosines = client.relevance(front.anchor_paper_ids, texts)
        for n, cos in zip(fresh, cosines):
            nid = n["id"]
            if nid in known:
                continue
            if not keep(cos, hop + 1, radius=radius, max_hops=max_hops):
                continue
            client.store_paper(n)
            known.add(nid)
            front.acquired_paper_ids.append(nid)
            front.hop_depth[nid] = hop + 1
            frontier.append((nid, hop + 1))
            added += 1
            if added >= per_run_budget:
                return {"added": added, "visited": len(front.visited), "stopped": "budget"}
    return {"added": added, "visited": len(front.visited), "stopped": "frontier"}
