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
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


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
