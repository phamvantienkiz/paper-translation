from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.ocr_block import OcrBlockModel
from app.repositories.ocr_block_repository import OcrBlockRepository
from app.repositories.segment_repository import SegmentRepository
from app.repositories.session_repository import SessionRepository
from app.services.sse_broadcaster import broadcaster
from app.services.translation.gemini_translator import GeminiTranslator
from app.services.translation.translator import BaseTranslator


class TranslationService:
    def __init__(self, translator: BaseTranslator | None = None):
        self.raw_translator = translator
        self.gemini_translator = GeminiTranslator(translator=translator)

    async def translate_session(self, session_id: str):
        """Tiến trình dịch thuật toàn bộ bài báo trong 1 lần gọi duy nhất (Single-Call)."""
        logger.info(f"[{session_id}] Bắt đầu tiến trình dịch thuật Single-Call...")
        async with AsyncSessionLocal() as db:
            session_repo = SessionRepository(db)
            block_repo = OcrBlockRepository(db)
            segment_repo = SegmentRepository(db)

            session = await session_repo.get_by_id(session_id)
            if not session:
                logger.error(f"[{session_id}] Không tìm thấy phiên để dịch thuật.")
                return

            db_blocks = await block_repo.get_by_session_id(session_id)
            db_segments = await segment_repo.get_by_session_id(session_id)

            if not db_blocks and not db_segments:
                logger.warning(f"[{session_id}] Phiên không có dữ liệu để dịch.")
                await session_repo.update_status(session_id, "COMPLETED", progress_percent=100)
                return

            await session_repo.update_status(session_id, "TRANSLATING", progress_percent=10)
            await broadcaster.emit(
                session_id,
                "progress_update",
                {
                    "step": "TRANSLATING",
                    "progress_percent": 10,
                    "message": "Đang chuẩn bị toàn văn bài báo để dịch trong 1 lần gọi duy nhất...",
                },
            )

            async def on_progress(current: int, total: int, msg: str) -> None:
                pct = 10 + int((current / max(1, total)) * 85)
                await session_repo.update_status(session_id, "TRANSLATING", progress_percent=pct)
                await broadcaster.emit(
                    session_id,
                    "progress_update",
                    {
                        "step": "TRANSLATING",
                        "progress_percent": pct,
                        "message": msg,
                        "current": current,
                        "total": total,
                    },
                )

            try:
                if db_blocks:
                    # Trường hợp bài báo PDF/ARXIV có các khối OCR
                    translated_map = await self.gemini_translator.translate_blocks(
                        db_blocks, progress_callback=on_progress
                    )

                    # Lưu bản dịch vào ocr_blocks
                    block_updates = []
                    for b in db_blocks:
                        if b.block_code in translated_map:
                            block_updates.append({
                                "id": b.id,
                                "translated_text": translated_map[b.block_code],
                            })
                    if block_updates:
                        await block_repo.bulk_update_translations(block_updates)

                    # Đồng bộ sang segments cho Dual-Pane UI (không đọc thuộc tính expired của db_blocks)
                    for idx, seg in enumerate(db_segments):
                        if idx < len(db_blocks):
                            code = db_blocks[idx].block_code
                            seg_trans = translated_map.get(code)
                            if seg_trans:
                                await segment_repo.update_translation(seg.id, seg_trans)

                else:
                    # Trường hợp bài báo DOCX không có ocr_blocks, bọc segments thành OcrBlockModel tạm thời
                    temp_blocks = [
                        OcrBlockModel(
                            id=seg.id,
                            session_id=session_id,
                            page_id="",
                            page_number=1,
                            block_code=f"BLK_{seg.order_index:04d}",
                            reading_order=seg.order_index,
                            label="text",
                            bbox_x0=0.0,
                            bbox_y0=0.0,
                            bbox_x1=1.0,
                            bbox_y1=1.0,
                            is_translatable=True,
                            original_text=seg.original_content,
                        )
                        for seg in db_segments
                        if not (seg.is_user_edited and seg.translated_content)
                    ]

                    translated_map = await self.gemini_translator.translate_blocks(
                        temp_blocks, progress_callback=on_progress
                    )

                    for seg in db_segments:
                        code = f"BLK_{seg.order_index:04d}"
                        if code in translated_map:
                            await segment_repo.update_translation(seg.id, translated_map[code])

                # Hoàn tất dịch thuật 100%
                await session_repo.update_status(session_id, "COMPLETED", progress_percent=100)
                await broadcaster.emit(
                    session_id,
                    "completed",
                    {
                        "step": "COMPLETED",
                        "progress_percent": 100,
                        "message": "Dịch thuật toàn văn hoàn tất thành công trong 1 lần gọi!",
                    },
                )
                logger.info(f"[{session_id}] Dịch thuật Single-Call hoàn tất 100%.")

            except Exception as e:
                logger.exception(f"[{session_id}] Lỗi trong tiến trình dịch thuật: {e}")
                await session_repo.update_status(session_id, "FAILED")
                session_rec = await session_repo.get_by_id(session_id)
                if session_rec:
                    session_rec.error_message = str(e)
                    await db.commit()
                await broadcaster.emit(
                    session_id,
                    "failed",
                    {
                        "step": "FAILED",
                        "message": f"Dịch thuật thất bại: {e}",
                    },
                )
