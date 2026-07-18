# AGENTS.md — agentic-researcher

## What this repo is

`agentic-researcher` is a deterministic Python driver that grows and relates a paper
library on top of **openbrain**. You steer it through named *topics* (git-tracked toml
files under `topics/`): it collects papers for a topic's search terms and, when enabled,
expands outward along the citation graph, keeping only papers relevant to that topic's
curated *core* papers. It runs locally and talks to a hosted openbrain over a FastMCP
client (SSH tunnel); the human operator drives it — it does not self-steer. openbrain
owns paper storage, retrieval, embeddings, and relevance scoring; this repo owns the
research agenda (topics, terms, core-paper curation, the collect/expand policy). It does
NOT store papers, compute embeddings, or expose a service of its own.

## Lifecycle: alpha

- **alpha** — pre-production: prefer the clean rewrite (reshape schemas, drop/recreate
  re-derivable data, break interfaces). No compat shims, dual-writes, or staged
  migrations unless asked.
- **beta** — same bias; rewrite carefully toward the best architecture.
- **production** — preserve schemas/interfaces/data, migrate safely, defer features
  rather than break compatibility.

Only the rules for the stage above apply.

## Engineering standards

- **Correct, complete solutions** over the minimal fix that just makes tests pass.
  Production behavior is the bar; verify the real code path, not mocks that go green
  while it stays broken.
- **No hack + "known limitation"** when the right fix is known and in scope — defer the
  proper fix only with explicit sign-off.
- **Modular, DRY, single-responsibility** — extract tangled data, if/elif that's really a
  lookup, and copy-paste special-cases into registries/config; keep files focused.
- **TDD** — failing test → minimal code → green → refactor.
- **Restructure proactively** — the existing structure is not a constraint. "It works" /
  "bigger change" / "don't duplicate" are not reasons to keep debt; surface the right
  restructuring as the primary option with its real cost.

## First reads

1. `README.md` — what the tool does and how to run it.
2. `ROADMAP.md` — scope and status.
3. `docs/plans/` and `docs/specs/` — plans and specs for active work (created as needed).
4. `ARCHITECTURE.md` — system design, **if the project has one** (it is optional;
   add it only when there is real design to record).

## Layout

This is the single source for the directory map — do not duplicate it elsewhere.

```
src/researcher/       package code (the `researcher` CLI + driver logic)
  cli.py              argparse CLI over the topics/ toml files
  config.py           config.yaml loader + env-var secrets (token, CA cert)
  openbrain.py        FastMCP client — the single seam to hosted openbrain
  topics.py           Topic model + toml load/save
  collect.py          collect papers for a topic's search terms
  expand.py           citation-graph expansion (gated by config)
  relevance.py        relevance gating against a topic's core papers
tests/                pytest suite (one test_*.py per module)
scripts/              ops entrypoints (import_bibtex.py)
topics/               git-tracked per-topic toml state
docs/plans/           plans; docs/specs/ for specs (created as needed)
config.yaml           acquisition/expansion policy + openbrain endpoint
```

## Commands

- `just setup` — install dependencies + git hooks (`uv sync` + `pre-commit install`)
- `just test` · `just lint` · `just fmt` — verify before declaring work done
  (`uv run pytest` · `uv run ruff check` · `uv run ruff format`)
- `uv run mypy src` — type-check (strict mode; must pass before committing)
- `uv run researcher <command>` — run the CLI (e.g. `researcher topic list`,
  `researcher collect "<topic>"`); see `README.md` for the full command set

## Hard constraints

- **openbrain owns the library.** Paper storage, embeddings, retrieval, and relevance
  scoring live in openbrain. This repo never persists papers or recomputes embeddings;
  it only curates topics and calls openbrain tools through `openbrain.py`.
- **`openbrain.py` is the only seam.** All MCP calls go through it so tests can inject a
  stand-in; do not open FastMCP clients elsewhere.
- **The Topic dataclass is the single source of truth for topic schema.** Load/save
  derive from it (`fields()` / `asdict()`); don't hand-code toml key lists.
- **Secrets and personal paths stay out of tracked files.** The MCP bearer token comes
  from `OPENBRAIN_MCP_TOKEN`; a self-signed CA cert path comes from `OPENBRAIN_CA_CERT`
  (both read from `.env`, which is git-ignored). `config.yaml` must not hardcode a
  personal filesystem path.
- **Core papers are curated, never automatic.** Expansion measures relevance against a
  topic's `core_paper_ids` but must never add to or reorder them.

If working with orchestra, run `orchestra guide`.
