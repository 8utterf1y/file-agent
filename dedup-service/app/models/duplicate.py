from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DuplicateCluster(Base):
    __tablename__ = "duplicate_cluster"

    cluster_id: Mapped[str] = mapped_column(String, primary_key=True)
    duplicate_type: Mapped[str] = mapped_column(String(32))
    canonical_chunk_id: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(32))
    suggested_action: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DuplicateMember(Base):
    __tablename__ = "duplicate_member"

    cluster_id: Mapped[str] = mapped_column(
        ForeignKey("duplicate_cluster.cluster_id", ondelete="CASCADE"),
        primary_key=True,
    )
    chunk_id: Mapped[str] = mapped_column(ForeignKey("chunk.chunk_id", ondelete="CASCADE"), primary_key=True)
    similarity_score: Mapped[float] = mapped_column(Float)
    match_type: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
