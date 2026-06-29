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


def test_harvest_uses_injected_client_and_saves(tmp_path):
    fd = str(tmp_path)
    main(["--fronts-dir", fd, "front", "create", "T", "--term", "a"])

    class StubClient:
        def acquire(self, query, *, since=None, limit=50, venues=None, dry_run=False):
            return {"stored": 2, "stored_ids": ["W1", "W2"]}

    rc = main(["--fronts-dir", fd, "harvest", "T"], client=StubClient())
    assert rc == 0
    assert load_front(Path(fd) / "t.toml").acquired_paper_ids == ["W1", "W2"]
