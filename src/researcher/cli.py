"""`researcher` CLI — sugar over the git-tracked fronts/ toml files."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import fronts as F
from .config import load_config
from .harvest import harvest_front
from .openbrain_client import OpenbrainClient
from .walk import walk_front


def _load(fronts_dir: str, label: str) -> tuple[F.Front, Path]:
    p = F.front_path(Path(fronts_dir), label)
    return F.load_front(p), Path(fronts_dir)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="researcher")
    parser.add_argument("--fronts-dir", default="fronts")
    parser.add_argument("--config-path", default="config.yaml")
    sub = parser.add_subparsers(dest="group", required=True)

    p_front = sub.add_parser("front")
    fsub = p_front.add_subparsers(dest="action", required=True)
    pc = fsub.add_parser("create")
    pc.add_argument("label")
    pc.add_argument("--term", action="append", default=[])
    pcl = fsub.add_parser("create-from-library")
    pcl.add_argument("label")
    pcl.add_argument("--query", required=True)
    fsub.add_parser("list")
    ps = fsub.add_parser("show")
    ps.add_argument("label")

    p_term = sub.add_parser("term")
    tsub = p_term.add_subparsers(dest="action", required=True)
    for act in ("add", "remove"):
        q = tsub.add_parser(act)
        q.add_argument("label")
        q.add_argument("term")

    p_anchor = sub.add_parser("anchor")
    asub = p_anchor.add_subparsers(dest="action", required=True)
    for act in ("add", "remove", "promote"):
        q = asub.add_parser(act)
        q.add_argument("label")
        q.add_argument("pid")

    p_harvest = sub.add_parser("harvest")
    p_harvest.add_argument("label")
    p_harvest.add_argument("--since", type=int, default=None)
    p_harvest.add_argument("--limit", type=int, default=50)

    p_walk = sub.add_parser("walk")
    p_walk.add_argument("label")
    return parser


def main(
    argv: list[str] | None = None,
    client: OpenbrainClient | None = None,
    config_path: str | None = None,
) -> int:
    args = _build_parser().parse_args(argv)
    fd = args.fronts_dir
    cfg_path = config_path or args.config_path

    if args.group == "front":
        if args.action == "create":
            F.create_front(Path(fd), args.label, args.term)
        elif args.action == "create-from-library":
            cfg = load_config(Path(cfg_path))
            ob = client or OpenbrainClient(cmd=cfg.openbrain_cmd)
            ids = ob.search_library(args.query, cfg.anchor_bootstrap_k)
            f = F.Front(
                label=args.label,
                anchor_paper_ids=list(ids),
                acquired_paper_ids=list(ids),
            )
            F.save_front(f, Path(fd))
        elif args.action == "list":
            for p in sorted(Path(fd).glob("*.toml")):
                print(F.load_front(p).label)
        elif args.action == "show":
            f, _ = _load(fd, args.label)
            print(
                f"{f.label}\n  terms: {f.terms}\n  anchors: {f.anchor_paper_ids}"
                f"\n  acquired: {len(f.acquired_paper_ids)}"
            )
        return 0

    if args.group == "term":
        f, d = _load(fd, args.label)
        (F.add_term if args.action == "add" else F.remove_term)(f, args.term)
        F.save_front(f, d)
        return 0

    if args.group == "anchor":
        f, d = _load(fd, args.label)
        {"add": F.add_anchor, "remove": F.remove_anchor, "promote": F.promote}[args.action](
            f, args.pid
        )
        F.save_front(f, d)
        return 0

    if args.group == "harvest":
        f, d = _load(fd, args.label)
        summary = harvest_front(
            f, client or OpenbrainClient(), since=args.since, limit=args.limit
        )
        F.save_front(f, d)
        print(summary)
        return 0

    if args.group == "walk":
        cfg = load_config(Path(cfg_path))
        if cfg.expansion != "citation":
            print("expansion disabled (set expansion: citation in config to enable the walk)")
            return 0
        f, d = _load(fd, args.label)
        ob = client or OpenbrainClient(cmd=cfg.openbrain_cmd)
        summary = walk_front(
            f,
            ob,
            radius=cfg.relevance_radius,
            max_hops=cfg.max_hops,
            per_run_budget=cfg.per_run_budget,
        )
        F.save_front(f, d)
        print(summary)
        return 0

    return 1
