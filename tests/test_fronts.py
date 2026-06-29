from researcher.fronts import (
    add_anchor,
    add_term,
    create_front,
    load_front,
    promote,
    remove_anchor,
    remove_term,
    save_front,
    slugify,
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


def test_load_ignores_stray_keys(tmp_path):
    p = tmp_path / "x.toml"
    p.write_text('label = "X"\nterms = ["a"]\nbogus = "ignore me"\n')
    g = load_front(p)
    assert g.label == "X" and g.terms == ["a"]


def test_term_ops_are_independent_of_anchors(tmp_path):
    f = create_front(tmp_path, "T", ["a", "b"])
    f.anchor_paper_ids = ["W1"]
    f.acquired_paper_ids = ["W1", "W2"]
    remove_term(f, "a")
    assert f.terms == ["b"]
    assert f.anchor_paper_ids == ["W1"]  # untouched
    assert f.acquired_paper_ids == ["W1", "W2"]  # untouched


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


def test_anchor_add_remove(tmp_path):
    f = create_front(tmp_path, "T", ["a"])
    add_anchor(f, "W1")
    add_anchor(f, "W1")
    assert f.anchor_paper_ids == ["W1"]
    remove_anchor(f, "W1")
    assert f.anchor_paper_ids == []
