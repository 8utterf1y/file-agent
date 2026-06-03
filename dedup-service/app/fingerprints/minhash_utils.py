from datasketch import MinHash

from app.fingerprints.hash_utils import normalize_text


def char_ngrams(text: str, n: int = 5) -> set[str]:
    normalized = normalize_text(text).lower()
    if len(normalized) <= n:
        return {normalized} if normalized else set()
    return {normalized[i : i + n] for i in range(len(normalized) - n + 1)}


def build_minhash(text: str, num_perm: int = 128) -> MinHash:
    minhash = MinHash(num_perm=num_perm)
    grams = char_ngrams(text)
    for gram in grams:
        minhash.update(gram.encode("utf-8"))
    if not grams:
        minhash.update(b"")
    return minhash
