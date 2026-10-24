import asyncio
from collections.abc import Callable
from typing import Any

from app.core.config import settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.ocr_block import OcrBlockModel
from app.repositories.ocr_block_repository import OcrBlockRepository
from app.repositories.segment_repository import SegmentRepository
from app.repositories.session_repository import SessionRepository
from app.services.sse_broadcaster import broadcaster
from app.services.translation.adaptive_batcher import AdaptiveBatcher
from app.services.translation.gemini_translator import GeminiTranslator
from app.services.translation.llama_client_service import LlamaInternalClient
from app.services.translation.llama_server_manager import LlamaServerManager
from app.services.translation.translator import BaseTranslator


class TranslationService:
    """
    Dịch vụ điều phối dịch thuật hỗ trợ hai chế độ:
    1. Local-First Standalone Serving: Quản lý tiến trình độc lập llama.cpp server
       chạy mô hình Gemma-4-E2B Q4_K_XL với tối ưu 4 P-cores trên Intel Core i5-13500H,
       phân lô 2000 - 2500 từ tiếng Anh, giao tiếp qua Python Client mạng nội bộ (127.0.0.1:8081),
       dự phòng output tiếng Việt nở 2.0x - 2.5x và giới hạn trần cứng <= 8.0 GB RAM.
    2. Cloud Option: Dịch Single-Call qua Google Gemini hoặc các mô hình OpenAI-Compatible.
    """

    def __init__(self, translator: BaseTranslator | None = None):
        self.raw_translator = translator
        self.gemini_translator = GeminiTranslator(translator=translator)
        self.batcher = AdaptiveBatcher()
        self.llama_client = LlamaInternalClient()

    async def _translate_with_local_llm(
        self,
        blocks: list[OcrBlockModel],
        progress_callback: Callable[[int, int, str], Any] | None = None,
    ) -> dict[str, str]:
        """Thực thi dịch thuật cục bộ qua Standalone llama.cpp Server bằng Python Client nội bộ."""
        # Áp dụng bộ lọc thông minh loại bỏ References, header/footer, figure
        self.gemini_translator.apply_smart_filter(blocks)

        translatable_blocks = [
            b for b in blocks if b.is_translatable and (b.original_text or "").strip()
        ]
        translated_map: dict[str, str] = {}

        # Gán nguyên văn cho các khối không dịch
        for b in blocks:
            if not b.is_translatable:
                translated_map[b.block_code] = b.original_text or ""

        if not translatable_blocks:
            return translated_map

        batches = self.batcher.create_batches(translatable_blocks)
        total_blocks = len(translatable_blocks)
        processed_blocks = 0

        # Đảm bảo Standalone llama.cpp Server đang chạy và phản hồi
        server_mgr = LlamaServerManager.get_instance()
        if not server_mgr.is_running or not await server_mgr.is_healthy_async():
            if progress_callback:
                res = progress_callback(0, total_blocks, f"Đang khởi động Standalone llama.cpp Server ({settings.LLM_MODEL_NAME})...")
                if asyncio.iscoroutine(res):
                    await res
            await server_mgr.ensure_server_running()

        for batch_idx, batch in enumerate(batches):
            b_start_idx = processed_blocks + 1
            b_end_idx = processed_blocks + len(batch)

            if progress_callback:
                msg = f"Đang suy luận qua Gemma-4-E2B Local Server: Lô {batch_idx + 1}/{len(batches)} (khối {b_start_idx}-{b_end_idx}/{total_blocks})..."
                res = progress_callback(processed_blocks, total_blocks, msg)
                if asyncio.iscoroutine(res):
                    await res

            messages = self.batcher.build_prompt_messages(batch)
            est_tokens = sum(self.batcher.estimate_tokens(b.original_text or "") for b in batch)
            logger.info(
                f"Bắt đầu suy luận Lô {batch_idx + 1}/{len(batches)}: {len(batch)} khối (~{est_tokens} tokens)..."
            )

            import time
            t0 = time.time()

            max_out_tokens = getattr(settings, "LLM_LOCAL_MAX_OUTPUT_TOKENS", 10240)
            response = await self.llama_client.create_chat_completion(
                messages=messages,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=max_out_tokens,
            )
            elapsed = time.time() - t0
            logger.info(
                f"Hoàn tất suy luận Lô {batch_idx + 1}/{len(batches)} trong {elapsed:.2f}s."
            )

            batch_map, missing_blocks = self.batcher.parse_response(response, batch)

            # Kích hoạt Fallback dịch đơn lẻ cho các khối bị sót mã
            if missing_blocks:
                logger.warning(
                    f"Batch {batch_idx + 1} phát hiện {len(missing_blocks)} khối bị sót mã. Kích hoạt Fallback đơn lẻ..."
                )
                for fb_idx, missing_b in enumerate(missing_blocks):
                    if progress_callback:
                        fb_msg = f"Đang hiệu đính riêng khối [[{missing_b.block_code}]] ({fb_idx + 1}/{len(missing_blocks)})..."
                        res = progress_callback(processed_blocks, total_blocks, fb_msg)
                        if asyncio.iscoroutine(res):
                            await res

                    fb_messages = self.batcher.build_single_fallback_messages(missing_b)
                    fb_resp = await self.llama_client.create_chat_completion(
                        messages=fb_messages,
                        temperature=settings.LLM_TEMPERATURE,
                        max_tokens=2048,
                    )
                    fb_map, _ = self.batcher.parse_response(fb_resp, [missing_b])
                    if missing_b.block_code in fb_map:
                        batch_map[missing_b.block_code] = fb_map[missing_b.block_code]
                    else:
                        batch_map[missing_b.block_code] = fb_resp.strip() or missing_b.original_text

            translated_map.update(batch_map)
            processed_blocks += len(batch)

            if progress_callback:
                msg = f"Đã hoàn tất Lô {batch_idx + 1}/{len(batches)} ({processed_blocks}/{total_blocks} khối)..."
                res = progress_callback(processed_blocks, total_blocks, msg)
                if asyncio.iscoroutine(res):
                    await res

        return translated_map

    async def translate_session(self, session_id: str):
        """Tiến trình dịch thuật toàn bộ bài báo theo cơ chế Local-First hoặc Cloud."""
        is_local = (
            self.raw_translator is None
            and settings.LLM_PROVIDER.lower() in ("llama_cpp", "local", "gemma", "qwen")
        )
        engine_label = f"Local LLM ({settings.LLM_MODEL_NAME})" if is_local else "Cloud API (Gemini/OpenAI)"
        logger.info(f"[{session_id}] Bắt đầu tiến trình dịch thuật với {engine_label}...")

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
                    "phase": "loading_llm" if is_local else "preparing_prompt",
                    "progress_percent": 10,
                    "active_engine": "local_llm" if is_local else "cloud_gemini",
                    "model_name": settings.LLM_MODEL_NAME if is_local else settings.LLM_MODEL,
                    "message": f"Khởi động tiến trình dịch thuật với {engine_label}...",
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
                        "phase": "translating_local" if is_local else "translating_cloud",
                        "progress_percent": pct,
                        "active_engine": "local_llm" if is_local else "cloud_gemini",
                        "model_name": settings.LLM_MODEL_NAME if is_local else settings.LLM_MODEL,
                        "message": msg,
                        "current": current,
                        "total": total,
                    },
                )

            try:
                blocks_to_translate = list(db_blocks)
                if not blocks_to_translate and db_segments:
                    # Trường hợp bài báo DOCX không có ocr_blocks, bọc segments thành OcrBlockModel tạm
                    blocks_to_translate = [
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

                if is_local:
                    translated_map = await self._translate_with_local_llm(
                        blocks_to_translate, progress_callback=on_progress
                    )
                else:
                    translated_map = await self.gemini_translator.translate_blocks(
                        blocks_to_translate, progress_callback=on_progress
                    )

                # Lưu bản dịch vào ocr_blocks nếu có
                if db_blocks:
                    block_updates = []
                    for b in db_blocks:
                        if b.block_code in translated_map:
                            block_updates.append({
                                "id": b.id,
                                "translated_text": translated_map[b.block_code],
                            })
                    if block_updates:
                        await block_repo.bulk_update_translations(block_updates)

                # Đồng bộ bản dịch vào paper_segments
                if db_segments:
                    for idx, seg in enumerate(db_segments):
                        code = db_blocks[idx].block_code if (db_blocks and idx < len(db_blocks)) else f"BLK_{seg.order_index + 1:04d}"
                        seg_trans = translated_map.get(code)
                        if seg_trans:
                            await segment_repo.update_translation(seg.id, seg_trans)

                # Hoàn tất dịch thuật 100%
                await session_repo.update_status(session_id, "COMPLETED", progress_percent=100)
                await broadcaster.emit(
                    session_id,
                    "completed",
                    {
                        "step": "COMPLETED",
                        "phase": "completed",
                        "progress_percent": 100,
                        "active_engine": "local_llm" if is_local else "cloud_gemini",
                        "model_name": settings.LLM_MODEL_NAME if is_local else settings.LLM_MODEL,
                        "message": "Dịch thuật hoàn tất thành công! Sẵn sàng xem trên Canvas Viewer.",
                    },
                )
                logger.info(f"[{session_id}] Dịch thuật {engine_label} hoàn tất 100%.")

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
                        "phase": "failed",
                        "message": f"Dịch thuật thất bại: {e}",
                    },
                )
