import pytest

from researcher.expand import expand_by_citations
from researcher.topics import Topic


class StubOpenbrain:
    """Citation neighbors carry DOIs but NO library id (they aren't stored yet).
    store_papers mints a library id 'lib-<doi>'; get_citations is keyed by the
    library id the driver actually walks (the seed, then each minted id).

      seed 'lib1' -> d2 (on-topic) + d3 (off-topic); 'lib-d2' -> d4 (on-topic).
    """

    GRAPH = {
        "lib1": [
            {"doi": "d2", "title": "t2", "abstract": ""},
            {"doi": "d3", "title": "t3", "abstract": ""},
        ],
        "lib-d2": [{"doi": "d4", "title": "t4", "abstract": ""}],
        "lib-d4": [],
    }
    SCORE = {"t2": 0.8, "t3": 0.1, "t4": 0.7}

    def __init__(self):
        self.stored = []

    def get_citations(self, paper_id):
        return self.GRAPH.get(paper_id, [])

    def score_relevance(self, core_paper_ids, texts):
        return [self.SCORE[t.split()[0]] for t in texts]

    def store_papers(self, papers):
        results = []
        for paper in papers:
            sid = "lib-" + paper["doi"]
            self.stored.append(sid)
            results.append({"id": sid, "deduped": False})
        return {"stored": len(papers), "deduped": 0, "results": results}


def test_expand_keeps_on_topic_outward_respects_distance():
    topic = Topic(name="T", core_paper_ids=["C0"], collected_paper_ids=["lib1"])
    ob = StubOpenbrain()
    summary = expand_by_citations(
        topic, ob, radius=0.40, max_citation_distance=2, max_papers_per_run=100
    )
    assert ob.stored == ["lib-d2", "lib-d4"]  # d3 (0.1) dropped
    assert "lib-d2" in topic.collected_paper_ids
    assert "lib-d4" in topic.collected_paper_ids
    assert "lib-d3" not in topic.collected_paper_ids
    assert topic.citation_distance == {"lib-d2": 1, "lib-d4": 2}
    assert summary["added"] == 2


def test_expand_respects_budget():
    topic = Topic(name="T", core_paper_ids=["C0"], collected_paper_ids=["lib1"])
    summary = expand_by_citations(
        topic, StubOpenbrain(), radius=0.40, max_citation_distance=5, max_papers_per_run=1
    )
    assert summary["added"] == 1 and summary["stopped"] == "budget"


def test_expand_raises_on_score_candidate_mismatch():
    topic = Topic(name="T", core_paper_ids=["C0"], collected_paper_ids=["lib1"])
    ob = StubOpenbrain()
    ob.score_relevance = lambda core, texts: [0.8]  # one score, two fresh neighbors
    with pytest.raises(ValueError, match="1 scores for 2 candidates"):
        expand_by_citations(
            topic, ob, radius=0.40, max_citation_distance=2, max_papers_per_run=100
        )


def test_expand_requires_core_papers():
    with pytest.raises(ValueError):
        expand_by_citations(
            Topic(name="T", collected_paper_ids=["lib1"]),
            StubOpenbrain(),
            radius=0.4,
            max_citation_distance=2,
            max_papers_per_run=10,
        )
