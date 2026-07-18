"""Driver config: the citation-expansion switch, its tunables, and the openbrain
MCP endpoint. See ``_DEFAULTS`` below for the default value of each tunable."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

_DEFAULTS: dict = {
    "citation_expansion": False,
    "relevance_radius": 0.40,
    "max_citation_distance": 2,
    "max_papers_per_run": 200,
    "core_bootstrap_count": 10,
    "openbrain_mcp_url": "http://localhost:8000/mcp",
    "openbrain_ca_cert": None,  # path to a CA cert (e.g. Caddy) if the MCP uses self-signed TLS
}

#: env var holding the openbrain MCP bearer token (kept out of the config file).
TOKEN_ENV = "OPENBRAIN_MCP_TOKEN"

#: env var overriding the CA cert path (a personal filesystem path, kept out of
#: the tracked config file). When set, it wins over any `openbrain_ca_cert` in yaml.
CA_CERT_ENV = "OPENBRAIN_CA_CERT"


@dataclass
class Config:
    citation_expansion: bool
    relevance_radius: float
    max_citation_distance: int
    max_papers_per_run: int
    core_bootstrap_count: int
    openbrain_mcp_url: str
    openbrain_ca_cert: str | None
    openbrain_mcp_token: str | None


def load_config(path: Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    merged = {**_DEFAULTS, **raw}
    merged["openbrain_ca_cert"] = os.environ.get(CA_CERT_ENV) or merged["openbrain_ca_cert"]
    return Config(
        **{k: merged[k] for k in _DEFAULTS},
        openbrain_mcp_token=os.environ.get(TOKEN_ENV) or None,
    )
