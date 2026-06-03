from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    __tablename__ = "document"

    doc_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_uri: Mapped[str] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(512))
    file_ext: Mapped[str] = mapped_column(String(32))
    file_size: Mapped[int] = mapped_column(Integer)
    mtime: Mapped[datetime] = mapped_column(DateTime)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    normalized_text_hash: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
