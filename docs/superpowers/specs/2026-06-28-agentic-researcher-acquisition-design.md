# Agentic Researcher — Acquisition & Expansion Design

Date: 2026-06-28
Status: design approved, pre-implementation
Scope: whole-loop framing (C) + buildable acquisition/expansion engine (A). The
generative layer (B: synthesis, gap analysis, ideation) is framed here but specced
and built as a later sub-project.

## 1. Purpose

Build a new repo, `agentic-researcher`, that owns an automated economics-research
process on top of openbrain. Two goals:

1. **Grow and relate a large library** of relevant papers (citation substrate for
   future lit reviews and journal articles).
2. **Surface gaps and new ideas** over that library — the higher-value goal.

openbrain already ships the deterministic primitives (`acquire`, `search_library`,
`search_findings`, `query_library`, `coverage`, `export_bibtex`, `fetch_paper`) and
**deliberately owns no agenda** (issue #004: "a driver calls `openbrain acquire
<query>`; openbrain owns no scheduler"). The agentic-researcher repo is that driver.
Orchestra is the harness that runs the driver's generative work as queue issues.

## 2. The seam: deterministic vs. AI

The architecture is one horizontal line. Below it = mechanical, verifiable, no
hallucination risk. Above it = generative, requires a verification harness.

```
   AI / generative      IDEATION    gaps, novel questions          ← goal 2 (B)
                        SYNTHESIS   lit review, claims w/ cites
                        TRIAGE      "is this term/paper worth it?"
══════════════════════ THE SEAM ═══════════════════════════════════════════════
   deterministic        ACQUIRE     openbrain acquire <query>        ← goal 1 (A/C)
                        RELATE      embeddings + findings links
                        STORE       library, dedup, bibtex
                        RETRIEVE    search_library / search_findings
```

Invariants of the seam:

- The AI layer reaches the library **only through openbrain's tools** — never sources
  or DB directly. Every generative claim must trace to a retrieved row with a citation.
  No tool call = no provenance = reject.
- **C and A are code, not agents.** They are deterministic Python calling openbrain.
  No LLM in the acquisition/expansion loop.
- The LLM layer (B + term-suggestion + triage) runs as orchestra agent-issues with
  prompts stored in the repo.

## 3. Two acquisition jobs: C (enter) and A (expand)

These are different jobs, not sequential steps:

| | job | driven by | when | LLM |
|---|---|---|---|---|
| **C** harvest | **enter** a literature you are not in yet | a text term | occasional — "I care about X now" | no |
| **A** walk | **expand** literatures you are already in | the library itself | continuous, deterministic | no |

With a base library already ingested, **the library is the seed**: A's frontier-zero
is the papers you already have, so A can run with an empty term list. C is only for
opening doors into subfields you have no papers in.

### 3.1 C — harvest (ships first, always on)

For each term in a front's `terms` list: run `openbrain acquire(query)`, optionally
`since:`-filtered to catch new publications. `acquire` already dedups on store and is
recall-gated, so re-runs pollute nothing — repetition only wastes some API calls
returning known IDs. Accepted papers join the front's `acquired_paper_ids`.

### 3.2 A — citation frontier walk (flag-gated, built now, enabled later)

The "mutable query" is **structural, not textual**: advance a frontier through the
citation graph rather than rewriting query text.

- From the front's current frontier (initially its members), fetch each paper's
  **references** (older, foundational) and **citing works** (newer follow-ons).
- **Visited-set** of paper IDs guarantees no walk ever re-fetches.
- The walk is **outward-biased** by construction (citations point to work you do not
  have) — the opposite of the LLM-text-mutation failure mode, where a model searches
  adjacent to what it already knows and the library narrows into an echo chamber.
- Each candidate passes the **relevance gate** (§4) or is dropped.
- Accepted candidates join `acquired_paper_ids` and the next frontier.

**Connector dependency (must confirm before building A):** citation-graph walking
requires source connectors to expose references / citing-works. OpenAlex and Semantic
Scholar do; openbrain's current connectors (arXiv/NBER/SSRN/USDA-ERS per #002) may not.
If absent, a small openbrain connector addition is a prerequisite for A.

### 3.3 The expansion flag

```yaml
expansion: none        # C only — harvest terms, dedup-store, stop
# expansion: citation  # enable A — walk the frontier from each front
```

A is strictly additive — it consumes C's output. Ship C, ingest the user's existing
papers, run C, then flip the flag. No rework.

## 4. The relevance gate (A's keep/drop)

Deterministic, below the seam, three parts — two fixed, one chosen (= anchor centroid).

1. **Metric (fixed):** cosine similarity on title+abstract embeddings (available at
   acquire time, pre-ingest). `keep if cosine(candidate, centroid) >= relevance_radius`.
   Findings-overlap may *refine* later (post-ingest); v1 gates on embeddings only,
   because findings do not yet exist for a brand-new candidate.
2. **Backstops (fixed, non-negotiable):**
   - **max_hops** per front — cap citation depth from any anchored paper.
   - **per_run_budget** — max papers added per run; hard cost ceiling regardless of
     radius. Both bound drift *and* token/API cost, and defeat stepping-stone drift
     (A~B, B~C, C~D, but D far from A).
3. **Anchor (chosen): per-front centroid.** Every candidate, however deep in the walk,
   is judged against the **fixed front anchor** — not its parent paper, not a moving
   target. This is what kills stepping-stone drift. (Rejected alternatives: nearest-
   library-paper drifts by construction; global library centroid is multi-topic mush.)

**Default tunables** (config.yaml; all are starting points — tune on real fronts):

| knob | default | meaning / how to tune |
|---|---|---|
| `relevance_radius` | `0.40` | min cosine to keep a candidate. **Model-dependent — the first knob to tune.** Raise if A drifts off-topic; lower if it's too sparse. |
| `max_hops` | `2` | citation depth from an anchored paper. 3+ explodes (refs×citations per hop). |
| `per_run_budget` | `200` | max papers added per run — hard cost ceiling regardless of radius. |
| anchor bootstrap top-K | `10` | size of the initial anchor set seeded from the defining query (§5.2). |

## 5. Fronts

A front is a **named topic with a curated, walk-immutable anchor and walk-state**.
Fronts are **driver state, stored in the agentic-researcher repo** (not openbrain —
openbrain owns no agenda), as git-tracked toml, one file per front.

```toml
# fronts/water-rights.toml
label   = "water rights"            # IDENTITY — permanent, never churns
terms   = ["water rights",          # ACQUISITION INPUTS — a mutable list;
           "prior appropriation"]    #   add/remove freely, lose nothing
anchor_paper_ids   = ["W123", ...]  # RELEVANCE ANCHOR — curated allow-list
acquired_paper_ids = [...]          # everything harvested/walked (library value)
visited   = [...]                   # walk frontier state (no re-fetch)
hop_depth = {}                      # depth-cap bookkeeping
```

The front decouples **three things** that are easy to conflate:

- **label** — stable identity, survives everything.
- **terms** — a mutable list, each runs `acquire`. **Remove a term and you lose
  nothing**: acquired papers stay in the library, the anchor is untouched, the label
  persists. Removing a term only stops harvesting *that query*.
- **anchor_paper_ids** — the relevance reference, independent of term churn.

### 5.1 The centroid is computed, never stored

Front files hold IDs and config, never a raw vector. The centroid is **recomputed at
run time** by pulling the anchor members' embeddings from openbrain and averaging. No
embedding duplication; openbrain stays the single source of vectors.

### 5.2 Anchor lifecycle — walk-immutable, human-curated

The invariant is not "anchors never change" — it is "**the walk** never changes them":

- The **walk MUST NOT** touch anchors (no automatic drift — the discipline).
- **You MAY** edit anchors anytime (deliberate curation — the steering).
- The **centroid is a pure function of the current anchor set**, recomputed each run.
  Adding a paper shifts the centroid **on purpose**.

**Setting them initially:** the defining query pre-populates the set as a starting
guess — top-K of the term's `acquire` (C path) or `search_library(query)` (library-
label path). Then curate.

**Adding them later** (the "we didn't know that foundational paper existed" case — the
system is *designed* to surface it):

1. **Promotion from the walk** (the elegant loop): A pulls in a high-relevance, high-
   citation paper as `acquired`; in review you promote its ID from `acquired_paper_ids`
   to `anchor_paper_ids`. The walk *discovers* candidate anchors; you *canonize* them.
   Anchors improve over time through curation.
2. **Direct pin:** find a paper via `search_library`/`search_findings`, add its ID.

**Consequence of an anchor change:** the centroid shifts, so the gate changes. Default
= **affects future walk steps only**. Rejected candidates are *not* marked `visited`,
so a better anchor naturally lets them back in on the next walk. Optional explicit
`re-gate` re-scores the rejected pool against the new centroid for immediate effect.

### 5.3 Creating a front

Two paths, both reducing to "a query that picks an initial member set whose mean
becomes the anchor":

1. **From a C seed term (automatic):** add term → C runs `acquire` → accepted results
   seed `anchor_paper_ids` and `acquired_paper_ids`.
2. **From a library label (one-time declare):** declare label + selector query →
   `search_library(query)` top-K seed the anchor. Turns the already-ingested corpus
   into fronts A can expand, with no re-acquisition.

## 6. The generative layer (B) — framed, not specced here

B sits entirely above the seam and is the next sub-project. Its reliability rule:
**every synthesized claim must cite a retrieved finding** (`search_findings` row with a
citation); unsourced claims are rejected. Triggers are event/you-driven, not calendar:

- **You-initiated:** run a gap review on demand.
- **Accumulation-triggered (later):** when a front's new-paper count crosses a
  threshold since its last review, enqueue a gap run.
- **Weekly digest (optional):** gap analysis focused on papers added since the last
  analysis vs. the standing library.

Term-suggestion (subfield jumps) is a **proposal you approve** into a front's `terms`,
never an autonomous loop — to avoid inward query drift.

## 7. Repo layout

A new project repo at **`projects/agentic-researcher`** (its own git repo, scaffolded
from `project-template`), registered in orchestra `PROJECTS.md` with queue
`queue/agentic-researcher.md`. Doc filenames follow the template
(AGENTS.md / CLAUDE.md / README.md / ARCHITECTURE.md / ROADMAP.md / docs/).

(Alternative home considered: a subdir of `ai-stack` next to openbrain, since it drives
openbrain. Rejected — own repo gives clean lifecycle, own queue, own AGENTS.md. openbrain
is reached as a service, not a code dependency.)

```
projects/agentic-researcher/
  README.md            # ★ the user's steering surface (see §8)
  AGENTS.md            # agent operating manual + one-line orchestra-guide pointer
  CLAUDE.md            # Claude-Code-specific notes (points at AGENTS.md)
  ARCHITECTURE.md      # the seam, C/A/B design, front model (narrative of this spec)
  ROADMAP.md           # build order (§9) + B as the next sub-project
  docs/
    superpowers/specs/ # this design (copied in at repo creation)
  config.yaml          # expansion flag, relevance_radius, max_hops, per_run_budget,
                       #   openbrain endpoint, term-rotation policy
  fronts/              # ★ per-front state, git-tracked toml
    water-rights.toml
  researcher/          # deterministic package
    fronts.py          # front model: load/save, anchor add/remove/promote, centroid
    harvest.py         # C: acquire terms → dedup-store
    walk.py            # A: citation frontier walk
    gate.py            # relevance gate: cosine vs centroid + depth/budget caps
    openbrain_client.py# thin wrapper over openbrain MCP/CLI
    cli.py             # researcher front|term|anchor|harvest|walk ...
  prompts/             # LLM task prompts (generative layer)
    gap-analysis.md    # B
    term-suggest.md    # subfield-jump proposals (user-approved)
  tests/
```

### 7.1 Orchestra integration (light, two paths)

- **Deterministic loop:** cron runs `researcher harvest` / `researcher walk` directly.
  No agent, no queue.
- **Generative loop:** orchestra enqueues a gap-analysis issue; an ephemeral agent runs
  it with a prompt from `prompts/`.

## 8. README — the user's control panel

The README is the most important deliverable: it reads as instructions to the user, not
API docs. It must document every steering action:

- Add / remove a **term** from a front (and what is/ isn't lost).
- Declare a **front** from a library label.
- **Anchor** ops: `anchor add`, `anchor remove`, promote from acquired.
- Flip **`expansion: citation`** on to enable A.
- Run a **gap analysis** (once B exists).
- Tune the **gate** (`relevance_radius`, `max_hops`, `per_run_budget`).

`fronts/*.toml` are hand-editable; `cli.py` is sugar over them. State is versioned and
diff-able in git.

## 9. Build order

1. Repo scaffold from `project-template` at `projects/agentic-researcher`: README,
   AGENTS.md, CLAUDE.md, ARCHITECTURE.md, ROADMAP.md, config.yaml, package skeleton;
   register in orchestra `PROJECTS.md` + create `queue/agentic-researcher.md`.
2. Front model (`fronts.py`) + CLI front/term/anchor ops + tests.
3. C harvest (`harvest.py`) over the term list via openbrain `acquire` + dedup.
4. Ingest the user's existing papers (base library) — establishes A's frontier-zero
   and seed anchors.
5. Confirm connector citation-edge support; if absent, openbrain connector add.
6. Relevance gate (`gate.py`) + A walk (`walk.py`), behind `expansion` flag (default
   `none`); tests with recorded fixtures, no live network.
7. Enable `expansion: citation`, tune radius/hops/budget on real fronts.
8. (Later sub-project) B: gap analysis prompt + orchestra issue wiring.

## 10. Non-goals / deferred

- Unsupervised auto-clustering of the whole library into fronts (v1 = named fronts).
- LLM query-text mutation in the nightly loop (drift risk; reserved for user-approved
  subfield jumps only).
- B (synthesis/gap/ideation) implementation — framed here, specced separately.
- Findings-based gating in v1 (embeddings only; findings refine later).
```

