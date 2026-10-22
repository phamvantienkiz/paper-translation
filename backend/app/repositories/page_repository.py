
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.page import PaperPageModel


class PageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, page_data: dict) -> PaperPageModel:
        page = PaperPageModel(**page_data)
        self.db.add(page)
        await self.db.commit()
        await self.db.refresh(page)
        return page

    async def bulk_create(self, pages_data: list[dict]) -> list[PaperPageModel]:
        pages = [PaperPageModel(**item) for item in pages_data]
        self.db.add_all(pages)
        await self.db.commit()
        return pages

    async def get_by_session_id(self, session_id: str) -> list[PaperPageModel]:
        stmt = (
            select(PaperPageModel)
            .where(PaperPageModel.session_id == session_id)
            .order_by(PaperPageModel.page_number.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_by_session_and_number(
        self, session_id: str, page_number: int
    ) -> PaperPageModel | None:
        stmt = select(PaperPageModel).where(
            PaperPageModel.session_id == session_id,
            PaperPageModel.page_number == page_number,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
