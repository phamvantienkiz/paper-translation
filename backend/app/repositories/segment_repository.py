from datetime import datetime, timezone
from typing import List, Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.segment import PaperSegmentModel
from app.models.math_token import MathTokenModel


class SegmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_create_segments(self, segments_data: List[dict]) -> List[PaperSegmentModel]:
        models = [PaperSegmentModel(**data) for data in segments_data]
        self.db.add_all(models)
        await self.db.commit()
        return models

    async def bulk_create_math_tokens(self, tokens_data: List[dict]) -> List[MathTokenModel]:
        models = [MathTokenModel(**data) for data in tokens_data]
        self.db.add_all(models)
        await self.db.commit()
        return models

    async def get_by_session_id(self, session_id: str) -> Sequence[PaperSegmentModel]:
        stmt = (
            select(PaperSegmentModel)
            .where(PaperSegmentModel.session_id == session_id)
            .order_by(PaperSegmentModel.order_index.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, segment_id: str) -> Optional[PaperSegmentModel]:
        stmt = select(PaperSegmentModel).where(PaperSegmentModel.id == segment_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_translation(
        self, segment_id: str, translated_content: str, is_user_edited: bool = False
    ) -> Optional[PaperSegmentModel]:
        segment = await self.get_by_id(segment_id)
        if segment:
            segment.translated_content = translated_content
            segment.status = "TRANSLATED"
            if is_user_edited:
                segment.is_user_edited = True
                segment.last_edited_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(segment)
        return segment

    async def get_math_tokens(self, session_id: str) -> Sequence[MathTokenModel]:
        stmt = select(MathTokenModel).where(MathTokenModel.session_id == session_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()
