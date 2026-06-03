from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.document import Document
from app.models.duplicate import DuplicateCluster, DuplicateMember


def render_markdown_report(db: Session) -> str:
    clusters = list(db.scalars(select(DuplicateCluster).order_by(DuplicateCluster.created_at.desc())))
    chunks = {chunk.chunk_id: chunk for chunk in db.scalars(select(Chunk))}
    documents = {doc.doc_id: doc for doc in db.scalars(select(Document))}
    members = list(db.scalars(select(DuplicateMember)))
    members_by_cluster: dict[str, list[DuplicateMember]] = {}
    for member in members:
        members_by_cluster.setdefault(member.cluster_id, []).append(member)

    lines = ["# Document Deduplication Report", ""]
    lines.append(f"Total clusters: {len(clusters)}")
    lines.append("")
    for cluster in clusters:
        lines.extend(
            [
                f"## Cluster {cluster.cluster_id}",
                "",
                f"- Type: {cluster.duplicate_type}",
                f"- Confidence: {cluster.confidence:.2f}",
                f"- Risk: {cluster.risk_level}",
                f"- Suggested action: {cluster.suggested_action}",
                f"- Canonical chunk: {cluster.canonical_chunk_id or 'N/A'}",
                f"- Summary: {cluster.summary}",
                "",
                "### Members",
            ]
        )
        for member in members_by_cluster.get(cluster.cluster_id, []):
            chunk = chunks.get(member.chunk_id)
            document = documents.get(chunk.doc_id) if chunk else None
            if not chunk or not document:
                continue
            preview = chunk.text[:160].replace("\n", " ")
            lines.append(
                f"- `{member.chunk_id}` `{member.match_type}` {member.similarity_score:.2f} "
                f"{document.filename} [{chunk.section_path or 'root'}] - {preview}"
            )
        lines.append("")
    return "\n".join(lines)
