from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.repositories.ocr_block_repository import OcrBlockRepository
from app.schemas.ocr_block import BlockResponse, BlockUpdateRequest
from app.schemas.session import ApiResponse
from app.services.layout_mapper import LayoutMapper

router = APIRouter(tags=["canvas"])


@router.get("/sessions/{session_id}/canvas-data", response_model=ApiResponse)
async def get_session_canvas_data(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy toàn bộ dữ liệu cấu trúc trang, ảnh nền Layer 0 và BBoxes chuẩn hóa
    phục vụ hiển thị trên 3-Layer HTML5 Canvas.
    """
    mapper = LayoutMapper(db)
    canvas_data = await mapper.get_canvas_data(session_id)
    if not canvas_data:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên bài báo.")

    return ApiResponse(
        success=True,
        data=canvas_data.model_dump(),
        message="Lấy dữ liệu Canvas thành công",
    )


@router.patch("/blocks/{block_id}", response_model=ApiResponse)
async def update_block_translation(
    block_id: str,
    req: BlockUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Chỉnh sửa nội dung dịch của một khối bố cục trực tiếp từ Canvas (Inline Edit).
    Đánh dấu cờ is_user_edited = True.
    """
    block_repo = OcrBlockRepository(db)
    updated = await block_repo.update_translation(
        block_id=block_id,
        translated_text=req.translated_text,
        is_user_edited=True,
    )
    if not updated:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy khối bố cục cần chỉnh sửa."
        )

    return ApiResponse(
        success=True,
        data=BlockResponse.model_validate(updated).model_dump(),
        message="Cập nhật khối bản dịch thành công",
    )
