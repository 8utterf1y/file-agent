from __future__ import annotations

from dataclasses import dataclass
import re

from app.fingerprints.hash_utils import normalize_text, sha256_text, stable_id


MIN_CHUNK_CHARS = 80
MAX_CHUNK_CHARS = 1800


@dataclass(frozen=True)
class ChunkItem:
    chunk_id: str
    doc_id: str
    section_path: str | None
    content_type: str
    text: str
    text_hash: str
    token_count: int


def chunk_markdown(doc_id: str, markdown: str) -> list[ChunkItem]:
    chunks: list[ChunkItem] = []
    sections: list[str] = []
    buffer: list[str] = []
    in_code = False
    code_buffer: list[str] = []

    def section_path() -> str | None:
        return " > ".join(sections) if sections else None

    def flush_paragraphs() -> None:
        nonlocal buffer
        text = "\n".join(buffer).strip()
        buffer = []
        if not text:
            return
        for paragraph in re.split(r"\n\s*\n", text):
            _append_chunk(chunks, doc_id, section_path(), "paragraph", paragraph)

    def flush_code() -> None:
        nonlocal code_buffer
        code = "\n".join(code_buffer).strip()
        code_buffer = []
        _append_chunk(chunks, doc_id, section_path(), "code", code)

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                in_code = False
                flush_code()
            else:
                flush_paragraphs()
                in_code = True
            continue
        if in_code:
            code_buffer.append(line)
            continue

        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            flush_paragraphs()
            level = len(heading.group(1))
            title = heading.group(2).strip()
            sections = sections[: level - 1]
            sections.append(title)
            continue
        buffer.append(line)

    if in_code:
        flush_code()
    flush_paragraphs()
    return chunks


def _append_chunk(
    chunks: list[ChunkItem],
    doc_id: str,
    section_path: str | None,
    content_type: str,
    text: str,
) -> None:
    normalized = normalize_text(text)
    if len(normalized) < MIN_CHUNK_CHARS:
        return
    parts = _split_long_text(normalized)
    for part in parts:
        raw_id = f"{doc_id}|{section_path or ''}|{content_type}|{len(chunks)}|{part}"
        chunks.append(
            ChunkItem(
                chunk_id=stable_id("chk", raw_id),
                doc_id=doc_id,
                section_path=section_path,
                content_type=content_type,
                text=part,
                text_hash=sha256_text(part),
                token_count=len(part.split()),
            )
        )


def _split_long_text(text: str) -> list[str]:
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + MAX_CHUNK_CHARS, len(text))
        split_at = text.rfind("\n", start, end)
        if split_at <= start + 200:
            split_at = text.rfind(" ", start, end)
        if split_at <= start:
            split_at = end
        parts.append(text[start:split_at].strip())
        start = split_at
    return [part for part in parts if part]
