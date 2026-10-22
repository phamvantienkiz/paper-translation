import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class PaperSegmentModel(Base):
    __tablename__ = "paper_segments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paper_sessions.id", ondelete="CASCADE"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    segment_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PARAGRAPH"
    )  # TITLE, HEADING, PARAGRAPH, TABLE, FIGURE
    
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    translated_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_user_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)

    # Relationships
    session: Mapped["PaperSessionModel"] = relationship(  # noqa: F821
        "PaperSessionModel", back_populates="segments"
    )

    __table_args__ = (
        Index("idx_segments_session_order", "session_id", "order_index"),
    )
