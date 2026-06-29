"""Thin, deterministic wrapper over the openbrain CLI (`openbrain-ingest`).

The driver reaches openbrain ONLY through here — never its DB or sources. Each
method shells out to a CLI subcommand and parses the JSON it prints.
"""

from __future__ import annotations

import json
import subprocess


class OpenbrainClient:
    def __init__(self, cmd: list[str] | None = None, runner=subprocess.run) -> None:
        self.cmd = cmd or ["openbrain-ingest"]
        self._runner = runner

    def _run_json(self, args: list[str]) -> object:
        proc = self._runner(self.cmd + args, capture_output=True, text=True, check=True)
        return json.loads(proc.stdout)

    def acquire(
        self,
        query: str,
        *,
        since: int | None = None,
        limit: int = 50,
        venues: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict:
        args = ["acquire", query, "--limit", str(limit)]
        if since is not None:
            args += ["--since", str(since)]
        for v in venues or []:
            args += ["--venue", v]
        if dry_run:
            args += ["--dry-run"]
        result = self._run_json(args)
        assert isinstance(result, dict)
        return result

    def citation_neighbors(self, paper_id: str) -> list[dict]:
        result = self._run_json(["citations", paper_id])
        assert isinstance(result, dict)
        return list(result.get("neighbors", []))

    def relevance(self, anchor_ids: list[str], texts: list[str]) -> list[float]:
        args = ["relevance"]
        for a in anchor_ids:
            args += ["--anchor", a]
        for t in texts:
            args += ["--text", t]
        result = self._run_json(args)
        assert isinstance(result, dict)
        return [float(x) for x in result["cosines"]]

    def store_paper(self, meta: dict) -> dict:
        result = self._run_json(["store-paper", "--json", json.dumps(meta)])
        assert isinstance(result, dict)
        return result

    def search_library(self, query: str, k: int) -> list[str]:
        result = self._run_json(["search-library", query, "--limit", str(k)])
        assert isinstance(result, dict)
        return [str(x) for x in result["ids"]]
