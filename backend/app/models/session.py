import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PaperSessionModel(Base):
    __tablename__ = "paper_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # PDF, DOCX, ARXIV
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    
    arxiv_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authors: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="[]")
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    segments: Mapped[List["PaperSegmentModel"]] = relationship(  # noqa: F821
        "PaperSegmentModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PaperSegmentModel.order_index",
    )
    math_tokens: Mapped[List["MathTokenModel"]] = relationship(  # noqa: F821
        "MathTokenModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )
