# agentic-researcher

Automated economics-research driver over openbrain: grows and relates a paper
library (deterministic harvest + citation-graph expansion), so future lit reviews
and idea-generation have a curated substrate. openbrain owns the library and
retrieval; this repo owns the agenda.

## Setup

- `just setup` — install dependencies + git hooks
- copy `.env.example` → `.env` and fill in secrets
- the openbrain CLI (`openbrain-ingest`) must be on PATH — this driver shells out to it

## Usage — your control panel

You steer the researcher; it does not self-steer. Everything is a **front** — a
named research topic stored as a git-tracked toml file under `fronts/`. The
`researcher` CLI is sugar over those files (you can also hand-edit them).

A front decouples three things, on purpose:
- **label** — its identity (permanent)
- **terms** — the search queries it harvests (a mutable list; removing one loses nothing else)
- **anchors** (`anchor_paper_ids`) — the relevance reference for expansion (curated by you, never moved by the walk)

### Open a front and harvest (C — enter a literature)

```sh
researcher front create "Water Rights" --term "water rights" --term "prior appropriation"
researcher term add "Water Rights" "water markets"      # add/remove terms anytime
researcher harvest "Water Rights"                        # run openbrain acquire for each term
```

Or seed a front from papers already in your library:

```sh
researcher front create-from-library "Water Rights" --query "water rights allocation"
```
This pulls the top-K semantic matches (`anchor_bootstrap_k`, default 10) as the
front's initial anchors.

### Curate anchors

Anchors define what "on-topic" means for the citation walk. They change **only**
when you say so:

```sh
researcher anchor add "Water Rights" <paper_id>       # pin a paper as canonical
researcher anchor remove "Water Rights" <paper_id>
researcher anchor promote "Water Rights" <paper_id>   # promote a walked paper -> anchor
```
`promote` is the loop: the walk surfaces a foundational paper, you canonize it.

### Expand along citations (A — deepen a literature)

Off by default. Enable in `config.yaml`:

```yaml
expansion: citation
```
Then:

```sh
researcher walk "Water Rights"     # no-op while expansion: none
```
The walk fetches each paper's references + citing works, keeps only those within
`relevance_radius` of the front's anchors, bounded by `max_hops` and
`per_run_budget`. See `docs/superpowers/design/tuning.md` for the knobs.

### Inspect

```sh
researcher front list
researcher front show "Water Rights"
```

## Development

- `just test` · `just lint` · `just fmt`

See `AGENTS.md` for working conventions. If the project has an `ARCHITECTURE.md`,
read it before changing code.
