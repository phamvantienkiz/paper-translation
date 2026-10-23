from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ocr_block import OcrBlockModel
from app.repositories.ocr_block_repository import OcrBlockRepository
from app.repositories.page_repository import PageRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.canvas import (
    CanvasBlockResponse,
    CanvasDataResponse,
    CanvasPageResponse,
)


class LayoutMapper:
    """
    Dịch vụ ánh xạ và chuyển đổi dữ liệu trang & khối bố cục
    sang định dạng chuẩn phục vụ HTML5 Canvas 3 Lớp (3-Layer Canvas).
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_repo = SessionRepository(db)
        self.page_repo = PageRepository(db)
        self.block_repo = OcrBlockRepository(db)

    async def get_canvas_data(self, session_id: str) -> CanvasDataResponse | None:
        """
        Lấy toàn bộ dữ liệu cấu trúc trang, ảnh Layer 0 và BBoxes chuẩn hóa
        cho phiên bài báo.
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            return None

        pages = await self.page_repo.get_by_session_id(session_id)
        blocks = await self.block_repo.get_by_session_id(session_id)

        # Gom nhóm blocks theo page_id
        blocks_by_page: dict[str, list[OcrBlockModel]] = {}
        for b in blocks:
            blocks_by_page.setdefault(b.page_id, []).append(b)

        page_responses: list[CanvasPageResponse] = []
        for p in pages:
            page_blocks = blocks_by_page.get(p.id, [])
            block_responses: list[CanvasBlockResponse] = []

            for b in page_blocks:
                figure_url = None
                if b.figure_image_path:
                    fig_fname = Path(b.figure_image_path).name
                    figure_url = f"/api/v1/assets/figures/{session_id}/{fig_fname}"

                block_responses.append(
                    CanvasBlockResponse(
                        id=b.id,
                        block_code=b.block_code,
                        reading_order=b.reading_order,
                        label=b.label,
                        bbox_norm=[b.bbox_x0, b.bbox_y0, b.bbox_x1, b.bbox_y1],
                        is_translatable=b.is_translatable,
                        original_text=b.original_text,
                        translated_text=b.translated_text,
                        figure_image_url=figure_url,
                        is_user_edited=b.is_user_edited,
                    )
                )

            page_image_url = f"/api/v1/assets/pages/{session_id}/page_{p.page_number}.png"

            page_responses.append(
                CanvasPageResponse(
                    page_number=p.page_number,
                    width_pt=p.width_pt,
                    height_pt=p.height_pt,
                    page_image_url=page_image_url,
                    blocks=block_responses,
                )
            )

        return CanvasDataResponse(
            session_id=session.id,
            title=session.title,
            total_pages=len(page_responses),
            pages=page_responses,
        )
