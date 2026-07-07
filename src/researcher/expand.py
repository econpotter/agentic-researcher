"""Expand a topic by following citations outward: from the papers a topic already
has, fetch each paper's references and citing works, keep only those still on-topic
(similarity to the topic's core papers, within the radius), and stop at the
citation-distance cap or the per-run paper budget. Deterministic; core papers are
read-only (the expansion never edits them).

openbrain returns citation neighbors as bibliographic metadata (title/doi/authors/
abstract) with NO library id — they aren't stored yet. So the driver dedups
neighbors by their DOI/title, stores the on-topic keepers (which mints a library
uuid), and walks outward from those minted uuids (openbrain.get_citations resolves
a uuid -> its DOI -> the OpenAlex work)."""

from __future__ import annotations

import re
from collections import deque

from .openbrain import Openbrain
from .relevance import is_relevant
from .topics import Topic

_WORD = re.compile(r"[a-z0-9]+")


def _key(candidate: dict) -> str:
    """Stable identity for a not-yet-stored neighbor (it has no library id). Uses
    the DOI when present, else a bibtex-slug-style key (first-author surname +
    year + leading title words) so DOI-less neighbors still dedup reliably."""
    doi = (candidate.get("doi") or "").strip().lower()
    if doi:
        return "doi:" + doi
    authors = candidate.get("authors") or []
    surname = ""
    if authors and authors[0].strip():
        first = authors[0].strip()
        surname = first.split(",")[0] if "," in first else first.split()[-1]
    surname = "".join(_WORD.findall(surname.lower()))
    year = str(candidate.get("year") or "")
    words = "-".join(_WORD.findall((candidate.get("title") or "").lower())[:6])
    slug = ":".join(p for p in (surname, year, words) if p)
    return "slug:" + slug if slug else ""


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
    expanded = set(topic.expanded_paper_ids)
    collected = set(topic.collected_paper_ids)
    seen_keys: set[str] = set()
    added = 0

    while frontier:
        paper_id, distance = frontier.popleft()
        if paper_id in expanded:
            continue
        expanded.add(paper_id)
        topic.expanded_paper_ids.append(paper_id)
        if distance >= max_citation_distance:
            continue

        neighbors = openbrain.get_citations(paper_id)
        fresh = []
        for candidate in neighbors:
            key = _key(candidate)
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            fresh.append(candidate)
        if not fresh:
            continue

        texts = [
            f"{c.get('title', '')} {c.get('abstract', '')}".strip() for c in fresh
        ]
        scores = openbrain.score_relevance(topic.core_paper_ids, texts)
        if len(scores) != len(fresh):
            raise ValueError(
                f"score_relevance returned {len(scores)} scores for "
                f"{len(fresh)} candidates walking {paper_id!r}"
            )
        for candidate, score in zip(fresh, scores):
            if not is_relevant(
                score, distance + 1, radius=radius, max_distance=max_citation_distance
            ):
                continue
            stored = openbrain.store_papers([candidate])
            results = stored.get("results", [])
            if not results:
                continue
            new_id = str(results[0]["id"])
            if new_id in collected:
                continue  # store deduped to a paper the topic already has
            collected.add(new_id)
            topic.collected_paper_ids.append(new_id)
            topic.citation_distance[new_id] = distance + 1
            frontier.append((new_id, distance + 1))
            added += 1
            if added >= max_papers_per_run:
                return {
                    "added": added,
                    "expanded": len(topic.expanded_paper_ids),
                    "stopped": "budget",
                }

    return {
        "added": added,
        "expanded": len(topic.expanded_paper_ids),
        "stopped": "frontier",
    }
