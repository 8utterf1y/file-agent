from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ScanRequest(BaseModel):
    source_path: str


class FailedFile(BaseModel):
    path: str
    error: str


class ScanResponse(BaseModel):
    source_path: str
    total_files: int
    processed: int
    skipped: int
    failed: list[FailedFile]
    cluster_count: int


class DocumentOut(BaseModel):
    doc_id: str
    source_uri: str
    path: str
    filename: str
    file_ext: str
    file_size: int
    mtime: datetime
    file_hash: str
    normalized_text_hash: str
    title: str | None
    status: str

    model_config = {"from_attributes": True}


class ChunkOut(BaseModel):
    chunk_id: str
    doc_id: str
    section_path: str | None
    content_type: str
    text: str
    text_hash: str
    token_count: int

    model_config = {"from_attributes": True}


class ClusterMemberOut(BaseModel):
    chunk_id: str
    doc_id: str
    filename: str
    path: str
    section_path: str | None
    preview: str
    similarity_score: float
    match_type: str


class ClusterOut(BaseModel):
    cluster_id: str
    duplicate_type: str
    canonical_chunk_id: str | None
    confidence: float
    risk_level: str
    suggested_action: str
    summary: str
    members: list[ClusterMemberOut]
