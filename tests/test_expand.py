import pytest

from researcher.expand import expand_by_citations
from researcher.topics import Topic


class StubOpenbrain:
    """W1 cites W2(on-topic) + W3(off-topic); W2 cites W4(on-topic)."""

    GRAPH = {
        "W1": [
            {"id": "W2", "title": "t2", "abstract": ""},
            {"id": "W3", "title": "t3", "abstract": ""},
        ],
        "W2": [{"id": "W4", "title": "t4", "abstract": ""}],
        "W4": [],
    }
    SCORE = {"W2": 0.8, "W3": 0.1, "W4": 0.7}

    def __init__(self):
        self.stored = []

    def get_citations(self, paper_id):
        return self.GRAPH.get(paper_id, [])

    def score_relevance(self, core_paper_ids, texts):
        ids = ["W" + t[1:] for t in texts]  # "t2" -> "W2"
        return [self.SCORE[i] for i in ids]

    def store_papers(self, papers):
        ids = [p["id"] for p in papers]
        self.stored.extend(ids)
        return {"stored_ids": ids}


def test_expand_keeps_on_topic_outward_respects_distance():
    topic = Topic(name="T", core_paper_ids=["C0"], collected_paper_ids=["W1"])
    ob = StubOpenbrain()
    summary = expand_by_citations(
        topic, ob, radius=0.40, max_citation_distance=2, max_papers_per_run=100
    )
    assert ob.stored == ["W2", "W4"]  # W3 (0.1) dropped
    assert "W2" in topic.collected_paper_ids and "W4" in topic.collected_paper_ids
    assert "W3" not in topic.collected_paper_ids
    assert topic.citation_distance == {"W2": 1, "W4": 2}
    assert summary["added"] == 2


def test_expand_respects_budget():
    topic = Topic(name="T", core_paper_ids=["C0"], collected_paper_ids=["W1"])
    summary = expand_by_citations(
        topic, StubOpenbrain(), radius=0.40, max_citation_distance=5, max_papers_per_run=1
    )
    assert summary["added"] == 1 and summary["stopped"] == "budget"


def test_expand_requires_core_papers():
    with pytest.raises(ValueError):
        expand_by_citations(
            Topic(name="T", collected_paper_ids=["W1"]),
            StubOpenbrain(),
            radius=0.4,
            max_citation_distance=2,
            max_papers_per_run=10,
        )
