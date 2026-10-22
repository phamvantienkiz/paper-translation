import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class MathTokenModel(Base):
    __tablename__ = "math_tokens"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paper_sessions.id", ondelete="CASCADE"), nullable=False
    )
    token_placeholder: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_latex: Mapped[str] = mapped_column(Text, nullable=False)
    is_display_math: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    session: Mapped["PaperSessionModel"] = relationship(  # noqa: F821
        "PaperSessionModel", back_populates="math_tokens"
    )

    __table_args__ = (
        Index("idx_session_token", "session_id", "token_placeholder"),
    )
