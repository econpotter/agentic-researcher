from pathlib import Path

from researcher.cli import main
from researcher.topics import load_topic, save_topic


def test_topic_create_then_term_add(tmp_path):
    td = str(tmp_path)
    assert (
        main(["--topics-dir", td, "topic", "create", "Water Rights", "--term", "water rights"])
        == 0
    )
    t = load_topic(Path(td) / "water-rights.toml")
    assert t.search_terms == ["water rights"]
    assert main(["--topics-dir", td, "term", "add", "Water Rights", "prior appropriation"]) == 0
    assert load_topic(Path(td) / "water-rights.toml").search_terms == [
        "water rights",
        "prior appropriation",
    ]


def test_term_remove(tmp_path):
    td = str(tmp_path)
    main(["--topics-dir", td, "topic", "create", "T", "--term", "a", "--term", "b"])
    assert main(["--topics-dir", td, "term", "remove", "T", "a"]) == 0
    assert load_topic(Path(td) / "t.toml").search_terms == ["b"]


def test_core_promote(tmp_path):
    td = str(tmp_path)
    main(["--topics-dir", td, "topic", "create", "T", "--term", "a"])
    t = load_topic(Path(td) / "t.toml")
    t.collected_paper_ids = ["W9"]
    save_topic(t, Path(td))
    assert main(["--topics-dir", td, "core", "promote", "T", "W9"]) == 0
    g = load_topic(Path(td) / "t.toml")
    assert g.core_paper_ids == ["W9"] and g.collected_paper_ids == []


def test_core_add_remove(tmp_path):
    td = str(tmp_path)
    main(["--topics-dir", td, "topic", "create", "T", "--term", "a"])
    main(["--topics-dir", td, "core", "add", "T", "W1"])
    assert load_topic(Path(td) / "t.toml").core_paper_ids == ["W1"]
    main(["--topics-dir", td, "core", "remove", "T", "W1"])
    assert load_topic(Path(td) / "t.toml").core_paper_ids == []


def _write_cfg(tmp_path, expansion: bool):
    p = tmp_path / "config.yaml"
    p.write_text(f"citation_expansion: {str(expansion).lower()}\n")
    return str(p)


class StubOpenbrain:
    def fetch_papers(self, topic, *, since=None, limit=50, store=False):
        return [
            {"id": "W1", "title": topic, "abstract": ""},
            {"id": "W2", "title": topic, "abstract": ""},
        ]

    def store_papers(self, papers):
        return {"stored_ids": [p["id"] for p in papers]}

    def find_papers(self, text, limit):
        return ["L1", "L2"]

    def get_citations(self, paper_id):
        return []

    def score_relevance(self, core_paper_ids, texts):
        return []


def test_collect_uses_injected_openbrain_and_saves(tmp_path):
    td = str(tmp_path)
    main(["--topics-dir", td, "topic", "create", "T", "--term", "water rights"])
    rc = main(
        ["--topics-dir", td, "collect", "T"],
        openbrain=StubOpenbrain(),
        config_path=_write_cfg(tmp_path, False),
    )
    assert rc == 0
    assert load_topic(Path(td) / "t.toml").collected_paper_ids == ["W1", "W2"]


def test_create_from_library_seeds_core(tmp_path):
    td = str(tmp_path)
    rc = main(
        ["--topics-dir", td, "topic", "create-from-library", "Water", "--query", "water rights"],
        openbrain=StubOpenbrain(),
        config_path=_write_cfg(tmp_path, False),
    )
    assert rc == 0
    t = load_topic(Path(td) / "water.toml")
    assert t.core_paper_ids == ["L1", "L2"]
    assert t.collected_paper_ids == ["L1", "L2"]


def test_expand_noop_when_off(tmp_path):
    td = str(tmp_path)
    main(["--topics-dir", td, "topic", "create", "T", "--term", "a"])
    rc = main(
        ["--topics-dir", td, "expand", "T"],
        openbrain=StubOpenbrain(),
        config_path=_write_cfg(tmp_path, False),
    )
    assert rc == 0  # no-op, expansion off


def test_expand_runs_when_on(tmp_path):
    td = str(tmp_path)
    main(
        ["--topics-dir", td, "topic", "create-from-library", "T", "--query", "q"],
        openbrain=StubOpenbrain(),
        config_path=_write_cfg(tmp_path, True),
    )
    rc = main(
        ["--topics-dir", td, "expand", "T"],
        openbrain=StubOpenbrain(),
        config_path=_write_cfg(tmp_path, True),
    )
    assert rc == 0  # core seeded, expand runs (empty citations -> added 0)
