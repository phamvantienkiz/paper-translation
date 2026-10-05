import asyncio
from typing import Optional
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.repositories.segment_repository import SegmentRepository
from app.repositories.session_repository import SessionRepository
from app.services.sse_broadcaster import broadcaster
from app.services.translation.translator import BaseTranslator, TranslationFactory


class TranslationService:
    def __init__(self, translator: Optional[BaseTranslator] = None):
        self.translator = translator or TranslationFactory.get_translator()

    async def translate_session(self, session_id: str):
        """Tiến trình dịch thuật toàn bộ phân đoạn của phiên bài báo trong nền."""
        logger.info(f"[{session_id}] Bắt đầu tiến trình dịch thuật...")
        async with AsyncSessionLocal() as db:
            session_repo = SessionRepository(db)
            segment_repo = SegmentRepository(db)

            session = await session_repo.get_by_id(session_id)
            if not session:
                logger.error(f"[{session_id}] Không tìm thấy phiên để dịch thuật.")
                return

            segments = await segment_repo.get_by_session_id(session_id)
            total_segments = len(segments)
            if total_segments == 0:
                logger.warning(f"[{session_id}] Phiên không có phân đoạn nào để dịch.")
                await session_repo.update_status(session_id, "COMPLETED", progress_percent=100)
                return

            await session_repo.update_status(session_id, "TRANSLATING", progress_percent=0)
            await broadcaster.emit(
                session_id,
                "progress_update",
                {
                    "step": "TRANSLATING",
                    "progress_percent": 0,
                    "message": "Bắt đầu dịch thuật các phân đoạn...",
                    "total_segments": total_segments,
                    "translated_count": 0,
                },
            )

            completed_count = 0
            for seg in segments:
                # Nếu người dùng đã chỉnh sửa thủ công thì giữ nguyên, không ghi đè
                if seg.is_user_edited and seg.translated_content:
                    completed_count += 1
                    continue

                try:
                    translated = await self.translator.translate_text(seg.original_content)
                    await segment_repo.update_translation(seg.id, translated)
                except Exception as e:
                    logger.error(f"[{session_id}] Lỗi khi dịch phân đoạn #{seg.order_index}: {e}")
                    # Gán bằng bản gốc nếu lỗi để không gián đoạn luồng
                    await segment_repo.update_translation(seg.id, seg.original_content)

                completed_count += 1
                progress = int((completed_count / total_segments) * 100)

                # Cập nhật tiến độ mỗi phân đoạn hoặc mỗi 3 phân đoạn để tối ưu DB
                if completed_count % 3 == 0 or completed_count == total_segments:
                    await session_repo.update_status(session_id, "TRANSLATING", progress_percent=progress)
                    await broadcaster.emit(
                        session_id,
                        "progress_update",
                        {
                            "step": "TRANSLATING",
                            "progress_percent": progress,
                            "message": f"Đang dịch: {completed_count}/{total_segments} phân đoạn ({progress}%)...",
                            "total_segments": total_segments,
                            "translated_count": completed_count,
                        },
                    )

                # Giãn cách một khoảng rất ngắn để nhường event loop
                await asyncio.sleep(0.01)

            # Hoàn tất dịch thuật
            await session_repo.update_status(session_id, "COMPLETED", progress_percent=100)
            await broadcaster.emit(
                session_id,
                "completed",
                {
                    "step": "COMPLETED",
                    "progress_percent": 100,
                    "message": f"Dịch thuật hoàn tất thành công! ({total_segments}/{total_segments} phân đoạn).",
                    "total_segments": total_segments,
                    "translated_count": total_segments,
                },
            )
            logger.info(f"[{session_id}] Dịch thuật hoàn tất 100%.")
