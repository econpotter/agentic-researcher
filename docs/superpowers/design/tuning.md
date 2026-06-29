# Tuning citation expansion

`researcher expand` is governed by four knobs in `config.yaml`. Defaults follow the
acquisition design spec §4; they are starting points, tuned on real topics.

| knob | default | what it does |
|------|---------|--------------|
| `relevance_radius` | `0.40` | min similarity (candidate vs the topic's core papers) to keep a paper |
| `max_citation_distance` | `2` | how many citation hops from a core paper expansion reaches |
| `max_papers_per_run` | `200` | max papers added per `expand` run — a hard cost ceiling |
| `core_bootstrap_count` | `10` | core papers seeded when creating a topic from the library |

## `relevance_radius` — the first knob to tune

It is **model-dependent** (a similarity score from whatever embedding openbrain uses),
so the default `0.40` is only a starting point.

- **Expansion drifts off-topic** (pulls in tangential papers) → **raise** it (0.45, 0.50).
- **Expansion is too sparse** (keeps almost nothing) → **lower** it (0.35, 0.30).

Judge by reviewing what a run added (`researcher topic show` + the library), not the
number alone. Better core papers also tighten relevance — curating `core_paper_ids` is
often more effective than chasing the radius.

## `max_citation_distance` vs `max_papers_per_run` — the two backstops

These bound drift and cost *independently of the radius*, so a loose radius can't run
away:

- **`max_citation_distance`** caps how far from your core papers expansion reaches.
  Each hop multiplies (references × citing works), so distance is expensive — `3+`
  explodes. Keep it at `2` unless a literature is small and well-bounded.
- **`max_papers_per_run`** caps papers added per run. Hit it and expansion stops with
  `stopped: "budget"`; run again later to continue from the saved frontier
  (`expanded_paper_ids` / `citation_distance` persist in the topic file). Use it to
  pace API/compute.

## Why core papers are read-only during expansion

Expansion reads the core papers but never edits them — relevance is always judged
against the *fixed* core set, not the parent paper. That stops stepping-stone drift
(A~B~C~D where D is far from A). To move a topic deliberately, curate the core papers
yourself (`core add/remove/promote`); expansion will then score against the new set on
its next run.
