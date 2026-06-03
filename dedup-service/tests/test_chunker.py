from app.chunking.markdown_chunker import chunk_markdown


LONG_TEXT = "This paragraph is intentionally long enough to pass the chunk minimum length filter. " * 3


def test_markdown_heading_forms_section_path() -> None:
    chunks = chunk_markdown("doc_1", f"# Guide\n\n## Install\n\n{LONG_TEXT}")
    assert chunks
    assert chunks[0].section_path == "Guide > Install"


def test_code_block_content_type_is_code() -> None:
    code = "print('hello world')\n" * 8
    chunks = chunk_markdown("doc_1", f"# Guide\n\n```\n{code}\n```")
    assert chunks
    assert chunks[0].content_type == "code"


def test_short_text_is_filtered() -> None:
    assert chunk_markdown("doc_1", "# Tiny\n\nshort") == []
