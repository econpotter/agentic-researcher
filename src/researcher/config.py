"""Driver config: the expansion flag + gate tunables (spec §4 defaults)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_DEFAULTS: dict = {
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
