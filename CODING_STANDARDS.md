# Coding standards

Read and apply `~/.config/agents/references/coding-standards.md`.

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

## Hard constraints

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
