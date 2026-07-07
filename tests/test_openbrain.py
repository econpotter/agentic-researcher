"""Direct unit tests for the openbrain seam: `_call` result normalization (per
branch), the round-trip timeout, and the boundary checks that used to be bare
`assert isinstance(...)` (now explicit exceptions that survive `python -O`)."""

import asyncio
import sys
import types

import pytest

from researcher.openbrain import Openbrain, _expect_dict, _normalize_result


class FakeBlock:
    def __init__(self, text):
        self.text = text


class FakeResult:
    """Stands in for a fastmcp CallToolResult: has `.data` and `.content`."""

    def __init__(self, data=None, content=None):
        self.data = data
        self.content = content or []


# --- _normalize_result: one test per branch --------------------------------


def test_normalize_passes_through_structured_dict():
    assert _normalize_result(FakeResult(data={"scores": [0.1]})) == {"scores": [0.1]}


def test_normalize_parses_json_string():
    assert _normalize_result(FakeResult(data='{"a": 1}')) == {"a": 1}


def test_normalize_returns_plain_prose_unparsed():
    assert _normalize_result(FakeResult(data="stored 3 papers")) == "stored 3 papers"


def test_normalize_falls_back_to_content_block_when_data_empty():
    result = FakeResult(data=None, content=[FakeBlock('{"x": 2}')])
    assert _normalize_result(result) == {"x": 2}


def test_normalize_content_block_plain_text():
    result = FakeResult(data=None, content=[FakeBlock("batch summary")])
    assert _normalize_result(result) == "batch summary"


def test_normalize_none_without_content_stays_none():
    assert _normalize_result(FakeResult(data=None)) is None


# --- _expect_dict boundary check -------------------------------------------


def test_expect_dict_passes_dict_through():
    assert _expect_dict({"ok": 1}, "find_papers") == {"ok": 1}


def test_expect_dict_raises_with_tool_context():
    with pytest.raises(TypeError, match="find_papers"):
        _expect_dict("not a dict", "find_papers")


# --- _call: timeout + passthrough via an injected fake fastmcp --------------


def _install_fake_fastmcp(monkeypatch, call_tool):
    """Inject a `fastmcp` module whose Client.call_tool runs `call_tool`."""

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def call_tool(self, tool, args):
            return await call_tool(tool, args)

    module = types.ModuleType("fastmcp")
    module.Client = FakeClient
    monkeypatch.setitem(sys.modules, "fastmcp", module)


def test_call_normalizes_result_without_timeout(monkeypatch):
    async def call_tool(tool, args):
        return FakeResult(data={"tool": tool, "args": args})

    _install_fake_fastmcp(monkeypatch, call_tool)
    ob = Openbrain("mcp://x")
    assert ob._call("get_citations", {"paper_id": "p1"}) == {
        "tool": "get_citations",
        "args": {"paper_id": "p1"},
    }


def test_call_bounds_roundtrip_with_timeout(monkeypatch):
    async def call_tool(tool, args):
        await asyncio.sleep(10)  # never completes within the timeout
        return FakeResult(data={})

    _install_fake_fastmcp(monkeypatch, call_tool)
    ob = Openbrain("mcp://x")
    with pytest.raises(asyncio.TimeoutError):
        ob._call("fetch_papers", {}, timeout=0.01)


# --- score_relevance length validation -------------------------------------


class _ScoreStub(Openbrain):
    """Openbrain with `_call` short-circuited to a canned score_relevance reply."""

    def __init__(self, reply):
        super().__init__("mcp://x")
        self._reply = reply

    def _call(self, tool, args, timeout=None):
        return self._reply


def test_score_relevance_rejects_length_mismatch():
    ob = _ScoreStub({"scores": [0.1, 0.2]})
    with pytest.raises(ValueError, match="3 texts"):
        ob.score_relevance(["C1"], ["t1", "t2", "t3"])


def test_score_relevance_rejects_missing_scores_key():
    ob = _ScoreStub({"anchors": []})
    with pytest.raises(ValueError, match="missing 'scores'"):
        ob.score_relevance(["C1"], ["t1"])


def test_score_relevance_returns_floats_on_match():
    ob = _ScoreStub({"scores": [0.1, 0.9]})
    assert ob.score_relevance(["C1"], ["t1", "t2"]) == [0.1, 0.9]
