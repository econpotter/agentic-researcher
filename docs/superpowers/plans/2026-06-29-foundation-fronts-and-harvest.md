# Agentic Researcher — Foundation (Fronts + C Harvest) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `agentic-researcher` project and its deterministic C (harvest) layer: a front data model (git-tracked toml), a thin openbrain CLI client, and a harvest loop that runs `openbrain acquire` per front term and records which papers landed.

**Architecture:** A Python package `researcher/` in `projects/agentic-researcher`. Fronts are plain toml files under `fronts/`. The package reaches openbrain **only** through its CLI (`openbrain-ingest <subcommand>`, JSON out) — never its DB or sources directly. No LLM anywhere in this plan (C is deterministic). The relevance gate, centroids, and the A citation-walk are **out of scope** — they live in the expansion plan and need openbrain embedding/citation primitives this plan does not.

**Tech Stack:** Python 3.11+, `uv`, `ruff`, `pytest`; `tomllib` (stdlib, read) + `tomli-w` (write); openbrain CLI as a subprocess.

## Global Constraints

- **The seam:** `researcher/` calls openbrain only via the `openbrain-ingest` CLI. No direct DB/source/embedding access in this plan.
- **Deterministic:** no LLM calls in any task here. C harvest is `acquire` + bookkeeping.
- **Fronts are git-tracked toml**, one file per front under `fronts/`, hand-editable; the CLI is sugar over them. Centroid is NOT stored (computed later in the expansion plan).
- **Front decouples three things** (spec §5): `label` (identity, permanent), `terms` (mutable acquisition inputs), `anchor_paper_ids` (relevance anchor, walk-immutable, human-curated). Removing a term loses nothing else.
- **Repo location:** `projects/agentic-researcher` (own git repo; orchestra-managed, registered in orchestra `PROJECTS.md`).
- **Package/slug:** import name `researcher`; project slug `agentic_researcher`; project name `agentic-researcher`.
- **Spec:** `docs/superpowers/specs/2026-06-28-agentic-researcher-acquisition-design.md` (this repo). §3.1 (C), §5 (fronts), §7 (layout).
- **openbrain CLI entrypoint** is `openbrain-ingest` (a Typer app; `console.print_json` output). Cross-repo openbrain edits land in `projects/ai-stack/openbrain` (its own repo).

## Dependency

**Task 1 is gated on the project-template docs/layout polish** (`orchestra/docs/superpowers/plans/2026-06-29-project-template-docs-and-layout-polish.md`). Do that plan first; Task 1 applies the polished template. Tasks 2–6 do not depend on the polish and could be drafted in parallel, but they assume the package skeleton Task 1 produces.

---

### Task 1: Apply the polished template + register the project

**Files:**
- Create (materialized from `projects/project-template`, python variant, into `projects/agentic-researcher/`): `AGENTS.md`, `CLAUDE.md`, `README.md`, `ROADMAP.md`, `pyproject.toml`, `justfile`, `.pre-commit-config.yaml`, `.gitignore` (merge), `.env.example`, `src/agentic_researcher/__init__.py`, `tests/test_smoke.py`, `docs/superpowers/design/.gitkeep`
- Preserve (already in repo): `docs/superpowers/specs/2026-06-28-agentic-researcher-acquisition-design.md`, `docs/superpowers/plans/*`
- Modify (orchestra repo): `PROJECTS.md`; Create: `orchestra/queue/agentic-researcher.md`

**Note on package name:** the template materializes `src/agentic_researcher/`. This plan's package import name is `researcher`. Rename after materializing: `git mv src/agentic_researcher src/researcher` and set `pyproject` `[project.scripts]` `researcher = "researcher.cli:main"` (added in Task 6). Keep the distribution name `agentic-researcher`.

- [ ] **Step 1: Materialize the template into the repo (overlay, preserving docs)**

