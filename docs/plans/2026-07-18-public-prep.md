# Public-Release Prep Implementation Plan (agentic-researcher)

> **For agentic workers:** Execute task-by-task. This plan PREPARES the repo
> for public release. Do NOT change repository visibility — the flip is a
> separate operator action after operator review. Do NOT touch the local
> `.env` file's token (operator rotates it manually, server-side).

**Goal:** Fix the four public-readiness findings from the 2026-07-18 recon and
rewrite the README as informative, public-facing documentation.

**Tech Stack:** Python/uv project; Markdown.

## Global Constraints

- Do NOT run `gh repo edit`, change visibility, or push. Local commits only.
- Do NOT read, print, copy, or move the value in the untracked `.env` — its
  token is being rotated by the operator.
- README and any prose follow `~/.config/agents/references/writing-style.md`:
  plain, concrete, no hype, honest alpha status.

---

### Task 1: Remove the personal cert path from tracked config

**Files:**
- Modify: `config.yaml` (line ~12 hardcodes a personal absolute cert path under the operator's home directory)
- Modify: `.env.example` (document the new variable)

- [ ] **Step 1: Find how the cert path is consumed.** `grep -rn "caddy-rhythm\|cert" --include="*.py" --include="*.yaml" .` — identify the config key and the code that reads it.

- [ ] **Step 2: Replace the hardcoded path.** Set the config value to `null`
(or remove the key if the loader tolerates absence) and make the code accept
an environment-variable override (name it after the existing env-var naming
pattern in the repo, e.g. `AGENTIC_RESEARCHER_TLS_CERT` — match whatever
prefix the repo already uses). Add the variable to `.env.example` with a
comment: local TLS cert path for the private MCP endpoint, unset by default.

- [ ] **Step 3: Verify.**

```bash
grep -rn "/home/" --include="*.yaml" --include="*.py" . && echo "FIX" || echo "clean"
uv run pytest -q 2>&1 | tail -2
```

Expected: `clean`; tests green (or unchanged from pre-task baseline — record
the baseline first with the same command).

- [ ] **Step 4: Commit** — `git add -A && git commit -m "fix: cert path via env var, not tracked personal path"`

---

### Task 2: Delete legacy planning docs with workspace paths

**Files:**
- Delete: `docs/superpowers/` (legacy plan docs containing orchestra/workspace paths; git history preserves them; the operator's docs convention has moved to top-level `docs/plans|specs|design`)

- [ ] **Step 1:** `git rm -r docs/superpowers` (verify first that nothing under it is referenced elsewhere: `grep -rn "docs/superpowers" --include="*.md" --include="*.py" . | grep -v "^docs/superpowers"` — expect no hits outside the directory itself; if hits exist, fix the referrers in this task).

- [ ] **Step 2: Commit** — `git commit -m "docs: remove legacy planning docs ahead of public release"`

---

### Task 3: Complete AGENTS.md

**Files:**
- Modify: `AGENTS.md` (two TODO placeholders per recon)

- [ ] **Step 1:** Locate: `grep -n "TODO\|<TODO" AGENTS.md`. Fill each from the
repo's actual state (read the code/config to state true facts — purpose,
commands, constraints). No invented capabilities; if a fact is unknowable from
the repo, state the honest unknown rather than a placeholder.

- [ ] **Step 2: Verify** — `grep -n "TODO" AGENTS.md` → no output.

- [ ] **Step 3: Commit** — `git commit -am "docs: complete AGENTS.md"`

---

### Task 4: Rewrite README, public-facing (operator's headline requirement)

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write for a stranger arriving from a Projects link.** Structure:
  - What it is, 2-3 plain sentences: an agentic research assistant that
    acquires papers/articles and feeds a personal knowledge pipeline (state
    what it ACTUALLY does today — read the code and existing docs; do not
    oversell planned features).
  - Status line: "Alpha — in active development; interfaces change freely."
  - Install and run: exact working commands (`uv sync`, actual entry points).
  - Configuration: `.env.example` variables, one line each.
  - Relationship to openbrain (it feeds it) in one sentence, if accurate.
  - License: MIT.

- [ ] **Step 2: Style check** — no marketing language, no unproven claims,
matches the operator's style guide. Then: `grep -nE "/home/|rhythm\.herknet" README.md` → no output.

- [ ] **Step 3: Commit** — `git commit -am "docs: public-facing README rewrite"`

- [ ] **Step 4: Report** — full new README text in the report for operator
review, plus confirmation of Tasks 1-3 verifications. Explicit line: "ready
for operator flip after README approval and token rotation." No visibility
change, no push.
