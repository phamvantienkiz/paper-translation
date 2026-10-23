import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class PaperSessionModel(Base):
    __tablename__ = "paper_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # PDF, DOCX, ARXIV
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    arxiv_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    authors: Mapped[str | None] = mapped_column(Text, nullable=True, default="[]")
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    pages: Mapped[list["PaperPageModel"]] = relationship(  # noqa: F821
        "PaperPageModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PaperPageModel.page_number",
    )
    blocks: Mapped[list["OcrBlockModel"]] = relationship(  # noqa: F821
        "OcrBlockModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="OcrBlockModel.reading_order",
    )
    segments: Mapped[list["PaperSegmentModel"]] = relationship(  # noqa: F821
        "PaperSegmentModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PaperSegmentModel.order_index",
    )
    math_tokens: Mapped[list["MathTokenModel"]] = relationship(  # noqa: F821
        "MathTokenModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )
