from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger
from app.db.base import Base
from app.db.session import engine
from app.middlewares import register_middlewares


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure directories and database tables exist inside backend/storage
    logger.info(f"Khởi động dịch vụ {settings.PROJECT_NAME}...")
    
    # Cô lập toàn bộ thư mục tạm và lưu trữ trong workspace backend/storage/
    import os
    import tempfile
    
    # Thiết lập biến môi trường cô lập tuyệt đối bên trong workspace
    temp_dir_path = str(settings.temp_dir)
    os.environ["TMPDIR"] = temp_dir_path
    os.environ["TEMP"] = temp_dir_path
    os.environ["TMP"] = temp_dir_path
    tempfile.tempdir = temp_dir_path

    # Chuyển hướng toàn bộ cache HuggingFace vào trong workspace
    hf_cache_dir = str(settings.models_dir / "cache")
    os.environ["HF_HOME"] = hf_cache_dir
    os.environ["HUGGINGFACE_HUB_CACHE"] = hf_cache_dir

    # Thư mục chứa model Indra OCR cục bộ trong workspace
    os.environ["INDRA_OCR_MODEL_DIR"] = str(settings.indra_models_dir)

    (settings.STORAGE_DIR / "raw").mkdir(parents=True, exist_ok=True)
    (settings.STORAGE_DIR / "assets").mkdir(parents=True, exist_ok=True)
    (settings.STORAGE_DIR / "exports").mkdir(parents=True, exist_ok=True)
    (settings.STORAGE_DIR / "pages").mkdir(parents=True, exist_ok=True)
    (settings.STORAGE_DIR / "figures").mkdir(parents=True, exist_ok=True)
    (settings.STORAGE_DIR / "raw_pdfs").mkdir(parents=True, exist_ok=True)
    (settings.STORAGE_DIR / "temp").mkdir(parents=True, exist_ok=True)
    (settings.STORAGE_DIR / "models").mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Đã khởi tạo xong bảng cơ sở dữ liệu SQLite.")

    yield

    # Shutdown
    logger.info("Đang đóng các kết nối cơ sở dữ liệu và thu hồi tài nguyên...")
    from app.services.translation.llama_service import LlamaCppService
    LlamaCppService.reset()
    await engine.dispose()
    logger.info("Hệ thống đã dừng an toàn.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description="Backend API cho Paper Translation — Dịch thuật bài báo khoa học CNTT & AI",
        lifespan=lifespan,
    )

    # 1. Đăng ký Middleware theo thứ tự chuẩn
    register_middlewares(app)

    # 2. Đăng ký Router chính (ưu tiên khớp các endpoints cụ thể trước như /api/v1/assets/pages, /api/v1/assets/figures)
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # 3. Phục vụ tệp tĩnh (hình ảnh crop/trích xuất legacy)
    assets_dir = settings.STORAGE_DIR / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/api/v1/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    return app


app = create_app()
