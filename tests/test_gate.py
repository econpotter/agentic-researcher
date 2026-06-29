from researcher.gate import keep


def test_keeps_on_topic_within_depth():
    assert keep(0.55, 1, radius=0.40, max_hops=2) is True


def test_drops_below_radius():
    assert keep(0.30, 1, radius=0.40, max_hops=2) is False


def test_drops_beyond_depth():
    assert keep(0.99, 3, radius=0.40, max_hops=2) is False


def test_boundary_inclusive():
    assert keep(0.40, 2, radius=0.40, max_hops=2) is True
