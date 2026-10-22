import asyncio
import gc
import re
import uuid
from pathlib import Path

import httpx
from fastapi import UploadFile

from app.core.config import settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.repositories.ocr_block_repository import OcrBlockRepository
from app.repositories.page_repository import PageRepository
from app.repositories.segment_repository import SegmentRepository
from app.repositories.session_repository import SessionRepository
from app.services.asset.page_asset_service import PageAssetService
from app.services.parser.docx_parser import DocxParser
from app.services.parser.indra_ocr_service import IndraOcrService
from app.services.parser.math_isolator import LaTeXIsolator
from app.services.parser.pdf_parser import PdfParser
from app.services.sse_broadcaster import broadcaster
from app.services.translation.gemini_translator import GeminiTranslator


class IngestionService:
    def __init__(self):
        self.pdf_parser = PdfParser()
        self.docx_parser = DocxParser()
        self.indra_ocr_service = IndraOcrService()
        self.page_asset_service = PageAssetService()
        self.gemini_translator = GeminiTranslator()

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

    async def save_uploaded_file(self, file: UploadFile) -> tuple[str, Path, int, str]:
        """Lưu tệp tải lên vào thư mục storage/raw/{session_id}/ và storage/raw_pdfs/."""
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

        # Sao lưu thêm vào raw_pdfs/{session_id}.pdf nếu là tệp PDF
        if source_type == "PDF":
            raw_pdf_path = settings.raw_pdfs_dir / f"{session_id}.pdf"
            with open(raw_pdf_path, "wb") as f:
                f.write(content)

        return session_id, target_path, file_size, source_type

    async def ingest_arxiv(self, arxiv_input: str) -> tuple[str, Path, int, str]:
        """Tải bài báo trực tiếp từ arXiv."""
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

            raw_pdf_path = settings.raw_pdfs_dir / f"{session_id}.pdf"
            with open(raw_pdf_path, "wb") as f:
                f.write(content)

        return session_id, target_path, file_size, "ARXIV"

    async def process_paper_background(self, session_id: str, file_path: Path, source_type: str):
        """
        Tiến trình chạy nền v3.1:
        1. Phân tích bố cục 2 cột bằng Indra OCR & chuẩn hóa tọa độ [0.0 .. 1.0].
        2. Kết xuất ảnh toàn trang Layer 0 (200 DPI) & crop hình vẽ bằng PyMuPDF.
        3. Dịch toàn văn trong 1 lần gọi (Gemini Single-Call với max_tokens=65536).
        4. Lưu trữ cấu trúc Canvas vào paper_pages và ocr_blocks.
        """
        async with AsyncSessionLocal() as db:
            session_repo = SessionRepository(db)
            page_repo = PageRepository(db)
            block_repo = OcrBlockRepository(db)
            segment_repo = SegmentRepository(db)

            try:
                # -------------------------------------------------------------
                # Giai đoạn 1: OCR_PROCESSING
                # -------------------------------------------------------------
                await session_repo.update_status(session_id, "OCR_PROCESSING", progress_percent=15)
                await broadcaster.emit(
                    session_id,
                    "progress_update",
                    {
                        "status": "OCR_PROCESSING",
                        "step": "OCR_PROCESSING",
                        "progress_percent": 15,
                        "message": "Đang phân tích bố cục 2 cột & thứ tự đọc bằng Indra OCR...",
                    },
                )

                if source_type in ("PDF", "ARXIV"):
                    # 1. Chạy Indra OCR & chuẩn hóa tọa độ
                    parsed_doc = await asyncio.to_thread(self.indra_ocr_service.parse_pdf, file_path)

                    await broadcaster.emit(
                        session_id,
                        "progress_update",
                        {
                            "status": "OCR_PROCESSING",
                            "step": "OCR_PROCESSING",
                            "progress_percent": 30,
                            "message": f"Đang kết xuất ảnh nền Layer 0 ({parsed_doc.total_pages} trang)...",
                        },
                    )

                    # 2. Kết xuất Layer 0 và Crop figures bằng PyMuPDF
                    await asyncio.to_thread(
                        self.page_asset_service.render_page_snapshots,
                        session_id,
                        file_path,
                        parsed_doc.pages,
                    )
                    await asyncio.to_thread(
                        self.page_asset_service.crop_figure_blocks,
                        session_id,
                        file_path,
                        parsed_doc.pages,
                    )

                    # 3. Lưu dữ liệu PaperPages và OcrBlocks vào SQLite
                    pages_to_create = []
                    blocks_to_create = []
                    page_id_map = {}

                    for p in parsed_doc.pages:
                        page_uid = str(uuid.uuid4())
                        page_id_map[p.page_number] = page_uid
                        pages_to_create.append({
                            "id": page_uid,
                            "session_id": session_id,
                            "page_number": p.page_number,
                            "width_pt": p.width_pt,
                            "height_pt": p.height_pt,
                            "ocr_rotation": p.rotation,
                            "ocr_skew": p.skew,
                            "page_image_path": p.page_image_path,
                        })

                        for b in p.blocks:
                            blocks_to_create.append({
                                "id": str(uuid.uuid4()),
                                "session_id": session_id,
                                "page_id": page_uid,
                                "page_number": p.page_number,
                                "block_code": b.block_code,
                                "reading_order": b.reading_order,
                                "label": b.label,
                                "bbox_x0": b.bbox_norm[0],
                                "bbox_y0": b.bbox_norm[1],
                                "bbox_x1": b.bbox_norm[2],
                                "bbox_y1": b.bbox_norm[3],
                                "is_translatable": b.is_translatable,
                                "original_text": b.text,
                                "translated_text": None,
                                "figure_image_path": b.figure_image_path,
                                "is_user_edited": False,
                            })

                    if pages_to_create:
                        await page_repo.bulk_create(pages_to_create)
                    if blocks_to_create:
                        await block_repo.bulk_create(blocks_to_create)

                    # Lưu thêm segments & math tokens để tương thích ngược 100% với Dual-Pane UI và các bài test cũ
                    segments_data = []
                    math_tokens_data = []
                    current_math_idx = 1

                    for idx, b in enumerate(parsed_doc.blocks):
                        masked_text, extracted_tokens = LaTeXIsolator.isolate_formulas(
                            b.text, start_index=current_math_idx
                        )
                        current_math_idx += len(extracted_tokens)

                        for token_info in extracted_tokens:
                            math_tokens_data.append({
                                "session_id": session_id,
                                "token_placeholder": token_info["token_placeholder"],
                                "raw_latex": token_info["raw_latex"],
                                "is_display_math": token_info["is_display_math"],
                            })

                        seg_type = "PARAGRAPH"
                        if b.label == "title":
                            seg_type = "TITLE"
                        elif b.label == "section header":
                            seg_type = "HEADING"
                        elif b.label == "table":
                            seg_type = "TABLE"
                        elif b.label == "figure":
                            seg_type = "FIGURE"

                        segments_data.append({
                            "session_id": session_id,
                            "order_index": idx,
                            "segment_type": seg_type,
                            "original_content": masked_text,
                            "translated_content": None,
                            "media_path": b.figure_image_path,
                            "status": "PENDING",
                        })

                    if math_tokens_data:
                        await segment_repo.bulk_create_math_tokens(math_tokens_data)
                    if segments_data:
                        await segment_repo.bulk_create_segments(segments_data)

                    # Cập nhật metadata phiên
                    await session_repo.update_metadata(
                        session_id,
                        title=parsed_doc.title or "Untitled Scientific Paper",
                        authors="[]",
                        abstract=None,
                    )
                    # Cập nhật total_pages
                    session_record = await session_repo.get_by_id(session_id)
                    if session_record:
                        session_record.total_pages = parsed_doc.total_pages
                        session_record.pdf_path = str(file_path)
                        await db.commit()

                elif source_type == "DOCX":
                    # Xử lý tệp DOCX (giữ nguyên quy trình bóc tách DOCX)
                    parsed_docx = self.docx_parser.parse(file_path, session_id)
                    segments_data = []
                    math_tokens_data = []
                    current_math_idx = 1

                    for block in parsed_docx.blocks:
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
                            "translated_content": None,
                            "media_path": block.media_path,
                            "status": "PENDING",
                        })

                    if math_tokens_data:
                        await segment_repo.bulk_create_math_tokens(math_tokens_data)
                    if segments_data:
                        await segment_repo.bulk_create_segments(segments_data)

                    await session_repo.update_metadata(
                        session_id,
                        title=parsed_docx.title or "Untitled Scientific Paper",
                        authors="[]",
                        abstract=parsed_docx.abstract,
                    )

                # -------------------------------------------------------------
                # Giai đoạn 2: TRANSLATING (Gemini Single-Call)
                # -------------------------------------------------------------
                await session_repo.update_status(session_id, "TRANSLATING", progress_percent=50)
                await broadcaster.emit(
                    session_id,
                    "progress_update",
                    {
                        "status": "TRANSLATING",
                        "step": "TRANSLATING",
                        "progress_percent": 50,
                        "message": "Đang dịch toàn bộ bài báo trong 1 lần gọi qua Google Gemini API...",
                    },
                )

                if source_type in ("PDF", "ARXIV"):
                    async def on_translation_progress(current: int, total: int, msg: str) -> None:
                        pct = 50 + int((current / max(1, total)) * 45)  # 50% -> 95%
                        await session_repo.update_status(session_id, "TRANSLATING", progress_percent=pct)
                        await broadcaster.emit(
                            session_id,
                            "progress_update",
                            {
                                "status": "TRANSLATING",
                                "step": "TRANSLATING",
                                "progress_percent": pct,
                                "message": msg,
                                "current": current,
                                "total": total,
                            },
                        )

                    db_blocks = await block_repo.get_by_session_id(session_id)
                    translated_map = await self.gemini_translator.translate_blocks(
                        db_blocks, progress_callback=on_translation_progress
                    )

                    # Ánh xạ bản dịch vào ocr_blocks
                    block_updates = []
                    for b in db_blocks:
                        if b.block_code in translated_map:
                            b.translated_text = translated_map[b.block_code]
                            block_updates.append({"id": b.id, "translated_text": b.translated_text})
                    if block_updates:
                        await block_repo.bulk_update_translations(block_updates)

                    # Đồng bộ sang segments cho Dual-Pane UI
                    db_segments = await segment_repo.get_by_session_id(session_id)
                    for idx, seg in enumerate(db_segments):
                        if idx < len(db_blocks):
                            seg_trans = db_blocks[idx].translated_text
                            if seg_trans:
                                await segment_repo.update_translation(seg.id, seg_trans)

                elif source_type == "DOCX":
                    from app.services.translation.translation_service import TranslationService
                    translation_service = TranslationService()
                    await translation_service.translate_session(session_id)

                # -------------------------------------------------------------
                # Giai đoạn 3: COMPLETED
                # -------------------------------------------------------------
                await session_repo.update_status(session_id, "COMPLETED", progress_percent=100)
                await broadcaster.emit(
                    session_id,
                    "completed",
                    {
                        "status": "COMPLETED",
                        "step": "COMPLETED",
                        "progress_percent": 100,
                        "message": "Hoàn tất! Sẵn sàng tái hiện bài báo trên HTML Canvas.",
                    },
                )
                logger.info(f"[{session_id}] Toàn bộ pipeline v3.1 hoàn tất 100%.")

            except Exception as e:
                logger.exception(f"[{session_id}] Lỗi trong tiến trình xử lý bài báo: {e}")
                await session_repo.update_status(session_id, "FAILED")
                session_rec = await session_repo.get_by_id(session_id)
                if session_rec:
                    session_rec.error_message = str(e)
                    await db.commit()
                await broadcaster.emit(
                    session_id,
                    "error",
                    {"status": "FAILED", "step": "FAILED", "message": f"Lỗi xử lý tài liệu: {str(e)}"},
                )
            finally:
                # Thu hồi toàn bộ tài nguyên phần cứng (ONNX InferenceSessions, ThreadPool, memory buffers)
                self.indra_ocr_service.unload()
                gc.collect()
