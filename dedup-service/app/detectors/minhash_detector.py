from __future__ import annotations

from datasketch import MinHash, MinHashLSH

from app.fingerprints.minhash_utils import build_minhash


class MinHashDetector:
    def __init__(self, threshold: float = 0.82, num_perm: int = 128) -> None:
        self.threshold = threshold
        self.num_perm = num_perm
        self.lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
        self._minhashes: dict[str, MinHash] = {}

    def add(self, chunk_id: str, text: str) -> None:
        minhash = build_minhash(text, num_perm=self.num_perm)
        self._minhashes[chunk_id] = minhash
        self.lsh.insert(chunk_id, minhash)

    def query(self, text: str) -> list[str]:
        return list(self.lsh.query(build_minhash(text, num_perm=self.num_perm)))

    def jaccard_estimate(self, chunk_id_a: str, chunk_id_b: str) -> float | None:
        a = self._minhashes.get(chunk_id_a)
        b = self._minhashes.get(chunk_id_b)
        if a is None or b is None:
            return None
        return float(a.jaccard(b))
