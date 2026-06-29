# Agentic Researcher — Expansion (Gate + Citation Walk) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the deterministic A layer — a citation-graph frontier walk that expands each front outward from what it already has, bounded by an embedding relevance gate plus depth/budget caps — behind an `expansion` config flag (default off).

**Architecture:** The walk and gate are driver code in `researcher/` (policy: frontier, visited-set, hop-depth, budget, radius). The embedding-heavy and source-heavy work lives in **openbrain** as three new deterministic retrieval primitives the driver calls (citation-neighbor fetch, anchor-relative relevance scoring, single-paper store). No vectors cross the seam as data, and no agenda lives in openbrain — the driver passes radius/anchors/budget as parameters, exactly as `acquire(query, min_overlap=…)` already takes policy params. No LLM anywhere.

**Tech Stack:** Python 3.11+ (driver); openbrain Python (Typer CLI, asyncpg pool, OpenAlex source, embeddings) for the primitives. OpenAlex `referenced_works` + `cited_by` carry the citation edges.

## Global Constraints

- **Builds on the foundation plan** (`2026-06-29-foundation-fronts-and-harvest.md`): `Front`, `OpenbrainClient`, fronts CLI must exist.
- **The seam:** the driver reaches openbrain only via the `openbrain-ingest` CLI. Embeddings never leave openbrain as raw vectors — openbrain returns *cosines*; the driver decides keep/drop.
- **Deterministic, walk-immutable anchors:** the walk MUST NOT modify `anchor_paper_ids`; it only reads them (for relevance) and appends to `acquired_paper_ids`/`visited`/`hop_depth`. Anchor curation stays human-only (foundation plan's `anchor` CLI).
- **Default tunables (spec §4):** `relevance_radius = 0.40`, `max_hops = 2`, `per_run_budget = 200`, `anchor_bootstrap_k = 10`. All config, tuned on real fronts; `relevance_radius` is model-dependent and the first knob to tune.
- **Backstops are non-negotiable:** depth cap (`max_hops`) AND per-run budget (`per_run_budget`) bound drift and cost regardless of radius.
- **Anchor = per-front, frozen against the walk; relevance is judged against the anchor set, never the parent paper** (kills stepping-stone drift — spec §4).
- **Spec:** `docs/superpowers/specs/2026-06-28-agentic-researcher-acquisition-design.md` §3.2 (A walk), §4 (gate), §5.1–5.3 (anchors/centroid/library-label fronts).
- **openbrain repo:** `projects/ai-stack/openbrain` (unittest-style tests, mocked pool + monkeypatched HTTP/embeddings; `ruff` clean; no live network in tests).

---

### Task 1: openbrain primitives — citation neighbors, relevance, store-one (cross-repo)

**Files (in `projects/ai-stack/openbrain`):**
- Modify: `openbrain/sources.py` (OpenAlex citation-edge fetch)
- Modify: `openbrain/brain.py` (relevance scoring helper; reuse the existing `embed` + stored-embedding access)
- Modify: `openbrain/cli.py` (three new commands, JSON out via `_emit`)
- Test: `openbrain/tests/test_sources.py`, `openbrain/tests/test_brain.py`, `openbrain/tests/test_cli.py` (follow existing offline patterns: monkeypatched HTTP/embeddings, mocked pool)

**Proposed surface (confirm exact shapes against openbrain conventions while implementing):**

- `sources.openalex_citation_neighbors(openalex_id: str) -> list[PaperMeta]` — one OpenAlex `works/{id}` fetch; read `referenced_works` (outbound) and follow `cited_by_api_url` (inbound, first page); return de-duplicated `PaperMeta` (the existing TypedDict: id/title/abstract/doi/year/...), reusing `_openalex_record`.
- `brain.relevance(anchor_ids: list[str], candidate_texts: list[str]) -> list[float]` — centroid = mean of the stored embeddings for `anchor_ids` (read from the library table; skip ids with no embedding); embed each candidate text via the existing `brain.embed`; return cosine(centroid, candidate) per text. Empty `anchor_ids` or empty centroid → raise `ValueError` (the walk requires anchors).
- `brain.store_one(meta: dict) -> dict` — thin wrapper over the existing `store_acquired_paper(meta)`; returns `{"id", "title", "deduped"}`.

**CLI commands (all `_emit` JSON):**
- `citations <openalex_id>` → `{"neighbors": [PaperMeta, ...]}`
- `relevance --anchor <id> [--anchor <id> ...] --text <t> [--text <t> ...]` → `{"cosines": [float, ...]}` (order matches `--text`)
- `store-paper --json '<meta>'` → `{"id", "title", "deduped"}`

- [ ] **Step 1: Failing tests** — add, mirroring existing offline patterns:
  - `test_sources.py`: monkeypatch the OpenAlex HTTP fetch to a fixture work with `referenced_works: ["W2"]` + a `cited_by` page `[{...W3...}]`; assert `openalex_citation_neighbors("W1")` returns metas for `W2` and `W3`, de-duplicated.
  - `test_brain.py`: stub the pool to return anchor embeddings `[[1,0],[0,1]]` for two ids and monkeypatch `embed` to return `[1,0]`; assert `relevance(["A","B"], ["t"])` returns `[cos([0.5,0.5],[1,0])]` ≈ `[0.7071]` (one element, correct value); assert `relevance([], ["t"])` raises `ValueError`.
  - `test_cli.py`: assert each new command parses and `_emit`s the expected JSON keys (monkeypatch the brain/sources funcs).

- [ ] **Step 2: Run, verify fail**

Run: `cd projects/ai-stack/openbrain && uv run pytest tests/test_sources.py tests/test_brain.py tests/test_cli.py -q`
Expected: FAIL (missing functions/commands).

- [ ] **Step 3: Implement** the three functions + three CLI commands per the surface above. Reuse `_openalex_record`, `brain.embed`, `store_acquired_paper`. Compute cosine with the stdlib (`math`) — no new deps. Centroid = component-wise mean over anchor embeddings.

- [ ] **Step 4: Run, verify pass + full suite + lint**

Run: `cd projects/ai-stack/openbrain && uv run pytest -q && uv run ruff check .`
Expected: new tests PASS, suite green, lint clean.

- [ ] **Step 5: Commit (openbrain repo)**

```bash
cd projects/ai-stack/openbrain
git add openbrain/sources.py openbrain/brain.py openbrain/cli.py tests/
git commit -m "feat: citation-neighbor fetch + anchor-relative relevance + store-one (driver primitives)"
```

---

### Task 2: Driver config

**Files (in `projects/agentic-researcher`):**
- Create: `config.yaml`, `src/researcher/config.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `@dataclass Config(expansion: str, relevance_radius: float, max_hops: int, per_run_budget: int, anchor_bootstrap_k: int, openbrain_cmd: list[str])`; `load_config(path: Path) -> Config` with the spec §4 defaults when keys are absent.

- [ ] **Step 1: Write `config.yaml`**

```yaml
# Acquisition/expansion policy. See docs/superpowers/specs/...-acquisition-design.md §4.
expansion: none          # none = C harvest only; citation = enable the A walk
relevance_radius: 0.40   # min cosine to keep a walked candidate (first knob to tune)
max_hops: 2              # citation depth from an anchored paper
per_run_budget: 200      # max papers added per walk run (hard cost ceiling)
anchor_bootstrap_k: 10   # initial anchor set size when declaring a front
openbrain_cmd: ["openbrain-ingest"]
```

- [ ] **Step 2: Failing test**

```python
# tests/test_config.py
from pathlib import Path
from researcher.config import load_config

def test_load_defaults(tmp_path):
    p = tmp_path / "c.yaml"; p.write_text("expansion: citation\n")
    c = load_config(p)
    assert c.expansion == "citation"
    assert c.relevance_radius == 0.40
    assert c.max_hops == 2 and c.per_run_budget == 200
    assert c.anchor_bootstrap_k == 10
    assert c.openbrain_cmd == ["openbrain-ingest"]
```

- [ ] **Step 3: Run, verify fail** — `uv run pytest tests/test_config.py -q` → FAIL.

- [ ] **Step 4: Implement `config.py`**

```python
# src/researcher/config.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_DEFAULTS = {
    "expansion": "none",
    "relevance_radius": 0.40,
    "max_hops": 2,
    "per_run_budget": 200,
    "anchor_bootstrap_k": 10,
    "openbrain_cmd": ["openbrain-ingest"],
}


