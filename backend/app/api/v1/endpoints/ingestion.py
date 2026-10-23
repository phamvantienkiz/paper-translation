from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.repositories.session_repository import SessionRepository
from app.schemas.session import ApiResponse, ArxivIngestRequest, SessionCreateResponse
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
ingestion_service = IngestionService()


@router.post("/upload", response_model=ApiResponse)
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Tiếp nhận tệp bài báo tải lên (hỗ trợ định dạng PDF hoặc DOCX).
    Bảo toàn cấu trúc và bắt đầu quy trình bóc tách trong nền.
    """
    try:
        session_id, file_path, file_size, source_type = await ingestion_service.save_uploaded_file(file)
        
        session_repo = SessionRepository(db)
        await session_repo.create({
            "id": session_id,
            "source_type": source_type,
            "file_name": file.filename or "unknown",
            "file_size_bytes": file_size,
            "file_path": str(file_path),
            "status": "PENDING",
            "progress_percent": 0,
        })

        # Kích hoạt tác vụ bóc tách chạy nền
        background_tasks.add_task(
            ingestion_service.process_paper_background,
            session_id,
            file_path,
            source_type,
        )

        return ApiResponse(
            success=True,
            data=SessionCreateResponse(
                session_id=session_id,
                file_name=file.filename or "unknown",
                source_type=source_type,
                status="PENDING",
                message="Tệp đã được tải lên thành công và bắt đầu bóc tách trong nền.",
            ).model_dump(),
            message="Upload thành công",
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý tệp: {str(exc)}")


@router.post("/arxiv", response_model=ApiResponse)
async def ingest_arxiv_paper(
    req: ArxivIngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Tải bài báo trực tiếp từ arXiv thông qua link hoặc mã arXiv ID.
    """
    try:
        session_id, file_path, file_size, source_type = await ingestion_service.ingest_arxiv(req.arxiv_input)

        session_repo = SessionRepository(db)
        await session_repo.create({
            "id": session_id,
            "source_type": source_type,
            "file_name": file_path.name,
            "file_size_bytes": file_size,
            "file_path": str(file_path),
            "arxiv_id": req.arxiv_input,
            "status": "PENDING",
            "progress_percent": 0,
        })

        background_tasks.add_task(
            ingestion_service.process_paper_background,
            session_id,
            file_path,
            source_type,
        )

        return ApiResponse(
            success=True,
            data=SessionCreateResponse(
                session_id=session_id,
                file_name=file_path.name,
                source_type=source_type,
                status="PENDING",
                message="Đã tải bài báo từ arXiv và bắt đầu phân tích bóc tách.",
            ).model_dump(),
            message="Thu thập arXiv thành công",
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi thu thập arXiv: {str(exc)}")
