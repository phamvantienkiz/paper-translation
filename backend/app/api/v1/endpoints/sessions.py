from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.math_token import MathTokenModel
from app.repositories.segment_repository import SegmentRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.segment import MathTokenResponse, SegmentResponse, SegmentUpdateRequest
from app.schemas.session import ApiResponse, SessionDetailResponse
from app.services.sse_broadcaster import broadcaster

router = APIRouter(tags=["sessions"])


@router.get("/sessions", response_model=ApiResponse)
async def list_recent_sessions(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách các phiên bài báo gần đây."""
    session_repo = SessionRepository(db)
    sessions = await session_repo.list_recent()
    data = [SessionDetailResponse.model_validate(s).model_dump() for s in sessions]
    return ApiResponse(success=True, data=data)


@router.get("/sessions/{session_id}", response_model=ApiResponse)
async def get_session_detail(session_id: str, db: AsyncSession = Depends(get_db)):
    """Lấy thông tin chi tiết và trạng thái của phiên bài báo."""
    session_repo = SessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên bài báo.")
    return ApiResponse(success=True, data=SessionDetailResponse.model_validate(session).model_dump())


@router.get("/sessions/{session_id}/segments", response_model=ApiResponse)
async def get_session_segments(session_id: str, db: AsyncSession = Depends(get_db)):
    """Lấy danh sách toàn bộ các phân đoạn song ngữ của bài báo phục vụ Dual-Pane UI."""
    segment_repo = SegmentRepository(db)
    segments = await segment_repo.get_by_session_id(session_id)
    data = [SegmentResponse.model_validate(s).model_dump() for s in segments]
    return ApiResponse(success=True, data=data)


@router.get("/sessions/{session_id}/tokens", response_model=ApiResponse)
async def get_session_math_tokens(session_id: str, db: AsyncSession = Depends(get_db)):
    """Lấy danh sách các math token đã được bóc tách của bài báo."""
    stmt = (
        select(MathTokenModel)
        .where(MathTokenModel.session_id == session_id)
        .order_by(MathTokenModel.token_placeholder)
    )
    result = await db.execute(stmt)
    tokens = result.scalars().all()
    data = [MathTokenResponse.model_validate(t).model_dump() for t in tokens]
    return ApiResponse(success=True, data=data)


@router.get("/sessions/{session_id}/progress")
async def stream_session_progress(session_id: str):
    """Kênh truyền Server-Sent Events (SSE) theo dõi tiến độ xử lý thời gian thực."""
    return StreamingResponse(
        broadcaster.subscribe(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.patch("/segments/{segment_id}", response_model=ApiResponse)
async def update_segment_content(
    segment_id: str,
    req: SegmentUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Chỉnh sửa nội dung phân đoạn bản dịch (Inline Edit)."""
    segment_repo = SegmentRepository(db)
    segment = await segment_repo.update_translation(
        segment_id=segment_id,
        translated_content=req.translated_content,
        is_user_edited=True,
    )
    if not segment:
        raise HTTPException(status_code=404, detail="Không tìm thấy phân đoạn cần chỉnh sửa.")
    return ApiResponse(
        success=True,
        data=SegmentResponse.model_validate(segment).model_dump(),
        message="Cập nhật phân đoạn thành công",
    )


@router.post("/sessions/{session_id}/translate", response_model=ApiResponse)
async def start_session_translation(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Kích hoạt tiến trình dịch thuật toàn bộ phân đoạn bài báo trong nền."""
    session_repo = SessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên bài báo.")

    from app.services.translation.translation_service import TranslationService
    translation_service = TranslationService()
    background_tasks.add_task(translation_service.translate_session, session_id)

    return ApiResponse(
        success=True,
        message="Đã kích hoạt tiến trình dịch thuật bài báo trong nền.",
    )


@router.get("/sessions/{session_id}/export/pdf")
async def export_translated_pdf(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Xuất bản dịch bài báo ra tệp PDF tải về, bảo toàn công thức toán học, bảng biểu và hình ảnh."""
    session_repo = SessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên bài báo.")

    segment_repo = SegmentRepository(db)
    segments = await segment_repo.get_by_session_id(session_id)
    math_tokens = await segment_repo.get_math_tokens(session_id)

    from app.services.export.pdf_exporter import PDFExporter
    exporter = PDFExporter()
    pdf_path = exporter.export_pdf(session, list(segments), list(math_tokens))

    filename = f"{Path(session.file_name).stem}_translated.pdf"
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=filename,
    )
