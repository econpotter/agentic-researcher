from researcher.collect import collect_for_topic
from researcher.topics import Topic


def _cand(name):
    """A discovery candidate as fetch_papers(store=False) returns it: bibliographic
    metadata + abstract, no library id yet (store_papers mints that)."""
    return {"doi": f"d-{name}", "title": name, "abstract": f"abstract of {name}"}


class StubOpenbrain:
    """Driver-side gate stub: discovery returns candidates, relevance returns a
    score keyed by candidate title, store mints id == doi."""

    def __init__(self, by_term, scores):
        self.by_term = by_term  # term -> [candidate dict]
        self.scores = scores  # title -> similarity
        self.discovered = []
        self.stored = []

    def fetch_candidates(self, topic, *, sources=None):
        self.discovered.append(topic)
        return self.by_term[topic]

    def score_relevance(self, core_paper_ids, texts):
        # text is "<title> abstract of <title>"; first token is the title key
        self.scored_texts = list(texts)
        return [self.scores[t.split()[0]] for t in texts]

    def store_papers(self, papers):
        self.stored.extend(papers)
        return {"stored": len(papers), "deduped": 0,
                "results": [{"id": p["doi"], "deduped": False} for p in papers]}


def test_collect_gates_by_radius_then_stores_and_dedups():
    topic = Topic(name="T", search_terms=["a", "b"], core_paper_ids=["C1"],
                  collected_paper_ids=["C1"])
    ob = StubOpenbrain(
        by_term={"a": [_cand("p1"), _cand("p2")], "b": [_cand("p2"), _cand("p3")]},
        scores={"p1": 0.9, "p2": 0.5, "p3": 0.1},  # radius 0.4 -> p3 dropped
    )
    summary = collect_for_topic(topic, ob, radius=0.4)

    assert ob.discovered == ["a", "b"]
    assert summary["per_term"] == {"a": 2, "b": 1}  # b: only p2 clears radius
    assert summary["new_ids"] == ["d-p1", "d-p2"]  # p2 deduped across terms
    assert topic.collected_paper_ids == ["C1", "d-p1", "d-p2"]


def test_collect_null_abstract_not_stringified():
    # A candidate with a null abstract must score on its title alone, never the
    # literal "None" (fetch_papers returns abstract: null for some records).
    topic = Topic(name="T", search_terms=["a"], core_paper_ids=["C1"])
    ob = StubOpenbrain(
        by_term={"a": [{"doi": "d-p1", "title": "p1", "abstract": None}]},
        scores={"p1": 0.9},
    )
    collect_for_topic(topic, ob, radius=0.4)
    assert ob.scored_texts == ["p1"]


def test_collect_no_terms_is_noop():
    topic = Topic(name="T", search_terms=[], core_paper_ids=["C1"])
    summary = collect_for_topic(topic, StubOpenbrain({}, {}), radius=0.4)
    assert summary["per_term"] == {} and summary["new_ids"] == []


def test_collect_requires_core_for_gate():
    topic = Topic(name="T", search_terms=["a"])  # no core papers
    try:
        collect_for_topic(topic, StubOpenbrain({"a": [_cand("p1")]}, {"p1": 0.9}), radius=0.4)
    except ValueError:
        return
    raise AssertionError("collect must refuse to gate without core papers")
