"""Step 5B candidate-pool tests."""

from uuid import uuid4

from marketpilot.benchmark.step5_pool import build_pool


def test_top_k_pool_union_and_dedup() -> None:
    a, b, c, d = (uuid4() for _ in range(4))
    pool = build_pool([[a, b], [a, c], [b, d]], top_k=2)
    assert pool == [a, b, c, d]
    assert len(pool) == len(set(pool))


def test_prefix_semantics() -> None:
    a, b, c = (uuid4() for _ in range(3))
    rankings = [[a, b], [c, a]]
    assert build_pool(rankings[:1], 2) == [a, b]
    assert build_pool(rankings[:2], 2) == [a, b, c]
