from researcher.topics import (
    add_core_paper,
    add_search_term,
    create_topic,
    load_topic,
    promote_to_core,
    remove_core_paper,
    remove_search_term,
    save_topic,
    slugify,
)


def test_slugify():
    assert slugify("Water Rights") == "water-rights"
    assert slugify("prior  appropriation!") == "prior-appropriation"


def test_create_and_roundtrip(tmp_path):
    t = create_topic(tmp_path, "Water Rights", ["water rights"])
    assert t.name == "Water Rights"
    assert t.search_terms == ["water rights"]
    p = save_topic(t, tmp_path)
    assert p == tmp_path / "water-rights.toml"
    g = load_topic(p)
    assert g.name == "Water Rights"
    assert g.search_terms == ["water rights"]
    assert g.core_paper_ids == [] and g.citation_distance == {}


def test_load_ignores_stray_keys(tmp_path):
    p = tmp_path / "x.toml"
    p.write_text('name = "X"\nsearch_terms = ["a"]\nbogus = "ignore me"\n')
    g = load_topic(p)
    assert g.name == "X" and g.search_terms == ["a"]


def test_search_terms_independent_of_core(tmp_path):
    t = create_topic(tmp_path, "T", ["a", "b"])
    t.core_paper_ids = ["W1"]
    t.collected_paper_ids = ["W1", "W2"]
    remove_search_term(t, "a")
    assert t.search_terms == ["b"]
    assert t.core_paper_ids == ["W1"]  # untouched
    assert t.collected_paper_ids == ["W1", "W2"]  # untouched


def test_promote_moves_collected_to_core(tmp_path):
    t = create_topic(tmp_path, "T", ["a"])
    t.collected_paper_ids = ["W9"]
    promote_to_core(t, "W9")
    assert "W9" in t.core_paper_ids
    assert "W9" not in t.collected_paper_ids


def test_add_search_term_dedups(tmp_path):
    t = create_topic(tmp_path, "T", ["a"])
    add_search_term(t, "a")
    assert t.search_terms == ["a"]


def test_core_add_remove(tmp_path):
    t = create_topic(tmp_path, "T", ["a"])
    add_core_paper(t, "W1")
    add_core_paper(t, "W1")
    assert t.core_paper_ids == ["W1"]
    remove_core_paper(t, "W1")
    assert t.core_paper_ids == []