```bash
cd /home/potterzot/orchestra/projects/agentic-researcher
# copy a throwaway materialization of the python variant, then overlay non-docs files
rm -rf /tmp/ar-tpl && cp -r /home/potterzot/orchestra/projects/project-template /tmp/ar-tpl && rm -rf /tmp/ar-tpl/.git
( cd /tmp/ar-tpl && bash init.sh python agentic-researcher )
# overlay everything except the template's docs/ (this repo's docs/ already has specs+plans)
rsync -a --exclude 'docs/' /tmp/ar-tpl/ ./
# bring only the missing docs/superpowers/design/.gitkeep
mkdir -p docs/superpowers/design && touch docs/superpowers/design/.gitkeep
rm -rf /tmp/ar-tpl
```

- [ ] **Step 2: Rename the package to `researcher`**

```bash
cd /home/potterzot/orchestra/projects/agentic-researcher
git add -A
git mv src/agentic_researcher src/researcher
sed -i 's/agentic_researcher/researcher/g' pyproject.toml
```

- [ ] **Step 3: Verify the scaffold materialized cleanly**

Run:
```bash
cd /home/potterzot/orchestra/projects/agentic-researcher
test -f AGENTS.md && test -f README.md && test -f pyproject.toml && echo DOCS_OK
test -f src/researcher/__init__.py && echo PKG_OK
test -d docs/superpowers/specs && test -f docs/superpowers/specs/2026-06-28-agentic-researcher-acquisition-design.md && echo SPEC_PRESERVED
test ! -d variants && test ! -f ARCHITECTURE.md && echo CLEAN
uv sync && uv run pytest -q && echo SMOKE_OK
```
Expected: `DOCS_OK`, `PKG_OK`, `SPEC_PRESERVED`, `CLEAN`, `SMOKE_OK`.

- [ ] **Step 4: Register in orchestra**

Append to `/home/potterzot/orchestra/PROJECTS.md`:
```markdown

## agentic-researcher
- Path: projects/agentic-researcher
- Branch: main
- Purpose: Automated economics-research driver over openbrain (paper harvest, relate, lit-review)
- Queue: queue/agentic-researcher.md
- Workflow: python
- Focus: none
```
Create `/home/potterzot/orchestra/queue/agentic-researcher.md`:
```markdown
# Queue — agentic-researcher
```

- [ ] **Step 5: Commit (both repos)**

```bash
cd /home/potterzot/orchestra/projects/agentic-researcher
git add -A && git commit -m "chore: scaffold from project-template (python), package=researcher"
cd /home/potterzot/orchestra
git add PROJECTS.md queue/agentic-researcher.md
git commit -m "chore(projects): register agentic-researcher"
```

---

### Task 2: Front data model

**Files:**
- Create: `src/researcher/fronts.py`
- Create: `tests/test_fronts.py`
- Create: `fronts/.gitkeep`

**Interfaces:**
- Produces:
  - `@dataclass Front` with fields `label: str`, `terms: list[str]`, `anchor_paper_ids: list[str]`, `acquired_paper_ids: list[str]`, `visited: list[str]`, `hop_depth: dict[str, int]`
  - `slugify(label: str) -> str`
  - `front_path(fronts_dir: Path, label: str) -> Path`
  - `load_front(path: Path) -> Front`
  - `save_front(front: Front, fronts_dir: Path) -> Path`
  - `create_front(fronts_dir: Path, label: str, terms: list[str]) -> Front`
  - `add_term(front, term)` / `remove_term(front, term)`
  - `add_anchor(front, pid)` / `remove_anchor(front, pid)` / `promote(front, pid)` (moves pid from `acquired_paper_ids` to `anchor_paper_ids`)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_fronts.py
from pathlib import Path
from researcher.fronts import (
    Front, slugify, create_front, load_front, save_front,
    add_term, remove_term, add_anchor, remove_anchor, promote,
)

def test_slugify():
    assert slugify("Water Rights") == "water-rights"
    assert slugify("prior  appropriation!") == "prior-appropriation"

def test_create_and_roundtrip(tmp_path):
    f = create_front(tmp_path, "Water Rights", ["water rights"])
    assert f.label == "Water Rights"
    assert f.terms == ["water rights"]
    p = save_front(f, tmp_path)
    assert p == tmp_path / "water-rights.toml"
    g = load_front(p)
    assert g.label == "Water Rights"
    assert g.terms == ["water rights"]
    assert g.anchor_paper_ids == [] and g.hop_depth == {}

