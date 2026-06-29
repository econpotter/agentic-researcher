from researcher.collect import collect_for_topic
from researcher.topics import Topic


class StubOpenbrain:
    def __init__(self, by_term):
        self.by_term = by_term
        self.calls = []

    def acquire(self, query, *, since=None, limit=50):
        self.calls.append((query, since, limit))
        return {"stored": len(self.by_term[query]), "stored_ids": self.by_term[query]}


def test_collect_gathers_and_dedups():
    topic = Topic(name="T", search_terms=["a", "b"], collected_paper_ids=["W1"])
    ob = StubOpenbrain({"a": ["W1", "W2"], "b": ["W2", "W3"]})
    summary = collect_for_topic(topic, ob, since=2010, limit=5)
    assert topic.collected_paper_ids == ["W1", "W2", "W3"]  # deduped, order kept
    assert summary["per_term"] == {"a": 2, "b": 2}
    assert summary["new_ids"] == ["W2", "W3"]
    assert ob.calls == [("a", 2010, 5), ("b", 2010, 5)]


def test_collect_no_terms_is_noop():
    topic = Topic(name="T", search_terms=[])
    summary = collect_for_topic(topic, StubOpenbrain({}))
    assert summary["per_term"] == {} and summary["new_ids"] == []


def test_collect_without_ids_degrades_gracefully():
    class NoIds:
        def acquire(self, query, *, since=None, limit=50):
            return {"stored": 4}

    topic = Topic(name="T", search_terms=["a"])
    summary = collect_for_topic(topic, NoIds())
    assert topic.collected_paper_ids == []
    assert summary["per_term"] == {"a": 0} and summary["new_ids"] == []
