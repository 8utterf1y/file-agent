from itertools import combinations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.clustering.cluster_builder import build_clusters
from app.config import get_settings
from app.detectors.exact_detector import (
    SimilarityPair,
    chunk_exact_pairs,
    grouped_document_ids_by_file_hash,
    grouped_document_ids_by_text_hash,
)
from app.detectors.minhash_detector import MinHashDetector
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.duplicate import DuplicateCluster, DuplicateMember
from app.recommendations.canonical_selector import select_canonical_chunk
from app.recommendations.reorg_suggester import suggest_action


def run_dedup_analysis(db: Session) -> int:
    db.execute(delete(DuplicateMember))
    db.execute(delete(DuplicateCluster))
    db.commit()

    documents = list(db.scalars(select(Document)))
    chunks = list(db.scalars(select(Chunk)))
    documents_by_id = {doc.doc_id: doc for doc in documents}
    chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    chunk_ids_by_doc = _first_chunk_ids_by_doc(chunks)

    pairs: list[SimilarityPair] = []
    pairs.extend(_doc_groups_to_chunk_pairs(grouped_document_ids_by_file_hash(documents), chunk_ids_by_doc, "file_exact"))
    pairs.extend(_doc_groups_to_chunk_pairs(grouped_document_ids_by_text_hash(documents), chunk_ids_by_doc, "text_exact"))
    pairs.extend(chunk_exact_pairs(chunks))
    pairs.extend(_chunk_near_pairs(chunks))

    clusters = build_clusters(pairs)
    for cluster in clusters:
        cluster_chunks = [chunks_by_id[chunk_id] for chunk_id in cluster.members if chunk_id in chunks_by_id]
        canonical_chunk_id, reason = select_canonical_chunk(cluster_chunks, documents_by_id)
        action, risk = suggest_action(cluster.duplicate_type, len(cluster.members), cluster.confidence)
        summary = f"{reason} 簇内共有 {len(cluster.members)} 个片段，平均相似度 {cluster.confidence:.2f}。"
        db.add(
            DuplicateCluster(
                cluster_id=cluster.cluster_id,
                duplicate_type=cluster.duplicate_type,
                canonical_chunk_id=canonical_chunk_id,
                confidence=cluster.confidence,
                risk_level=risk,
                suggested_action=action,
                summary=summary,
            )
        )
        for chunk_id in cluster.members:
            db.add(
                DuplicateMember(
                    cluster_id=cluster.cluster_id,
                    chunk_id=chunk_id,
                    similarity_score=cluster.member_scores.get(chunk_id, cluster.confidence),
                    match_type=cluster.member_match_types.get(chunk_id, cluster.duplicate_type),
                    reason=reason,
                )
            )
    db.commit()
    return len(clusters)


def _first_chunk_ids_by_doc(chunks: list[Chunk]) -> dict[str, str]:
    result: dict[str, str] = {}
    for chunk in sorted(chunks, key=lambda item: item.chunk_id):
        result.setdefault(chunk.doc_id, chunk.chunk_id)
    return result


def _doc_groups_to_chunk_pairs(
    doc_groups: list[list[str]],
    chunk_ids_by_doc: dict[str, str],
    match_type: str,
) -> list[SimilarityPair]:
    pairs: list[SimilarityPair] = []
    for group in doc_groups:
        chunk_ids = [chunk_ids_by_doc[doc_id] for doc_id in group if doc_id in chunk_ids_by_doc]
        for a, b in combinations(chunk_ids, 2):
            pairs.append((a, b, 1.0, match_type))
    return pairs


def _chunk_near_pairs(chunks: list[Chunk]) -> list[SimilarityPair]:
    settings = get_settings()
    detector = MinHashDetector(threshold=settings.lsh_threshold, num_perm=settings.minhash_num_perm)
    for chunk in chunks:
        detector.add(chunk.chunk_id, chunk.text)

    pairs: list[SimilarityPair] = []
    seen: set[frozenset[str]] = set()
    for chunk in chunks:
        for candidate_id in detector.query(chunk.text):
            if candidate_id == chunk.chunk_id:
                continue
            key = frozenset((chunk.chunk_id, candidate_id))
            if key in seen:
                continue
            seen.add(key)
            score = detector.jaccard_estimate(chunk.chunk_id, candidate_id)
            if score is not None and score < 1.0:
                pairs.append((chunk.chunk_id, candidate_id, round(score, 4), "chunk_near"))
    return pairs
