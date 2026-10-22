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
    # Startup: Ensure directories and database tables exist
    logger.info(f"Khởi động dịch vụ {settings.PROJECT_NAME}...")
    (settings.STORAGE_DIR / "raw").mkdir(parents=True, exist_ok=True)
    (settings.STORAGE_DIR / "assets").mkdir(parents=True, exist_ok=True)
    (settings.STORAGE_DIR / "exports").mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Đã khởi tạo xong bảng cơ sở dữ liệu SQLite.")

    yield

    # Shutdown
    logger.info("Đang đóng các kết nối cơ sở dữ liệu...")
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
