"""Connection to the hosted openbrain, reached as a FastMCP client over the SSH
tunnel (the local openbrain checkout is dev-only and does not run).

Every method calls one openbrain MCP tool and returns its structured result. This
is the single seam between the deterministic driver and openbrain; unit tests inject
a stand-in with the same methods, so the live transport is exercised only in an
integration smoke against the deployed server.

Requires these openbrain MCP tools (acquire/search_library exist today; the rest are
added by the openbrain "external-driver primitives" issue and a host redeploy):
  acquire, get_citations, score_relevance, store_paper, search_library
"""

from __future__ import annotations

import asyncio


class Openbrain:
    def __init__(self, mcp_url: str, token: str | None = None) -> None:
        self._url = mcp_url
        self._token = token

    def _call(self, tool: str, args: dict) -> object:
        async def go() -> object:
            from fastmcp import Client  # imported lazily so tests need no live server

            client = Client(self._url, auth=self._token)
            async with client:
                result = await client.call_tool(tool, args)
                return result.data

        return asyncio.run(go())

    def acquire(
        self,
        query: str,
        *,
        since: int | None = None,
        limit: int = 50,
    ) -> dict:
        args: dict = {"query": query, "limit": limit}
        if since is not None:
            args["since"] = since
        result = self._call("acquire", args)
        assert isinstance(result, dict)
        return result

    def get_citations(self, paper_id: str) -> list[dict]:
        result = self._call("get_citations", {"paper_id": paper_id})
        assert isinstance(result, dict)
        return list(result.get("citations", []))

    def score_relevance(self, core_paper_ids: list[str], texts: list[str]) -> list[float]:
        result = self._call(
            "score_relevance", {"core_paper_ids": core_paper_ids, "texts": texts}
        )
        assert isinstance(result, dict)
        return [float(x) for x in result["scores"]]

    def store_paper(self, paper: dict) -> dict:
        result = self._call("store_paper", {"paper": paper})
        assert isinstance(result, dict)
        return result

    def search_library(self, query: str, limit: int) -> list[str]:
        result = self._call("search_library", {"query": query, "limit": limit})
        assert isinstance(result, dict)
        return [str(x) for x in result["ids"]]
