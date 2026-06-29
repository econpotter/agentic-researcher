"""Topic model: a named research topic with curated core papers and collection state.

A topic is a git-tracked toml file under topics/, one per topic. Three things are
deliberately separate:
  - name           — its identity (permanent)
  - search_terms   — the queries we collect papers for (a mutable list; removing one
                     loses nothing else)
  - core_paper_ids — the papers that DEFINE the topic; relevance during expansion is
                     measured against these. You curate them; expansion never changes them.

The relevance centroid is NOT stored here; openbrain computes it from the core papers'
embeddings at expansion time.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import tomli_w


@dataclass
class Topic:
    name: str
    search_terms: list[str] = field(default_factory=list)
    core_paper_ids: list[str] = field(default_factory=list)
    collected_paper_ids: list[str] = field(default_factory=list)
    expanded_paper_ids: list[str] = field(default_factory=list)
    citation_distance: dict[str, int] = field(default_factory=dict)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def topic_path(topics_dir: Path, name: str) -> Path:
    return Path(topics_dir) / f"{slugify(name)}.toml"


def load_topic(path: Path) -> Topic:
    # Derive from the dataclass schema: keep only known fields (robust to stray
    # toml keys); the dataclass fills defaults for any absent ones.
    data = tomllib.loads(Path(path).read_text())
    known = {f.name for f in fields(Topic)}
    return Topic(**{k: v for k, v in data.items() if k in known})


def save_topic(topic: Topic, topics_dir: Path) -> Path:
    # asdict() derives the payload from the dataclass — the schema is defined once.
    path = topic_path(topics_dir, topic.name)
    Path(topics_dir).mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps(asdict(topic)))
    return path


def create_topic(topics_dir: Path, name: str, search_terms: list[str]) -> Topic:
    topic = Topic(name=name, search_terms=list(dict.fromkeys(search_terms)))
    save_topic(topic, topics_dir)
    return topic


def add_search_term(topic: Topic, term: str) -> None:
    if term not in topic.search_terms:
        topic.search_terms.append(term)


def remove_search_term(topic: Topic, term: str) -> None:
    if term in topic.search_terms:
        topic.search_terms.remove(term)


def add_core_paper(topic: Topic, paper_id: str) -> None:
    if paper_id not in topic.core_paper_ids:
        topic.core_paper_ids.append(paper_id)


def remove_core_paper(topic: Topic, paper_id: str) -> None:
    if paper_id in topic.core_paper_ids:
        topic.core_paper_ids.remove(paper_id)


def promote_to_core(topic: Topic, paper_id: str) -> None:
    """Promote a collected paper to a core (defining) paper of the topic."""
    if paper_id in topic.collected_paper_ids:
        topic.collected_paper_ids.remove(paper_id)
    add_core_paper(topic, paper_id)
