from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ocr_block import OcrBlockModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class OcrBlockRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, block_data: dict) -> OcrBlockModel:
        block = OcrBlockModel(**block_data)
        self.db.add(block)
        await self.db.commit()
        await self.db.refresh(block)
        return block

    async def bulk_create(self, blocks_data: list[dict]) -> list[OcrBlockModel]:
        blocks = [OcrBlockModel(**item) for item in blocks_data]
        self.db.add_all(blocks)
        await self.db.commit()
        return blocks

    async def get_by_session_id(self, session_id: str) -> list[OcrBlockModel]:
        stmt = (
            select(OcrBlockModel)
            .where(OcrBlockModel.session_id == session_id)
            .order_by(OcrBlockModel.reading_order.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_by_page_id(self, page_id: str) -> list[OcrBlockModel]:
        stmt = (
            select(OcrBlockModel)
            .where(OcrBlockModel.page_id == page_id)
            .order_by(OcrBlockModel.reading_order.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_by_id(self, block_id: str) -> OcrBlockModel | None:
        stmt = select(OcrBlockModel).where(OcrBlockModel.id == block_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def update_translation(
        self,
        block_id: str,
        translated_text: str,
        is_user_edited: bool = False,
    ) -> OcrBlockModel | None:
        stmt = (
            update(OcrBlockModel)
            .where(OcrBlockModel.id == block_id)
            .values(
                translated_text=translated_text,
                is_user_edited=is_user_edited,
                last_edited_at=utc_now() if is_user_edited else None,
            )
            .returning(OcrBlockModel)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.scalar_one_or_none()

    async def bulk_update_translations(self, updates: list[dict]) -> None:
        """updates is a list of {'id': block_id, 'translated_text': text}"""
        for item in updates:
            await self.db.execute(
                update(OcrBlockModel)
                .where(OcrBlockModel.id == item["id"])
                .values(translated_text=item["translated_text"])
            )
        await self.db.commit()
