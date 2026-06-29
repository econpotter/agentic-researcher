from researcher.fronts import Front
from researcher.harvest import harvest_front


class StubClient:
    def __init__(self, by_term):
        self.by_term = by_term
        self.calls = []

    def acquire(self, query, *, since=None, limit=50, venues=None, dry_run=False):
        self.calls.append((query, since, limit))
        return {"stored": len(self.by_term[query]), "stored_ids": self.by_term[query]}


def test_harvest_collects_and_dedups():
    front = Front(label="T", terms=["a", "b"], acquired_paper_ids=["W1"])
    client = StubClient({"a": ["W1", "W2"], "b": ["W2", "W3"]})
    summary = harvest_front(front, client, since=2010, limit=5)
    assert front.acquired_paper_ids == ["W1", "W2", "W3"]  # deduped, order kept
    assert summary["per_term"] == {"a": 2, "b": 2}
    assert summary["new_ids"] == ["W2", "W3"]
    assert client.calls == [("a", 2010, 5), ("b", 2010, 5)]


def test_harvest_no_terms_is_noop():
    front = Front(label="T", terms=[])
    summary = harvest_front(front, StubClient({}))
    assert summary["per_term"] == {} and summary["new_ids"] == []


def test_harvest_without_stored_ids_degrades_gracefully():
    # Mirrors live openbrain before Task 4: report has no stored_ids.
    class NoIdsClient:
        def acquire(self, query, *, since=None, limit=50, venues=None, dry_run=False):
            return {"stored": 4}

    front = Front(label="T", terms=["a"])
    summary = harvest_front(front, NoIdsClient())
    assert front.acquired_paper_ids == []
    assert summary["per_term"] == {"a": 0} and summary["new_ids"] == []
