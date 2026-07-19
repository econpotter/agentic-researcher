# agentic-researcher

An agentic research assistant. It grows and relates a paper
library on top of [**openbrain**](https:github.com/econpotter/openbrain) (or any other DB you like with a little plumbing): you define named research *topics*, and it collects
papers for each topic's search terms and — when you enable it — expands outward along the
citation graph, keeping only papers relevant to the papers you've marked as defining the
topic. The result is a curated substrate for later literature reviews and idea generation.

It runs deterministic Python on your machine and talks to a hosted openbrain instance as a
[FastMCP](https://github.com/jlowin/fastmcp) client (typically over an SSH tunnel).
openbrain owns paper storage, retrieval, embeddings, and relevance scoring; this repo owns
the research agenda. You steer it — it does not self-steer.

## Status

**Alpha — in active development; interfaces, config, and on-disk formats change freely.**
There are no backward-compatibility guarantees yet.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management
- Access to a running openbrain MCP endpoint and its bearer token

## Install

```sh
uv sync                 # install dependencies into a local .venv
```

Or, if you use [just](https://github.com/casey/just):

```sh
just setup              # uv sync + install the pre-commit git hooks
```

Then configure it (see below) and run the CLI:

```sh
uv run researcher topic list
```

## Configuration

Two files:

- **`config.yaml`** — acquisition/expansion policy and the openbrain connection. Set
  `openbrain_mcp_url` to your MCP endpoint. Each key is documented inline.
- **`.env`** — secrets and personal paths, git-ignored. Copy `.env.example` to `.env` and
  fill in:
  - `OPENBRAIN_MCP_TOKEN` — bearer token for the hosted openbrain MCP server.
  - `OPENBRAIN_CA_CERT` — optional local path to a CA cert if the MCP endpoint uses
    self-signed TLS; overrides `openbrain_ca_cert` in `config.yaml`. Leave unset otherwise.

## Usage — your control panel

Everything is a **topic**: a named research area stored as a git-tracked toml file under
`topics/`. The `researcher` CLI is sugar over those files (you can also hand-edit them).

A topic keeps three things separate, on purpose:

- **name** — its identity (permanent).
- **search_terms** — the queries it collects papers for (a mutable list; removing one
  loses nothing else).
- **core_paper_ids** — the papers that *define* the topic; expansion measures relevance
  against these. You curate them; expansion never moves them.

Run any command with `uv run researcher ...`.

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

Core papers define what "on-topic" means for expansion. They change **only** when you say
so:

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

Expansion follows each paper's references and citing works, keeps only those within
`relevance_radius` of the topic's core papers, and stops at `max_citation_distance` or
`max_papers_per_run`. Those knobs live in `config.yaml`, documented inline.

### Inspect

```sh
researcher topic list
researcher topic show "Water Rights"
```

## Development

```sh
uv run pytest           # tests
uv run ruff check       # lint
uv run ruff format      # format
uv run mypy src         # type-check (strict)
```

See `AGENTS.md` for working conventions and hard constraints.

## License

MIT — see [`LICENSE`](LICENSE).
