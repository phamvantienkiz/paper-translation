from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.repositories.segment_repository import SegmentRepository
from app.repositories.session_repository import SessionRepository
from app.services.export.pdf_exporter import PDFExporter

router = APIRouter(tags=["assets"])


@router.get("/assets/pages/{session_id}/{filename}")
async def get_page_image(session_id: str, filename: str):
    """Phục vụ ảnh nền toàn trang gốc (Layer 0) 200 DPI cho HTML Canvas."""
    file_path = settings.pages_dir / session_id / filename
    if not file_path.is_file():
        raise HTTPException(
            status_code=404, detail="Không tìm thấy tệp ảnh trang được yêu cầu."
        )
    return FileResponse(path=str(file_path), media_type="image/png")


@router.get("/assets/figures/{session_id}/{filename}")
async def get_figure_image(session_id: str, filename: str):
    """Phục vụ ảnh sơ đồ/đồ thị được crop riêng theo Bounding Box."""
    file_path = settings.figures_dir / session_id / filename
    if not file_path.is_file():
        raise HTTPException(
            status_code=404, detail="Không tìm thấy tệp ảnh hình vẽ được yêu cầu."
        )
    return FileResponse(path=str(file_path), media_type="image/png")


@router.get("/export/{session_id}/pdf")
async def export_session_pdf(session_id: str, db: AsyncSession = Depends(get_db)):
    """Tải về tệp PDF bản dịch bài báo hoàn chỉnh từ backend."""
    session_repo = SessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên bài báo.")

    from app.services.layout_mapper import LayoutMapper
    mapper = LayoutMapper(db)
    canvas_data = await mapper.get_canvas_data(session_id)

    segment_repo = SegmentRepository(db)
    segments = await segment_repo.get_by_session_id(session_id)
    math_tokens = await segment_repo.get_math_tokens(session_id)

    exporter = PDFExporter()
    pdf_path = exporter.export_pdf(
        session=session,
        canvas_data=canvas_data,
        segments=list(segments),
        math_tokens=list(math_tokens),
    )

    filename = f"{Path(session.file_name).stem}_translated.pdf"
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=filename,
    )
