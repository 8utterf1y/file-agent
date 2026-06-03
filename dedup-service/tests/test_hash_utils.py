from app.fingerprints.hash_utils import normalize_text, sha256_text


def test_same_text_hashes_equal_after_normalization() -> None:
    left = "Hello   world\r\n\r\n\r\nPort  8080"
    right = "Hello world\n\nPort 8080"
    assert normalize_text(left) == normalize_text(right)
    assert sha256_text(left) == sha256_text(right)


def test_different_text_hashes_differ() -> None:
    assert sha256_text("Port 8080") != sha256_text("Port 9090")
