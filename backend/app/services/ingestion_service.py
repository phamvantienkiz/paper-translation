import asyncio
import re
import uuid
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.repositories.segment_repository import SegmentRepository
from app.repositories.session_repository import SessionRepository
from app.services.parser.docx_parser import DocxParser
from app.services.parser.math_isolator import LaTeXIsolator
from app.services.parser.pdf_parser import PdfParser
from app.services.sse_broadcaster import broadcaster


class IngestionService:
    def __init__(self):
        self.pdf_parser = PdfParser()
        self.docx_parser = DocxParser()

    @staticmethod
    def validate_file(filename: str, file_size: int, first_bytes: bytes) -> str:
        """Kiểm tra định dạng và tính hợp lệ của tệp."""
        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise ValueError(f"Dung lượng tệp ({file_size / (1024*1024):.1f}MB) vượt quá giới hạn 50MB.")

        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            if not first_bytes.startswith(b"%PDF-"):
                raise ValueError("Tệp PDF không hợp lệ (sai Magic Bytes header).")
            return "PDF"
        elif ext == ".docx":
            # DOCX is a zip archive starting with PK\x03\x04
            if not first_bytes.startswith(b"PK\x03\x04"):
                raise ValueError("Tệp DOCX không hợp lệ (sai cấu trúc zip header).")
            return "DOCX"
        else:
            raise ValueError("Định dạng tệp không được hỗ trợ. Hệ thống chỉ hỗ trợ tệp PDF hoặc DOCX.")

    async def save_uploaded_file(self, file: UploadFile) -> Tuple[str, Path, int, str]:
        """Lưu tệp tải lên vào thư mục storage/raw/{session_id}/."""
        session_id = str(uuid.uuid4())
        session_dir = settings.STORAGE_DIR / "raw" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        content = await file.read()
        file_size = len(content)
        first_bytes = content[:10]

        source_type = self.validate_file(file.filename or "unknown", file_size, first_bytes)
        ext = Path(file.filename or "").suffix.lower()
        target_path = session_dir / f"original{ext}"

        with open(target_path, "wb") as f:
            f.write(content)

        return session_id, target_path, file_size, source_type

    async def ingest_arxiv(self, arxiv_input: str) -> Tuple[str, Path, int, str]:
        """Tải bài báo trực tiếp từ arXiv."""
        # Trích xuất arXiv ID: e.g. 1706.03762 hoặc https://arxiv.org/abs/1706.03762
        match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", arxiv_input)
        if not match:
            raise ValueError("Không tìm thấy mã định dạng arXiv hợp lệ (vd: 1706.03762).")

        arxiv_id = match.group(1)
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        logger.info(f"Đang tải bài báo từ arXiv: {pdf_url}")

        session_id = str(uuid.uuid4())
        session_dir = settings.STORAGE_DIR / "raw" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        target_path = session_dir / "original.pdf"

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {"User-Agent": "PaperTranslationBot/1.0 (academic research tool)"}
            resp = await client.get(pdf_url, headers=headers)
            if resp.status_code != 200:
                raise ValueError(f"Không thể tải bài báo từ arXiv (Mã phản hồi HTTP {resp.status_code}).")

            content = resp.content
            file_size = len(content)
            if not content.startswith(b"%PDF-"):
                raise ValueError("Nội dung tải về từ arXiv không phải tệp PDF hợp lệ.")

            with open(target_path, "wb") as f:
                f.write(content)

        return session_id, target_path, file_size, "ARXIV"

    async def process_paper_background(self, session_id: str, file_path: Path, source_type: str):
        """Tiến trình chạy nền: Bóc tách cấu trúc, cô lập công thức toán LaTeX và lưu CSDL."""
        async with AsyncSessionLocal() as db:
            session_repo = SessionRepository(db)
            segment_repo = SegmentRepository(db)

            try:
                # 1. Phát tiến trình bắt đầu
                await session_repo.update_status(session_id, "PARSING", progress_percent=20)
                await broadcaster.emit(
                    session_id,
                    "progress_update",
                    {"step": "PARSING", "progress_percent": 20, "message": "Đang bóc tách cấu trúc bài báo..."},
                )

                # 2. Gọi trình bóc tách tương ứng
                if source_type in ("PDF", "ARXIV"):
                    parsed_doc = self.pdf_parser.parse(file_path, session_id)
                elif source_type == "DOCX":
                    parsed_doc = self.docx_parser.parse(file_path, session_id)
                else:
                    raise ValueError(f"Loại nguồn {source_type} không được hỗ trợ.")

                # 3. Cô lập công thức toán học và chuẩn bị dữ liệu phân đoạn
                await broadcaster.emit(
                    session_id,
                    "progress_update",
                    {"step": "PARSING", "progress_percent": 50, "message": "Đang cô lập công thức toán LaTeX & hình/bảng..."},
                )

                segments_data = []
                math_tokens_data = []
                current_math_idx = 1

                for block in parsed_doc.blocks:
                    # Cô lập công thức toán học trong nội dung block
                    masked_content, extracted_tokens = LaTeXIsolator.isolate_formulas(
                        block.content, start_index=current_math_idx
                    )
                    current_math_idx += len(extracted_tokens)

                    for token_info in extracted_tokens:
                        math_tokens_data.append({
                            "session_id": session_id,
                            "token_placeholder": token_info["token_placeholder"],
                            "raw_latex": token_info["raw_latex"],
                            "is_display_math": token_info["is_display_math"],
                        })

                    segments_data.append({
                        "session_id": session_id,
                        "order_index": block.order_index,
                        "segment_type": block.segment_type,
                        "original_content": masked_content,
                        # Ban đầu bản dịch gán bằng bản gốc (để xem được ngay song ngữ khi chưa dịch)
                        "translated_content": None,
                        "media_path": block.media_path,
                        "status": "PENDING",
                    })

                # 4. Lưu vào CSDL
                if math_tokens_data:
                    await segment_repo.bulk_create_math_tokens(math_tokens_data)
                if segments_data:
                    await segment_repo.bulk_create_segments(segments_data)

                # Cập nhật thông tin tiêu đề và hoàn tất bóc tách
                await session_repo.update_metadata(
                    session_id,
                    title=parsed_doc.title or "Untitled Scientific Paper",
                    authors="[]",
                    abstract=parsed_doc.abstract,
                )
                await session_repo.update_status(session_id, "PARSED", progress_percent=100)

                await broadcaster.emit(
                    session_id,
                    "progress_update",
                    {
                        "step": "PARSED",
                        "progress_percent": 100,
                        "message": f"Bóc tách hoàn tất! Đã trích xuất {len(segments_data)} phân đoạn và {len(math_tokens_data)} công thức toán. Bắt đầu dịch thuật...",
                    },
                )

                # 5. Tự động kích hoạt dịch thuật chuyên ngành IT/AI
                from app.services.translation.translation_service import TranslationService
                translation_service = TranslationService()
                await translation_service.translate_session(session_id)

            except Exception as e:
                logger.exception(f"[{session_id}] Lỗi trong tiến trình bóc tách bài báo: {e}")
                await session_repo.update_status(session_id, "FAILED")
                await broadcaster.emit(
                    session_id,
                    "error",
                    {"step": "FAILED", "message": f"Lỗi bóc tách tài liệu: {str(e)}"},
                )
