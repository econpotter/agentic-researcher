# Tuning the citation walk

The A-walk's behavior is set by four knobs in `config.yaml`. All have spec
defaults (§4 of the acquisition design spec); they are starting points, tuned on
real fronts.

| knob | default | what it does |
|------|---------|--------------|
| `relevance_radius` | `0.40` | min cosine (candidate vs anchor centroid) to keep a walked paper |
| `max_hops` | `2` | citation depth from an anchored paper |
| `per_run_budget` | `200` | max papers added per `walk` run — a hard cost ceiling |
| `anchor_bootstrap_k` | `10` | size of the initial anchor set when declaring a front from the library |

## `relevance_radius` — the first knob to tune

It is **model-dependent** (it's a cosine on whatever embedding openbrain uses), so
the default `0.40` is only a starting point.

- **Walk drifts off-topic** (pulls in tangential papers) → **raise** it (e.g. 0.45, 0.50).
- **Walk is too sparse** (keeps almost nothing) → **lower** it (e.g. 0.35, 0.30).

Judge by reviewing what a run added (`researcher front show` + the library), not by
the number alone. Better anchors also tighten relevance — curating
`anchor_paper_ids` (see README) is often more effective than chasing the radius.

## `max_hops` vs `per_run_budget` — the two backstops

These bound drift and cost *independently of the radius*, so a loose radius can't
run away:

- **`max_hops`** caps how far from your anchored papers the walk reaches. Each hop
  multiplies (references × citing-works), so depth is expensive — `3+` explodes.
  Keep it at `2` unless a literature is small and well-bounded.
- **`per_run_budget`** caps papers added per run. Hit it and the walk stops with
  `stopped: "budget"`; run again later to continue from the saved frontier
  (`visited`/`hop_depth` persist in the front file). Use it to pace API/compute.

## Why anchors are frozen against the walk

The walk reads anchors but never edits them — relevance is always judged against
the *fixed* anchor set, not the parent paper. That's what stops stepping-stone
drift (A~B~C~D where D is far from A). To move a topic deliberately, curate anchors
yourself (`anchor add/remove/promote`); the walk will then score against the new set
on its next run.