def test_term_ops_are_independent_of_anchors(tmp_path):
    f = create_front(tmp_path, "T", ["a", "b"])
    f.anchor_paper_ids = ["W1"]
    f.acquired_paper_ids = ["W1", "W2"]
    remove_term(f, "a")
    assert f.terms == ["b"]
    assert f.anchor_paper_ids == ["W1"]          # untouched
    assert f.acquired_paper_ids == ["W1", "W2"]   # untouched

def test_promote_moves_acquired_to_anchor(tmp_path):
    f = create_front(tmp_path, "T", ["a"])
    f.acquired_paper_ids = ["W9"]
    promote(f, "W9")
    assert "W9" in f.anchor_paper_ids
    assert "W9" not in f.acquired_paper_ids

def test_add_term_dedups(tmp_path):
    f = create_front(tmp_path, "T", ["a"])
    add_term(f, "a")
    assert f.terms == ["a"]
```

- [ ] **Step 2: Run, verify fail**

Run: `cd projects/agentic-researcher && uv run pytest tests/test_fronts.py -q`
Expected: FAIL (`ModuleNotFoundError: researcher.fronts`).

- [ ] **Step 3: Implement `fronts.py`**

```python
# src/researcher/fronts.py
"""Front model: a named topic with a curated, walk-immutable anchor and walk-state.

Fronts are git-tracked toml under fronts/, one per front. Identity (label),
acquisition inputs (terms), and the relevance anchor (anchor_paper_ids) are
deliberately separate — removing a term loses nothing else. The centroid is NOT
stored here; it is computed from anchor embeddings in the expansion layer.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import tomli_w


@dataclass
class Front:
    label: str
    terms: list[str] = field(default_factory=list)
    anchor_paper_ids: list[str] = field(default_factory=list)
    acquired_paper_ids: list[str] = field(default_factory=list)
    visited: list[str] = field(default_factory=list)
    hop_depth: dict[str, int] = field(default_factory=dict)


def slugify(label: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return s


def front_path(fronts_dir: Path, label: str) -> Path:
    return Path(fronts_dir) / f"{slugify(label)}.toml"


def load_front(path: Path) -> Front:
    # Derive from the dataclass schema: keep only known fields (robust to stray
    # toml keys); the dataclass fills defaults for any absent ones.
    data = tomllib.loads(Path(path).read_text())
    known = {f.name for f in fields(Front)}
    return Front(**{k: v for k, v in data.items() if k in known})


def save_front(front: Front, fronts_dir: Path) -> Path:
    # asdict() derives the payload from the dataclass — the schema is defined
    # once (the Front fields), not restated here.
    path = front_path(fronts_dir, front.label)
    Path(fronts_dir).mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps(asdict(front)))
    return path


def create_front(fronts_dir: Path, label: str, terms: list[str]) -> Front:
    front = Front(label=label, terms=list(dict.fromkeys(terms)))
    save_front(front, fronts_dir)
    return front


def add_term(front: Front, term: str) -> None:
    if term not in front.terms:
        front.terms.append(term)


def remove_term(front: Front, term: str) -> None:
    if term in front.terms:
        front.terms.remove(term)


def add_anchor(front: Front, pid: str) -> None:
    if pid not in front.anchor_paper_ids:
        front.anchor_paper_ids.append(pid)


def remove_anchor(front: Front, pid: str) -> None:
    if pid in front.anchor_paper_ids:
        front.anchor_paper_ids.remove(pid)


def promote(front: Front, pid: str) -> None:
    if pid in front.acquired_paper_ids:
        front.acquired_paper_ids.remove(pid)
    add_anchor(front, pid)
```

- [ ] **Step 4: Add `tomli-w` dependency**

In `pyproject.toml` set `dependencies = ["tomli-w>=1.0"]`. Then:
```bash
cd projects/agentic-researcher && uv sync
```

- [ ] **Step 5: Run, verify pass**

Run: `uv run pytest tests/test_fronts.py -q`
Expected: PASS (5 tests).

- [ ] **Step 6: Commit**

```bash
git add src/researcher/fronts.py tests/test_fronts.py pyproject.toml uv.lock fronts/.gitkeep
git commit -m "feat(fronts): front model — label/terms/anchors decoupled, toml roundtrip"
```

---

### Task 3: openbrain CLI client

**Files:**
- Create: `src/researcher/openbrain_client.py`
- Create: `tests/test_openbrain_client.py`

**Interfaces:**
- Consumes: openbrain CLI `openbrain-ingest acquire <query> [--since N] [--limit N] [--venue V ...] [--dry-run]`, JSON on stdout.
- Produces:
  - `class OpenbrainClient(cmd: list[str] = ["openbrain-ingest"], runner=subprocess.run)`
  - `acquire(self, query: str, *, since: int | None = None, limit: int = 50, venues: list[str] | None = None, dry_run: bool = False) -> dict` — returns the parsed report dict (includes `stored`, `found`, and, after Task 4, `stored_ids: list[str]`)
  - `_run_json(self, args: list[str]) -> object` — run + parse stdout JSON

- [ ] **Step 1: Write failing tests** (subprocess is faked — no real openbrain)

```python
# tests/test_openbrain_client.py
import json
import types
from researcher.openbrain_client import OpenbrainClient


def fake_runner(result_obj):
    def _run(args, capture_output, text, check):
        return types.SimpleNamespace(stdout=json.dumps(result_obj), returncode=0)
    return _run


def test_acquire_builds_args_and_parses():
    captured = {}

    def _run(args, capture_output, text, check):
        captured["args"] = args
        return types.SimpleNamespace(
            stdout=json.dumps({"stored": 2, "stored_ids": ["W1", "W2"]}),
            returncode=0,
        )

    client = OpenbrainClient(runner=_run)
    report = client.acquire("water rights", since=2015, limit=10, venues=["AER"])
    assert report["stored_ids"] == ["W1", "W2"]
    a = captured["args"]
    assert a[:2] == ["openbrain-ingest", "acquire"]
    assert "water rights" in a
    assert "--since" in a and "2015" in a
    assert "--limit" in a and "10" in a
    assert "--venue" in a and "AER" in a


def test_acquire_dry_run_flag():
    captured = {}

    def _run(args, capture_output, text, check):
        captured["args"] = args
        return types.SimpleNamespace(stdout=json.dumps({"stored": 0}), returncode=0)

    OpenbrainClient(runner=_run).acquire("x", dry_run=True)
    assert "--dry-run" in captured["args"]
```

- [ ] **Step 2: Run, verify fail**

Run: `uv run pytest tests/test_openbrain_client.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement `openbrain_client.py`**

```python
# src/researcher/openbrain_client.py
"""Thin, deterministic wrapper over the openbrain CLI (`openbrain-ingest`).

