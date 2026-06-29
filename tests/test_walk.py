import pytest

from researcher.fronts import Front
from researcher.walk import walk_front


class StubClient:
    """W1 cites W2(on-topic) + W3(off-topic); W2 cites W4(on-topic)."""

    GRAPH = {
        "W1": [
            {"id": "W2", "title": "t2", "abstract": ""},
            {"id": "W3", "title": "t3", "abstract": ""},
        ],
        "W2": [{"id": "W4", "title": "t4", "abstract": ""}],
        "W4": [],
    }
    COS = {"W2": 0.8, "W3": 0.1, "W4": 0.7}

    def __init__(self):
        self.stored = []

    def citation_neighbors(self, paper_id):
        return self.GRAPH.get(paper_id, [])

    def relevance(self, anchor_ids, texts):
        ids = ["W" + t[1:] for t in texts]  # "t2" -> "W2"
        return [self.COS[i] for i in ids]

    def store_paper(self, meta):
        self.stored.append(meta["id"])
        return {"id": meta["id"], "deduped": False}


def test_walk_keeps_on_topic_outward_respects_depth():
    front = Front(label="T", anchor_paper_ids=["A0"], acquired_paper_ids=["W1"])
    client = StubClient()
    summary = walk_front(front, client, radius=0.40, max_hops=2, per_run_budget=100)
    assert client.stored == ["W2", "W4"]  # W3 (0.1) dropped
    assert "W2" in front.acquired_paper_ids and "W4" in front.acquired_paper_ids
    assert "W3" not in front.acquired_paper_ids
    assert front.hop_depth == {"W2": 1, "W4": 2}
    assert summary["added"] == 2


def test_walk_respects_budget():
    front = Front(label="T", anchor_paper_ids=["A0"], acquired_paper_ids=["W1"])
    summary = walk_front(front, StubClient(), radius=0.40, max_hops=5, per_run_budget=1)
    assert summary["added"] == 1 and summary["stopped"] == "budget"


def test_walk_requires_anchors():
    with pytest.raises(ValueError):
        walk_front(
            Front(label="T", acquired_paper_ids=["W1"]),
            StubClient(),
            radius=0.4,
            max_hops=2,
            per_run_budget=10,
        )
