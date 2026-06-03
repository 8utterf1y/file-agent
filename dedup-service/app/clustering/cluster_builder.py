from dataclasses import dataclass

from app.clustering.union_find import UnionFind
from app.fingerprints.hash_utils import stable_id

SimilarityPair = tuple[str, str, float, str]


@dataclass(frozen=True)
class ClusterBuildResult:
    cluster_id: str
    members: list[str]
    duplicate_type: str
    confidence: float
    member_scores: dict[str, float]
    member_match_types: dict[str, str]


MATCH_PRIORITY = {
    "file_exact": 4,
    "text_exact": 3,
    "chunk_exact": 2,
    "chunk_near": 1,
}


def build_clusters(pairs: list[SimilarityPair]) -> list[ClusterBuildResult]:
    uf = UnionFind()
    pair_lookup: dict[frozenset[str], tuple[float, str]] = {}
    for a, b, score, match_type in pairs:
        uf.union(a, b)
        key = frozenset((a, b))
        old = pair_lookup.get(key)
        if old is None or MATCH_PRIORITY.get(match_type, 0) > MATCH_PRIORITY.get(old[1], 0):
            pair_lookup[key] = (score, match_type)

    results: list[ClusterBuildResult] = []
    for members in uf.clusters():
        member_scores = {member: 1.0 for member in members}
        member_match_types = {member: "chunk_near" for member in members}
        best_type = "chunk_near"
        scores: list[float] = []
        for key, (score, match_type) in pair_lookup.items():
            pair_members = list(key)
            if all(member in members for member in pair_members):
                scores.append(score)
                if MATCH_PRIORITY.get(match_type, 0) > MATCH_PRIORITY.get(best_type, 0):
                    best_type = match_type
                for member in pair_members:
                    member_scores[member] = max(member_scores.get(member, 0.0), score)
                    if MATCH_PRIORITY.get(match_type, 0) > MATCH_PRIORITY.get(member_match_types.get(member, ""), 0):
                        member_match_types[member] = match_type
        confidence = sum(scores) / len(scores) if scores else 1.0
        results.append(
            ClusterBuildResult(
                cluster_id=stable_id("clu", "|".join(members)),
                members=members,
                duplicate_type=best_type,
                confidence=round(confidence, 4),
                member_scores=member_scores,
                member_match_types=member_match_types,
            )
        )
    return results
