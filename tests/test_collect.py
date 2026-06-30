from researcher.collect import collect_for_topic
from researcher.topics import Topic


def _cand(pid, text):
    return {"id": pid, "title": text, "abstract": ""}


class StubOpenbrain:
    def __init__(self, by_term):
        self.by_term = by_term
        self.fetched = []
        self.stored = []

    def fetch_papers(self, topic, *, since=None, limit=50, store=False):
        self.fetched.append((topic, since, limit, store))
        return self.by_term[topic]

    def store_papers(self, papers):
        ids = [p["id"] for p in papers]
        self.stored.append(ids)
        return {"stored_ids": ids}


def test_collect_gates_dedups_and_records():
    topic = Topic(
        name="T",
        search_terms=["water rights", "prior appropriation"],
        collected_paper_ids=["W1"],
    )
    ob = StubOpenbrain(
        {
            "water rights": [
                _cand("W1", "water rights doctrine"),  # overlap 2 -> kept
                _cand("W2", "surface water rights"),  # overlap 2 -> kept
                _cand("WX", "unrelated subject"),  # overlap 0 -> gated out
            ],
            "prior appropriation": [
                _cand("W2", "prior appropriation rule"),  # overlap 2 -> kept (dup)
                _cand("W3", "prior appropriation west"),  # overlap 2 -> kept
            ],
        }
    )
    summary = collect_for_topic(topic, ob, since=2010, limit=5, min_overlap=2)

    assert topic.collected_paper_ids == ["W1", "W2", "W3"]  # deduped, order kept
    assert ob.stored == [["W1", "W2"], ["W2", "W3"]]  # WX dropped by the gate
    assert summary["per_term"] == {"water rights": 2, "prior appropriation": 2}
    assert summary["new_ids"] == ["W2", "W3"]
    assert ob.fetched == [
        ("water rights", 2010, 5, False),
        ("prior appropriation", 2010, 5, False),
    ]


def test_collect_no_terms_is_noop():
    topic = Topic(name="T", search_terms=[])
    summary = collect_for_topic(topic, StubOpenbrain({}))
    assert summary["per_term"] == {} and summary["new_ids"] == []


def test_collect_without_stored_ids_degrades_gracefully():
    class NoIds:
        def fetch_papers(self, topic, *, since=None, limit=50, store=False):
            return [{"id": "W1", "title": "a b", "abstract": ""}]

        def store_papers(self, papers):
            return {"stored": len(papers)}  # older server: no stored_ids

    topic = Topic(name="T", search_terms=["a b"])
    summary = collect_for_topic(topic, NoIds(), min_overlap=2)
    assert topic.collected_paper_ids == []
    assert summary["per_term"] == {"a b": 0} and summary["new_ids"] == []