The driver reaches openbrain ONLY through here — never its DB or sources. Each
method shells out to a CLI subcommand and parses the JSON it prints.
"""
from __future__ import annotations

import json
import subprocess


class OpenbrainClient:
    def __init__(self, cmd: list[str] | None = None, runner=subprocess.run) -> None:
        self.cmd = cmd or ["openbrain-ingest"]
        self._runner = runner

    def _run_json(self, args: list[str]) -> object:
        proc = self._runner(
            self.cmd + args, capture_output=True, text=True, check=True
        )
        return json.loads(proc.stdout)

    def acquire(
        self,
        query: str,
        *,
        since: int | None = None,
        limit: int = 50,
        venues: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict:
        args = ["acquire", query, "--limit", str(limit)]
        if since is not None:
            args += ["--since", str(since)]
        for v in venues or []:
            args += ["--venue", v]
        if dry_run:
            args += ["--dry-run"]
        result = self._run_json(args)
        assert isinstance(result, dict)
        return result
```

- [ ] **Step 4: Run, verify pass**

Run: `uv run pytest tests/test_openbrain_client.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/researcher/openbrain_client.py tests/test_openbrain_client.py
git commit -m "feat(client): openbrain CLI wrapper — acquire via subprocess, JSON out"
```

---

### Task 4: openbrain — `acquire` returns stored paper IDs (cross-repo)

**Why:** the harvest loop must record *which* papers landed in a front. `acquire`'s report currently carries counts (`stored`) but no IDs. `store_acquired_paper` already `RETURNING id, title`; capture and surface them.

**Files (in `projects/ai-stack/openbrain`, its own repo):**
- Modify: `openbrain/acquire.py` (the store loop + the return dict)
- Test: `openbrain/tests/test_acquire.py` (project uses unittest-style + mocked pool; follow existing patterns there)

- [ ] **Step 1: Read the store loop + return**

Run: `cd projects/ai-stack/openbrain && sed -n '170,200p' openbrain/acquire.py` to confirm the loop calling `store_acquired_paper(...)` and the `return {...}` at the end.

- [ ] **Step 2: Write a failing test** (mirror the existing acquire test's mocked-store pattern; assert the report carries `stored_ids`)

Add to `openbrain/tests/test_acquire.py` a test that runs `acquire(...)` with the store path mocked to return `{"id": "W1", "deduped": False}` / `{"id": "W2", "deduped": False}` and asserts `report["stored_ids"] == ["W1", "W2"]`. Match the file's existing mock wiring (mocked pool + monkeypatched `sources`/`store_acquired_paper`).

- [ ] **Step 3: Run, verify fail**

Run: `cd projects/ai-stack/openbrain && uv run pytest tests/test_acquire.py -q`
Expected: FAIL (`KeyError: 'stored_ids'`).

- [ ] **Step 4: Implement — collect IDs in the store loop, add to report**

In `openbrain/acquire.py`: initialize `stored_ids: list[str] = []` before the store loop; where a paper is stored (the branch that increments `stored`), append the returned id: `stored_ids.append(str(result["id"]))`. Add `"stored_ids": stored_ids,` to the returned report dict.

- [ ] **Step 5: Run, verify pass; full suite green**

Run: `cd projects/ai-stack/openbrain && uv run pytest tests/test_acquire.py -q && uv run ruff check .`
Expected: PASS + clean.

- [ ] **Step 6: Commit (openbrain repo)**

```bash
cd projects/ai-stack/openbrain
git add openbrain/acquire.py tests/test_acquire.py
git commit -m "feat(acquire): report stored paper IDs (stored_ids) for external drivers"
```

---

### Task 5: C harvest loop

**Files:**
- Create: `src/researcher/harvest.py`
- Create: `tests/test_harvest.py`

**Interfaces:**
- Consumes: `Front` + `save_front` (Task 2); `OpenbrainClient.acquire` returning `{"stored_ids": [...]}` (Tasks 3–4).
- Produces:
  - `harvest_front(front: Front, client: OpenbrainClient, *, since: int | None = None, limit: int = 50) -> dict` — runs `client.acquire` for each term, extends `front.acquired_paper_ids` (deduped, order-preserving), returns a per-term summary `{"per_term": {term: count}, "new_ids": [...]}`. Mutates `front` in place; caller saves.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_harvest.py
from researcher.fronts import Front
from researcher.harvest import harvest_front


class StubClient:
    def __init__(self, by_term):
        self.by_term = by_term
        self.calls = []

    def acquire(self, query, *, since=None, limit=50, venues=None, dry_run=False):
        self.calls.append((query, since, limit))
        return {"stored": len(self.by_term[query]), "stored_ids": self.by_term[query]}


def test_harvest_collects_and_dedups():
    front = Front(label="T", terms=["a", "b"], acquired_paper_ids=["W1"])
    client = StubClient({"a": ["W1", "W2"], "b": ["W2", "W3"]})
    summary = harvest_front(front, client, since=2010, limit=5)
    assert front.acquired_paper_ids == ["W1", "W2", "W3"]   # deduped, order kept
    assert summary["per_term"] == {"a": 2, "b": 2}
    assert summary["new_ids"] == ["W2", "W3"]
    assert client.calls == [("a", 2010, 5), ("b", 2010, 5)]


def test_harvest_no_terms_is_noop():
    front = Front(label="T", terms=[])
    summary = harvest_front(front, StubClient({}))
    assert summary["per_term"] == {} and summary["new_ids"] == []
```

- [ ] **Step 2: Run, verify fail**

Run: `uv run pytest tests/test_harvest.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement `harvest.py`**

```python
# src/researcher/harvest.py
"""C — harvest: run `openbrain acquire` for each of a front's terms and record
which papers landed. Deterministic; no LLM. Mutates the front in place."""
from __future__ import annotations

from .fronts import Front
from .openbrain_client import OpenbrainClient


def harvest_front(
    front: Front,
    client: OpenbrainClient,
    *,
    since: int | None = None,
    limit: int = 50,
) -> dict:
    seen = set(front.acquired_paper_ids)
    per_term: dict[str, int] = {}
    new_ids: list[str] = []
    for term in front.terms:
        report = client.acquire(term, since=since, limit=limit)
        ids = list(report.get("stored_ids", []))
        per_term[term] = len(ids)
        for pid in ids:
            if pid not in seen:
                seen.add(pid)
                front.acquired_paper_ids.append(pid)
                new_ids.append(pid)
    return {"per_term": per_term, "new_ids": new_ids}
```

- [ ] **Step 4: Run, verify pass**

Run: `uv run pytest tests/test_harvest.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/researcher/harvest.py tests/test_harvest.py
git commit -m "feat(harvest): C loop — acquire per term, record stored IDs into the front"
```

---

### Task 6: `researcher` CLI (front / term / anchor / harvest)

**Files:**
- Create: `src/researcher/cli.py`
- Create: `tests/test_cli.py`
- Modify: `pyproject.toml` (`[project.scripts] researcher = "researcher.cli:main"`)

**Interfaces:**
- Consumes: everything above.
- Produces: `main(argv: list[str] | None = None) -> int` with subcommands:
  - `front create <label> [--term T ...]`, `front list`, `front show <label>`
  - `term add <label> <term>` / `term remove <label> <term>`
  - `anchor add <label> <pid>` / `anchor remove <label> <pid>` / `anchor promote <label> <pid>`
  - `harvest <label> [--since N] [--limit N]`
  - `--fronts-dir` (default `fronts/`) global option

- [ ] **Step 1: Write failing tests** (filesystem only; harvest stubbed via a fake client injected through `main`'s `client` param)

```python
# tests/test_cli.py
from pathlib import Path
from researcher.cli import main
from researcher.fronts import load_front


def test_front_create_then_term_add(tmp_path):
    fd = str(tmp_path)
    assert main(["--fronts-dir", fd, "front", "create", "Water Rights", "--term", "water rights"]) == 0
    f = load_front(Path(fd) / "water-rights.toml")
    assert f.terms == ["water rights"]
    assert main(["--fronts-dir", fd, "term", "add", "Water Rights", "prior appropriation"]) == 0
    assert load_front(Path(fd) / "water-rights.toml").terms == ["water rights", "prior appropriation"]


def test_anchor_promote(tmp_path):
    fd = str(tmp_path)
    main(["--fronts-dir", fd, "front", "create", "T", "--term", "a"])
    f = load_front(Path(fd) / "t.toml")
    f.acquired_paper_ids = ["W9"]
    from researcher.fronts import save_front
    save_front(f, Path(fd))
    assert main(["--fronts-dir", fd, "anchor", "promote", "T", "W9"]) == 0
    g = load_front(Path(fd) / "t.toml")
    assert g.anchor_paper_ids == ["W9"] and g.acquired_paper_ids == []
```

- [ ] **Step 2: Run, verify fail**

Run: `uv run pytest tests/test_cli.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement `cli.py`** (argparse; `harvest` builds a real `OpenbrainClient` unless one is injected)

```python
# src/researcher/cli.py
"""`researcher` CLI — sugar over the git-tracked fronts/ toml files."""
from __future__ import annotations

import argparse
from pathlib import Path

from . import fronts as F
from .harvest import harvest_front
from .openbrain_client import OpenbrainClient


def _load(fronts_dir: str, label: str) -> tuple[F.Front, Path]:
    p = F.front_path(Path(fronts_dir), label)
    return F.load_front(p), Path(fronts_dir)


def main(argv: list[str] | None = None, client: OpenbrainClient | None = None) -> int:
    parser = argparse.ArgumentParser(prog="researcher")
    parser.add_argument("--fronts-dir", default="fronts")
    sub = parser.add_subparsers(dest="group", required=True)

    p_front = sub.add_parser("front")
    fsub = p_front.add_subparsers(dest="action", required=True)
    pc = fsub.add_parser("create"); pc.add_argument("label"); pc.add_argument("--term", action="append", default=[])
    fsub.add_parser("list")
    ps = fsub.add_parser("show"); ps.add_argument("label")

    p_term = sub.add_parser("term")
    tsub = p_term.add_subparsers(dest="action", required=True)
    for act in ("add", "remove"):
        q = tsub.add_parser(act); q.add_argument("label"); q.add_argument("term")

    p_anchor = sub.add_parser("anchor")
    asub = p_anchor.add_subparsers(dest="action", required=True)
    for act in ("add", "remove", "promote"):
        q = asub.add_parser(act); q.add_argument("label"); q.add_argument("pid")

    p_harvest = sub.add_parser("harvest")
    p_harvest.add_argument("label")
    p_harvest.add_argument("--since", type=int, default=None)
    p_harvest.add_argument("--limit", type=int, default=50)

    args = parser.parse_args(argv)
    fd = args.fronts_dir

    if args.group == "front":
        if args.action == "create":
            F.create_front(Path(fd), args.label, args.term)
        elif args.action == "list":
            for p in sorted(Path(fd).glob("*.toml")):
                print(F.load_front(p).label)
        elif args.action == "show":
            f, _ = _load(fd, args.label)
            print(f"{f.label}\n  terms: {f.terms}\n  anchors: {f.anchor_paper_ids}"
                  f"\n  acquired: {len(f.acquired_paper_ids)}")
        return 0

    if args.group == "term":
        f, d = _load(fd, args.label)
        (F.add_term if args.action == "add" else F.remove_term)(f, args.term)
        F.save_front(f, d)
        return 0

    if args.group == "anchor":
        f, d = _load(fd, args.label)
        {"add": F.add_anchor, "remove": F.remove_anchor, "promote": F.promote}[args.action](f, args.pid)
        F.save_front(f, d)
        return 0

    if args.group == "harvest":
        f, d = _load(fd, args.label)
        summary = harvest_front(f, client or OpenbrainClient(), since=args.since, limit=args.limit)
        F.save_front(f, d)
        print(summary)
        return 0

    return 1
```

- [ ] **Step 4: Wire the entry point**

In `pyproject.toml` add under `[project.scripts]`: `researcher = "researcher.cli:main"`. Then `uv sync`.

- [ ] **Step 5: Run, verify pass + lint**

Run: `uv run pytest -q && uv run ruff check`
Expected: all tests PASS, lint clean.

- [ ] **Step 6: Commit**

```bash
git add src/researcher/cli.py tests/test_cli.py pyproject.toml uv.lock
git commit -m "feat(cli): researcher front/term/anchor/harvest over fronts/ toml"
```

---

## Self-Review

**Spec coverage (this plan = the C/foundation slice):**
- §7 repo layout + scaffold → Task 1 ✓
- §5 front model (label/terms/anchors decoupled, toml, walk-immutable human-curated anchors, promote-from-acquired) → Task 2 ✓ (centroid deferred to expansion plan, as §5.1 allows — not stored)
- seam: openbrain only via CLI → Task 3 ✓
- §3.1 C harvest (acquire per term, since-filter, dedup, record membership) → Tasks 4 (IDs) + 5 ✓
- §8 steering surface (add/remove term, anchor add/remove/promote) → Task 6 ✓
- Out of scope here, in the expansion plan: relevance gate (§4), centroids (§5.1), A walk (§3.2), library-label fronts (§5.3 path 2 — needs semantic search), B (§6).

**Placeholder scan:** none — all code complete. Task 4 references the existing openbrain test file's patterns rather than pasting them, because they must match that repo's conventions (an instruction, with the exact assertion specified).

**Type/name consistency:** `stored_ids` consistent across Tasks 4 (openbrain emits), 3 (client passes through), 5 (harvest reads). `Front` field names identical across Tasks 2, 5, 6. `front_path`/`save_front`/`load_front`/`promote` signatures consistent across Tasks 2 and 6.
