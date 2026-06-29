import json
import types

from researcher.openbrain_client import OpenbrainClient


def test_acquire_builds_args_and_parses():
    captured = {}

    def _run(args, capture_output, text, check):
        captured["args"] = args
        return types.SimpleNamespace(
            stdout=json.dumps({"stored": 2, "stored_ids": ["W1", "W2"]}),
            returncode=0,
        )

    client = OpenbrainClient(runner=_run)
    report = client.acquire("water rights", since=2015, limit=10, venues=["AER"])
    assert report["stored_ids"] == ["W1", "W2"]
    a = captured["args"]
    assert a[:2] == ["openbrain-ingest", "acquire"]
    assert "water rights" in a
    assert "--since" in a and "2015" in a
    assert "--limit" in a and "10" in a
    assert "--venue" in a and "AER" in a


def test_acquire_dry_run_flag():
    captured = {}

    def _run(args, capture_output, text, check):
        captured["args"] = args
        return types.SimpleNamespace(stdout=json.dumps({"stored": 0}), returncode=0)

    OpenbrainClient(runner=_run).acquire("x", dry_run=True)
    assert "--dry-run" in captured["args"]


def test_acquire_missing_stored_ids_is_absent_not_error():
    # Without the openbrain stored_ids change (Task 4), the report has no
    # stored_ids; the client must still return the dict unharmed.
    def _run(args, capture_output, text, check):
        return types.SimpleNamespace(stdout=json.dumps({"stored": 3}), returncode=0)

    report = OpenbrainClient(runner=_run).acquire("x")
    assert report["stored"] == 3
    assert "stored_ids" not in report


def test_citation_neighbors_parses():
    def _run(args, capture_output, text, check):
        assert args[:2] == ["openbrain-ingest", "citations"]
        assert args[2] == "W1"
        return types.SimpleNamespace(
            stdout=json.dumps({"neighbors": [{"id": "W2"}, {"id": "W3"}]}),
            returncode=0,
        )

    out = OpenbrainClient(runner=_run).citation_neighbors("W1")
    assert [n["id"] for n in out] == ["W2", "W3"]


def test_relevance_builds_anchors_then_texts_in_order():
    captured = {}

    def _run(args, capture_output, text, check):
        captured["args"] = args
        return types.SimpleNamespace(stdout=json.dumps({"cosines": [0.8, 0.1]}), returncode=0)

    out = OpenbrainClient(runner=_run).relevance(["A1", "A2"], ["t1", "t2"])
    assert out == [0.8, 0.1]
    a = captured["args"]
    assert a[:1] == ["openbrain-ingest"] and a[1] == "relevance"
    # anchors precede texts, order preserved
    assert a.index("--anchor") < a.index("--text")
    assert "A1" in a and "A2" in a and "t1" in a and "t2" in a


def test_store_paper_passes_json():
    captured = {}

    def _run(args, capture_output, text, check):
        captured["args"] = args
        return types.SimpleNamespace(
            stdout=json.dumps({"id": "W9", "deduped": False}), returncode=0
        )

    out = OpenbrainClient(runner=_run).store_paper({"id": "W9", "title": "t"})
    assert out["id"] == "W9"
    assert "store-paper" in captured["args"] and "--json" in captured["args"]


def test_search_library_returns_ids():
    def _run(args, capture_output, text, check):
        assert args[1] == "search-library" and "--limit" in args
        return types.SimpleNamespace(stdout=json.dumps({"ids": ["L1", "L2"]}), returncode=0)

    assert OpenbrainClient(runner=_run).search_library("water", 5) == ["L1", "L2"]
