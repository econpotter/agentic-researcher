"""Connection to the hosted openbrain, reached as a FastMCP client over the SSH
tunnel (the local openbrain checkout is dev-only and does not run).

Every method calls one openbrain MCP tool and returns its structured result. This
is the single seam between the deterministic driver and openbrain; unit tests inject
a stand-in with the same methods, so the live transport is exercised only in an
integration smoke against the deployed server.

Requires these openbrain MCP tools:
  find_papers, fetch_papers, store_papers, get_citations, score_relevance
"""

from __future__ import annotations

import asyncio
import json


def _normalize_result(result: object) -> object:
    """openbrain tools vary: some return structured data, some a JSON string
    (json.dumps), some plain prose (e.g. fetch_papers' batch summary). Parse JSON
    when it parses, otherwise hand back the raw string. Falls back to the first
    text-content block when `.data` is empty."""
    data = getattr(result, "data", None)
    content = getattr(result, "content", None)
    if data is None and content:
        data = getattr(content[0], "text", None)
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            pass  # plain-text tool result; return as-is
    return data


def _expect_dict(result: object, tool: str) -> dict:
    """Boundary check for a tool that must return a structured dict. Raises with
    context (kept as an explicit exception, not `assert`, so it still fires under
    `python -O`)."""
    if not isinstance(result, dict):
        raise TypeError(
            f"openbrain tool {tool!r} returned {type(result).__name__}, expected dict"
        )
    return result


class Openbrain:
    def __init__(
        self, mcp_url: str, token: str | None = None, ca_cert: str | None = None
    ) -> None:
        self._url = mcp_url
        self._token = token
        self._ca_cert = ca_cert

    def _call(self, tool: str, args: dict, timeout: float | None = None) -> object:
        async def go() -> object:
            from fastmcp import Client  # imported lazily so tests need no live server

            client = Client(self._url, auth=self._token, verify=self._ca_cert or True)
            async with client:
                call = client.call_tool(tool, args)
                # Bound the round-trip: a stalled server read once hung the client
                # for hours (no default timeout on the transport).
                result = await (asyncio.wait_for(call, timeout) if timeout else call)
                return _normalize_result(result)

        return asyncio.run(go())

    def find_papers(
        self,
        *,
        text: str | None = None,
        ids: str | None = None,
        limit: int = 10,
        threshold: float = 0.4,
    ) -> dict:
        """Topical/semantic search over the library. Anchor on `text` (a topic
        query) or `ids` (comma-separated library ids → similar papers). Returns
        the tool's dict: `anchors`, `ids` (rank-ordered library ids), `results`."""
        args: dict = {"limit": limit, "threshold": threshold}
        if text is not None:
            args["text"] = text
        if ids is not None:
            args["ids"] = ids
        return _expect_dict(self._call("find_papers", args), "find_papers")

    def fetch_candidates(self, topic: str, *, sources: str | None = None) -> list[dict]:
        """Discovery (topic mode, store=False): fan out across external sources and
        return ranked candidate metadata records (title/doi/authors/year/abstract),
        storing nothing. The driver gates these against the topic's core papers and
        stores only the keepers via `store_papers`."""
        args: dict = {"topic": topic, "store": False}
        if sources is not None:
            args["sources"] = sources
        result = _expect_dict(self._call("fetch_papers", args), "fetch_papers")
        return list(result.get("candidates", []))

    def get_citations(self, paper_id: str) -> list[dict]:
        result = _expect_dict(
            self._call("get_citations", {"paper_id": paper_id}), "get_citations"
        )
        return list(result.get("citations", []))

    def score_relevance(self, core_paper_ids: list[str], texts: list[str]) -> list[float]:
        result = _expect_dict(
            self._call(
                "score_relevance", {"core_paper_ids": core_paper_ids, "texts": texts}
            ),
            "score_relevance",
        )
        if "scores" not in result:
            raise ValueError("score_relevance result missing 'scores'")
        scores = result["scores"]
        if len(scores) != len(texts):
            raise ValueError(
                f"score_relevance returned {len(scores)} scores for {len(texts)} texts"
            )
        return [float(x) for x in scores]

    def fetch_papers(
        self,
        identifiers: list[str],
        *,
        sources: str | None = None,
        force: bool = False,
        timeout: float | None = None,
    ) -> dict:
        """Known-item batch lookup: fetch metadata+abstract for one or more
        DOIs/arXiv IDs/titles from external sources and store them in the library.
        Returns the tool's prose batch summary wrapped as a dict. Dedupes by DOI
        server-side, so re-runs are safe. `timeout` bounds the round-trip
        (seconds); a stalled batch raises asyncio.TimeoutError."""
        args: dict = {"identifiers": list(identifiers), "force": force}
        if sources is not None:
            args["sources"] = sources
        result = self._call("fetch_papers", args, timeout=timeout)
        # fetch_papers returns a prose batch summary; normalize to a dict either way.
        if isinstance(result, str):
            return {"result": result}
        return _expect_dict(result, "fetch_papers")

    def store_papers(self, papers: list[dict]) -> dict:
        """Store chosen paper metadata dicts into the library (crossref enrich,
        venue canon, embed abstract). Returns {stored, deduped, results}."""
        return _expect_dict(
            self._call("store_papers", {"papers": list(papers)}), "store_papers"
        )
