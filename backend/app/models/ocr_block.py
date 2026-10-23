import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class OcrBlockModel(Base):
    __tablename__ = "ocr_blocks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paper_sessions.id", ondelete="CASCADE"), nullable=False
    )
    page_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paper_pages.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    block_code: Mapped[str] = mapped_column(String(20), nullable=False)
    reading_order: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(40), nullable=False)

    bbox_x0: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y0: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x1: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y1: Mapped[float] = mapped_column(Float, nullable=False)

    is_translatable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    figure_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_user_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    session: Mapped["PaperSessionModel"] = relationship(  # noqa: F821
        "PaperSessionModel", back_populates="blocks"
    )
    page: Mapped["PaperPageModel"] = relationship(  # noqa: F821
        "PaperPageModel", back_populates="blocks"
    )

    __table_args__ = (
        Index("idx_blocks_session_reading", "session_id", "reading_order"),
        Index("idx_blocks_page", "page_id", "reading_order"),
    )
