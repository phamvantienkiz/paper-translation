from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.page import PaperPageModel
from app.models.session import PaperSessionModel


class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, session_data: dict) -> PaperSessionModel:
        session = PaperSessionModel(**session_data)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_by_id(
        self,
        session_id: str,
        include_segments: bool = False,
        include_canvas_data: bool = False,
    ) -> PaperSessionModel | None:
        stmt = select(PaperSessionModel).where(PaperSessionModel.id == session_id)
        if include_segments:
            stmt = stmt.options(
                selectinload(PaperSessionModel.segments),
                selectinload(PaperSessionModel.math_tokens),
            )
        if include_canvas_data:
            stmt = stmt.options(
                selectinload(PaperSessionModel.pages).selectinload(PaperPageModel.blocks),
            )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self, session_id: str, status: str, progress_percent: int | None = None
    ) -> PaperSessionModel | None:
        session = await self.get_by_id(session_id)
        if session:
            session.status = status
            if progress_percent is not None:
                session.progress_percent = progress_percent
            await self.db.commit()
            await self.db.refresh(session)
        return session

    async def update_metadata(
        self, session_id: str, title: str | None, authors: str | None, abstract: str | None
    ) -> PaperSessionModel | None:
        session = await self.get_by_id(session_id)
        if session:
            if title:
                session.title = title
            if authors:
                session.authors = authors
            if abstract:
                session.abstract = abstract
            await self.db.commit()
            await self.db.refresh(session)
        return session

    async def list_recent(self, limit: int = 20) -> Sequence[PaperSessionModel]:
        stmt = (
            select(PaperSessionModel)
            .order_by(PaperSessionModel.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
