from researcher.relevance import is_relevant


def test_keeps_on_topic_within_distance():
    assert is_relevant(0.55, 1, radius=0.40, max_distance=2) is True


def test_drops_below_radius():
    assert is_relevant(0.30, 1, radius=0.40, max_distance=2) is False


def test_drops_beyond_distance():
    assert is_relevant(0.99, 3, radius=0.40, max_distance=2) is False


def test_boundary_inclusive():
    assert is_relevant(0.40, 2, radius=0.40, max_distance=2) is True
