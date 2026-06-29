from researcher.config import load_config


def test_load_overrides_and_defaults(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("expansion: citation\n")
    c = load_config(p)
    assert c.expansion == "citation"  # override
    assert c.relevance_radius == 0.40  # default
    assert c.max_hops == 2 and c.per_run_budget == 200
    assert c.anchor_bootstrap_k == 10
    assert c.openbrain_cmd == ["openbrain-ingest"]


def test_empty_file_is_all_defaults(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("")
    c = load_config(p)
    assert c.expansion == "none"
    assert c.relevance_radius == 0.40


def test_repo_config_yaml_parses():
    from pathlib import Path

    repo_cfg = Path(__file__).resolve().parent.parent / "config.yaml"
    c = load_config(repo_cfg)
    assert c.expansion == "none"
    assert c.openbrain_cmd == ["openbrain-ingest"]
