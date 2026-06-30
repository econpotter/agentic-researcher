"""`researcher` CLI — sugar over the git-tracked topics/ toml files.

  researcher topic create <name> [--term T ...]
  researcher topic create-from-library <name> --query Q
  researcher topic list | show <name>
  researcher term add|remove <name> <term>
  researcher core add|remove|promote <name> <paper_id>
  researcher collect <name> [--since N] [--limit N]
  researcher expand <name>
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import topics as T
from .collect import collect_for_topic
from .config import load_config
from .expand import expand_by_citations
from .openbrain import Openbrain


def _load(topics_dir: str, name: str) -> tuple[T.Topic, Path]:
    return T.load_topic(T.topic_path(Path(topics_dir), name)), Path(topics_dir)


def _connect(cfg) -> Openbrain:
    return Openbrain(
        cfg.openbrain_mcp_url, token=cfg.openbrain_mcp_token, ca_cert=cfg.openbrain_ca_cert
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="researcher")
    parser.add_argument("--topics-dir", default="topics")
    parser.add_argument("--config-path", default="config.yaml")
    sub = parser.add_subparsers(dest="group", required=True)

    p_topic = sub.add_parser("topic")
    tsub = p_topic.add_subparsers(dest="action", required=True)
    pc = tsub.add_parser("create")
    pc.add_argument("name")
    pc.add_argument("--term", action="append", default=[])
    pcl = tsub.add_parser("create-from-library")
    pcl.add_argument("name")
    pcl.add_argument("--query", required=True)
    tsub.add_parser("list")
    ps = tsub.add_parser("show")
    ps.add_argument("name")

    p_term = sub.add_parser("term")
    term_sub = p_term.add_subparsers(dest="action", required=True)
    for act in ("add", "remove"):
        q = term_sub.add_parser(act)
        q.add_argument("name")
        q.add_argument("term")

    p_core = sub.add_parser("core")
    core_sub = p_core.add_subparsers(dest="action", required=True)
    for act in ("add", "remove", "promote"):
        q = core_sub.add_parser(act)
        q.add_argument("name")
        q.add_argument("paper_id")

    p_collect = sub.add_parser("collect")
    p_collect.add_argument("name")
    p_collect.add_argument("--since", type=int, default=None)
    p_collect.add_argument("--limit", type=int, default=50)

    p_expand = sub.add_parser("expand")
    p_expand.add_argument("name")
    return parser


def main(
    argv: list[str] | None = None,
    openbrain: Openbrain | None = None,
    config_path: str | None = None,
) -> int:
    from dotenv import load_dotenv

    load_dotenv()  # pull OPENBRAIN_MCP_TOKEN from a local .env if present
    args = _build_parser().parse_args(argv)
    td = args.topics_dir
    cfg_path = config_path or args.config_path

    if args.group == "topic":
        if args.action == "create":
            T.create_topic(Path(td), args.name, args.term)
        elif args.action == "create-from-library":
            cfg = load_config(Path(cfg_path))
            ob = openbrain or _connect(cfg)
            ids = ob.find_papers(args.query, cfg.core_bootstrap_count)
            topic = T.Topic(
                name=args.name,
                core_paper_ids=list(ids),
                collected_paper_ids=list(ids),
            )
            T.save_topic(topic, Path(td))
        elif args.action == "list":
            for p in sorted(Path(td).glob("*.toml")):
                print(T.load_topic(p).name)
        elif args.action == "show":
            topic, _ = _load(td, args.name)
            print(
                f"{topic.name}\n  search_terms: {topic.search_terms}"
                f"\n  core_papers: {topic.core_paper_ids}"
                f"\n  collected: {len(topic.collected_paper_ids)}"
            )
        return 0

    if args.group == "term":
        topic, d = _load(td, args.name)
        (T.add_search_term if args.action == "add" else T.remove_search_term)(topic, args.term)
        T.save_topic(topic, d)
        return 0

    if args.group == "core":
        topic, d = _load(td, args.name)
        {
            "add": T.add_core_paper,
            "remove": T.remove_core_paper,
            "promote": T.promote_to_core,
        }[args.action](topic, args.paper_id)
        T.save_topic(topic, d)
        return 0

    if args.group == "collect":
        cfg = load_config(Path(cfg_path))
        topic, d = _load(td, args.name)
        summary = collect_for_topic(
            topic,
            openbrain or _connect(cfg),
            since=args.since,
            limit=args.limit,
            min_overlap=cfg.min_overlap,
        )
        T.save_topic(topic, d)
        print(summary)
        return 0

    if args.group == "expand":
        cfg = load_config(Path(cfg_path))
        if not cfg.citation_expansion:
            print("citation_expansion is off — set citation_expansion: true in config to enable")
            return 0
        topic, d = _load(td, args.name)
        summary = expand_by_citations(
            topic,
            openbrain or _connect(cfg),
            radius=cfg.relevance_radius,
            max_citation_distance=cfg.max_citation_distance,
            max_papers_per_run=cfg.max_papers_per_run,
        )
        T.save_topic(topic, d)
        print(summary)
        return 0

    return 1
