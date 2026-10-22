import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PaperPageModel(Base):
    __tablename__ = "paper_pages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paper_sessions.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    width_pt: Mapped[float] = mapped_column(Float, nullable=False)
    height_pt: Mapped[float] = mapped_column(Float, nullable=False)
    ocr_rotation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ocr_skew: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    page_image_path: Mapped[str] = mapped_column(String(500), nullable=False)

    # Relationships
    session: Mapped["PaperSessionModel"] = relationship(  # noqa: F821
        "PaperSessionModel", back_populates="pages"
    )
    blocks: Mapped[list["OcrBlockModel"]] = relationship(  # noqa: F821
        "OcrBlockModel",
        back_populates="page",
        cascade="all, delete-orphan",
        order_by="OcrBlockModel.reading_order",
    )

    __table_args__ = (
        Index("idx_pages_session_num", "session_id", "page_number"),
    )
