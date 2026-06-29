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
