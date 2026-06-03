from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.chunking.markdown_chunker import chunk_markdown
from app.fingerprints.hash_utils import normalize_text, sha256_file, sha256_text, stable_id
from app.models.chunk import Chunk
from app.models.document import Document
from app.parsers.doc_parser import parse_document
from app.sources.local_scanner import FileItem


@dataclass(frozen=True)
class ProcessResult:
    doc_id: str
    processed: bool
    skipped: bool


def process_file(db: Session, item: FileItem) -> ProcessResult:
    file_hash = sha256_file(item.path)
    doc_id = stable_id("doc", item.path)
    existing = db.get(Document, doc_id)
    if existing and existing.file_hash == file_hash:
        return ProcessResult(doc_id=doc_id, processed=False, skipped=True)

    parsed = parse_document(item.path)
    normalized_text_hash = sha256_text(parsed.markdown)
    document = existing or Document(doc_id=doc_id)
    document.source_uri = f"file://{item.path}"
    document.path = item.path
    document.filename = item.filename
    document.file_ext = item.file_ext
    document.file_size = item.file_size
    document.mtime = item.mtime
    document.file_hash = file_hash
    document.normalized_text_hash = normalized_text_hash
    document.title = parsed.title
    document.status = "active"
    db.add(document)
    db.flush()

    db.execute(delete(Chunk).where(Chunk.doc_id == doc_id))
    for chunk in chunk_markdown(doc_id, normalize_text(parsed.markdown)):
        db.add(
            Chunk(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                section_path=chunk.section_path,
                content_type=chunk.content_type,
                text=chunk.text,
                text_hash=chunk.text_hash,
                token_count=chunk.token_count,
            )
        )
    db.commit()
    return ProcessResult(doc_id=doc_id, processed=True, skipped=False)
