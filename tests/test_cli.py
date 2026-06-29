from pathlib import Path

from researcher.cli import main
from researcher.fronts import load_front, save_front


def test_front_create_then_term_add(tmp_path):
    fd = str(tmp_path)
    assert (
        main(["--fronts-dir", fd, "front", "create", "Water Rights", "--term", "water rights"])
        == 0
    )
    f = load_front(Path(fd) / "water-rights.toml")
    assert f.terms == ["water rights"]
    assert main(["--fronts-dir", fd, "term", "add", "Water Rights", "prior appropriation"]) == 0
    assert load_front(Path(fd) / "water-rights.toml").terms == [
        "water rights",
        "prior appropriation",
    ]


def test_term_remove(tmp_path):
    fd = str(tmp_path)
    main(["--fronts-dir", fd, "front", "create", "T", "--term", "a", "--term", "b"])
    assert main(["--fronts-dir", fd, "term", "remove", "T", "a"]) == 0
    assert load_front(Path(fd) / "t.toml").terms == ["b"]


def test_anchor_promote(tmp_path):
    fd = str(tmp_path)
    main(["--fronts-dir", fd, "front", "create", "T", "--term", "a"])
    f = load_front(Path(fd) / "t.toml")
    f.acquired_paper_ids = ["W9"]
    save_front(f, Path(fd))
    assert main(["--fronts-dir", fd, "anchor", "promote", "T", "W9"]) == 0
    g = load_front(Path(fd) / "t.toml")
    assert g.anchor_paper_ids == ["W9"] and g.acquired_paper_ids == []


def test_anchor_add_remove(tmp_path):
    fd = str(tmp_path)
    main(["--fronts-dir", fd, "front", "create", "T", "--term", "a"])
    main(["--fronts-dir", fd, "anchor", "add", "T", "W1"])
    assert load_front(Path(fd) / "t.toml").anchor_paper_ids == ["W1"]
    main(["--fronts-dir", fd, "anchor", "remove", "T", "W1"])
    assert load_front(Path(fd) / "t.toml").anchor_paper_ids == []


def _write_cfg(tmp_path, expansion):
    p = tmp_path / "config.yaml"
    p.write_text(f"expansion: {expansion}\n")
    return str(p)


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
    rc = main(
        ["--fronts-dir", fd, "front", "create-from-library", "Water", "--query", "water rights"],
        client=WalkStub(),
        config_path=_write_cfg(tmp_path, "none"),
    )
    assert rc == 0
    f = load_front(Path(fd) / "water.toml")
    assert f.anchor_paper_ids == ["L1", "L2"]
    assert f.acquired_paper_ids == ["L1", "L2"]


def test_walk_noop_when_expansion_off(tmp_path):
    fd = str(tmp_path)
    main(["--fronts-dir", fd, "front", "create", "T", "--term", "a"])
    rc = main(
        ["--fronts-dir", fd, "walk", "T"],
        client=WalkStub(),
        config_path=_write_cfg(tmp_path, "none"),
    )
    assert rc == 0  # no-op, expansion off


def test_walk_runs_when_expansion_on(tmp_path):
    fd = str(tmp_path)
    main(
        ["--fronts-dir", fd, "front", "create-from-library", "T", "--query", "q"],
        client=WalkStub(),
        config_path=_write_cfg(tmp_path, "citation"),
    )
    rc = main(
        ["--fronts-dir", fd, "walk", "T"],
        client=WalkStub(),
        config_path=_write_cfg(tmp_path, "citation"),
    )
    assert rc == 0  # anchors seeded, walk runs (empty neighbors -> added 0)


def test_harvest_uses_injected_client_and_saves(tmp_path):
    fd = str(tmp_path)
    main(["--fronts-dir", fd, "front", "create", "T", "--term", "a"])

    class StubClient:
        def acquire(self, query, *, since=None, limit=50, venues=None, dry_run=False):
            return {"stored": 2, "stored_ids": ["W1", "W2"]}

    rc = main(["--fronts-dir", fd, "harvest", "T"], client=StubClient())
    assert rc == 0
    assert load_front(Path(fd) / "t.toml").acquired_paper_ids == ["W1", "W2"]