@dataclass
class Config:
    expansion: str
    relevance_radius: float
    max_hops: int
    per_run_budget: int
    anchor_bootstrap_k: int
    openbrain_cmd: list[str]


def load_config(path: Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    merged = {**_DEFAULTS, **raw}
    return Config(**{k: merged[k] for k in _DEFAULTS})
```

- [ ] **Step 5: Add `pyyaml` dep** — set `dependencies = ["tomli-w>=1.0", "pyyaml>=6.0"]`; `uv sync`.

- [ ] **Step 6: Run, verify pass; commit**

```bash
uv run pytest tests/test_config.py -q
git add config.yaml src/researcher/config.py tests/test_config.py pyproject.toml uv.lock
git commit -m "feat(config): expansion flag + gate tunables with spec defaults"
```

---

### Task 3: The relevance gate (pure decision function)

**Files:** Create `src/researcher/gate.py`, `tests/test_gate.py`

**Interfaces:**
- Produces: `keep(cosine: float, hop: int, *, radius: float, max_hops: int) -> bool` — `cosine >= radius and hop <= max_hops`. Pure; no embeddings (openbrain computed the cosine). Budget is enforced by the walk loop, not here.

- [ ] **Step 1: Failing tests**

```python
# tests/test_gate.py
from researcher.gate import keep

def test_keeps_on_topic_within_depth():
    assert keep(0.55, 1, radius=0.40, max_hops=2) is True

def test_drops_below_radius():
    assert keep(0.30, 1, radius=0.40, max_hops=2) is False

def test_drops_beyond_depth():
    assert keep(0.99, 3, radius=0.40, max_hops=2) is False

def test_boundary_inclusive():
    assert keep(0.40, 2, radius=0.40, max_hops=2) is True
```

- [ ] **Step 2: Run, verify fail** — `uv run pytest tests/test_gate.py -q` → FAIL.

- [ ] **Step 3: Implement `gate.py`**

```python
# src/researcher/gate.py
"""Relevance gate: keep a walked candidate iff it is on-topic (cosine vs the
front's anchor set, computed by openbrain) AND within the depth cap. Per-run
budget is enforced by the walk loop."""
from __future__ import annotations


def keep(cosine: float, hop: int, *, radius: float, max_hops: int) -> bool:
    return cosine >= radius and hop <= max_hops
```

- [ ] **Step 4: Run, verify pass; commit**

```bash
uv run pytest tests/test_gate.py -q
git add src/researcher/gate.py tests/test_gate.py
git commit -m "feat(gate): pure keep/drop — radius + depth cap"
```

---

### Task 4: The A citation walk

**Files:** Create `src/researcher/walk.py`, `tests/test_walk.py`. Extend `OpenbrainClient` (in `openbrain_client.py`) with the three Task-1 commands.

**Interfaces:**
- Consumes: `Front`; `gate.keep`; `OpenbrainClient` with new methods:
  - `citation_neighbors(self, paper_id: str) -> list[dict]` → `["citations"]`/`["neighbors"]` metas (each has `id`, `title`, `abstract`)
  - `relevance(self, anchor_ids: list[str], texts: list[str]) -> list[float]` → `["cosines"]`
  - `store_paper(self, meta: dict) -> dict`
- Produces: `walk_front(front: Front, client: OpenbrainClient, *, radius: float, max_hops: int, per_run_budget: int) -> dict` returning `{"added": int, "visited": int, "stopped": "budget"|"frontier"}`. Mutates `front` (`acquired_paper_ids`, `visited`, `hop_depth`) in place; raises `ValueError` if `anchor_paper_ids` is empty.

**Walk semantics:** BFS frontier seeded from `acquired_paper_ids` (or `anchor_paper_ids` if none acquired yet), each at hop 0. Pop a paper, mark visited, and if its hop `< max_hops` fetch its citation neighbors; score all neighbors in one `relevance(anchor_ids, texts)` call; for each neighbor not already known, if `keep(cos, hop+1, …)` then `store_paper`, append to `acquired_paper_ids`, set `hop_depth`, and enqueue at hop+1. Stop when frontier drains or `added == per_run_budget`. Anchors are read-only throughout.

- [ ] **Step 1: Extend the client (add methods + tests)**

Add to `openbrain_client.py`:
```python
    def citation_neighbors(self, paper_id: str) -> list[dict]:
        result = self._run_json(["citations", paper_id])
        assert isinstance(result, dict)
        return list(result.get("neighbors", []))

    def relevance(self, anchor_ids: list[str], texts: list[str]) -> list[float]:
        args = ["relevance"]
        for a in anchor_ids:
            args += ["--anchor", a]
        for t in texts:
            args += ["--text", t]
        result = self._run_json(args)
        assert isinstance(result, dict)
        return [float(x) for x in result["cosines"]]

    def store_paper(self, meta: dict) -> dict:
        import json as _json
        result = self._run_json(["store-paper", "--json", _json.dumps(meta)])
        assert isinstance(result, dict)
        return result
```
Add `tests/test_openbrain_client.py` cases asserting arg construction for `relevance` (anchors then texts, order preserved) and `citation_neighbors` parsing, using the existing fake-runner pattern.

- [ ] **Step 2: Write failing `test_walk.py`** (fully stubbed client — no openbrain)

```python
# tests/test_walk.py
from researcher.fronts import Front
from researcher.walk import walk_front


class StubClient:
    """W1 cites W2(on-topic) + W3(off-topic); W2 cites W4(on-topic)."""
    GRAPH = {
        "W1": [{"id": "W2", "title": "t2", "abstract": ""},
               {"id": "W3", "title": "t3", "abstract": ""}],
        "W2": [{"id": "W4", "title": "t4", "abstract": ""}],
        "W4": [],
    }
    COS = {"W2": 0.8, "W3": 0.1, "W4": 0.7}

    def __init__(self):
        self.stored = []

    def citation_neighbors(self, paper_id):
        return self.GRAPH.get(paper_id, [])

    def relevance(self, anchor_ids, texts):
        # map each text back via its leading token "tN" -> "WN"
        ids = ["W" + t[1:] for t in texts]
        return [self.COS[i] for i in ids]

    def store_paper(self, meta):
        self.stored.append(meta["id"])
        return {"id": meta["id"], "deduped": False}


def test_walk_keeps_on_topic_outward_respects_depth():
    front = Front(label="T", anchor_paper_ids=["A0"], acquired_paper_ids=["W1"])
    client = StubClient()
    summary = walk_front(front, client, radius=0.40, max_hops=2, per_run_budget=100)
    # W2 (hop1, 0.8) kept; W3 (0.1) dropped; W4 (hop2, 0.7) kept; nothing at hop3
    assert client.stored == ["W2", "W4"]
    assert "W2" in front.acquired_paper_ids and "W4" in front.acquired_paper_ids
    assert "W3" not in front.acquired_paper_ids
    assert front.hop_depth == {"W2": 1, "W4": 2}
    assert summary["added"] == 2

def test_walk_respects_budget():
    front = Front(label="T", anchor_paper_ids=["A0"], acquired_paper_ids=["W1"])
    summary = walk_front(front, StubClient(), radius=0.40, max_hops=5, per_run_budget=1)
    assert summary["added"] == 1 and summary["stopped"] == "budget"

def test_walk_requires_anchors():
    import pytest
    with pytest.raises(ValueError):
        walk_front(Front(label="T", acquired_paper_ids=["W1"]), StubClient(),
                   radius=0.4, max_hops=2, per_run_budget=10)
```

- [ ] **Step 3: Run, verify fail** — `uv run pytest tests/test_walk.py -q` → FAIL.

- [ ] **Step 4: Implement `walk.py`**

```python
# src/researcher/walk.py
"""A — citation frontier walk. Expand a front outward along citation edges,
keeping only candidates within the anchor relevance radius, bounded by depth and
per-run budget. Deterministic; anchors are read-only."""
from __future__ import annotations

from collections import deque

from .fronts import Front
from .gate import keep
from .openbrain_client import OpenbrainClient


def walk_front(
    front: Front,
    client: OpenbrainClient,
    *,
    radius: float,
    max_hops: int,
    per_run_budget: int,
) -> dict:
    if not front.anchor_paper_ids:
        raise ValueError("citation walk requires a non-empty anchor set")

    seeds = front.acquired_paper_ids or front.anchor_paper_ids
    frontier: deque[tuple[str, int]] = deque((pid, 0) for pid in seeds)
    known = set(front.acquired_paper_ids) | set(front.visited)
    added = 0
    stopped = "frontier"

    while frontier:
        pid, hop = frontier.popleft()
        if pid in front.visited:
            continue
        front.visited.append(pid)
        if hop >= max_hops:
            continue
        neighbors = client.citation_neighbors(pid)
        fresh = [n for n in neighbors if n["id"] not in known]
        if not fresh:
            continue
        texts = [f"{n.get('title', '')} {n.get('abstract', '')}".strip() for n in fresh]
        cosines = client.relevance(front.anchor_paper_ids, texts)
        for n, cos in zip(fresh, cosines):
            nid = n["id"]
            if nid in known:
                continue
            if not keep(cos, hop + 1, radius=radius, max_hops=max_hops):
                continue
            client.store_paper(n)
            known.add(nid)
            front.acquired_paper_ids.append(nid)
            front.hop_depth[nid] = hop + 1
            frontier.append((nid, hop + 1))
            added += 1
            if added >= per_run_budget:
                return {"added": added, "visited": len(front.visited), "stopped": "budget"}
    return {"added": added, "visited": len(front.visited), "stopped": stopped}
```

- [ ] **Step 5: Run, verify pass** — `uv run pytest tests/test_walk.py tests/test_openbrain_client.py -q` → PASS.

- [ ] **Step 6: Commit**

```bash
git add src/researcher/walk.py tests/test_walk.py src/researcher/openbrain_client.py tests/test_openbrain_client.py
git commit -m "feat(walk): A citation frontier walk — radius+depth+budget bounded, anchors read-only"
```

---

### Task 5: Library-label fronts + `walk` CLI behind the expansion flag

**Files:** Modify `src/researcher/cli.py`, `src/researcher/openbrain_client.py` (add `search_library`), `tests/test_cli.py`. Requires the openbrain `search-library` command.

**openbrain dependency (fold into Task 1 if building both at once):** a CLI `search-library <query> --limit K` → `{"ids": [...]}` over the existing semantic `search_library`. Add it alongside the Task-1 commands.

**Interfaces:**
- `OpenbrainClient.search_library(self, query: str, k: int) -> list[str]` → `["ids"]`
- CLI additions:
  - `front create-from-library <label> --query Q` → `search_library(Q, anchor_bootstrap_k)` seeds both `anchor_paper_ids` and `acquired_paper_ids`.
  - `walk <label>` → loads `config.yaml`; if `expansion != "citation"`, print a notice and return 0 (no-op); else `walk_front(...)` with config tunables, then save.

- [ ] **Step 1: Failing tests** (inject a stub client into `main`; `expansion` toggled via a temp config)

```python
# add to tests/test_cli.py
from researcher.cli import main
from researcher.fronts import load_front
from pathlib import Path

class WalkStub:
    def search_library(self, query, k):
        return ["L1", "L2"]
    def citation_neighbors(self, pid):
        return []
    def relevance(self, anchors, texts):
        return []
    def store_paper(self, meta):
        return {"id": meta["id"]}

def test_create_from_library_seeds_anchors(tmp_path):
    fd = str(tmp_path)
    rc = main(["--fronts-dir", fd, "front", "create-from-library", "Water", "--query", "water rights"],
              client=WalkStub(), config_path=str(_write_cfg(tmp_path, "none")))
    assert rc == 0
    f = load_front(Path(fd) / "water.toml")
    assert f.anchor_paper_ids == ["L1", "L2"]
    assert f.acquired_paper_ids == ["L1", "L2"]

def test_walk_noop_when_expansion_off(tmp_path):
    fd = str(tmp_path)
    main(["--fronts-dir", fd, "front", "create", "T", "--term", "a"])
    rc = main(["--fronts-dir", fd, "walk", "T"], client=WalkStub(),
              config_path=str(_write_cfg(tmp_path, "none")))
    assert rc == 0  # no-op, expansion is off

def _write_cfg(tmp_path, expansion):
    p = tmp_path / "config.yaml"; p.write_text(f"expansion: {expansion}\n"); return p
```

- [ ] **Step 2: Run, verify fail** — `uv run pytest tests/test_cli.py -q` → FAIL.

- [ ] **Step 3: Implement** — add `search_library` to the client; in `cli.py` add a `--config-path` global (default `config.yaml`) and a `config_path` param to `main`; wire `front create-from-library` and `walk` (loading `Config`, honoring `expansion`). Use `load_config` (Task 2), `walk_front` (Task 4).

- [ ] **Step 4: Run, verify pass + lint** — `uv run pytest -q && uv run ruff check` → PASS, clean.

- [ ] **Step 5: Commit**

```bash
git add src/researcher/cli.py src/researcher/openbrain_client.py tests/test_cli.py
git commit -m "feat(cli): library-label fronts + walk command gated by expansion flag"
```

---

### Task 6: README steering section + tuning notes

**Files:** Modify `README.md` (the control-panel section, spec §8), `docs/superpowers/design/.gitkeep` → replace with `docs/superpowers/design/tuning.md`.

- [ ] **Step 1: Document the steering surface** in `README.md`: add/remove a term, `front create` vs `front create-from-library`, `anchor add/remove/promote` (incl. promote-from-walk), flipping `expansion: citation`, running `harvest` and `walk`, and tuning `relevance_radius`/`max_hops`/`per_run_budget`. Frame as instructions to the user (spec §8).

- [ ] **Step 2: Write `docs/superpowers/design/tuning.md`** — how to tune `relevance_radius` (raise if the walk drifts off-topic, lower if too sparse; model-dependent), and what `max_hops`/`per_run_budget` trade off.

- [ ] **Step 3: Commit**

```bash
git add README.md docs/superpowers/design/
git commit -m "docs: README steering control-panel + gate tuning notes"
```

---

## Self-Review

**Spec coverage (the A/expansion slice):**
- §3.2 citation frontier walk (refs+citations, visited-set, outward, radius-gated, depth+budget) → Tasks 1 (neighbors) + 4 (walk) ✓
- §4 relevance gate (cosine vs anchor centroid, fixed-anchor, depth+budget backstops, defaults) → Tasks 1 (relevance, centroid openbrain-side) + 2 (defaults) + 3 (keep) + 4 (budget loop) ✓
- §5.1 centroid computed-not-stored → openbrain `relevance` computes it from anchor_ids; driver stores no vectors ✓
- §5.2 anchors walk-immutable, human-curated → walk reads anchors only; curation stays in foundation `anchor` CLI ✓
- §5.3 library-label fronts → Task 5 ✓
- expansion flag default off, additive → Tasks 2 + 5 ✓
- Out of scope: B / synthesis / gap analysis (§6) — a later plan; promote-from-walk is supported (foundation `anchor promote`) and documented (Task 6).

**Placeholder scan:** driver code (config, gate, walk, client methods) is complete. Task 1 and Task 5's openbrain commands are specified by signature + behavior + exact test expectations rather than full openbrain source, because they must follow that repo's conventions (asyncpg pool, `_emit`, `_openalex_record`) a fresh implementer will read first — the proposed surface and the assertions pin them.

**Type/name consistency:** `citation_neighbors`/`relevance`/`store_paper`/`search_library` identical across client (Tasks 4–5), walk (Task 4), and openbrain CLI (Task 1). `keep(cosine, hop, *, radius, max_hops)` identical in Tasks 3 and 4. `Config` field names match `config.yaml` keys and the spec §4 defaults. `relevance` returns cosines (openbrain owns embeddings) — no vectors cross the seam.
```

