from app.clustering.cluster_builder import build_clusters
from app.clustering.union_find import UnionFind


def test_pair_can_form_cluster() -> None:
    uf = UnionFind()
    uf.union("a", "b")
    assert uf.clusters() == [["a", "b"]]


def test_cluster_builder_merges_pairs() -> None:
    clusters = build_clusters([("a", "b", 1.0, "chunk_exact"), ("b", "c", 0.92, "chunk_near")])
    assert len(clusters) == 1
    assert clusters[0].members == ["a", "b", "c"]
