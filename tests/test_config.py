from pathlib import Path

from researcher.config import load_config


def test_load_overrides_and_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENBRAIN_MCP_TOKEN", raising=False)
    p = tmp_path / "c.yaml"
    p.write_text("citation_expansion: true\n")
    c = load_config(p)
    assert c.citation_expansion is True  # override
    assert c.relevance_radius == 0.40  # default
    assert c.max_citation_distance == 2 and c.max_papers_per_run == 200
    assert c.core_bootstrap_count == 10
    assert c.openbrain_mcp_url.endswith("/mcp")
    assert c.openbrain_mcp_token is None


def test_token_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENBRAIN_MCP_TOKEN", "secret123")
    p = tmp_path / "c.yaml"
    p.write_text("")
    c = load_config(p)
    assert c.citation_expansion is False
    assert c.openbrain_mcp_token == "secret123"


def test_repo_config_yaml_parses():
    repo_cfg = Path(__file__).resolve().parent.parent / "config.yaml"
    c = load_config(repo_cfg)
    assert c.citation_expansion is False
