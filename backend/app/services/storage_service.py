import shutil
from pathlib import Path

from app.core.config import settings
from app.core.logging import logger
from app.models.session import PaperSessionModel


class StorageService:
    """
    Dịch vụ quản lý tệp tin, dọn dẹp rác, và xóa phiên tài liệu.
    Bảo đảm 100% tệp lưu trữ và tệp tạm nằm cô lập trong backend/storage/.
    """

    @staticmethod
    def cleanup_session_files(session: PaperSessionModel | None, session_id: str) -> None:
        """
        Xóa toàn bộ các tệp vật lý gắn liền với một phiên bài báo:
        - raw upload: backend/storage/raw/{session_id}/
        - raw pdf copy: backend/storage/raw_pdfs/{session_id}.pdf
        - page images: backend/storage/pages/{session_id}/
        - cropped figures: backend/storage/figures/{session_id}/
        - exported pdfs: backend/storage/exports/{session_id}/
        """
        # 1. Xóa thư mục trang (pages)
        pages_folder = settings.pages_dir / session_id
        if pages_folder.exists() and pages_folder.is_dir():
            shutil.rmtree(pages_folder, ignore_errors=True)
            logger.info(f"Đã dọn dẹp thư mục ảnh trang: {pages_folder}")

        # 2. Xóa thư mục hình ảnh sơ đồ (figures)
        figures_folder = settings.figures_dir / session_id
        if figures_folder.exists() and figures_folder.is_dir():
            shutil.rmtree(figures_folder, ignore_errors=True)
            logger.info(f"Đã dọn dẹp thư mục sơ đồ: {figures_folder}")

        # 3. Xóa thư mục raw upload
        raw_session_folder = settings.STORAGE_DIR / "raw" / session_id
        if raw_session_folder.exists() and raw_session_folder.is_dir():
            shutil.rmtree(raw_session_folder, ignore_errors=True)

        # 4. Xóa tệp pdf raw nếu có
        raw_pdf_file = settings.raw_pdfs_dir / f"{session_id}.pdf"
        if raw_pdf_file.exists() and raw_pdf_file.is_file():
            try:
                raw_pdf_file.unlink()
            except OSError as err:
                logger.warning(f"Không thể xóa tệp {raw_pdf_file}: {err}")

        # 5. Xóa các tệp xuất bản dịch
        exports_session_folder = settings.exports_dir / session_id
        if exports_session_folder.exists() and exports_session_folder.is_dir():
            shutil.rmtree(exports_session_folder, ignore_errors=True)

        # 6. Xóa theo đường dẫn cụ thể ghi nhận trong session model
        if session:
            for path_str in [session.file_path, session.pdf_path]:
                if path_str:
                    p = Path(path_str)
                    if p.is_file() and p.exists():
                        try:
                            p.unlink()
                        except OSError:
                            pass

    @staticmethod
    def cleanup_all_temp_files() -> int:
        """
        Dọn dẹp thư mục tạm backend/storage/temp/.
        Trả về số lượng tệp đã xóa.
        """
        temp_dir = settings.temp_dir
        deleted_count = 0
        if not temp_dir.exists():
            return 0

        for item in temp_dir.iterdir():
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()
                    deleted_count += 1
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    deleted_count += 1
            except Exception as exc:
                logger.warning(f"Lỗi khi xóa tệp tạm {item}: {exc}")

        logger.info(f"Đã dọn dẹp xong {deleted_count} mục trong thư mục tạm {temp_dir}.")
        return deleted_count
