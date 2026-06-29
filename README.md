# agentic-researcher

Automated economics-research driver over openbrain: grows and relates a paper
library (deterministic collection + citation-graph expansion), so future lit reviews
and idea-generation have a curated substrate. openbrain owns the library and
retrieval; this repo owns the agenda.

It runs deterministic Python on this machine and talks to the **hosted openbrain**
as a FastMCP client over your SSH tunnel — the local openbrain checkout is dev-only.

## Setup

- `just setup` — install dependencies + git hooks
- copy `.env.example` → `.env`; set `OPENBRAIN_MCP_TOKEN` (the openbrain MCP bearer token)
- in `config.yaml`, set `openbrain_mcp_url` to your tunneled openbrain MCP endpoint

## Usage — your control panel

You steer the researcher; it does not self-steer. Everything is a **topic** — a named
research area stored as a git-tracked toml file under `topics/`. The `researcher` CLI
is sugar over those files (you can also hand-edit them).

A topic keeps three things separate, on purpose:
- **name** — its identity (permanent)
- **search_terms** — the queries it collects papers for (a mutable list; removing one loses nothing else)
- **core_paper_ids** — the papers that *define* the topic; expansion measures relevance against these. You curate them; the expansion never moves them.

### Open a topic and collect papers

```sh
researcher topic create "Water Rights" --term "water rights" --term "prior appropriation"
researcher term add "Water Rights" "water markets"     # add/remove terms anytime
researcher collect "Water Rights"                       # openbrain search for each term
```

Or seed a topic from papers already in your library:

```sh
researcher topic create-from-library "Water Rights" --query "water rights allocation"
```
This pulls the top matches (`core_bootstrap_count`, default 10) as the topic's initial
core papers.

### Curate the core papers

Core papers define what "on-topic" means for expansion. They change **only** when you
say so:

```sh
researcher core add "Water Rights" <paper_id>       # pin a paper as defining
researcher core remove "Water Rights" <paper_id>
researcher core promote "Water Rights" <paper_id>   # promote a collected paper -> core
```
`promote` is the loop: expansion surfaces a foundational paper, you canonize it.

### Expand along citations

Off by default. Enable in `config.yaml`:

```yaml
citation_expansion: true
```
Then:

```sh
researcher expand "Water Rights"     # no-op while citation_expansion: false
```
Expansion follows each paper's references + citing works, keeps only those within
`relevance_radius` of the topic's core papers, and stops at `max_citation_distance`
or `max_papers_per_run`. See `docs/superpowers/design/tuning.md`.

### Inspect

```sh
researcher topic list
researcher topic show "Water Rights"
```

## Development

- `just test` · `just lint` · `just fmt`

See `AGENTS.md` for working conventions. If the project has an `ARCHITECTURE.md`,
read it before changing code.
