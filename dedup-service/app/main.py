from __future__ import annotations

from fastapi import Depends, FastAPI, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.duplicate import DuplicateCluster, DuplicateMember
from app.reports.markdown_report import render_markdown_report
from app.schemas import ChunkOut, ClusterMemberOut, ClusterOut, DocumentOut, ScanRequest, ScanResponse
from app.services.scan_service import scan_and_analyze


app = FastAPI(title="dedup-service", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/scan", response_model=ScanResponse)
def scan(request: ScanRequest, db: Session = Depends(get_db)) -> ScanResponse:
    return scan_and_analyze(db, request.source_path)


@app.get("/documents", response_model=list[DocumentOut])
def documents(db: Session = Depends(get_db)) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.created_at.desc()).limit(500)))


@app.get("/chunks", response_model=list[ChunkOut])
def chunks(doc_id: str | None = Query(default=None), db: Session = Depends(get_db)) -> list[Chunk]:
    statement = select(Chunk).order_by(Chunk.created_at.desc()).limit(500)
    if doc_id:
        statement = select(Chunk).where(Chunk.doc_id == doc_id).order_by(Chunk.created_at.desc()).limit(500)
    return list(db.scalars(statement))


@app.get("/clusters", response_model=list[ClusterOut])
def clusters(db: Session = Depends(get_db)) -> list[ClusterOut]:
    cluster_rows = list(db.scalars(select(DuplicateCluster).order_by(DuplicateCluster.created_at.desc())))
    member_rows = list(db.scalars(select(DuplicateMember)))
    chunks_by_id = {chunk.chunk_id: chunk for chunk in db.scalars(select(Chunk))}
    documents_by_id = {doc.doc_id: doc for doc in db.scalars(select(Document))}
    members_by_cluster: dict[str, list[DuplicateMember]] = {}
    for member in member_rows:
        members_by_cluster.setdefault(member.cluster_id, []).append(member)

    result: list[ClusterOut] = []
    for cluster in cluster_rows:
        members: list[ClusterMemberOut] = []
        for member in members_by_cluster.get(cluster.cluster_id, []):
            chunk = chunks_by_id.get(member.chunk_id)
            document = documents_by_id.get(chunk.doc_id) if chunk else None
            if not chunk or not document:
                continue
            members.append(
                ClusterMemberOut(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    filename=document.filename,
                    path=document.path,
                    section_path=chunk.section_path,
                    preview=chunk.text[:220],
                    similarity_score=member.similarity_score,
                    match_type=member.match_type,
                )
            )
        result.append(
            ClusterOut(
                cluster_id=cluster.cluster_id,
                duplicate_type=cluster.duplicate_type,
                canonical_chunk_id=cluster.canonical_chunk_id,
                confidence=cluster.confidence,
                risk_level=cluster.risk_level,
                suggested_action=cluster.suggested_action,
                summary=cluster.summary,
                members=members,
            )
        )
    return result


@app.get("/report.md")
def report(db: Session = Depends(get_db)) -> PlainTextResponse:
    return PlainTextResponse(render_markdown_report(db), media_type="text/markdown")
