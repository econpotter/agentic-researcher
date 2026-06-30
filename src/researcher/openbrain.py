"""Connection to the hosted openbrain, reached as a FastMCP client over the SSH
tunnel (the local openbrain checkout is dev-only and does not run).

Every method calls one openbrain MCP tool and returns its structured result. This
is the single seam between the deterministic driver and openbrain; unit tests inject
a stand-in with the same methods, so the live transport is exercised only in an
integration smoke against the deployed server.

Requires these openbrain MCP tools (find_papers exists today; fetch_papers and
store_papers split the old combined search-and-store tool in the "external-driver
primitives" lockstep — its server-side lexical recall gate now lives driver-side —
and a host redeploy adds the rest):
  fetch_papers, store_papers, get_citations, score_relevance, find_papers
"""

from __future__ import annotations

import asyncio
import json


class Openbrain:
    def __init__(
        self, mcp_url: str, token: str | None = None, ca_cert: str | None = None
    ) -> None:
        self._url = mcp_url
        self._token = token
        self._ca_cert = ca_cert

    def _call(self, tool: str, args: dict) -> object:
        async def go() -> object:
            from fastmcp import Client  # imported lazily so tests need no live server

            client = Client(self._url, auth=self._token, verify=self._ca_cert or True)
            async with client:
                result = await client.call_tool(tool, args)
                # openbrain tools vary: some return structured data, others a JSON
                # string (json.dumps). Normalize to the parsed object. Falls back to
                # the first text-content block when .data is empty.
                data = result.data
                if data is None and result.content:
                    data = getattr(result.content[0], "text", None)
                if isinstance(data, str):
                    data = json.loads(data)
                return data

        return asyncio.run(go())

    def fetch_papers(
        self,
        topic: str,
        *,
        since: int | None = None,
        limit: int = 50,
        store: bool = False,
    ) -> list[dict]:
        args: dict = {"topic": topic, "limit": limit, "store": store}
        if since is not None:
            args["since"] = since
        result = self._call("fetch_papers", args)
        assert isinstance(result, dict)
        return [dict(c) for c in result.get("candidates", [])]

    def store_papers(self, papers: list[dict]) -> dict:
        result = self._call("store_papers", {"papers": papers})
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

    def find_papers(self, text: str, limit: int) -> list[str]:
        result = self._call("find_papers", {"text": text, "limit": limit})
        assert isinstance(result, dict)
        return [str(x) for x in result["ids"]]
