from collections import defaultdict
from itertools import combinations

from app.models.chunk import Chunk
from app.models.document import Document


SimilarityPair = tuple[str, str, float, str]


def grouped_document_ids_by_file_hash(documents: list[Document]) -> list[list[str]]:
    return _groups([(doc.file_hash, doc.doc_id) for doc in documents if doc.file_hash])


def grouped_document_ids_by_text_hash(documents: list[Document]) -> list[list[str]]:
    return _groups([(doc.normalized_text_hash, doc.doc_id) for doc in documents if doc.normalized_text_hash])


def chunk_exact_pairs(chunks: list[Chunk]) -> list[SimilarityPair]:
    pairs: list[SimilarityPair] = []
    groups = _groups([(chunk.text_hash, chunk.chunk_id) for chunk in chunks if chunk.text_hash])
    for group in groups:
        for a, b in combinations(group, 2):
            pairs.append((a, b, 1.0, "chunk_exact"))
    return pairs


def _groups(items: list[tuple[str, str]]) -> list[list[str]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for key, value in items:
        buckets[key].append(value)
    return [values for values in buckets.values() if len(values) > 1]
