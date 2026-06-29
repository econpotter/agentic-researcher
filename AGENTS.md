# AGENTS.md — agentic-researcher

## What this repo is

<TODO: one paragraph — what agentic-researcher does, who consumes it, and what it does
NOT own. Keep it concrete.>

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

1. `ROADMAP.md` — scope and status.
2. `docs/superpowers/` — specs and plans for active work.
3. `ARCHITECTURE.md` — system design, **if the project has one** (it is optional;
   add it only when there is real design to record).

## Layout

This is the single source for the directory map — do not duplicate it elsewhere.

<TODO: replace with the real tree, e.g.>

```
src/agentic_researcher/   package code
tests/              test suite
docs/superpowers/   specs + plans
scripts/            ops entrypoints
```

## Commands

- `just setup` — install dependencies + git hooks
- `just test` · `just lint` · `just fmt` — verify before declaring work done
- <TODO: run entry points, e.g. `python -m agentic_researcher ...`>

## Hard constraints

<TODO: the invariants an agent must not violate — single source of truth for schema,
identifier-agnostic logic, "never import X", secrets in `.env` only. Delete if none.>

If working with orchestra, run `orchestra guide`.
